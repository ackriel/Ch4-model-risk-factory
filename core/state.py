"""Pipeline state and audit trail.

Each stage moves through:  not_started -> completed -> approved | rejected
A stage may only run when the previous stage has been APPROVED by a human.
Re-running a stage resets every later stage, so stale approvals never survive.
Every run and every decision is appended to outputs/audit_log.jsonl.
"""
from __future__ import annotations

import getpass
import json
from datetime import datetime, timezone

from core import config

STAGES = config.PIPELINE_STAGES


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_user() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def _blank() -> dict:
    return {"stages": {s: {"status": "not_started"} for s in STAGES}}


def load() -> dict:
    if config.STATE_FILE.exists():
        state = json.loads(config.STATE_FILE.read_text())
        for s in STAGES:
            state["stages"].setdefault(s, {"status": "not_started"})
        return state
    return _blank()


def save(state: dict) -> None:
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    config.STATE_FILE.write_text(json.dumps(state, indent=2))


def audit(event: str, **details) -> None:
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(config.AUDIT_LOG, "a") as fh:
        fh.write(json.dumps({"timestamp": now(), "event": event, **details}) + "\n")


def read_audit() -> list[dict]:
    if not config.AUDIT_LOG.exists():
        return []
    return [json.loads(line) for line in config.AUDIT_LOG.read_text().splitlines() if line.strip()]


def previous_stage(stage: str) -> str | None:
    i = STAGES.index(stage)
    return STAGES[i - 1] if i > 0 else None


def can_run(stage: str, state: dict | None = None) -> tuple[bool, str]:
    state = state or load()
    prev = previous_stage(stage)
    if prev is None:
        return True, "First stage."
    prev_status = state["stages"][prev]["status"]
    if prev_status == "approved":
        return True, f"'{prev}' approved."
    return False, f"Waiting for human approval of '{prev}' (currently: {prev_status})."


def record_run(stage: str, actor: str, summary: dict, duration_s: float, ok: bool = True) -> None:
    state = load()
    state["stages"][stage] = {
        "status": "completed" if ok else "failed",
        "run_at": now(), "run_by": actor,
        "duration_seconds": round(duration_s, 3), "summary": summary,
    }
    # Invalidate downstream stages.
    for later in STAGES[STAGES.index(stage) + 1:]:
        if state["stages"][later]["status"] != "not_started":
            audit("stage_invalidated", stage=later, reason=f"'{stage}' was re-run")
        state["stages"][later] = {"status": "not_started"}
    save(state)
    audit("stage_run", stage=stage, actor=actor, ok=ok,
          duration_seconds=round(duration_s, 3), summary=summary)


def record_review(stage: str, decision: str, reviewer: str, comment: str = "",
                  automated: bool = False) -> None:
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")
    state = load()
    if state["stages"][stage]["status"] not in ("completed", "approved", "rejected"):
        raise RuntimeError(f"Stage '{stage}' has no completed output to review.")
    state["stages"][stage]["status"] = decision
    state["stages"][stage]["review"] = {"decision": decision, "reviewer": reviewer,
                                        "comment": comment, "at": now(),
                                        "automated": automated}
    save(state)
    audit("stage_review", stage=stage, decision=decision, reviewer=reviewer,
          comment=comment, automated=automated)


def reset() -> None:
    save(_blank())
    audit("pipeline_reset", actor=default_user())
