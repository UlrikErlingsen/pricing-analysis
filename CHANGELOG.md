# Changelog

## 1.3.0 — 2026-10-03

### Larger datasets

- Larger datasets: run locally, Tag Signal has no built-in limit on file size, rows or columns (was 50 MB, 250,000 rows and 500 columns); memory is the limit, and running out of memory gives a plain message. A public demo (`SIGNAL_PUBLIC=1`) keeps those values as demo limits, all in the new `tagsignal.limits` module, with messages that say the downloaded app has none.
- CSV is read in 250,000-row chunks and numbers are stored in the smallest lossless type (unit counts in one byte); the analysis converts every declared column to double precision. Uploaded frames are no longer copied once more after reading.
- Above 100,000 rows the bootstraps resample counts instead of rows, with exactly the same distributions: randomized arm means from multinomial counts over distinct outcome values, WTP acceptance curves from multinomial counts between grid prices, and WTP quantile uncertainty from the exact Beta distribution of resampled order statistics. The diagnostics record the method (`bootstrap_method`). At 5,000,000 rows each route takes about one to two seconds; the previous WTP bootstrap needed about 6 seconds for 250,000 rows. Smaller data keep the previous resampling and identical results.
- The app keeps the audit for the current data and contract instead of recomputing it on every rerun, and no longer re-reads and re-hashes an unchanged upload on each rerun; the analysis shows a progress spinner.
- Launchers default `TAGSIGNAL_MAX_UPLOAD_MB` to 10000 (the Windows launcher now honours it and `TAGSIGNAL_PORT`), and the Docker image sets `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000`. Signal Hub mode (`SIGNAL_HUB=1`) is unchanged.

### Suite

- Suite: Rival, Reach, Learn and Blueprint Signal added to the suite table (README) and to the theme copy's app list; `.streamlit/config.toml` carries Signal Hub's 10,000 MB upload cap.

## 1.2.0 — 2026-10-02

Signal brand refresh and Signal Hub entry point. The analysis, statistics, data contract, decision statuses and export schemas are unchanged.

### Brand

- Display name written **Tag Signal** (with a space) in the app, README, docs, launchers, export labels and metadata. Package, file, schema and environment-variable names stay `tagsignal` / `TAGSIGNAL_*`; the bridge schema stays `signal.price-evidence.v1`. The name screen still covers the exact string “TagSignal” only; no new clearance is claimed.
- The app uses the shared `signal_theme` module (Organic Signal design, Research family colour `#a06f1f`, Figtree): sidebar lockup, masthead, hero, cards, notes, decision header, footer, Plotly template and the mark as favicon replace the pasted styles. The demand-and-economics chart keeps its meaning with theme colours (volume in the family colour, interval band in the soft neutral, contribution in ink, declared prices as dotted threshold markers).
- New banner, social preview and marks in `assets/`; the old banner SVG is removed. `.streamlit/config.toml` uses the family colours.
- README follows the Signal template; bug-report and feature-request issue templates added.
- Embedded Figtree font, no Google Fonts request: the re-synced theme loads Figtree from the bundled `signal_font.py`, and the chart colorway follows the per-family contrast order.

### First run

- Opens with the fictional demo preloaded: on first run the randomized price test is loaded with its saved contract and already analysed, so every page shows results without an upload. The demo buttons still switch or restore routes, and an upload replaces the demo.

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

