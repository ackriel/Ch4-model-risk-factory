"""Discrimination, calibration and cost metrics for probability-of-default models.

All functions are plain, deterministic Python/numpy/scipy. AI never computes
or edits these numbers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve

from core import config


def auc(y_true, scores) -> float:
    return float(roc_auc_score(y_true, scores))


def gini(y_true, scores) -> float:
    return 2.0 * auc(y_true, scores) - 1.0


def ks_statistic(y_true, scores) -> float:
    """Kolmogorov-Smirnov: max distance between score CDFs of defaulters and non-defaulters."""
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    return float(stats.ks_2samp(scores[y_true == 1], scores[y_true == 0]).statistic)


def calibration_table(y_true, scores, n_bins: int = 10) -> pd.DataFrame:
    """Predicted vs observed default rate by score decile."""
    df = pd.DataFrame({"y": np.asarray(y_true), "p": np.asarray(scores)})
    df["bin"] = pd.qcut(df["p"].rank(method="first"), q=n_bins, labels=False)
    out = df.groupby("bin").agg(n=("y", "size"), predicted_pd=("p", "mean"),
                                observed_dr=("y", "mean")).reset_index()
    out["bin"] = out["bin"] + 1
    return out


def hosmer_lemeshow(y_true, scores, n_bins: int = 10) -> dict:
    tab = calibration_table(y_true, scores, n_bins)
    expected = tab["predicted_pd"] * tab["n"]
    observed = tab["observed_dr"] * tab["n"]
    n = tab["n"]
    denom = expected * (1 - expected / n)
    hl = float((((observed - expected) ** 2) / denom.replace(0, np.nan)).sum())
    dof = n_bins - 2
    return {"statistic": hl, "dof": dof, "p_value": float(1 - stats.chi2.cdf(hl, dof))}


def brier(y_true, scores) -> float:
    return float(brier_score_loss(y_true, scores))


def confusion_at_threshold(y_true, scores, threshold: float) -> dict:
    """'Reject' when PD >= threshold. Positive class = default."""
    y = np.asarray(y_true)
    rej = np.asarray(scores) >= threshold
    tp = int(((y == 1) & rej).sum())   # defaulter correctly rejected
    fn = int(((y == 1) & ~rej).sum())  # defaulter wrongly approved
    fp = int(((y == 0) & rej).sum())   # good customer wrongly rejected
    tn = int(((y == 0) & ~rej).sum())
    return {"threshold": threshold, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "approval_rate": float((~rej).mean())}


def expected_cost(y_true, scores, threshold: float = config.DECISION_THRESHOLD) -> dict:
    c = confusion_at_threshold(y_true, scores, threshold)
    total = c["fn"] * config.COST_FALSE_APPROVE + c["fp"] * config.COST_FALSE_REJECT
    n = len(np.asarray(y_true))
    # Baseline: approve everyone (no model).
    baseline = float(np.asarray(y_true).sum() * config.COST_FALSE_APPROVE)
    return {**c, "total_cost": float(total), "cost_per_applicant": float(total / n),
            "baseline_cost_approve_all": baseline,
            "cost_saving_vs_no_model": float(baseline - total)}


def roc_points(y_true, scores) -> dict:
    fpr, tpr, _ = roc_curve(y_true, scores)
    return {"fpr": fpr.tolist(), "tpr": tpr.tolist()}


def performance_summary(y_true, scores) -> dict:
    a = auc(y_true, scores)
    return {
        "n": int(len(np.asarray(y_true))),
        "default_rate": float(np.mean(y_true)),
        "auc": a,
        "gini": 2 * a - 1,
        "ks": ks_statistic(y_true, scores),
        "brier": brier(y_true, scores),
        "mean_predicted_pd": float(np.mean(scores)),
        "hosmer_lemeshow": hosmer_lemeshow(y_true, scores),
        "calibration_table": calibration_table(y_true, scores).to_dict(orient="records"),
        "cost": expected_cost(y_true, scores),
    }
