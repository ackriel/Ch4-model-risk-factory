"""Integration tests: agents and approval gates, run against an isolated copy of outputs/."""
import json

import pytest

from core import config, pipeline, state


@pytest.fixture()
def isolated_outputs(tmp_path, monkeypatch):
    out = tmp_path / "outputs"
    for name, sub in [("OUTPUTS", ""), ("MODEL_CARDS_DIR", "model_cards"), ("REPORTS_DIR", "reports"),
                      ("MONITORING_DIR", "monitoring"), ("LLM_CACHE_DIR", "llm_cache")]:
        monkeypatch.setattr(config, name, out / sub if sub else out)
    monkeypatch.setattr(config, "INVENTORY_FILE", out / "inventory.json")
    monkeypatch.setattr(config, "STATE_FILE", out / "pipeline_state.json")
    monkeypatch.setattr(config, "AUDIT_LOG", out / "audit_log.jsonl")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config.ensure_dirs()
    return out


def test_gate_blocks_until_approved(isolated_outputs):
    with pytest.raises(PermissionError):
        pipeline.run_stage("document")
    pipeline.run_stage("discover", actor="t")
    with pytest.raises(PermissionError):
        pipeline.run_stage("document")
    state.record_review("discover", "approved", "tester")
    pipeline.run_stage("document", actor="t")
    assert state.load()["stages"]["document"]["status"] == "completed"


def test_rerun_invalidates_downstream(isolated_outputs):
    pipeline.run_stage("discover", actor="t")
    state.record_review("discover", "approved", "tester")
    pipeline.run_stage("document", actor="t")
    state.record_review("document", "approved", "tester")
    pipeline.run_stage("discover", actor="t")
    assert state.load()["stages"]["document"]["status"] == "not_started"
    assert any(e["event"] == "stage_invalidated" for e in state.read_audit())


def test_full_pipeline(isolated_outputs):
    for stage in config.PIPELINE_STAGES:
        pipeline.run_stage(stage, actor="t")
        state.record_review(stage, "approved", "tester", "ok")
    inv = json.loads(config.INVENTORY_FILE.read_text())
    assert inv["n_models"] == 4
    assert {m["language"] for m in inv["models"]} == {"R", "Python", "SAS"}
    assert len(list(config.MODEL_CARDS_DIR.glob("*.md"))) == 4
    par = json.loads((config.REPORTS_DIR / "CR-PD-001_parity.json").read_text())
    assert par["parity_passed"] and par["genuine_migration"]
    assert par["test_predictions"]["max_abs_diff"] < config.PARITY_TOLERANCE
    summary = json.loads((config.REPORTS_DIR / "validation_summary.json").read_text())
    assert summary["models"]["CR-BH-004"]["rag"] == "NOT VALIDATED"
    assert (config.REPORTS_DIR / "CR-PD-001_validation_report.html").exists()
    mon = json.loads((config.MONITORING_DIR / "latest.json").read_text())
    assert mon["scenario"] == "drift" and mon["alerts"]


def test_recorded_r_outputs_used_when_r_missing(isolated_outputs, monkeypatch):
    """Simulates a Mac without R: the agent must fall back to the recorded genuine R outputs."""
    from agents import discover, redevelop
    discover.run()
    monkeypatch.setattr(redevelop.shutil, "which", lambda name: None)
    m = next(x for x in discover.load_inventory()["models"] if x["model_id"] == "CR-PD-001")
    rep = redevelop.redevelop_model(m)
    assert rep["legacy_mode"] == "GENUINE_R_RECORDED" and rep["parity_passed"]
