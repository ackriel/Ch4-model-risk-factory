"""Business impact estimate. Measured inputs come from the pipeline state; every
assumption is listed explicitly so judges/reviewers can challenge it."""
from __future__ import annotations

import json

from core import config, state

ASSUMPTIONS = {
    "manual_validation_weeks_low": 8,     # from the challenge brief
    "manual_validation_weeks_high": 12,   # from the challenge brief
    "estate_size": 250,                   # models in the bank's inventory (brief)
    "human_review_days_per_model_with_factory": 5,  # ASSUMPTION: expert review of the automated pack
    "working_days_per_week": 5,
}


def estimate() -> dict:
    st = state.load()
    stages = st["stages"]
    machine_seconds = sum(s.get("duration_seconds", 0) for s in stages.values())
    n_models = 0
    if config.INVENTORY_FILE.exists():
        n_models = json.loads(config.INVENTORY_FILE.read_text())["n_models"]
    a = ASSUMPTIONS
    manual_days = (a["manual_validation_weeks_low"] * a["working_days_per_week"],
                   a["manual_validation_weeks_high"] * a["working_days_per_week"])
    factory_days = a["human_review_days_per_model_with_factory"]
    reduction = (1 - factory_days / manual_days[0], 1 - factory_days / manual_days[1])
    estate_manual_years = tuple(d * a["estate_size"] / 250 for d in manual_days)  # ~250 working days/yr
    estate_factory_years = factory_days * a["estate_size"] / 250
    return {
        "measured": {"models_processed": n_models,
                     "machine_time_seconds_all_stages": round(machine_seconds, 1)},
        "assumptions": a,
        "per_model_days": {"manual": manual_days, "with_factory": factory_days},
        "effort_reduction_range": reduction,
        "estate_person_years": {"manual": estate_manual_years, "with_factory": estate_factory_years},
        "caveat": ("The factory automates evidence gathering, not judgement. Human review time "
                   "is an assumption, not a measurement."),
    }
