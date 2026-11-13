"""Population Stability Index (PSI) for scores and input characteristics."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core import config

_EPS = 1e-6


def _psi_from_shares(expected: np.ndarray, actual: np.ndarray) -> float:
    e = np.clip(expected, _EPS, None)
    a = np.clip(actual, _EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def psi_numeric(expected, actual, n_bins: int = 10) -> float:
    """PSI with bins set on the quantiles of the expected (reference) sample."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, n_bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e_counts = np.histogram(expected, bins=edges)[0] / len(expected)
    a_counts = np.histogram(actual, bins=edges)[0] / len(actual)
    return _psi_from_shares(e_counts, a_counts)


def psi_categorical(expected, actual) -> float:
    e = pd.Series(expected).value_counts(normalize=True)
    a = pd.Series(actual).value_counts(normalize=True)
    cats = e.index.union(a.index)
    return _psi_from_shares(e.reindex(cats, fill_value=0).values,
                            a.reindex(cats, fill_value=0).values)


def psi_status(value: float) -> str:
    if value >= config.PSI_ALERT:
        return "ALERT"
    if value >= config.PSI_WARN:
        return "WARN"
    return "OK"


def feature_psi_table(reference: pd.DataFrame, current: pd.DataFrame,
                      numeric: list[str], categorical: list[str]) -> list[dict]:
    rows = []
    for col in numeric:
        v = psi_numeric(reference[col], current[col])
        rows.append({"feature": col, "type": "numeric", "psi": v, "status": psi_status(v)})
    for col in categorical:
        v = psi_categorical(reference[col], current[col])
        rows.append({"feature": col, "type": "categorical", "psi": v, "status": psi_status(v)})
    return sorted(rows, key=lambda r: r["psi"], reverse=True)
