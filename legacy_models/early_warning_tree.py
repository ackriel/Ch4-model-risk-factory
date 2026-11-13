# =============================================================================
# MODEL_ID:     CR-EW-002
# MODEL_NAME:   Early-Warning Default Decision Tree
# OWNER:        Collections Strategy
# PURPOSE:      Flag existing borrowers at elevated risk of default for early outreach
# USE:          Prioritising collections contact lists
# LANGUAGE:     Python (scikit-learn)
# LAST_REVIEW:  2021-07
# =============================================================================
"""Legacy decision-tree model. Run from the project root:
    python legacy_models/early_warning_tree.py
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import config, data  # noqa: E402

MODEL_ID = "CR-EW-002"
TARGET = "default_flag"
FEATURES = ["status", "duration", "credit_history", "amount", "savings",
            "employment_duration", "age", "property", "housing"]
CATEGORICAL = ["status", "credit_history", "savings", "employment_duration",
               "property", "housing"]


def build_model() -> Pipeline:
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
        remainder="passthrough")
    tree = DecisionTreeClassifier(max_depth=4, min_samples_leaf=25,
                                  class_weight="balanced", random_state=42)
    return Pipeline([("prep", pre), ("model", tree)])


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
