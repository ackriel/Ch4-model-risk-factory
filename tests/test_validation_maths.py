"""Unit tests for the deterministic validation maths, checked against known answers."""
import numpy as np
import pandas as pd
import pytest

from validation import fairness, metrics, parity, stability


def test_auc_and_gini_perfect_and_random():
    y = np.array([0, 0, 1, 1])
    assert metrics.auc(y, [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert metrics.gini(y, [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert metrics.auc(y, [0.5, 0.5, 0.5, 0.5]) == 0.5


def test_ks_perfect_separation():
    assert metrics.ks_statistic([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)


def test_calibration_table_sums():
    rng = np.random.default_rng(0)
    p = rng.uniform(size=1000)
    y = rng.binomial(1, p)
    tab = metrics.calibration_table(y, p)
    assert tab["n"].sum() == 1000
    # Well-calibrated synthetic data -> Hosmer-Lemeshow should not reject.
    assert metrics.hosmer_lemeshow(y, p)["p_value"] > 0.01


def test_expected_cost_matches_hand_calculation():
    y = np.array([1, 1, 0, 0])
    p = np.array([0.9, 0.1, 0.9, 0.1])    # one bad approved (5), one good rejected (1)
    c = metrics.expected_cost(y, p, threshold=0.5)
    assert (c["fn"], c["fp"], c["total_cost"]) == (1, 1, 6.0)
    assert c["baseline_cost_approve_all"] == 10.0


def test_psi_zero_for_identical_and_positive_for_shift():
    rng = np.random.default_rng(1)
    a = rng.normal(size=5000)
    assert stability.psi_numeric(a, a) == pytest.approx(0.0, abs=1e-9)
    assert stability.psi_numeric(a, a + 1.0) > 0.25
    assert stability.psi_categorical(list("aabb"), list("aabb")) == pytest.approx(0.0, abs=1e-9)
    assert stability.psi_status(0.05) == "OK" and stability.psi_status(0.3) == "ALERT"


def test_fairness_disparate_impact():
    y = np.zeros(100)
    p = np.r_[np.full(50, 0.05), np.r_[np.full(25, 0.05), np.full(25, 0.9)]]
    g = np.r_[["A"] * 50, ["B"] * 50]
    res = fairness.group_metrics(y, p, g, threshold=0.5)
    b = next(r for r in res["groups"] if r["group"] == "B")
    assert res["reference_group"] == "A"
    assert b["disparate_impact_ratio"] == pytest.approx(0.5)
    assert "B" in res["flagged_groups"]


def test_parity_detects_difference():
    a = pd.DataFrame({"customer_id": [1, 2], "pd": [0.1, 0.2]})
    assert parity.compare_predictions(a, a.copy())["passed"]
    b = a.assign(pd=[0.1, 0.2001])
    assert not parity.compare_predictions(a, b)["passed"]
