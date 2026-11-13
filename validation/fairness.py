"""Group fairness checks on model decisions.

Decision rule: approve when PD < config.DECISION_THRESHOLD.
Metrics per group:
  * approval_rate                 share of applicants approved
  * true_approval_rate            share of genuinely good customers approved (equal opportunity)
  * observed default rate, mean PD, AUC (when both classes are present)
Comparisons against the most-approved group:
  * disparate_impact_ratio        approval_rate / reference approval_rate (screen: >= 0.8)
  * equal_opportunity_gap         reference true_approval_rate - group true_approval_rate
These are screening heuristics, not legal tests.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from core import config

MIN_GROUP_SIZE = 30


def group_metrics(y_true, scores, groups, threshold: float = config.DECISION_THRESHOLD) -> dict:
    df = pd.DataFrame({"y": np.asarray(y_true), "p": np.asarray(scores),
                       "g": np.asarray(groups)})
    df["approved"] = df["p"] < threshold
    rows = []
    for g, sub in df.groupby("g"):
        good = sub[sub["y"] == 0]
        auc = float(roc_auc_score(sub["y"], sub["p"])) if sub["y"].nunique() == 2 else None
        rows.append({
            "group": str(g), "n": int(len(sub)),
            "approval_rate": float(sub["approved"].mean()),
            "true_approval_rate": float(good["approved"].mean()) if len(good) else None,
            "observed_default_rate": float(sub["y"].mean()),
            "mean_pd": float(sub["p"].mean()),
            "auc": auc,
            "small_sample": bool(len(sub) < MIN_GROUP_SIZE),
        })
    # Reference = most-approved group among groups large enough to be reliable.
    eligible = [r for r in rows if not r["small_sample"]] or rows
    ref = max(eligible, key=lambda r: r["approval_rate"])
    flags = []
    for r in rows:
        r["disparate_impact_ratio"] = (r["approval_rate"] / ref["approval_rate"]
                                       if ref["approval_rate"] > 0 else None)
        if r["true_approval_rate"] is not None and ref["true_approval_rate"] is not None:
            r["equal_opportunity_gap"] = ref["true_approval_rate"] - r["true_approval_rate"]
        else:
            r["equal_opportunity_gap"] = None
        r["flag_disparate_impact"] = bool(r["disparate_impact_ratio"] is not None
                                          and r["disparate_impact_ratio"] < config.DISPARATE_IMPACT_MIN)
        r["flag_equal_opportunity"] = bool(r["equal_opportunity_gap"] is not None
                                           and r["equal_opportunity_gap"] > config.EQUAL_OPPORTUNITY_MAX_GAP)
        if r["flag_disparate_impact"] or r["flag_equal_opportunity"]:
            flags.append(r["group"])
    return {"reference_group": ref["group"], "threshold": threshold,
            "groups": rows, "flagged_groups": flags}
