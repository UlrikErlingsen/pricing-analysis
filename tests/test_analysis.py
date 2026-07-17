from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tagsignal.analysis import PriceConfig, analyze_price, audit_price_data, classify_decision
from tagsignal.errors import DataProblem
from tagsignal.examples import demo_contract, historical_demo, randomized_demo, valuation_demo


def config(mode: str, **overrides) -> PriceConfig:
    values = demo_contract(mode)
    values.update(overrides)
    values["controls"] = tuple(values.get("controls", ()))
    return PriceConfig(**values)


def test_randomized_demo_recovers_downward_price_response_deterministically() -> None:
    result = analyze_price(randomized_demo(), config("randomized", bootstrap_iterations=300))
    assert result.evidence_tier == "RANDOMIZED PRICE EVIDENCE"
    assert result.diagnostics["elasticity"] < 0
    assert result.diagnostics["price_arms"] == 4
    assert result.diagnostics["bootstrap_draws"] == 300
    assert result.price_grid["price"].min() == pytest.approx(24.0)
    assert result.price_grid["price"].max() == pytest.approx(39.0)
    assert np.isfinite(result.price_grid["expected_contribution"]).all()


def test_unconfirmed_randomization_is_labeled_association_only() -> None:
    result = analyze_price(
        randomized_demo(), config("randomized", randomized_confirmed=False, bootstrap_iterations=150)
    )
    assert result.evidence_tier == "ASSOCIATION ONLY"
    assert any("not confirmed" in warning for warning in result.warnings)


def test_historical_demo_recovers_plausible_constant_elasticity() -> None:
    result = analyze_price(historical_demo(), config("historical", bootstrap_iterations=250))
    assert result.evidence_tier == "ASSOCIATION ONLY"
    assert -2.2 < result.diagnostics["elasticity"] < -0.7
    assert result.diagnostics["covariance"].startswith("Newey")
    assert result.diagnostics["r_squared"] > 0.55
    assert result.diagnostics["smearing_factor"] > 0


def test_valuation_curve_is_empirical_and_monotone() -> None:
    result = analyze_price(valuation_demo(), config("valuation", bootstrap_iterations=200))
    quantities = result.price_grid["expected_quantity_per_planning_unit"].to_numpy()
    assert result.evidence_tier == "STATED VALUATION"
    assert np.all(np.diff(quantities) <= 1e-12)
    median = result.diagnostics["median_wtp"]
    index = (result.price_grid["price"] - median).abs().idxmin()
    assert 0.40 <= result.price_grid.loc[index, "expected_quantity_per_planning_unit"] <= 0.60
    assert any("hypothetical" in warning.casefold() for warning in result.warnings)


@pytest.mark.parametrize(
    ("point", "low", "high", "threshold", "support", "expected"),
    [
        (50, 25, 80, 20, True, "MEANINGFUL UPSIDE"),
        (50, 20, 80, 20, True, "SUPPORTED UPSIDE"),  # lower bound exactly at threshold does not clear it
        (12, 3, 18, 20, True, "SUPPORTED UPSIDE"),
        (12, -4, 30, 10, True, "UNCERTAIN UPSIDE"),
        (-2, -15, 9, 5, True, "NO CLEAR ADVANTAGE"),
        (-1, -5, 0, 5, True, "NO EVIDENCE OF UPSIDE"),
        (0, 0, 0, 5, True, "NO EVIDENCE OF UPSIDE"),
        (-12, -20, -2, 5, True, "POTENTIAL HARM"),
        (50, 25, 80, 20, False, "OUTSIDE EVIDENCE RANGE"),
    ],
)
def test_decision_boundaries(point, low, high, threshold, support, expected) -> None:
    assert classify_decision(point, low, high, threshold, support)["status"] == expected


def test_zero_worthwhile_threshold_is_refused_at_every_layer() -> None:
    with pytest.raises(DataProblem, match="above zero"):
        config("randomized", minimum_worthwhile_contribution=0.0)
    with pytest.raises(DataProblem, match="above zero"):
        config("randomized", minimum_worthwhile_contribution=-5.0)
    with pytest.raises(DataProblem, match="above zero"):
        classify_decision(10.0, 5.0, 20.0, 0.0, True)
    with pytest.raises(TypeError):
        classify_decision(10.0, 5.0, 20.0)  # type: ignore[call-arg]  # threshold must be explicit


def test_bootstrap_discard_share_is_reported_near_zero_purchase_rates() -> None:
    rare = pd.DataFrame(
        {
            "assigned_price": [10.0] * 20 + [20.0] * 20,
            "purchased": [1] + [0] * 19 + [1] * 10 + [0] * 10,
        }
    )
    result = analyze_price(
        rare,
        PriceConfig(
            mode="randomized",
            price_col="assigned_price",
            quantity_col="purchased",
            unit_cost=2.0,
            reference_price=10.0,
            candidate_price=20.0,
            minimum_worthwhile_contribution=50.0,
            randomized_confirmed=True,
            bootstrap_iterations=100,
        ),
    )
    assert any("bootstrap resamples were discarded" in warning for warning in result.warnings)
    assert any("conditioned on positive demand" in warning for warning in result.warnings)


def test_demo_randomized_run_reports_no_bootstrap_discards() -> None:
    result = analyze_price(randomized_demo(), config("randomized", bootstrap_iterations=150))
    assert not any("discarded" in warning for warning in result.warnings)


def test_historical_audit_blocks_zero_quantity_and_short_series() -> None:
    frame = pd.DataFrame({"price": [10, 11, 12], "quantity": [3, 0, 2]})
    audit = audit_price_data(
        frame,
        PriceConfig(
            mode="historical",
            price_col="price",
            quantity_col="quantity",
            unit_cost=2,
            reference_price=10,
            candidate_price=11,
            minimum_worthwhile_contribution=100.0,
            bootstrap_iterations=100,
        ),
    )
    assert audit.blockers
    with pytest.raises(DataProblem):
        analyze_price(
            frame,
            PriceConfig(
                mode="historical",
                price_col="price",
                quantity_col="quantity",
                unit_cost=2,
                reference_price=10,
                candidate_price=11,
                minimum_worthwhile_contribution=100.0,
                bootstrap_iterations=100,
            ),
        )

