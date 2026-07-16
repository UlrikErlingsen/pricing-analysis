# Methods

## Randomized assigned-price route

For each assigned price arm, PriceSignal calculates the mean non-negative quantity or purchase outcome. It fits

`log(mean quantity) = intercept + elasticity × log(price)`

using arm counts as weights. The fitted slope is a constant price elasticity. Uncertainty comes from resampling units with replacement **within each assigned arm**, recomputing arm means, and refitting the curve. This preserves the realized arm sizes.

With two arms the slope is identified, but curvature cannot be checked. With several arms the power curve remains a restriction. The app clips fitted values to `[0, 1]` when the observed outcome is binary.

## Historical route

The model is

`log(quantity_t) = β0 + β1 log(price_t) + controls_t β + error_t`.

`β1` is reported as a constant-elasticity association. Controls are held at their sample means for the displayed price grid. PriceSignal supports Newey–West HAC covariance with a declared lag count or HC3 covariance. It uses Duan's smearing factor, the mean of `exp(residual)`, when retranslating fitted log quantity.

Coefficient draws from the robust covariance matrix propagate parameter uncertainty through volume and contribution. They do not repair a misspecified conditional mean or identify an endogenous price coefficient. The smearing factor is held fixed across coefficient draws, so its own sampling uncertainty is not propagated into the intervals.

## WTP route

For a price `p`, empirical acceptance is

`A(p) = count(WTP_i ≥ p) / n`.

Respondents are bootstrapped with replacement. This creates an uncertainty distribution for acceptance, projected volume, contribution, and the price with the highest modeled contribution over the displayed grid.

This is a valuation scenario. It equates a respondent's declared reservation price with acceptance under the study context, which is not the same as observed purchase in a market.

## Economic layer

For every route:

`projected volume(p) = modeled quantity(p) × planning units`

`contribution(p) = projected volume(p) × (p − unit cost)`

PriceSignal compares candidate and reference contribution draw by draw. The 2.5th and 97.5th percentiles form the displayed interval. No p-value controls the action status.

The declared minimum worthwhile contribution must be above zero. With a zero threshold, MEANINGFUL UPSIDE would reduce to "the interval excludes zero" — a bare significance statement — so PriceSignal refuses to run the comparison until a positive threshold is declared. MEANINGFUL UPSIDE requires the interval lower bound to lie strictly above that threshold.

In the randomized route, bootstrap resamples in which any arm mean is non-positive cannot support the log-curve refit and are discarded; when this happens, PriceSignal reports the discard share and notes that the interval is conditioned on positive demand.

## Reproducibility

The fictional examples and uncertainty draws use fixed seeds. The evidence pack stores the source fingerprint, contract, evidence tier, settings, diagnostics, aggregate tables, warnings, and decision. It deliberately excludes row-level evidence.

