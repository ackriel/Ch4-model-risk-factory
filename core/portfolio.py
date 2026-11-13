"""Estate health: one verdict per model, built from the files the agents wrote.

Status rules (deterministic, most severe wins):
  BLOCKED          the model cannot be executed in the factory, so no validation evidence exists
  FAILING          validation rating RED, R->Python parity FAILED, or a monitoring ALERT
  NEEDS ATTENTION  validation rating AMBER, a monitoring WARN, or stale documentation
  OK               validated GREEN with no monitoring warnings
  PENDING          the stages needed to judge the model have not run yet

Only outputs of stages that have actually run in the current pipeline are used,
so the view never mixes in results from an earlier, invalidated run.

Writes outputs/reports/portfolio.json and outputs/reports/portfolio_report.html.
"""
from __future__ import annotations

import json

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core import config, state

STATUS_ORDER = ["FAILING", "BLOCKED", "NEEDS ATTENTION", "PENDING", "OK"]
STATUS_RULES = {
    "FAILING": "Validation rating RED, R->Python parity FAILED, or a monitoring ALERT",
    "BLOCKED": "The model cannot be executed in the factory, so no validation evidence exists",
    "NEEDS ATTENTION": "Validation rating AMBER, a monitoring WARN, or stale documentation",
    "PENDING": "The stages needed to judge the model have not run yet",
    "OK": "Validated GREEN with no monitoring warnings",
}


def _read(path):
    return json.loads(path.read_text()) if path.exists() else None


def _ran(stages: dict, stage: str) -> bool:
    return stages[stage]["status"] in ("completed", "approved", "rejected")


def model_row(m: dict, stages: dict, monitoring: dict | None) -> dict:
    mid = m["model_id"]
    reasons: list[tuple[str, str]] = []   # (level, text)

    card = _read(config.MODEL_CARDS_DIR / f"{mid}.json") if _ran(stages, "document") else None
    parity = _read(config.REPORTS_DIR / f"{mid}_parity.json") if _ran(stages, "redevelop") else None
    val = _read(config.REPORTS_DIR / f"{mid}_validation.json") if _ran(stages, "validate") else None
    mon = monitoring["models"].get(mid) if monitoring else None

    if not m["executable"]:
        reasons.append(("BLOCKED", f"Cannot be executed in the factory: {m['execution_note']}"))
    parity_txt = "n/a"
    if parity:
        parity_txt = parity["verdict"]
        if not parity["parity_passed"]:
            reasons.append(("FAILING", "R->Python parity FAILED"))
        elif not parity["genuine_migration"]:
            reasons.append(("NEEDS ATTENTION", "Parity is SIMULATED (no genuine R run)"))

    rag, auc, n_high, n_med, top = "not run", None, 0, 0, []
    if val:
        rag = val["rag_rating"]
        auc = val["performance"]["test"]["auc"]
        n_high = sum(f["severity"] == "High" for f in val["findings"])
        n_med = sum(f["severity"] == "Medium" for f in val["findings"])
        top = [f"[{f['severity']}] {f['finding']}" for f in val["findings"]
               if f["severity"] in ("High", "Medium")][:4]
        if rag == "RED":
            reasons.append(("FAILING", f"Validation RED ({n_high} high-severity findings)"))
        elif rag == "AMBER":
            reasons.append(("NEEDS ATTENTION", f"Validation AMBER ({n_med} medium-severity findings)"))
    elif _ran(stages, "validate") and m["executable"]:
        rag = "missing"

    mon_status = "not run"
    if mon is not None:
        if not mon.get("monitored"):
            mon_status = "not monitored"
        else:
            mon_status = mon["status"]
            if mon_status == "ALERT":
                reasons.append(("FAILING", f"Monitoring ALERT (score PSI {mon['score_psi']:.2f}): re-validation required"))
            elif mon_status == "WARN":
                reasons.append(("NEEDS ATTENTION", f"Monitoring WARN (score PSI {mon['score_psi']:.2f})"))

    if m.get("documentation_stale"):
        reasons.append(("NEEDS ATTENTION",
                        f"Original documentation {m['documentation_age_years']} years old; "
                        "new draft model card needs owner sign-off" if card else
                        f"Documentation {m['documentation_age_years']} years old"))

    levels = {lvl for lvl, _ in reasons}
    if "FAILING" in levels:
        status = "FAILING"
    elif "BLOCKED" in levels:
        status = "BLOCKED"
    elif not val:
        status = "PENDING" if m["executable"] else "BLOCKED"
    elif "NEEDS ATTENTION" in levels:
        status = "NEEDS ATTENTION"
    else:
        status = "OK"

    return {
        "model_id": mid, "model_name": m["model_name"], "language": m["language"],
        "methodology": m["methodology"], "risk_tier": m["risk_tier"].split(" - ")[0],
        "owner": m["owner"], "executable": m["executable"],
        "documented": card is not None, "documentation_age_years": m["documentation_age_years"],
        "parity": parity_txt, "validation_rating": rag, "test_auc": auc,
        "high_findings": n_high, "medium_findings": n_med, "top_findings": top,
        "monitoring_status": mon_status, "status": status,
        "reasons": [t for _, t in sorted(reasons, key=lambda r: STATUS_ORDER.index(r[0]))],
        "report_file": (f"{mid}_validation_report.html" if val else None),
    }


def build(write: bool = True) -> dict | None:
    if not config.INVENTORY_FILE.exists():
        return None
    st = state.load()["stages"]
    if not _ran(st, "discover"):
        return None
    inv = json.loads(config.INVENTORY_FILE.read_text())
    monitoring = _read(config.MONITORING_DIR / "latest.json") if _ran(st, "monitor") else None
    rows = sorted((model_row(m, st, monitoring) for m in inv["models"]),
                  key=lambda r: (STATUS_ORDER.index(r["status"]), r["model_id"]))
    languages = sorted({r["language"] for r in rows})
    by_language = {lang: {s: sum(r["language"] == lang and r["status"] == s for r in rows)
                          for s in STATUS_ORDER} for lang in languages}
    result = {
        "generated_at": state.now(),
        "n_models": len(rows),
        "status_counts": {s: sum(r["status"] == s for r in rows) for s in STATUS_ORDER},
        "by_language": by_language,
        "stages": {s: st[s]["status"] for s in config.PIPELINE_STAGES},
        "monitoring_scenario": monitoring and {"scenario": monitoring["scenario"],
                                               "severity": monitoring["severity"]},
        "models": rows,
        "status_rules": STATUS_RULES,
    }
    if write:
        config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (config.REPORTS_DIR / "portfolio.json").write_text(json.dumps(result, indent=2, default=float))
        env = Environment(loader=FileSystemLoader(config.TEMPLATES_DIR), autoescape=select_autoescape())
        html = env.get_template("portfolio_report.html.j2").render(p=result, order=STATUS_ORDER)
        (config.REPORTS_DIR / "portfolio_report.html").write_text(html)
    return result


if __name__ == "__main__":
    p = build()
    print(json.dumps(p and {k: p[k] for k in ["status_counts", "by_language"]}, indent=2))
