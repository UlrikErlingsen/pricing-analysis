# Changelog

## 1.2.0 — 2026-10-02

Signal brand refresh and Signal Hub entry point. The analysis, statistics, data contract, decision statuses and export schemas are unchanged.

### Brand

- Display name written **Tag Signal** (with a space) in the app, README, docs, launchers, export labels and metadata. Package, file, schema and environment-variable names stay `tagsignal` / `TAGSIGNAL_*`; the bridge schema stays `signal.price-evidence.v1`. The name screen still covers the exact string “TagSignal” only; no new clearance is claimed.
- The app uses the shared `signal_theme` module (Organic Signal design, Research family colour `#a06f1f`, Figtree): sidebar lockup, masthead, hero, cards, notes, decision header, footer, Plotly template and the mark as favicon replace the pasted styles. The demand-and-economics chart keeps its meaning with theme colours (volume in the family colour, interval band in the soft neutral, contribution in ink, declared prices as dotted threshold markers).
- New banner, social preview and marks in `assets/`; the old banner SVG is removed. `.streamlit/config.toml` uses the family colours.
- README follows the Signal template; bug-report and feature-request issue templates added.

### Signal Hub contract

- `tagsignal.ui` exposes `APP_INFO` and `render()`, so Signal Hub can embed the app; `app.py` is now a thin standalone entry point.
- All session-state and widget keys are namespaced `tag:` (including the page selector).
- `streamlit` and `plotly` moved to a `ui` extra (also in `test`); the analysis core installs without them. `requirements.txt` still lists everything.
- The UI reads no repository-root files (demos and starter workbooks are generated in code, marks ship as package data), so a packaged install works inside Signal Hub.
- New tests: no Streamlit/Plotly import outside `tagsignal.ui`, `render()` runs from a script without a page config, every widget key is namespaced, no repository-root file reads, the shared shell and the README template.

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

