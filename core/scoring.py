"""Load any executable model in the estate and score a DataFrame with it."""
from __future__ import annotations

import importlib.util

import joblib
import numpy as np
import pandas as pd

from core import config


def _load_redeveloped(model_id: str):
    module_file = config.REDEVELOPED_DIR / f"{model_id.lower().replace('-', '_')}_logit.py"
    params_file = config.REDEVELOPED_DIR / f"{model_id}_python_coefficients.csv"
    if not module_file.exists() or not params_file.exists():
        return None
    spec = importlib.util.spec_from_file_location(module_file.stem, module_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    model = mod.RedevelopedLogit.from_coefficients(pd.read_csv(params_file))
    return lambda df: model.predict_proba(df)


def get_scorer(model_id: str):
    """Return f(DataFrame) -> np.ndarray of PDs, or None if the model cannot be executed."""
    redeveloped = _load_redeveloped(model_id)
    if redeveloped is not None:
        return redeveloped
    path = config.LEGACY_ARTIFACTS / f"{model_id}_model.joblib"
    if path.exists():
        pipe = joblib.load(path)
        features = list(pipe.feature_names_in_)
        return lambda df: pipe.predict_proba(df[features])[:, 1]
    return None


def stored_scores(model_id: str, split: str) -> pd.DataFrame | None:
    """Scores produced at build time: redeveloped Python first, then legacy outputs."""
    candidates = [
        config.REDEVELOPED_DIR / f"{model_id}_python_{split}_scores.csv",
        config.LEGACY_ARTIFACTS / f"{model_id}_{split}_scores.csv",
        config.LEGACY_ARTIFACTS / f"{model_id}_r_{split}_scores.csv",
    ]
    for c in candidates:
        if c.exists():
            df = pd.read_csv(c)
            df.attrs["source_file"] = config.rel(c)
            return df
    return None


def score_frame(model_id: str, df: pd.DataFrame) -> np.ndarray | None:
    scorer = get_scorer(model_id)
    return None if scorer is None else np.asarray(scorer(df), dtype=float)
