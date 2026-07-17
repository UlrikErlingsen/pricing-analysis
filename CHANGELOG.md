# Changelog

## 1.1.0 — 2026-07-17

- Renamed from PriceSignal to TagSignal after the working name was found to collide with an active commercial pricing-intelligence product. No analytical changes.

## 1.0.1 — 2026-07-16

### Security

- Export sanitizer now also neutralizes formula-like column headers and strips control characters; Docker images keep application code root-owned; defusedxml hardens workbook XML parsing. The user-typed currency label is HTML-escaped in the decision-contract note.

## 1.0.0 — 2026-07-16

- Added randomized assigned-price analysis with arm audits and stratified bootstrap uncertainty.
- Added historical log–log demand association with HAC or HC3 covariance and smearing retransformation.
- Added stated and incentive-compatible WTP valuation routes with respondent bootstrap.
- Added bounded demand, volume, margin, and contribution scenarios.
- Added predeclared candidate-versus-reference statuses based on practical contribution thresholds.
- Required a positive minimum worthwhile contribution at every layer (contract, classifier, app input) so the decision reading cannot collapse into a bare significance statement.
- Reported the bootstrap discard share whenever randomized resamples with non-positive arm means are dropped.
- Added privacy-minimized JSON, XLSX, CSV-ZIP, and GateSignal-bridge exports.
- Added deterministic fictional examples, launchers, container packaging, documentation, and analytical fixtures.

