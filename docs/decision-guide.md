# Decision guide

PriceSignal compares a declared candidate price with a reference price. It does not automatically adopt the price with the largest point estimate.

## Read in this order

1. **Evidence tier:** randomized price evidence, association only, stated valuation, or incentive-compatible valuation.
2. **Support:** whether both declared prices lie inside the observed price or WTP range.
3. **Audit:** missingness, arm sizes, price variation, and design warnings.
4. **Demand or acceptance:** the modeled volume effect and its functional-form limits.
5. **Economics:** unit margin, projected volume, expected contribution, and interval.
6. **Decision status:** comparison with zero and the predeclared worthwhile threshold.

## Status meanings

- **MEANINGFUL UPSIDE:** the 95% interval for candidate-minus-reference contribution is entirely above the declared threshold.
- **SUPPORTED UPSIDE:** the interval is entirely positive but does not clear the threshold.
- **UNCERTAIN UPSIDE:** the point estimate is positive but the interval includes no improvement.
- **NO CLEAR ADVANTAGE:** plausible results include both improvement and harm.
- **NO EVIDENCE OF UPSIDE:** the candidate does not improve modeled contribution.
- **POTENTIAL HARM:** the full interval is below zero.
- **OUTSIDE EVIDENCE RANGE:** at least one declared price requires extrapolation.

The interval contains modeled sampling uncertainty. It does not automatically include competitor response, capacity, stock-outs, retention, brand effects, tax, channel conflict, implementation errors, legal risk, fairness, or model-selection uncertainty.

## Boundary optima

If the highest modeled contribution is at the minimum or maximum supported price, the data do not identify an interior optimum. The appropriate next action is usually a bounded test at another defensible price—not extrapolation.

## Responsible pricing

PriceSignal is not a personalized dynamic-pricing engine. Do not use protected characteristics or proxies to set individual prices. Review consumer-protection, disclosure, competition, discrimination, contract, and sector-specific requirements with qualified experts. A numerically profitable price can still be unfair, illegal, strategically destructive, or inconsistent with the brand.

