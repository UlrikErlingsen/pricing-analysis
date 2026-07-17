"""Pricing evidence audits, response estimation, and bounded economic comparisons."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .errors import DataProblem


SUPPORTED_MODES = {"historical", "randomized", "valuation"}

ZERO_THRESHOLD_REFUSAL = (
    "Set the minimum worthwhile incremental contribution above zero — with zero, the reading collapses into a "
    "bare significance statement, which TagSignal refuses to present as a decision."
)


@dataclass(frozen=True)
class PriceConfig:
    mode: str
    unit_cost: float
    reference_price: float
    candidate_price: float
    planning_units: float = 1.0
    minimum_worthwhile_contribution: float = 0.0
    currency: str = "NOK"
    price_col: str | None = None
    quantity_col: str | None = None
    wtp_col: str | None = None
    controls: tuple[str, ...] = field(default_factory=tuple)
    randomized_confirmed: bool = False
    valuation_method: str = "Stated hypothetical WTP"
    covariance: str = "HAC"
    hac_lags: int = 4
    bootstrap_iterations: int = 500
    seed: int = 20260716

    def __post_init__(self) -> None:
        if self.mode not in SUPPORTED_MODES:
            raise DataProblem("Choose historical, randomized, or valuation evidence.")
        if self.unit_cost < 0:
            raise DataProblem("Unit cost cannot be negative.")
        if self.reference_price <= 0 or self.candidate_price <= 0:
            raise DataProblem("Reference and candidate prices must be positive.")
        if self.planning_units <= 0:
            raise DataProblem("The planning multiplier or number of opportunities must be positive.")
        if self.minimum_worthwhile_contribution <= 0:
            raise DataProblem(ZERO_THRESHOLD_REFUSAL)
        if not 100 <= self.bootstrap_iterations <= 5_000:
            raise DataProblem("Use between 100 and 5,000 uncertainty draws.")
        if not 0 <= self.hac_lags <= 52:
            raise DataProblem("HAC lags must be between 0 and 52.")


@dataclass
class AuditResult:
    mode: str
    summary: dict[str, Any]
    support_table: pd.DataFrame
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass
class PriceAnalysis:
    config: PriceConfig
    evidence_tier: str
    audit: AuditResult
    coefficients: pd.DataFrame
    price_grid: pd.DataFrame
    arm_or_quantile_summary: pd.DataFrame
    diagnostics: dict[str, Any]
    optimal: dict[str, Any]
    comparison: dict[str, Any]
    warnings: tuple[str, ...]


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise DataProblem(f"Column '{column}' was not found in the table.")
    return pd.to_numeric(frame[column], errors="coerce")


def _analysis_frame(frame: pd.DataFrame, config: PriceConfig) -> pd.DataFrame:
    if config.mode in {"historical", "randomized"}:
        if not config.price_col or not config.quantity_col:
            raise DataProblem("Choose both a price column and a quantity or purchase column.")
        columns = [config.price_col, config.quantity_col, *config.controls]
    else:
        if not config.wtp_col:
            raise DataProblem("Choose a willingness-to-pay column.")
        columns = [config.wtp_col]
    if len(columns) != len(set(columns)):
        raise DataProblem("Each analytical role must use a different column.")
    data = pd.DataFrame(index=frame.index)
    for column in columns:
        data[column] = _numeric(frame, column)
    return data


def audit_price_data(frame: pd.DataFrame, config: PriceConfig) -> AuditResult:
    """Check whether the declared table can support the selected evidence route."""
    data = _analysis_frame(frame, config)
    warnings: list[str] = []
    blockers: list[str] = []
    total_rows = len(data)
    complete = data.dropna()
    omitted = total_rows - len(complete)
    if total_rows == 0:
        blockers.append("The table has no data rows.")
    if omitted:
        share = omitted / max(total_rows, 1)
        message = f"{omitted:,} row(s) ({share:.1%}) are incomplete for the declared analysis and will be omitted."
        (blockers if share > 0.25 else warnings).append(message)

    if config.mode in {"historical", "randomized"}:
        price = complete[config.price_col]  # type: ignore[index]
        quantity = complete[config.quantity_col]  # type: ignore[index]
        if (price <= 0).any():
            blockers.append("Prices must be strictly positive.")
        if (quantity < 0).any():
            blockers.append("Quantity or purchase outcomes cannot be negative.")
        usable = complete.loc[(price > 0) & (quantity >= 0)].copy()
        unique_prices = int(usable[config.price_col].nunique()) if len(usable) else 0  # type: ignore[index]
        support_min = float(usable[config.price_col].min()) if len(usable) else np.nan  # type: ignore[index]
        support_max = float(usable[config.price_col].max()) if len(usable) else np.nan  # type: ignore[index]
        price_cv = (
            float(usable[config.price_col].std(ddof=1) / usable[config.price_col].mean())  # type: ignore[index]
            if len(usable) > 1 and usable[config.price_col].mean()  # type: ignore[index]
            else np.nan
        )
        if config.mode == "historical":
            if (quantity <= 0).any():
                blockers.append("Historical log-demand estimation requires strictly positive quantities in every used row.")
            if len(usable) < 24:
                blockers.append("Historical estimation needs at least 24 complete positive-price observations.")
            if unique_prices < 6:
                blockers.append("Historical estimation needs at least six distinct observed prices.")
            if np.isfinite(price_cv) and price_cv < 0.04:
                warnings.append("Observed price variation is narrow; elasticity and distant candidate prices will be fragile.")
            warnings.append(
                "Historical price coefficients are observational associations unless a separate identification design addresses "
                "price endogeneity, promotions, seasonality, competition, and other demand shocks."
            )
            support = pd.DataFrame(
                {
                    "metric": ["Rows used", "Distinct prices", "Minimum price", "Median price", "Maximum price", "Price CV"],
                    "value": [
                        len(usable),
                        unique_prices,
                        support_min,
                        float(usable[config.price_col].median()) if len(usable) else np.nan,  # type: ignore[index]
                        support_max,
                        price_cv,
                    ],
                }
            )
        else:
            if len(usable) < 40:
                blockers.append("A randomized price test needs at least 40 complete units in this release.")
            if unique_prices < 2:
                blockers.append("A randomized price test needs at least two assigned price arms.")
            arm = (
                usable.groupby(config.price_col, observed=True)[config.quantity_col]  # type: ignore[arg-type]
                .agg(n="size", mean_quantity="mean", sd_quantity="std")
                .reset_index()
                .rename(columns={config.price_col: "price"})
                .sort_values("price")
            )
            if len(arm) and (arm["n"] < 15).any():
                warnings.append("At least one assigned-price arm has fewer than 15 observed units.")
            if len(arm) and (arm["mean_quantity"] <= 0).any():
                blockers.append("Every price arm needs a positive mean quantity to estimate the power demand curve.")
            if not config.randomized_confirmed:
                warnings.append("Random assignment was not confirmed; the result will be labeled association only.")
            support = arm
        summary = {
            "rows_received": total_rows,
            "complete_rows": len(complete),
            "rows_used": len(usable),
            "distinct_prices": unique_prices,
            "support_min": support_min,
            "support_max": support_max,
            "price_cv": price_cv,
        }
    else:
        wtp = complete[config.wtp_col]  # type: ignore[index]
        if (wtp <= 0).any():
            blockers.append("Willingness-to-pay values must be strictly positive.")
        usable = complete.loc[wtp > 0].copy()
        if len(usable) < 50:
            blockers.append("The valuation route needs at least 50 complete respondent-level WTP values.")
        if len(usable) and usable[config.wtp_col].nunique() < 8:  # type: ignore[index]
            warnings.append("WTP has few distinct values; the acceptance and profit curves will be step-like.")
        if "stated" in config.valuation_method.casefold() or "hypothetical" in config.valuation_method.casefold():
            warnings.append(
                "Stated WTP is a hypothetical valuation distribution, not an observed market demand curve; hypothetical bias "
                "and context sensitivity remain material."
            )
        else:
            warnings.append(
                "An incentive-compatible elicitation can strengthen value revelation under its protocol, but it still does not "
                "recreate market availability, repeat purchase, competition, or long-run demand."
            )
        quantiles = usable[config.wtp_col].quantile([0.05, 0.25, 0.5, 0.75, 0.95])  # type: ignore[index]
        support = pd.DataFrame(
            {
                "quantile": ["5%", "25%", "50%", "75%", "95%"],
                "wtp": quantiles.to_numpy(dtype=float),
            }
        )
        summary = {
            "rows_received": total_rows,
            "complete_rows": len(complete),
            "rows_used": len(usable),
            "distinct_values": int(usable[config.wtp_col].nunique()) if len(usable) else 0,  # type: ignore[index]
            "support_min": 0.0,
            "support_max": float(usable[config.wtp_col].max()) if len(usable) else np.nan,  # type: ignore[index]
            "median_wtp": float(usable[config.wtp_col].median()) if len(usable) else np.nan,  # type: ignore[index]
        }

    support_min = summary.get("support_min")
    support_max = summary.get("support_max")
    if isinstance(support_min, (float, int)) and isinstance(support_max, (float, int)):
        if np.isfinite(support_min) and np.isfinite(support_max):
            if not support_min <= config.candidate_price <= support_max:
                warnings.append("The candidate price is outside the observed evidence range.")
            if not support_min <= config.reference_price <= support_max:
                warnings.append("The reference price is outside the observed evidence range.")
    if config.candidate_price <= config.unit_cost:
        warnings.append("The candidate price does not exceed declared unit cost before any other variable costs.")
    return AuditResult(config.mode, summary, support, tuple(dict.fromkeys(warnings)), tuple(dict.fromkeys(blockers)))


def _weighted_log_curve(prices: np.ndarray, means: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x = np.column_stack([np.ones(len(prices)), np.log(prices)])
    root_w = np.sqrt(weights)[:, None]
    beta, *_ = np.linalg.lstsq(x * root_w, np.log(means) * root_w[:, 0], rcond=None)
    return beta


def _psd(covariance: np.ndarray) -> np.ndarray:
    covariance = (covariance + covariance.T) / 2
    values, vectors = np.linalg.eigh(covariance)
    values = np.clip(values, 1e-12, None)
    return (vectors * values) @ vectors.T


def _price_grid(support_min: float, support_max: float, config: PriceConfig, points: int = 81) -> np.ndarray:
    lower = max(0.01, support_min)
    grid = np.linspace(lower, support_max, points)
    return np.unique(np.concatenate([grid, [config.reference_price, config.candidate_price]])).astype(float)


def _decision_status(
    point: float,
    low: float,
    high: float,
    threshold: float,
    within_support: bool,
) -> tuple[str, str]:
    if not within_support:
        return (
            "OUTSIDE EVIDENCE RANGE",
            "The candidate or reference price requires extrapolation beyond the observed evidence. Treat the comparison as a scenario, not a supported decision.",
        )
    if high < 0:
        return "POTENTIAL HARM", "The full uncertainty interval is below zero incremental contribution."
    if low > threshold:
        return "MEANINGFUL UPSIDE", "The full interval clears the declared minimum worthwhile contribution."
    if low > 0:
        return "SUPPORTED UPSIDE", "The full interval is positive but does not clear the declared worthwhile threshold."
    if point > 0:
        return "UNCERTAIN UPSIDE", "The point estimate is positive, but the interval includes no improvement."
    if low < 0 < high:
        return "NO CLEAR ADVANTAGE", "The interval includes both improvement and harm."
    return "NO EVIDENCE OF UPSIDE", "The candidate does not improve expected contribution in this model."


def classify_decision(
    point: float,
    low: float,
    high: float,
    threshold: float,
    within_support: bool = True,
) -> dict[str, str]:
    """Public decision classifier used by the app and analytical fixtures.

    ``threshold`` must be declared explicitly and must be positive: with a zero threshold,
    MEANINGFUL UPSIDE would collapse into a bare significance statement.
    """
    if threshold <= 0:
        raise DataProblem(ZERO_THRESHOLD_REFUSAL)
    status, explanation = _decision_status(point, low, high, threshold, within_support)
    return {"status": status, "explanation": explanation}


def _summarize_grid(
    prices: np.ndarray,
    quantity_point: np.ndarray,
    quantity_draws: np.ndarray,
    config: PriceConfig,
) -> tuple[pd.DataFrame, np.ndarray]:
    projected_point = quantity_point * config.planning_units
    projected_draws = quantity_draws * config.planning_units
    margin = prices - config.unit_cost
    contribution_draws = projected_draws * margin[None, :]
    contribution_point = projected_point * margin
    frame = pd.DataFrame(
        {
            "price": prices,
            "unit_margin": margin,
            "expected_quantity_per_planning_unit": quantity_point,
            "projected_volume": projected_point,
            "volume_low": np.quantile(projected_draws, 0.025, axis=0),
            "volume_high": np.quantile(projected_draws, 0.975, axis=0),
            "expected_contribution": contribution_point,
            "contribution_low": np.quantile(contribution_draws, 0.025, axis=0),
            "contribution_high": np.quantile(contribution_draws, 0.975, axis=0),
        }
    )
    return frame, contribution_draws


def _comparison_and_optimum(
    grid: pd.DataFrame,
    contribution_draws: np.ndarray,
    config: PriceConfig,
    support_min: float,
    support_max: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    prices = grid["price"].to_numpy(dtype=float)
    ref_index = int(np.argmin(np.abs(prices - config.reference_price)))
    candidate_index = int(np.argmin(np.abs(prices - config.candidate_price)))
    differences = contribution_draws[:, candidate_index] - contribution_draws[:, ref_index]
    point = float(
        grid.iloc[candidate_index]["expected_contribution"] - grid.iloc[ref_index]["expected_contribution"]
    )
    low, high = np.quantile(differences, [0.025, 0.975])
    within_support = bool(
        support_min <= config.reference_price <= support_max and support_min <= config.candidate_price <= support_max
    )
    classified = classify_decision(point, float(low), float(high), config.minimum_worthwhile_contribution, within_support)
    comparison: dict[str, Any] = {
        **classified,
        "reference_price": config.reference_price,
        "candidate_price": config.candidate_price,
        "reference_volume": float(grid.iloc[ref_index]["projected_volume"]),
        "candidate_volume": float(grid.iloc[candidate_index]["projected_volume"]),
        "reference_contribution": float(grid.iloc[ref_index]["expected_contribution"]),
        "candidate_contribution": float(grid.iloc[candidate_index]["expected_contribution"]),
        "incremental_contribution": point,
        "incremental_low": float(low),
        "incremental_high": float(high),
        "minimum_worthwhile_contribution": config.minimum_worthwhile_contribution,
        "within_observed_support": within_support,
    }
    point_optimum_index = int(grid["expected_contribution"].to_numpy().argmax())
    draw_optimum_prices = prices[np.argmax(contribution_draws, axis=1)]
    optimal = {
        "point_price": float(prices[point_optimum_index]),
        "point_contribution": float(grid.iloc[point_optimum_index]["expected_contribution"]),
        "price_draw_median": float(np.median(draw_optimum_prices)),
        "price_draw_low": float(np.quantile(draw_optimum_prices, 0.025)),
        "price_draw_high": float(np.quantile(draw_optimum_prices, 0.975)),
        "at_support_boundary": bool(point_optimum_index in {0, len(prices) - 1}),
    }
    return comparison, optimal


def _analyze_historical(frame: pd.DataFrame, config: PriceConfig, audit: AuditResult) -> PriceAnalysis:
    data = _analysis_frame(frame, config).dropna()
    data = data.loc[(data[config.price_col] > 0) & (data[config.quantity_col] > 0)].copy()  # type: ignore[index]
    y = np.log(data[config.quantity_col].to_numpy(dtype=float))  # type: ignore[index]
    x_data: dict[str, np.ndarray] = {"log_price": np.log(data[config.price_col].to_numpy(dtype=float))}  # type: ignore[index]
    for control in config.controls:
        x_data[control] = data[control].to_numpy(dtype=float)
    x = sm.add_constant(pd.DataFrame(x_data), has_constant="add")
    model = sm.OLS(y, x)
    if config.covariance.upper() == "HAC":
        fit = model.fit(cov_type="HAC", cov_kwds={"maxlags": config.hac_lags})
        covariance_label = f"Newey–West HAC ({config.hac_lags} lag{'s' if config.hac_lags != 1 else ''})"
    else:
        fit = model.fit(cov_type="HC3")
        covariance_label = "HC3 heteroskedasticity-consistent"
    smearing = float(np.mean(np.exp(fit.resid)))
    support_min = float(audit.summary["support_min"])
    support_max = float(audit.summary["support_max"])
    prices = _price_grid(support_min, support_max, config)
    names = list(x.columns)
    means = {control: float(data[control].mean()) for control in config.controls}
    base_vector = np.array([1.0, np.log(config.reference_price), *[means[name] for name in config.controls]])
    if names != ["const", "log_price", *config.controls]:
        raise DataProblem("Internal historical design columns did not match the declared contract.")
    prediction_x = np.column_stack(
        [
            np.ones(len(prices)),
            np.log(prices),
            *[np.full(len(prices), means[control]) for control in config.controls],
        ]
    )
    params = np.asarray(fit.params, dtype=float)
    quantity_point = smearing * np.exp(prediction_x @ params)
    rng = np.random.default_rng(config.seed)
    draws = rng.multivariate_normal(
        params,
        _psd(np.asarray(fit.cov_params(), dtype=float)),
        size=config.bootstrap_iterations,
        check_valid="ignore",
    )
    quantity_draws = smearing * np.exp(draws @ prediction_x.T)
    grid, contribution_draws = _summarize_grid(prices, quantity_point, quantity_draws, config)
    comparison, optimal = _comparison_and_optimum(
        grid, contribution_draws, config, support_min=support_min, support_max=support_max
    )
    confidence = np.asarray(fit.conf_int(alpha=0.05), dtype=float)
    coefficients = pd.DataFrame(
        {
            "term": names,
            "estimate": params,
            "robust_se": np.asarray(fit.bse, dtype=float),
            "low_95": confidence[:, 0],
            "high_95": confidence[:, 1],
        }
    )
    warnings = list(audit.warnings)
    elasticity = float(params[names.index("log_price")])
    if elasticity >= 0:
        warnings.append("Estimated historical price elasticity is non-negative; omitted demand shocks or weak variation may dominate.")
    if optimal["at_support_boundary"]:
        warnings.append("The model's highest contribution occurs at an observed-price boundary; it does not identify an interior optimum.")
    diagnostics = {
        "n": int(fit.nobs),
        "r_squared": float(fit.rsquared),
        "adjusted_r_squared": float(fit.rsquared_adj),
        "elasticity": elasticity,
        "elasticity_low": float(confidence[names.index("log_price"), 0]),
        "elasticity_high": float(confidence[names.index("log_price"), 1]),
        "covariance": covariance_label,
        "smearing_factor": smearing,
        "controls_held_at": means,
        "reference_prediction_vector": base_vector.tolist(),
    }
    return PriceAnalysis(
        config,
        "ASSOCIATION ONLY",
        audit,
        coefficients,
        grid,
        audit.support_table,
        diagnostics,
        optimal,
        comparison,
        tuple(dict.fromkeys(warnings)),
    )


def _analyze_randomized(frame: pd.DataFrame, config: PriceConfig, audit: AuditResult) -> PriceAnalysis:
    data = _analysis_frame(frame, config).dropna()
    data = data.loc[(data[config.price_col] > 0) & (data[config.quantity_col] >= 0)].copy()  # type: ignore[index]
    grouped = [group for _, group in data.groupby(config.price_col, sort=True, observed=True)]  # type: ignore[arg-type]
    arm_prices = np.array([float(group[config.price_col].iloc[0]) for group in grouped])  # type: ignore[index]
    arm_means = np.array([float(group[config.quantity_col].mean()) for group in grouped])  # type: ignore[index]
    arm_n = np.array([len(group) for group in grouped], dtype=float)
    beta = _weighted_log_curve(arm_prices, arm_means, arm_n)
    support_min = float(arm_prices.min())
    support_max = float(arm_prices.max())
    prices = _price_grid(support_min, support_max, config)
    binary_like = bool(set(np.unique(data[config.quantity_col].to_numpy(dtype=float))).issubset({0.0, 1.0}))  # type: ignore[index]
    quantity_point = np.exp(beta[0] + beta[1] * np.log(prices))
    if binary_like:
        quantity_point = np.clip(quantity_point, 0, 1)
    rng = np.random.default_rng(config.seed)
    bootstrap_betas: list[np.ndarray] = []
    attempts = 0
    while len(bootstrap_betas) < config.bootstrap_iterations and attempts < config.bootstrap_iterations * 4:
        attempts += 1
        sampled_means = []
        for group in grouped:
            values = group[config.quantity_col].to_numpy(dtype=float)  # type: ignore[index]
            sampled_means.append(float(np.mean(rng.choice(values, size=len(values), replace=True))))
        sampled = np.asarray(sampled_means)
        if np.all(sampled > 0):
            bootstrap_betas.append(_weighted_log_curve(arm_prices, sampled, arm_n))
    if len(bootstrap_betas) < 100:
        raise DataProblem("Too many resampled price arms had zero mean quantity; uncertainty could not be estimated reliably.")
    discarded_resamples = attempts - len(bootstrap_betas)
    beta_draws = np.vstack(bootstrap_betas)
    quantity_draws = np.exp(beta_draws[:, [0]] + beta_draws[:, [1]] * np.log(prices)[None, :])
    if binary_like:
        quantity_draws = np.clip(quantity_draws, 0, 1)
    grid, contribution_draws = _summarize_grid(prices, quantity_point, quantity_draws, config)
    comparison, optimal = _comparison_and_optimum(
        grid, contribution_draws, config, support_min=support_min, support_max=support_max
    )
    elasticity_draws = beta_draws[:, 1]
    coefficients = pd.DataFrame(
        {
            "term": ["log intercept", "price elasticity"],
            "estimate": beta,
            "bootstrap_se": np.std(beta_draws, axis=0, ddof=1),
            "low_95": np.quantile(beta_draws, 0.025, axis=0),
            "high_95": np.quantile(beta_draws, 0.975, axis=0),
        }
    )
    warnings = list(audit.warnings)
    if discarded_resamples:
        discard_share = discarded_resamples / attempts
        warnings.append(
            f"{discard_share:.1%} of bootstrap resamples were discarded because an arm mean was non-positive; "
            "the interval is conditioned on positive demand and may be too narrow near zero purchase rates."
        )
    if beta[1] >= 0:
        warnings.append("The fitted price-response slope is non-negative; verify execution, sampling variation, and demand conditions.")
    if len(arm_prices) == 2:
        warnings.append("Two price arms identify only one power-curve slope; curvature cannot be checked.")
    if optimal["at_support_boundary"]:
        warnings.append("The model's highest contribution is at a tested-price boundary; test another bounded price before extrapolating.")
    evidence_tier = "RANDOMIZED PRICE EVIDENCE" if config.randomized_confirmed else "ASSOCIATION ONLY"
    diagnostics = {
        "n": int(len(data)),
        "price_arms": int(len(arm_prices)),
        "elasticity": float(beta[1]),
        "elasticity_low": float(np.quantile(elasticity_draws, 0.025)),
        "elasticity_high": float(np.quantile(elasticity_draws, 0.975)),
        "bootstrap_draws": int(len(beta_draws)),
        "binary_purchase_outcome": binary_like,
        "functional_form": "Power curve fitted to assigned-price arm means",
    }
    return PriceAnalysis(
        config,
        evidence_tier,
        audit,
        coefficients,
        grid,
        audit.support_table,
        diagnostics,
        optimal,
        comparison,
        tuple(dict.fromkeys(warnings)),
    )


def _acceptance(values: np.ndarray, prices: np.ndarray) -> np.ndarray:
    ordered = np.sort(values)
    first_acceptable = np.searchsorted(ordered, prices, side="left")
    return (len(ordered) - first_acceptable) / len(ordered)


def _analyze_valuation(frame: pd.DataFrame, config: PriceConfig, audit: AuditResult) -> PriceAnalysis:
    data = _analysis_frame(frame, config).dropna()
    values = data.loc[data[config.wtp_col] > 0, config.wtp_col].to_numpy(dtype=float)  # type: ignore[index]
    support_min = 0.0
    support_max = float(values.max())
    lower = max(0.01, min(config.unit_cost, config.reference_price, config.candidate_price, float(values.min())))
    prices = _price_grid(lower, support_max, config, points=101)
    quantity_point = _acceptance(values, prices)
    rng = np.random.default_rng(config.seed)
    quantity_draws = np.empty((config.bootstrap_iterations, len(prices)), dtype=float)
    for index in range(config.bootstrap_iterations):
        sample = rng.choice(values, size=len(values), replace=True)
        quantity_draws[index] = _acceptance(sample, prices)
    grid, contribution_draws = _summarize_grid(prices, quantity_point, quantity_draws, config)
    comparison, optimal = _comparison_and_optimum(
        grid, contribution_draws, config, support_min=support_min, support_max=support_max
    )
    quantile_levels = np.array([0.05, 0.25, 0.5, 0.75, 0.95])
    quantiles = np.quantile(values, quantile_levels)
    coefficients = pd.DataFrame(
        {
            "term": [f"WTP {level:.0%}" for level in quantile_levels],
            "estimate": quantiles,
            "bootstrap_se": [
                np.std(
                    [np.quantile(rng.choice(values, size=len(values), replace=True), level) for _ in range(200)],
                    ddof=1,
                )
                for level in quantile_levels
            ],
        }
    )
    warnings = list(audit.warnings)
    if optimal["at_support_boundary"]:
        warnings.append("The highest modeled contribution is at the valuation support boundary; the price optimum is not bounded.")
    incentive = "incentive" in config.valuation_method.casefold() or "auction" in config.valuation_method.casefold()
    evidence_tier = "INCENTIVE-COMPATIBLE VALUATION" if incentive else "STATED VALUATION"
    diagnostics = {
        "n": int(len(values)),
        "median_wtp": float(np.median(values)),
        "mean_wtp": float(np.mean(values)),
        "valuation_method": config.valuation_method,
        "bootstrap_draws": config.bootstrap_iterations,
        "demand_interpretation": "Empirical share with WTP at or above price; not observed market conversion",
    }
    return PriceAnalysis(
        config,
        evidence_tier,
        audit,
        coefficients,
        grid,
        audit.support_table,
        diagnostics,
        optimal,
        comparison,
        tuple(dict.fromkeys(warnings)),
    )


def analyze_price(frame: pd.DataFrame, config: PriceConfig) -> PriceAnalysis:
    """Run the selected evidence route after a shared audit."""
    audit = audit_price_data(frame, config)
    if audit.blockers:
        raise DataProblem(" ".join(audit.blockers))
    if config.mode == "historical":
        return _analyze_historical(frame, config, audit)
    if config.mode == "randomized":
        return _analyze_randomized(frame, config, audit)
    return _analyze_valuation(frame, config, audit)
