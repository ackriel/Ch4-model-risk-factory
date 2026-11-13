"""Central configuration: paths, seeds and thresholds used across the factory.

Every threshold the pipeline uses to raise a flag lives here so that it is
visible, reviewable and identical across agents, tests and the dashboard.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DATA = DATA_DIR / "south_german_credit.csv"
TRAIN_DATA = DATA_DIR / "train.csv"
TEST_DATA = DATA_DIR / "test.csv"

LEGACY_DIR = ROOT / "legacy_models"
LEGACY_ARTIFACTS = LEGACY_DIR / "artifacts"
REDEVELOPED_DIR = ROOT / "redeveloped_models"
TEMPLATES_DIR = ROOT / "templates"

OUTPUTS = ROOT / "outputs"
INVENTORY_FILE = OUTPUTS / "inventory.json"
MODEL_CARDS_DIR = OUTPUTS / "model_cards"
REPORTS_DIR = OUTPUTS / "reports"
MONITORING_DIR = OUTPUTS / "monitoring"
STATE_FILE = OUTPUTS / "pipeline_state.json"
AUDIT_LOG = OUTPUTS / "audit_log.jsonl"
LLM_CACHE_DIR = OUTPUTS / "llm_cache"

# ---- Data -------------------------------------------------------------------
TARGET_RAW = "credit_risk"          # "good risk" / "bad risk" in the source data
TARGET = "default_flag"             # 1 = bad risk (default), 0 = good risk
RANDOM_SEED = 42
TEST_SIZE = 0.30

NUMERIC_FEATURES = ["duration", "amount", "age"]
CATEGORICAL_FEATURES = [
    "status", "credit_history", "purpose", "savings", "employment_duration",
    "installment_rate", "personal_status_sex", "other_debtors",
    "present_residence", "property", "other_installment_plans", "housing",
    "number_credits", "job", "people_liable", "telephone", "foreign_worker",
]

# ---- Business assumptions -----------------------------------------------------
# UCI cost matrix: approving a bad customer costs 5, rejecting a good one costs 1.
COST_FALSE_APPROVE = 5.0
COST_FALSE_REJECT = 1.0
# Cost-optimal cut-off on the probability of default: approve if PD < 1/(1+5).
DECISION_THRESHOLD = COST_FALSE_REJECT / (COST_FALSE_REJECT + COST_FALSE_APPROVE)

# ---- Validation thresholds -----------------------------------------------------
PARITY_TOLERANCE = 1e-6
AUC_MIN_ACCEPTABLE = 0.70
PSI_WARN = 0.10
PSI_ALERT = 0.25
DISPARATE_IMPACT_MIN = 0.80        # "four-fifths rule" used as a screening heuristic
EQUAL_OPPORTUNITY_MAX_GAP = 0.10

# Fairness groups that actually exist in this dataset (see data/DATA_NOTES.md).
AGE_BANDS = [(0, 25, "under 25"), (25, 200, "25 and over")]

# ---- Optional Claude API --------------------------------------------------------
CLAUDE_MODEL_DEFAULT = "claude-sonnet-5-5"

PIPELINE_STAGES = ["discover", "document", "redevelop", "validate", "monitor"]


def ensure_dirs() -> None:
    for d in [OUTPUTS, MODEL_CARDS_DIR, REPORTS_DIR, MONITORING_DIR, LLM_CACHE_DIR,
              LEGACY_ARTIFACTS, REDEVELOPED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def rel(path) -> str:
    """Path relative to the project root when possible (for display), else absolute."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)
