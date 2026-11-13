"""Runs stages, enforces approval gates and records timings + audit trail."""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
import traceback

from core import config, data, state


def setup(verbose: bool = True) -> dict:
    """Create the train/test split and (re)build the legacy model estate."""
    config.ensure_dirs()
    # Keep an existing split: the recorded R outputs were produced on it.
    tr, te = data.load_split()
    log = [f"Split: {len(tr)} train / {len(te)} test rows"]
    rscript = shutil.which("Rscript")
    if rscript:
        subprocess.run([rscript, "legacy_models/scorecard_logit.R"], cwd=config.ROOT, check=True)
        log.append("R scorecard fitted with Rscript")
    else:
        log.append("Rscript not found: keeping recorded R outputs in legacy_models/artifacts")
    for script in ["legacy_models/early_warning_tree.py", "legacy_models/pricing_gbm.py"]:
        subprocess.run([sys.executable, script], cwd=config.ROOT, check=True)
        log.append(f"Trained {script}")
    state.audit("setup", actor=state.default_user(), log=log)
    if verbose:
        print("\n".join(log))
    return {"log": log}


def _agent(stage: str):
    from agents import discover, document, monitor, redevelop, validate
    return {"discover": discover, "document": document, "redevelop": redevelop,
            "validate": validate, "monitor": monitor}[stage]


def run_stage(stage: str, actor: str | None = None, **kwargs) -> dict:
    actor = actor or state.default_user()
    ok, reason = state.can_run(stage)
    if not ok:
        raise PermissionError(reason)
    start = time.perf_counter()
    try:
        summary = _agent(stage).run(**kwargs)
        state.record_run(stage, actor, summary, time.perf_counter() - start, ok=True)
        return summary
    except Exception as exc:
        summary = {"error": str(exc), "traceback": traceback.format_exc(limit=3)}
        state.record_run(stage, actor, summary, time.perf_counter() - start, ok=False)
        raise


def run_all(reviewer: str, auto_approve: bool = False) -> None:
    """Run every stage in order. With auto_approve, approvals are logged as AUTOMATED."""
    for stage in config.PIPELINE_STAGES:
        summary = run_stage(stage, actor=reviewer)
        print(f"[{stage}] done: {summary}")
        if auto_approve:
            state.record_review(stage, "approved", reviewer,
                                "Auto-approved via run-all (testing only)", automated=True)
        else:
            ans = input(f"Approve '{stage}'? [y/N] ").strip().lower()
            state.record_review(stage, "approved" if ans == "y" else "rejected", reviewer)
            if ans != "y":
                print("Stopped: stage rejected.")
                return
