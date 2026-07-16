from __future__ import annotations

import pandas as pd

from pricesignal.examples import historical_demo, randomized_demo, starter_template, valuation_demo


def test_examples_are_deterministic_and_have_expected_shapes() -> None:
    pd.testing.assert_frame_equal(randomized_demo(), randomized_demo())
    pd.testing.assert_frame_equal(historical_demo(), historical_demo())
    pd.testing.assert_frame_equal(valuation_demo(), valuation_demo())
    assert len(randomized_demo()) == 720
    assert len(historical_demo()) == 84
    assert len(valuation_demo()) == 900


def test_each_starter_template_is_rectangular() -> None:
    for mode in ("randomized", "historical", "valuation"):
        frame = starter_template(mode)
        assert not frame.empty
        assert frame.columns.is_unique

