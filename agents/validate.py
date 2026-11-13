"""Stage 4 - Validate agent.

For every executable model: performance, stability and fairness on the hold-out
test set, a rule-based findings list with an overall RAG rating, and an HTML
validation report.

All numbers come from validation/*.py (deterministic). The only AI-written part
(optional) is the "Commentary" paragraph, which is labelled as such and is given
the computed numbers to quote.
"""
from __future__ import annotations

import base64
import io
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402

from agents import discover, document, redevelop  # noqa: E402
from core import config, data, llm, scoring, state  # noqa: E402
from validation import fairness, metrics, stability  # noqa: E402

FAIRNESS_DIMENSIONS = {
    "age_band": "Age band (protected characteristic)",
    "foreign_worker": "Foreign worker (proxy for nationality)",
    "personal_status_sex": "Personal status & sex (sex NOT fully recoverable - see note)",
}
SEX_NOTE = ("The dataset combines sex and marital status in one field and codes "
            "'female : non-single' and 'male : single' identically, so sex cannot be fully "
            "recovered. Results by this field are shown for transparency only.")


def _merge(df: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(scores[["customer_id", "pd"]], on="customer_id", how="inner")
    if len(out) != len(df):
        raise ValueError("Scores do not cover every record.")
    out["age_band"] = data.age_band(out["age"])
    return out


def findings_for(model: dict, perf_test: dict, perf_train: dict, stab: dict,
                 fair: dict, parity_report: dict | None) -> list[dict]:
    f = []

    def add(sev, area, text):
        f.append({"severity": sev, "area": area, "finding": text})

    if perf_test["auc"] < config.AUC_MIN_ACCEPTABLE:
        add("High", "Performance", f"Test AUC {perf_test['auc']:.3f} is below the {config.AUC_MIN_ACCEPTABLE} minimum.")
    gap = perf_train["auc"] - perf_test["auc"]
    if gap > 0.10:
        add("Medium", "Performance", f"Train/test AUC gap of {gap:.3f} suggests overfitting.")
    hl = perf_test["hosmer_lemeshow"]
    if hl["p_value"] < 0.05:
        p_txt = "< 0.001" if hl["p_value"] < 0.001 else f"{hl['p_value']:.3f}"
        add("Medium", "Calibration", f"Hosmer-Lemeshow p-value {p_txt} (below 0.05): "
            "predicted PDs do not match observed default rates.")
    ratio = perf_test["mean_predicted_pd"] / max(perf_test["default_rate"], 1e-9)
    if abs(ratio - 1) > 0.20:
        add("Medium", "Calibration", f"Mean predicted PD is {ratio:.2f}x the observed default rate.")
    s = stab["score_psi"]
    if s >= config.PSI_WARN:
        add("High" if s >= config.PSI_ALERT else "Medium", "Stability",
            f"Score PSI between development and test samples is {s:.3f}.")
    for r in stab["feature_psi"]:
        if r["status"] != "OK":
            add("Low", "Stability", f"Input '{r['feature']}' PSI {r['psi']:.3f} ({r['status']}).")
    for dim, res in fair.items():
        for g in res["groups"]:
            if g["flag_disparate_impact"]:
                add("Medium" if not g["small_sample"] else "Low", "Fairness",
                    f"{FAIRNESS_DIMENSIONS[dim].split(' (')[0]} = '{g['group']}': approval-rate ratio "
                    f"{g['disparate_impact_ratio']:.2f} vs '{res['reference_group']}' (screen {config.DISPARATE_IMPACT_MIN})"
                    + (" - small group, low confidence." if g["small_sample"] else "."))
            if g["flag_equal_opportunity"]:
                add("Medium" if not g["small_sample"] else "Low", "Fairness",
                    f"{FAIRNESS_DIMENSIONS[dim].split(' (')[0]} = '{g['group']}': good customers approved "
                    f"{g['equal_opportunity_gap']:.0%} less often than in '{res['reference_group']}'.")
    used_protected = [v for v in model["input_features"] if v in document.PROTECTED_OR_PROXY]
    if used_protected:
        add("Medium", "Fairness", f"Model uses {', '.join(used_protected)} directly as input(s); "
            "needs a documented business justification.")
    if model.get("documentation_stale"):
        add("Low", "Governance", f"Documentation is {model['documentation_age_years']} years old.")
    if parity_report is not None:
        if parity_report["parity_passed"] and parity_report["genuine_migration"]:
            add("Info", "Redevelopment", "Python redevelopment reproduces the R model within "
                f"{config.PARITY_TOLERANCE:g} (max test PD difference "
                f"{parity_report['test_predictions']['max_abs_diff']:.1e}).")
        elif not parity_report["parity_passed"]:
            add("High", "Redevelopment", "Python redevelopment does NOT reproduce the legacy model.")
    return f


def rag(findings: list[dict]) -> str:
    sev = {x["severity"] for x in findings}
    return "RED" if "High" in sev else "AMBER" if "Medium" in sev else "GREEN"


def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def charts(df_test: pd.DataFrame, perf: dict, fair: dict) -> dict:
    out = {}
    roc = metrics.roc_points(df_test[config.TARGET], df_test["pd"])
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.plot(roc["fpr"], roc["tpr"], color="#0b3d6b", lw=2, label=f"AUC = {perf['auc']:.3f}")
    ax.plot([0, 1], [0, 1], ls="--", color="#999")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve (test)"); ax.legend(loc="lower right")
    out["roc"] = _png(fig)

    cal = pd.DataFrame(perf["calibration_table"])
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.plot(cal["predicted_pd"], cal["observed_dr"], "o-", color="#0b3d6b", label="Deciles")
    lim = max(cal["predicted_pd"].max(), cal["observed_dr"].max()) * 1.05
    ax.plot([0, lim], [0, lim], ls="--", color="#999", label="Perfect calibration")
    ax.set_xlabel("Mean predicted PD"); ax.set_ylabel("Observed default rate")
    ax.set_title("Calibration (test)"); ax.legend(loc="upper left")
    out["calibration"] = _png(fig)

    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    for y, colr, lab in [(0, "#2e7d32", "Good"), (1, "#c62828", "Bad")]:
        ax.hist(df_test.loc[df_test[config.TARGET] == y, "pd"], bins=20, alpha=0.6, color=colr, label=lab)
    ax.axvline(config.DECISION_THRESHOLD, color="#333", ls=":", label="Cut-off")
    ax.set_xlabel("Predicted PD"); ax.set_ylabel("Applicants"); ax.set_title("Score distribution (test)")
    ax.legend()
    out["distribution"] = _png(fig)

    fig, axes = plt.subplots(1, len(fair), figsize=(4.0 * len(fair), 3.4))
    for ax, (dim, res) in zip(np.atleast_1d(axes), fair.items()):
        g = pd.DataFrame(res["groups"])
        ax.barh(g["group"], g["approval_rate"], color=["#c62828" if x else "#0b3d6b" for x in g["flag_disparate_impact"]])
        ax.set_xlim(0, 1); ax.set_title(dim.replace("_", " ")); ax.set_xlabel("Approval rate")
        ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    out["fairness"] = _png(fig)
    return out


def commentary(model: dict, result: dict) -> dict:
    facts = {
        "model": model["model_name"], "methodology": model["methodology"],
        "rag": result["rag_rating"],
        "test_auc": round(result["performance"]["test"]["auc"], 3),
        "test_gini": round(result["performance"]["test"]["gini"], 3),
        "test_ks": round(result["performance"]["test"]["ks"], 3),
        "score_psi": round(result["stability"]["score_psi"], 3),
        "findings": [f"[{x['severity']}] {x['finding']}" for x in result["findings"]],
    }
    res = llm.generate("Write a 4-6 sentence validation commentary for a model risk committee, "
                       "quoting only these computed results. End with a recommended next step.\n"
                       + json.dumps(facts, indent=1), max_tokens=500)
    if res:
        return {"source": f"ai_generated ({res['model']})", "text": res["text"]}
    n_high = sum(x["severity"] == "High" for x in result["findings"])
    n_med = sum(x["severity"] == "Medium" for x in result["findings"])
    text = (f"{model['model_name']} achieves a test AUC of {facts['test_auc']} (Gini {facts['test_gini']}, "
            f"KS {facts['test_ks']}) with a score PSI of {facts['score_psi']} between development and test "
            f"samples. The automated checks raised {n_high} high and {n_med} medium findings, giving an "
            f"overall {facts['rag']} rating. "
            + ("Recommended next step: remediate the high-severity findings before the model is used for decisions."
               if n_high else "Recommended next step: an independent validator reviews the medium findings, "
               "in particular fairness and calibration, and records a decision."))
    return {"source": "rule_based (template)", "text": text}


def validate_model(model: dict, env: Environment) -> dict:
    mid = model["model_id"]
    train, test = data.load_split()
    s_train, s_test = scoring.stored_scores(mid, "train"), scoring.stored_scores(mid, "test")
    if s_train is None or s_test is None:
        return {"model_id": mid, "validated": False,
                "reason": "No executable model outputs (e.g. SAS documentation-only)."}
    df_train, df_test = _merge(train, s_train), _merge(test, s_test)

    perf_test = metrics.performance_summary(df_test[config.TARGET], df_test["pd"])
    perf_train = metrics.performance_summary(df_train[config.TARGET], df_train["pd"])
    feats = model["input_features"]
    stab = {
        "reference": "development (train) sample", "comparison": "hold-out (test) sample",
        "score_psi": stability.psi_numeric(df_train["pd"], df_test["pd"]),
        "feature_psi": stability.feature_psi_table(
            df_train, df_test, [f for f in feats if f in config.NUMERIC_FEATURES],
            [f for f in feats if f in config.CATEGORICAL_FEATURES]),
    }
    stab["score_psi_status"] = stability.psi_status(stab["score_psi"])
    fair = {dim: fairness.group_metrics(df_test[config.TARGET], df_test["pd"], df_test[dim])
            for dim in FAIRNESS_DIMENSIONS}
    parity_report = redevelop.load_parity(mid)
    finds = findings_for(model, perf_test, perf_train, stab, fair, parity_report)

    result = {
        "model_id": mid, "model_name": model["model_name"], "validated": True,
        "generated_at": state.now(),
        "scores_source": {"train": s_train.attrs["source_file"], "test": s_test.attrs["source_file"]},
        "decision_threshold": config.DECISION_THRESHOLD,
        "performance": {"test": perf_test, "train": perf_train},
        "stability": stab, "fairness": fair, "fairness_notes": {"personal_status_sex": SEX_NOTE},
        "findings": finds, "rag_rating": rag(finds),
        "parity": parity_report and {k: parity_report[k] for k in ["legacy_mode", "verdict", "parity_passed"]},
    }
    result["commentary"] = commentary(model, result)
    (config.REPORTS_DIR / f"{mid}_validation.json").write_text(json.dumps(result, indent=2, default=float))

    html = env.get_template("validation_report.html.j2").render(
        r=result, m=model, card=document.load_card(mid), charts=charts(df_test, perf_test, fair),
        dims=FAIRNESS_DIMENSIONS, cfg=config, parity=parity_report)
    (config.REPORTS_DIR / f"{mid}_validation_report.html").write_text(html)
    return result


def run() -> dict:
    config.ensure_dirs()
    env = Environment(loader=FileSystemLoader(config.TEMPLATES_DIR), autoescape=select_autoescape())
    inv = discover.load_inventory()
    summary = {}
    for m in inv["models"]:
        r = validate_model(m, env)
        summary[m["model_id"]] = ({"rag": r["rag_rating"], "test_auc": round(r["performance"]["test"]["auc"], 4),
                                   "score_psi": round(r["stability"]["score_psi"], 4),
                                   "findings": len(r["findings"])}
                                  if r["validated"] else {"rag": "NOT VALIDATED", "reason": r["reason"]})
    (config.REPORTS_DIR / "validation_summary.json").write_text(json.dumps(
        {"generated_at": state.now(), "models": summary}, indent=2))
    return {"models_validated": sum(v["rag"] != "NOT VALIDATED" for v in summary.values()),
            "models_not_validated": sum(v["rag"] == "NOT VALIDATED" for v in summary.values()),
            "results": summary}


def load_validation(model_id: str) -> dict | None:
    p = config.REPORTS_DIR / f"{model_id}_validation.json"
    return json.loads(p.read_text()) if p.exists() else None


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
