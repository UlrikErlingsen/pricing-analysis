"""Deterministic fictional data for every supported evidence route."""

from __future__ import annotations

import numpy as np
import pandas as pd


def randomized_demo(seed: int = 6420) -> pd.DataFrame:
    """A fictional individually randomized posted-price test with a binary purchase outcome."""
    rng = np.random.default_rng(seed)
    prices = np.repeat(np.array([24.0, 29.0, 34.0, 39.0]), 180)
    rng.shuffle(prices)
    purchase_probability = 1 / (1 + np.exp(-(-0.15 - 0.095 * (prices - 30))))
    purchased = rng.binomial(1, purchase_probability)
    baseline_orders = np.clip(rng.poisson(2.2, len(prices)), 0, 8)
    return pd.DataFrame(
        {
            "customer_id": [f"C{i:04d}" for i in range(1, len(prices) + 1)],
            "assigned_price": prices,
            "purchased": purchased,
            "baseline_orders": baseline_orders,
        }
    )


def historical_demo(seed: int = 6421) -> pd.DataFrame:
    """A fictional weekly market series with price, distribution, and promotion variation."""
    rng = np.random.default_rng(seed)
    weeks = np.arange(1, 85)
    promotion = rng.binomial(1, 0.24, len(weeks))
    distribution = np.clip(0.72 + 0.0022 * weeks + rng.normal(0, 0.025, len(weeks)), 0.65, 0.94)
    list_price = 34.0 + 0.035 * weeks + rng.normal(0, 1.1, len(weeks))
    price = np.maximum(20.0, list_price - promotion * rng.uniform(3.0, 6.0, len(weeks)))
    season = 0.10 * np.sin(2 * np.pi * weeks / 13)
    log_quantity = (
        9.72
        - 1.38 * np.log(price)
        + 0.32 * promotion
        + 1.05 * distribution
        + season
        + rng.normal(0, 0.085, len(weeks))
    )
    quantity = np.maximum(1, np.rint(np.exp(log_quantity))).astype(int)
    return pd.DataFrame(
        {
            "period": [f"2025-W{i:02d}" for i in weeks],
            "price": np.round(price, 2),
            "quantity": quantity,
            "promotion": promotion,
            "distribution": np.round(distribution, 3),
        }
    )


def valuation_demo(seed: int = 6422) -> pd.DataFrame:
    """A fictional stated-WTP sample; values are not market transactions."""
    rng = np.random.default_rng(seed)
    segments = rng.choice(["Practical", "Enthusiast", "Occasional"], 900, p=[0.50, 0.22, 0.28])
    segment_shift = pd.Series(segments).map({"Practical": 0.0, "Enthusiast": 0.34, "Occasional": -0.24}).to_numpy()
    wtp = np.exp(rng.normal(np.log(31.0) + segment_shift, 0.30))
    wtp = np.clip(np.round(wtp, 2), 8.0, 85.0)
    return pd.DataFrame(
        {
            "respondent_id": [f"R{i:04d}" for i in range(1, len(wtp) + 1)],
            "wtp": wtp,
            "segment": segments,
        }
    )


def demo_contract(mode: str) -> dict[str, object]:
    common: dict[str, object] = {
        "mode": mode,
        "unit_cost": 11.0,
        "reference_price": 29.0,
        "candidate_price": 34.0,
        "planning_units": 30_000.0,
        "minimum_worthwhile_contribution": 12_000.0,
        "currency": "NOK",
        "bootstrap_iterations": 500,
        "seed": 20260716,
    }
    if mode == "randomized":
        common.update(
            {
                "price_col": "assigned_price",
                "quantity_col": "purchased",
                "randomized_confirmed": True,
            }
        )
    elif mode == "historical":
        common.update(
            {
                "price_col": "price",
                "quantity_col": "quantity",
                "controls": ["promotion", "distribution"],
                "planning_units": 1.0,
                "covariance": "HAC",
                "hac_lags": 4,
            }
        )
    elif mode == "valuation":
        common.update(
            {
                "wtp_col": "wtp",
                "valuation_method": "Stated hypothetical WTP",
            }
        )
    else:
        raise ValueError(f"Unknown demo mode: {mode}")
    return common


def starter_template(mode: str) -> pd.DataFrame:
    if mode == "randomized":
        return pd.DataFrame(
            {
                "unit_id": ["U001", "U002", "U003", "U004"],
                "assigned_price": [29.0, 34.0, 29.0, 34.0],
                "quantity": [1, 0, 1, 1],
            }
        )
    if mode == "historical":
        return pd.DataFrame(
            {
                "period": ["2026-01", "2026-02", "2026-03", "2026-04"],
                "price": [29.0, 31.0, 30.0, 33.0],
                "quantity": [4200, 3920, 4050, 3610],
                "promotion": [1, 0, 0, 0],
            }
        )
    if mode == "valuation":
        return pd.DataFrame({"respondent_id": ["R001", "R002", "R003"], "wtp": [28.0, 35.0, 31.0]})
    raise ValueError(f"Unknown template mode: {mode}")
