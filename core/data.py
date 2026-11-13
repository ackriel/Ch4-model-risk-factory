"""Loading and splitting the South German Credit data.

Run directly to (re)create data/train.csv and data/test.csv:
    python -m core.data
"""
from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

from core import config


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(config.RAW_DATA)
    df[config.TARGET] = (df[config.TARGET_RAW] == "bad risk").astype(int)
    df = df.drop(columns=[config.TARGET_RAW])
    # Every categorical column is stored as text so R and Python see identical values.
    for col in config.CATEGORICAL_FEATURES:
        df[col] = df[col].astype(str)
    return df


def make_split() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_raw()
    df.insert(0, "customer_id", range(1, len(df) + 1))
    train, test = train_test_split(
        df, test_size=config.TEST_SIZE, random_state=config.RANDOM_SEED,
        stratify=df[config.TARGET],
    )
    train = train.sort_values("customer_id")
    test = test.sort_values("customer_id")
    train.to_csv(config.TRAIN_DATA, index=False)
    test.to_csv(config.TEST_DATA, index=False)
    return train, test


def load_split() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not config.TRAIN_DATA.exists() or not config.TEST_DATA.exists():
        return make_split()
    dtypes = {c: str for c in config.CATEGORICAL_FEATURES}
    return (pd.read_csv(config.TRAIN_DATA, dtype=dtypes),
            pd.read_csv(config.TEST_DATA, dtype=dtypes))


def age_band(age: pd.Series) -> pd.Series:
    labels = pd.Series(index=age.index, dtype=object)
    for lo, hi, name in config.AGE_BANDS:
        labels[(age >= lo) & (age < hi)] = name
    return labels


def describe() -> dict:
    """Facts about the dataset, used by the dashboard and docs."""
    df = load_raw()
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "default_rate": float(df[config.TARGET].mean()),
        "numeric_features": config.NUMERIC_FEATURES,
        "categorical_features": config.CATEGORICAL_FEATURES,
        "personal_status_sex_levels": sorted(df["personal_status_sex"].unique().tolist()),
        "foreign_worker_levels": sorted(df["foreign_worker"].unique().tolist()),
    }


if __name__ == "__main__":
    tr, te = make_split()
    print(f"train: {len(tr)} rows, default rate {tr[config.TARGET].mean():.3f}")
    print(f"test:  {len(te)} rows, default rate {te[config.TARGET].mean():.3f}")
