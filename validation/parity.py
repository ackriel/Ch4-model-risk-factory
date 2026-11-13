"""Parity checks between a legacy model and its redeveloped version."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core import config


def compare_predictions(legacy: pd.DataFrame, redeveloped: pd.DataFrame,
                        key: str = "customer_id", col: str = "pd",
                        tolerance: float = config.PARITY_TOLERANCE) -> dict:
    merged = legacy[[key, col]].merge(redeveloped[[key, col]], on=key,
                                      suffixes=("_legacy", "_new"), how="outer",
                                      indicator=True)
    missing = int((merged["_merge"] != "both").sum())
    both = merged[merged["_merge"] == "both"]
    diff = (both[f"{col}_legacy"] - both[f"{col}_new"]).abs()
    return {
        "n_compared": int(len(both)),
        "n_unmatched_records": missing,
        "max_abs_diff": float(diff.max()),
        "mean_abs_diff": float(diff.mean()),
        "n_over_tolerance": int((diff > tolerance).sum()),
        "tolerance": tolerance,
        "passed": bool(missing == 0 and (diff <= tolerance).all()),
    }


def compare_coefficients(legacy: pd.DataFrame, redeveloped: pd.DataFrame,
                         tolerance: float = config.PARITY_TOLERANCE) -> dict:
    """Both frames need columns: term, estimate."""
    merged = legacy[["term", "estimate"]].merge(redeveloped[["term", "estimate"]],
                                                on="term", how="outer",
                                                suffixes=("_legacy", "_new"))
    merged["abs_diff"] = (merged["estimate_legacy"] - merged["estimate_new"]).abs()
    unmatched = merged[merged[["estimate_legacy", "estimate_new"]].isna().any(axis=1)]
    return {
        "n_terms": int(len(merged)),
        "unmatched_terms": unmatched["term"].tolist(),
        "max_abs_diff": float(merged["abs_diff"].max()),
        "passed": bool(len(unmatched) == 0 and (merged["abs_diff"] <= tolerance).all()),
        "table": merged.replace({np.nan: None}).to_dict(orient="records"),
    }
