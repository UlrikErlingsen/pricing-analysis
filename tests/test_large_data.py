"""Data limits: none locally, demo caps only with SIGNAL_PUBLIC=1, and exact count-based bootstraps for large data."""

from __future__ import annotations

import numpy as np
import pytest

from tagsignal import analysis, limits
from tagsignal.analysis import PriceConfig, analyze_price
from tagsignal.errors import DataProblem, friendly_message
from tagsignal.examples import demo_contract, randomized_demo, valuation_demo
from tagsignal.io import read_table


def _csv(rows: int) -> bytes:
    return b"price,quantity\n" + b"29,1\n34,0\n" * (rows // 2)


def _config(mode: str) -> PriceConfig:
    values = demo_contract(mode)
    values["controls"] = tuple(values.get("controls", ()))
    return PriceConfig(**values)


def test_local_mode_accepts_input_beyond_the_demo_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
    rows = limits.DEMO_MAX_ROWS + 2
    frame, _ = read_table(_csv(rows), "test.csv")
    assert len(frame) == rows
    assert frame["quantity"].dtype == np.int8


def test_public_demo_enforces_its_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    with pytest.raises(DataProblem, match="public demo"):
        read_table(_csv(limits.DEMO_MAX_ROWS + 2), "test.csv")
    monkeypatch.setattr(limits, "DEMO_MAX_UPLOAD_MB", 0)
    with pytest.raises(DataProblem, match="downloaded app has no built-in limit"):
        read_table(_csv(10), "small.csv")


def test_memory_errors_become_a_plain_message() -> None:
    assert "not enough memory" in friendly_message(MemoryError())


def test_count_based_acceptance_bootstrap_matches_resampling() -> None:
    rng = np.random.default_rng(4)
    values = np.round(rng.lognormal(3.3, 0.4, size=3000), 1)
    prices = np.array([20.0, 27.5, 35.0, 50.0])
    counted = analysis._acceptance_draws_from_counts(values, prices, 4000, np.random.default_rng(1))
    resampled = np.array(
        [analysis._acceptance(rng.choice(values, size=len(values), replace=True), prices) for _ in range(4000)]
    )
    assert counted.mean(axis=0) == pytest.approx(resampled.mean(axis=0), abs=0.002)
    assert counted.std(axis=0) == pytest.approx(resampled.std(axis=0), rel=0.08)


def test_order_statistic_quantile_bootstrap_matches_resampling() -> None:
    rng = np.random.default_rng(6)
    values = rng.lognormal(3.3, 0.4, size=2000)
    ordered = np.sort(values)
    for level in (0.05, 0.5, 0.95):
        exact = analysis._bootstrap_quantile_draws(ordered, level, 4000, np.random.default_rng(2))
        brute = np.array([np.quantile(rng.choice(values, size=len(values)), level) for _ in range(4000)])
        assert exact.mean() == pytest.approx(brute.mean(), rel=0.01)
        assert exact.std() == pytest.approx(brute.std(), rel=0.1)


@pytest.mark.parametrize(("mode", "demo"), [("randomized", randomized_demo), ("valuation", valuation_demo)])
def test_large_sample_bootstrap_path_is_labelled_and_consistent(monkeypatch: pytest.MonkeyPatch, mode, demo) -> None:
    standard = analyze_price(demo(), _config(mode))
    monkeypatch.setattr(analysis, "LARGE_SAMPLE_ROWS", 0)
    counted = analyze_price(demo(), _config(mode))
    assert "exact" in counted.diagnostics["bootstrap_method"].lower()
    assert counted.comparison["incremental_contribution"] == pytest.approx(standard.comparison["incremental_contribution"])
    width = standard.comparison["incremental_high"] - standard.comparison["incremental_low"]
    counted_width = counted.comparison["incremental_high"] - counted.comparison["incremental_low"]
    assert counted_width == pytest.approx(width, rel=0.25)
