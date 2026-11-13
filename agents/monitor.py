"""Stage 5 - Monitor agent.

Simulates a batch of new applications arriving in production, scores it with every
executable model, measures drift against the development sample (PSI on inputs and
scores) and, because this is a simulation where outcomes are known, the change in
AUC. Raises alerts and recommends re-validation when thresholds are breached.

Scenarios
  stable  - new batch resampled from the hold-out data with no change
  drift   - new batch with a shifted population: younger applicants, larger loans,
            more customers with overdrawn accounts. `severity` (0-1) scales the shift.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from agents import discover, validate
from core import config, data, scoring, state
from validation import metrics, stability

OVERDRAWN = "... < 0 DM"


def simulate_batch(scenario: str = "drift", severity: float = 0.6, n: int = 400,
                   seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    _, test = data.load_split()
    if scenario == "stable" or severity <= 0:
        batch = test.sample(n=n, replace=True, random_state=seed)
    else:
        # Over-sample overdrawn and young applicants -> genuine change in the population mix.
        w = np.ones(len(test))
        w[(test["status"] == OVERDRAWN).to_numpy()] *= 1 + 4 * severity
        w[(test["age"] < 30).to_numpy()] *= 1 + 3 * severity
        batch = test.sample(n=n, replace=True, weights=w / w.sum(), random_state=seed).copy()
        # Loan sizes inflate and terms lengthen (e.g. a new product / price change).
        batch["amount"] = (batch["amount"] * (1 + 0.6 * severity)
                           * rng.lognormal(0, 0.05, len(batch))).round().astype(int)
        batch["duration"] = np.clip(batch["duration"] + rng.integers(0, int(12 * severity) + 1, len(batch)), 4, 72)
    batch = batch.reset_index(drop=True)
    batch["customer_id"] = np.arange(100001, 100001 + len(batch))
    return batch


def monitor(scenario: str = "drift", severity: float = 0.6) -> dict:
    config.ensure_dirs()
    train, _ = data.load_split()
    batch = simulate_batch(scenario, severity)
    batch.to_csv(config.MONITORING_DIR / f"incoming_batch_{scenario}.csv", index=False)
    inv = discover.load_inventory()
    models, alerts = {}, []
    for m in inv["models"]:
        mid = m["model_id"]
        new_scores = scoring.score_frame(mid, batch)
        dev = scoring.stored_scores(mid, "train")
        if new_scores is None or dev is None:
            models[mid] = {"monitored": False, "reason": "Model not executable in the factory."}
            continue
        feats = m["input_features"]
        feat_psi = stability.feature_psi_table(
            train, batch, [f for f in feats if f in config.NUMERIC_FEATURES],
            [f for f in feats if f in config.CATEGORICAL_FEATURES])
        score_psi = stability.psi_numeric(dev["pd"], new_scores)
        val = validate.load_validation(mid)
        auc_ref = val["performance"]["test"]["auc"] if val else None
        auc_new = metrics.auc(batch[config.TARGET], new_scores)
        rate_new = float((new_scores < config.DECISION_THRESHOLD).mean())
        rate_ref = val["performance"]["test"]["cost"]["approval_rate"] if val else None
        res = {
            "monitored": True, "score_psi": score_psi, "score_psi_status": stability.psi_status(score_psi),
            "feature_psi": feat_psi, "auc_validation": auc_ref, "auc_new_batch": auc_new,
            "approval_rate_validation": rate_ref, "approval_rate_new_batch": rate_new,
            "mean_pd_new_batch": float(np.mean(new_scores)),
            "observed_default_rate_new_batch": float(batch[config.TARGET].mean()),
        }
        model_alerts = []
        if res["score_psi_status"] != "OK":
            model_alerts.append(("ALERT" if res["score_psi_status"] == "ALERT" else "WARN",
                                 f"Score distribution shift: PSI {score_psi:.3f}"))
        for f in feat_psi:
            if f["status"] != "OK":
                model_alerts.append((f["status"], f"Input '{f['feature']}' drift: PSI {f['psi']:.3f}"))
        if auc_ref is not None and auc_ref - auc_new > 0.05:
            model_alerts.append(("ALERT", f"Discrimination degraded: AUC {auc_ref:.3f} -> {auc_new:.3f}"))
        if rate_ref is not None and abs(rate_new - rate_ref) > 0.10:
            model_alerts.append(("WARN", f"Approval rate moved {rate_ref:.0%} -> {rate_new:.0%}"))
        res["alerts"] = [{"level": lvl, "message": msg} for lvl, msg in model_alerts]
        res["status"] = ("ALERT" if any(a["level"] == "ALERT" for a in res["alerts"])
                         else "WARN" if res["alerts"] else "OK")
        res["action"] = ("Trigger re-validation and notify model owner" if res["status"] == "ALERT"
                         else "Investigate drift at next monitoring review" if res["status"] == "WARN"
                         else "No action")
        for a in res["alerts"]:
            alerts.append({"model_id": mid, **a})
        models[mid] = res
    report = {
        "generated_at": state.now(), "scenario": scenario, "severity": severity,
        "batch_size": int(len(batch)),
        "note": ("SIMULATED production batch. Outcomes are known only because this is a simulation; "
                 "in production, default outcomes arrive 12+ months later, so AUC monitoring lags."),
        "models": models, "alerts": alerts,
        "models_needing_revalidation": [k for k, v in models.items() if v.get("status") == "ALERT"],
    }
    (config.MONITORING_DIR / f"monitoring_{scenario}.json").write_text(json.dumps(report, indent=2, default=float))
    (config.MONITORING_DIR / "latest.json").write_text(json.dumps(report, indent=2, default=float))
    return report


def run(scenario: str = "drift", severity: float = 0.6) -> dict:
    r = monitor(scenario, severity)
    return {"scenario": scenario, "severity": severity, "alerts": len(r["alerts"]),
            "models_needing_revalidation": r["models_needing_revalidation"]}


def load_latest() -> dict | None:
    p = config.MONITORING_DIR / "latest.json"
    return json.loads(p.read_text()) if p.exists() else None


if __name__ == "__main__":
    print(json.dumps(monitor("stable", 0)["models_needing_revalidation"]))
    print(json.dumps(run(), indent=2))
