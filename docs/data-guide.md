# Data guide

PriceSignal accepts CSV, XLSX, or JSON. A JSON file must be an array of row objects or an object with a `data` array. The first Excel worksheet is read. The local upload limit is 50 MB, 250,000 rows, and 500 columns.

## Shared rules

- Use one observation per analytical unit: assigned customer, historical period, or respondent.
- Prices, quantities, controls, and WTP must be numeric.
- Prices and WTP must be strictly positive. Randomized quantities may be zero; historical log-demand quantities must be positive.
- Keep one currency and one planning horizon throughout the contract.
- Remove names, emails, free text, direct identifiers, and unnecessary protected characteristics.
- Rows incomplete on any declared analytical column are omitted. More than 25% incomplete rows block analysis.

## Randomized assigned-price test

Required columns are assigned price and a non-negative outcome. The outcome can be purchase (`0/1`) or quantity per assigned unit. Use the assigned price, not the price finally chosen or observed after noncompliance.

This release requires at least 40 complete units, two distinct price arms, and a positive mean outcome in every arm. Arms below 15 observations receive a warning. Confirm randomization only when the assignment process is known and auditable.

The market-opportunity input scales the estimated per-unit demand. If the experimental outcome is purchase probability, enter the relevant number of purchase opportunities—not total population without eligibility or availability adjustments.

## Historical price–quantity series

Required columns are positive price and positive quantity. Optional controls must be numeric. Common controls include promotion, distribution, season indicators, category demand, and competitor price, but the right controls depend on the data-generating process.

This release requires at least 24 complete rows and six distinct prices. Rows should share a stable quantity definition and time interval. The planning multiplier defaults to one because historical quantity is normally already expressed per planning period.

Ordering the rows chronologically matters when HAC uncertainty is used. PriceSignal does not parse or sort a period label; prepare the file in the intended order before upload.

## Respondent-level WTP

Use one positive maximum WTP per respondent for the same product description, quantity, currency, and purchase context. Do not mix willingness to accept with willingness to pay.

This release requires at least 50 complete respondents. The empirical acceptance curve gives the sample share with WTP at or above each price. It does not model awareness, availability, repeat purchase, competition, strategic answering, or hypothetical bias.

Choose **Incentive-compatible BDM or auction** only when the implemented protocol actually connected truthful revelation to a real purchase opportunity under the method's assumptions.

## Economic fields

- **Unit cost:** the incremental cost applicable to one unit sold. Include channel or fulfillment costs when they vary with sales.
- **Reference price:** the current, control, or otherwise defensible comparison price.
- **Candidate price:** the price written into the decision contract before reading the result.
- **Planning multiplier / opportunities:** converts the modeled outcome into projected volume.
- **Minimum worthwhile contribution:** the smallest total incremental contribution that would justify acting, before implementation costs and omitted risks. It must be above zero; PriceSignal refuses a zero threshold because it would turn the decision reading into a bare significance statement.

