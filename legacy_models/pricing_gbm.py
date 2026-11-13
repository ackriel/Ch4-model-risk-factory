# =============================================================================
# MODEL_ID:     CR-PR-003
# MODEL_NAME:   Risk-Based Pricing Gradient Boosting Model
# OWNER:        Pricing & Product Analytics
# PURPOSE:      Estimate default risk to set the interest-rate band offered to applicants
# USE:          Risk-based pricing of personal loans
# LANGUAGE:     Python (scikit-learn)
# LAST_REVIEW:  2022-11
# =============================================================================
"""Legacy gradient boosting model. Run from the project root:
    python legacy_models/pricing_gbm.py
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import config, data  # noqa: E402

MODEL_ID = "CR-PR-003"
TARGET = "default_flag"
FEATURES = config.NUMERIC_FEATURES + config.CATEGORICAL_FEATURES
CATEGORICAL = config.CATEGORICAL_FEATURES


def build_model() -> Pipeline:
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
        remainder="passthrough")
    gbm = GradientBoostingClassifier(n_estimators=150, learning_rate=0.05,
                                     max_depth=3, subsample=0.8, random_state=42)
    return Pipeline([("prep", pre), ("model", gbm)])


def main() -> None:
    train, test = data.load_split()
    model = build_model().fit(train[FEATURES], train[TARGET])
    config.LEGACY_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, config.LEGACY_ARTIFACTS / f"{MODEL_ID}_model.joblib")
    for name, df in [("train", train), ("test", test)]:
        pd.DataFrame({"customer_id": df["customer_id"],
                      "pd": model.predict_proba(df[FEATURES])[:, 1]}).to_csv(
            config.LEGACY_ARTIFACTS / f"{MODEL_ID}_{name}_scores.csv", index=False)
    print(f"{MODEL_ID} trained on {len(train)} rows.")


if __name__ == "__main__":
    main()
