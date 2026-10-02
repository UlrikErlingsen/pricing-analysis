"""Tag Signal Streamlit UI.

Everything that draws the app runs inside ``render()`` (or the functions it calls), so it runs on every rerun,
both in the standalone ``app.py`` and inside Signal Hub. Module-level code here only defines constants and
functions. ``render()`` never calls ``st.set_page_config`` or ``st.navigation``.

The UI reads no files from the repository root: demos and starter templates are generated in code and the marks
ship as package data, so a packaged (non-editable) install inside Signal Hub works the same as the dev checkout.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import traceback

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from tagsignal import __version__
from tagsignal.analysis import PriceConfig, analyze_price, audit_price_data
from tagsignal.errors import DataProblem, friendly_message
from tagsignal.examples import demo_contract, historical_demo, randomized_demo, starter_template, valuation_demo
from tagsignal.io import (
    build_evidence_pack,
    build_gate_bridge,
    dataframe_to_xlsx,
    evidence_to_csv_zip,
    evidence_to_excel,
    evidence_to_json,
    read_table,
)
from tagsignal.ui import signal_theme as sig


NS = "tag"


def k(name: str) -> str:
    """Namespace a session-state or widget key with the app slug, so apps can share one Hub session."""
    return f"{NS}:{name}"


MODE_LABELS = {
    "randomized": "Randomized assigned-price test",
    "historical": "Historical price–quantity series",
    "valuation": "Respondent-level willingness to pay",
}
CAUTION = (
    "**Tag Signal bounds a pricing scenario; it does not turn a model into market truth.** Historical coefficients can "
    "be confounded, assigned-price tests support only their tested range, and WTP is not the same as realized demand. "
    "Contribution uses the cost and planning scale you declare."
)
SIDEBAR_TAGLINE = "Pricing evidence without false precision."
MASTHEAD_KICKER = "EVIDENCE → RESPONSE → ECONOMICS"
MASTHEAD_PROMISES = ["Bound the range", "Preserve uncertainty", "Name the evidence"]
FOOTER_LINE = "scenario bounds, not market truth"


def _rgba(hex_colour: str, alpha: float) -> str:
    """A theme token as a translucent fill (Plotly bands need rgba, the tokens are hex)."""
    value = hex_colour.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def full_width(widget, *args, **kwargs):
    try:
        parameters = inspect.signature(widget).parameters
    except (TypeError, ValueError):
        parameters = {}
    width_parameter = parameters.get("width")
    if width_parameter is not None and isinstance(width_parameter.default, str):
        kwargs["width"] = "stretch"
    elif "use_container_width" in parameters:
        kwargs["use_container_width"] = True
    return widget(*args, **kwargs)


def show_error(exc: Exception) -> None:
    """Render a useful error while keeping tracebacks opt-in."""
    st.error(friendly_message(exc))
    if not isinstance(exc, (DataProblem, ValueError)) and os.getenv("TAGSIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def reset_results() -> None:
    st.session_state.pop(k("audit"), None)
    st.session_state.pop(k("analysis"), None)


DEMO_FRAMES = {"randomized": randomized_demo, "historical": historical_demo, "valuation": valuation_demo}
DEMO_FILENAMES = {
    "randomized": "tagsignal-fictional-randomized-demo.csv",
    "historical": "tagsignal-fictional-historical-demo.csv",
    "valuation": "tagsignal-fictional-valuation-demo.csv",
}
# The demo that opens on first run: the randomized test is the strongest evidence tier and walks every page.
DEFAULT_DEMO = "randomized"


def load_demo(mode: str) -> None:
    st.session_state[k("data")] = DEMO_FRAMES[mode]()
    st.session_state[k("source")] = {
        "source_filename": DEMO_FILENAMES[mode],
        "source_sheet": "",
        "source_sha256": hashlib.sha256(f"tagsignal-{mode}-fictional-v1".encode()).hexdigest(),
        "source_type": "deterministic synthetic demonstration",
    }
    st.session_state[k("contract")] = demo_contract(mode)
    reset_results()


@st.cache_data(show_spinner=False)
def _demo_analysis(mode: str):
    """The fictional demo analysed with its own saved contract (deterministic, so cached across sessions)."""
    return analyze_price(DEMO_FRAMES[mode](), config_from_contract(demo_contract(mode)))


def _ensure_state() -> None:
    """Open with the default fictional demo already loaded and analysed when nothing is in session state.

    An upload or a demo button replaces it; this only runs while the session holds no data at all.
    """
    if k("data") not in st.session_state:
        load_demo(DEFAULT_DEMO)
        st.session_state[k("analysis")] = _demo_analysis(DEFAULT_DEMO)


def config_from_contract(contract: dict[str, object]) -> PriceConfig:
    accepted = {
        "mode",
        "unit_cost",
        "reference_price",
        "candidate_price",
        "planning_units",
        "minimum_worthwhile_contribution",
        "currency",
        "price_col",
        "quantity_col",
        "wtp_col",
        "controls",
        "randomized_confirmed",
        "valuation_method",
        "covariance",
        "hac_lags",
        "bootstrap_iterations",
        "seed",
    }
    values = {key: value for key, value in contract.items() if key in accepted}
    values["controls"] = tuple(values.get("controls", ()))
    return PriceConfig(**values)  # type: ignore[arg-type]


def money(value: float, currency: str) -> str:
    return f"{value:,.0f} {currency}"


def page_welcome() -> None:
    sig.hero(
        NS,
        eyebrow="PRICING EVIDENCE & DECISION SUPPORT",
        title="What price range is supported—and how does",
        em="profit move?",
        body=(
            "Bring an assigned-price test, a historical price–quantity series, or respondent-level valuations. "
            "Tag Signal audits the evidence, estimates only what that design can support, and compares a declared "
            "candidate with a reference price using demand, margin, contribution, and uncertainty."
        ),
        pills=[
            "price elasticity",
            "stratified bootstrap",
            "HAC / HC3 uncertainty",
            "empirical WTP curve",
            "candidate vs reference",
            "privacy-minimized evidence",
        ],
    )
    sig.note("warn", CAUTION)
    sig.cards(
        [
            (
                "01 / DECLARE",
                "Write the price decision first",
                "Name the reference, candidate, unit cost, planning scale, and minimum worthwhile contribution before "
                "reading the model.",
            ),
            (
                "02 / SEPARATE",
                "Keep evidence tiers visible",
                "A randomized price assignment, a historical association, and stated WTP do not earn the same "
                "interpretation.",
            ),
            (
                "03 / BOUND",
                "Stay inside observed support",
                "The app shows extrapolation, boundary optima, weak variation, and intervals rather than presenting "
                "one magical price.",
            ),
        ]
    )
    st.subheader("Fictional evidence is already loaded")
    st.markdown(
        "Tag Signal opens with a **fictional randomized price test** already loaded and analysed, so every page "
        "shows results straight away. All demo records, prices, and outcomes are invented. The buttons below switch "
        "to another fictional route or restore this one with its saved contract (then run the analysis on page 2); "
        "uploading your own table from the sidebar replaces the demo."
    )
    source = st.session_state.get(k("source"), {})
    if source.get("source_type") == "deterministic synthetic demonstration":
        st.caption(f"Currently loaded: fictional demo `{source.get('source_filename', '')}`.")
    else:
        st.caption(f"Currently loaded: your upload `{source.get('source_filename', '')}`.")
    left, middle, right = st.columns(3)
    with left:
        st.button(
            "Load randomized price test",
            key=k("load_random_demo"),
            type="primary",
            on_click=load_demo,
            args=("randomized",),
        )
    with middle:
        st.button("Load historical series", key=k("load_historical_demo"), on_click=load_demo, args=("historical",))
    with right:
        st.button("Load stated-WTP sample", key=k("load_valuation_demo"), on_click=load_demo, args=("valuation",))


def page_contract() -> None:
    sig.header(
        "Step 1",
        "Evidence contract",
        "Declare what generated the data and what economic comparison matters. Saving the contract clears old results.",
    )
    data = st.session_state.get(k("data"))
    if not isinstance(data, pd.DataFrame):
        st.info("Load a fictional example or upload a table from the sidebar first.")
        return
    current = dict(st.session_state.get(k("contract"), {}))
    mode_options = list(MODE_LABELS)
    current_mode = str(current.get("mode", "randomized"))
    mode = st.selectbox(
        "Evidence route",
        mode_options,
        index=mode_options.index(current_mode) if current_mode in mode_options else 0,
        format_func=MODE_LABELS.get,
        key=k("mode"),
    )
    columns = list(map(str, data.columns))
    numeric_columns = [column for column in columns if pd.to_numeric(data[column], errors="coerce").notna().mean() >= 0.8]
    if not numeric_columns:
        show_error(
            DataProblem(
                "The loaded table has no mostly-numeric columns. Tag Signal needs numeric price and quantity "
                "columns, or a numeric willingness-to-pay column. Check the data guide and load a numeric table."
            )
        )
        return
    values: dict[str, object] = {"mode": mode}
    st.subheader("Data roles")
    if mode in {"randomized", "historical"}:
        c1, c2 = st.columns(2)
        price_default = current.get("price_col") if current.get("price_col") in columns else numeric_columns[0]
        quantity_default = (
            current.get("quantity_col")
            if current.get("quantity_col") in columns
            else numeric_columns[min(1, len(numeric_columns) - 1)]
        )
        with c1:
            values["price_col"] = st.selectbox("Price", columns, index=columns.index(price_default), key=k("price_col"))
        with c2:
            values["quantity_col"] = st.selectbox(
                "Quantity or purchase outcome",
                columns,
                index=columns.index(quantity_default),
                key=k("quantity_col"),
            )
        if mode == "historical":
            role_columns = {values["price_col"], values["quantity_col"]}
            control_options = [column for column in numeric_columns if column not in role_columns]
            defaults = [column for column in current.get("controls", []) if column in control_options]
            values["controls"] = st.multiselect(
                "Numeric controls", control_options, default=defaults, key=k("controls")
            )
            c1, c2 = st.columns(2)
            with c1:
                values["covariance"] = st.selectbox(
                    "Uncertainty estimator",
                    ["HAC", "HC3"],
                    index=0 if current.get("covariance", "HAC") == "HAC" else 1,
                    key=k("covariance"),
                )
            with c2:
                values["hac_lags"] = st.number_input(
                    "HAC lags", 0, 52, int(current.get("hac_lags", 4)), key=k("hac_lags")
                )
        else:
            values["randomized_confirmed"] = st.checkbox(
                "I confirm price was assigned by a valid random process before the outcome",
                value=bool(current.get("randomized_confirmed", False)),
                key=k("randomized_confirmed"),
            )
    else:
        default = current.get("wtp_col") if current.get("wtp_col") in columns else numeric_columns[0]
        values["wtp_col"] = st.selectbox(
            "Respondent-level maximum WTP", columns, index=columns.index(default), key=k("wtp_col")
        )
        valuation_options = ["Stated hypothetical WTP", "Incentive-compatible BDM or auction"]
        previous = current.get("valuation_method", valuation_options[0])
        values["valuation_method"] = st.selectbox(
            "Elicitation class",
            valuation_options,
            index=valuation_options.index(previous) if previous in valuation_options else 0,
            key=k("valuation_method"),
        )
    st.subheader("Economic comparison")
    c1, c2, c3 = st.columns(3)
    with c1:
        values["unit_cost"] = st.number_input(
            "Declared unit cost",
            min_value=0.0,
            value=float(current.get("unit_cost", 0.0)),
            step=1.0,
            key=k("unit_cost"),
        )
    with c2:
        values["reference_price"] = st.number_input(
            "Reference price",
            min_value=0.01,
            value=float(current.get("reference_price", 29.0)),
            step=1.0,
            key=k("reference_price"),
        )
    with c3:
        values["candidate_price"] = st.number_input(
            "Candidate price",
            min_value=0.01,
            value=float(current.get("candidate_price", 34.0)),
            step=1.0,
            key=k("candidate_price"),
        )
    c1, c2, c3 = st.columns(3)
    with c1:
        label = "Planning multiplier" if mode == "historical" else "Addressable customers / opportunities"
        values["planning_units"] = st.number_input(
            label,
            min_value=0.01,
            value=float(current.get("planning_units", 1.0)),
            step=1.0,
            key=k("planning_units"),
        )
    with c2:
        values["minimum_worthwhile_contribution"] = st.number_input(
            "Minimum worthwhile incremental contribution",
            min_value=0.01,
            value=max(float(current.get("minimum_worthwhile_contribution", 1.0)), 0.01),
            step=1.0,
            help=(
                "The smallest total incremental contribution that would make the candidate price worth adopting. "
                "It must be above zero — with zero, the reading collapses into a bare significance statement, "
                "which Tag Signal refuses to present as a decision."
            ),
            key=k("minimum_worthwhile_contribution"),
        )
    with c3:
        values["currency"] = st.text_input(
            "Currency label", value=str(current.get("currency", "NOK")), max_chars=12, key=k("currency")
        )
    values["bootstrap_iterations"] = int(current.get("bootstrap_iterations", 500))
    values["seed"] = int(current.get("seed", 20260716))
    st.caption(
        "Historical quantity is interpreted in its existing planning unit and then multiplied by the planning multiplier. "
        "Randomized quantity is per assigned unit; WTP becomes an acceptance share."
    )
    if st.button("Save evidence contract", type="primary", key=k("save_contract")):
        try:
            config_from_contract(values)
            st.session_state[k("contract")] = values
            reset_results()
            st.success("Contract saved. Continue to the data and support audit.")
        except Exception as exc:
            show_error(exc)


def page_audit() -> None:
    sig.header(
        "Step 2",
        "Data and support audit",
        "Check row completeness, observed price support, blockers, and warnings before any model is fitted.",
    )
    data = st.session_state.get(k("data"))
    contract = st.session_state.get(k("contract"))
    if not isinstance(data, pd.DataFrame) or not isinstance(contract, dict):
        st.info("Load data and save an evidence contract first.")
        return
    try:
        config = config_from_contract(contract)
        audit = audit_price_data(data, config)
        st.session_state[k("audit")] = audit
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows received", f"{audit.summary.get('rows_received', 0):,}")
        c2.metric("Complete rows", f"{audit.summary.get('complete_rows', 0):,}")
        c3.metric("Evidence route", MODE_LABELS[config.mode].split()[0])
        c4.metric("Candidate", f"{config.candidate_price:,.2f} {config.currency}")
        if audit.blockers:
            for blocker in audit.blockers:
                st.error(blocker)
        for warning in audit.warnings:
            st.warning(warning)
        st.subheader("Observed support")
        full_width(st.dataframe, audit.support_table, hide_index=True)
        with st.expander("Preview the local input table"):
            full_width(st.dataframe, data.head(25), hide_index=True)
        if st.button("Run pricing analysis", type="primary", key=k("run_analysis"), disabled=bool(audit.blockers)):
            analysis = analyze_price(data, config)
            st.session_state[k("analysis")] = analysis
            st.success("Analysis complete. Continue to demand and economics.")
    except Exception as exc:
        show_error(exc)


def _analysis_or_message():
    analysis = st.session_state.get(k("analysis"))
    if analysis is None:
        st.info("Run the pricing analysis on page 2 first.")
        return None
    return analysis


def _economics_figure(analysis) -> go.Figure:
    """Projected volume (own family colour) with its interval band, expected contribution (estimate colour) on a
    secondary axis, and the declared reference and candidate prices as dotted markers."""
    config = analysis.config
    grid = analysis.price_grid
    volume_colour = sig.app(NS)["fam"]["600"]
    roles = sig.roles(NS)
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(
            x=grid["price"],
            y=grid["projected_volume"],
            name="Projected volume",
            line={"color": volume_colour, "width": 3},
            hovertemplate="Price %{x:.2f}<br>Volume %{y:,.1f}<extra></extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=pd.concat([grid["price"], grid["price"].iloc[::-1]]),
            y=pd.concat([grid["volume_high"], grid["volume_low"].iloc[::-1]]),
            fill="toself",
            fillcolor=_rgba(roles["interval"], 0.25),
            line={"color": "rgba(0,0,0,0)"},
            name="Volume interval",
            hoverinfo="skip",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=grid["price"],
            y=grid["expected_contribution"],
            name="Expected contribution",
            line={"color": roles["estimate"], "width": 3},
            hovertemplate="Price %{x:.2f}<br>Contribution %{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )
    for price, label in [(config.reference_price, "Reference"), (config.candidate_price, "Candidate")]:
        figure.add_vline(x=price, line_dash="dot", line_color=roles["threshold"], annotation_text=label)
    figure.update_layout(
        template=sig.template(NS),
        height=540,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        legend={"orientation": "h", "y": 1.08},
        hovermode="x unified",
    )
    figure.update_xaxes(title="Price")
    figure.update_yaxes(title="Projected volume / acceptance", secondary_y=False)
    figure.update_yaxes(title=f"Contribution ({config.currency})", secondary_y=True)
    return figure


def page_effects() -> None:
    sig.header(
        "Step 3",
        "Demand and economics",
        "Read the response estimate, the bounded volume and contribution curves, and every warning together.",
    )
    analysis = _analysis_or_message()
    if analysis is None:
        return
    config = analysis.config
    diagnostics = analysis.diagnostics
    c1, c2, c3, c4 = st.columns(4)
    if "elasticity" in diagnostics:
        c1.metric("Elasticity", f"{diagnostics['elasticity']:.2f}")
        c2.metric("95% interval", f"[{diagnostics['elasticity_low']:.2f}, {diagnostics['elasticity_high']:.2f}]")
    else:
        c1.metric("Median WTP", f"{diagnostics['median_wtp']:,.2f} {config.currency}")
        c2.metric("Respondents", f"{diagnostics['n']:,}")
    c3.metric("Highest modeled contribution", f"{analysis.optimal['point_price']:,.2f} {config.currency}")
    c4.metric("Evidence tier", analysis.evidence_tier)
    sig.chart(NS, _economics_figure(analysis), key=k("economics_chart"))
    st.caption(
        "The highest modeled contribution is a bounded scenario over the evidence range—not an automatic price recommendation. "
        "Intervals carry only the modeled sampling uncertainty, not every market risk."
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Model or valuation summary")
        full_width(st.dataframe, analysis.coefficients, hide_index=True)
    with right:
        st.subheader("Diagnostics")
        diagnostic_rows = [{"field": key, "value": str(value)} for key, value in diagnostics.items()]
        full_width(st.dataframe, pd.DataFrame(diagnostic_rows), hide_index=True)
    with st.expander("Price scenario table"):
        full_width(st.dataframe, analysis.price_grid, hide_index=True)
    for warning in analysis.warnings:
        st.warning(warning)


def page_decision() -> None:
    sig.header(
        "Step 4",
        "Decision and export",
        "Compare the declared candidate with the reference price and export the privacy-minimized evidence pack.",
    )
    analysis = _analysis_or_message()
    if analysis is None:
        return
    comparison = analysis.comparison
    config = analysis.config
    sig.header(str(analysis.evidence_tier), str(comparison["status"]), str(comparison["explanation"]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reference contribution", money(comparison["reference_contribution"], config.currency))
    c2.metric("Candidate contribution", money(comparison["candidate_contribution"], config.currency))
    c3.metric("Incremental", money(comparison["incremental_contribution"], config.currency))
    c4.metric(
        "95% interval",
        f"{comparison['incremental_low']:,.0f} to {comparison['incremental_high']:,.0f}",
    )
    # sig.note escapes HTML, so the user-typed currency label cannot inject markup.
    sig.note(
        "boundary",
        f"**Decision contract:** compare {config.candidate_price:,.2f} with {config.reference_price:,.2f} "
        f"{config.currency}; require at least {config.minimum_worthwhile_contribution:,.0f} {config.currency} "
        f"incremental contribution. The candidate {'is' if comparison['within_observed_support'] else 'is not'} "
        "inside observed support.",
    )
    source = st.session_state.get(k("source"), {})
    contract = st.session_state.get(k("contract"), {})
    pack = build_evidence_pack(source=source, contract=contract, analysis=analysis)
    bridge = build_gate_bridge(analysis)
    st.subheader("Portable, aggregate evidence")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.download_button(
            "Evidence JSON",
            evidence_to_json(pack),
            "tagsignal-evidence.json",
            "application/json",
            key=k("download_json"),
        )
    with d2:
        st.download_button(
            "Evidence workbook",
            evidence_to_excel(pack),
            "tagsignal-evidence.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=k("download_xlsx"),
        )
    with d3:
        st.download_button(
            "CSV evidence pack",
            evidence_to_csv_zip(pack),
            "tagsignal-evidence.zip",
            "application/zip",
            key=k("download_csv_zip"),
        )
    with d4:
        st.download_button(
            "Gate Signal bridge",
            evidence_to_json(bridge),
            "tagsignal-gate-bridge.json",
            "application/json",
            key=k("download_gate_bridge"),
        )
    st.caption("Exports exclude uploaded row-level records, identifiers, fitted values, residuals, and free text.")


def page_methods() -> None:
    sig.header(
        "Methods and limits",
        "What Tag Signal calculates",
        "Three evidence routes keep their own interpretation; one transparent economic layer sits on top.",
    )
    sig.note("warn", CAUTION)
    st.subheader("Three routes, three interpretations")
    st.markdown(
        """
        - **Randomized assigned-price test:** fits a power demand curve to price-arm means and uses a stratified
          within-arm bootstrap. Random assignment supports causal comparisons among tested arms when implementation,
          outcome observation, interference, and analysis are credible. A smooth curve between arms remains a model.
        - **Historical series:** estimates a log–log demand association with numeric controls. HAC or HC3 uncertainty
          addresses parts of the error structure; neither solves price endogeneity or omitted demand shocks.
        - **WTP distribution:** converts respondent valuations into the empirical share at or above each price and
          bootstraps respondents. Stated WTP is hypothetical. Incentive-compatible elicitation strengthens a protocol,
          but does not recreate a competitive market.
        """
    )
    st.subheader("Economic layer")
    st.markdown(
        """
        At each supported price, Tag Signal calculates `projected volume × (price − declared unit cost)`. It then
        compares the candidate with the reference price and classifies the interval against a declared minimum
        worthwhile contribution. Taxes, fixed costs, capacity, cannibalization, competitor response, channel margins,
        fairness, legal constraints, and long-run retention remain outside the calculation unless reflected in inputs.
        """
    )
    st.subheader("Primary method references")
    st.markdown(
        """
        - Becker, DeGroot, and Marschak (1964), [single-response utility measurement](https://doi.org/10.1002/bs.3830090304).
        - Vickrey (1961), *Counterspeculation, Auctions, and Competitive Sealed Tenders*, *Journal of Finance*, 16, 8–37.
        - Newey and West (1987), [heteroskedasticity and autocorrelation-consistent covariance](https://doi.org/10.2307/1913610).
        - MacKinnon and White (1985), [HC covariance estimators](https://doi.org/10.1016/0304-4076(85)90158-7).
        - Efron (1979), [bootstrap methods](https://doi.org/10.1214/aos/1176344552).
        - Duan (1983), [smearing retransformation](https://doi.org/10.1080/01621459.1983.10478017).
        - Schmidt and Bijmolt (2020), [consumer WTP hypothetical-bias meta-analysis](https://doi.org/10.1007/s11747-019-00666-6).
        """
    )
    st.info(
        "Tag Signal is independently designed from public literature. It does not reproduce lecture slides, classroom "
        "cases, exam material, proprietary pricing templates, or institution-specific wording."
    )


PAGES = {
    "Welcome": page_welcome,
    "1 · Evidence contract": page_contract,
    "2 · Data & support audit": page_audit,
    "3 · Demand & economics": page_effects,
    "4 · Decision & export": page_decision,
    "Methods & limits": page_methods,
}


def _handle_upload(upload) -> None:
    fingerprint = hashlib.sha256(upload.getvalue()).hexdigest()
    if st.session_state.get(k("uploaded_sha256")) == fingerprint:
        return
    try:
        data, source = read_table(upload.getvalue(), upload.name)
        st.session_state[k("data")] = data
        st.session_state[k("source")] = source
        st.session_state[k("uploaded_sha256")] = fingerprint
        st.session_state.pop(k("contract"), None)
        reset_results()
        st.success(f"Loaded {len(data):,} rows.")
    except Exception as exc:
        show_error(exc)


def _sidebar() -> str:
    """Draw the sidebar lockup, page selector, upload and starter workbook; return the selected page."""
    sig.sidebar_brand(NS, SIDEBAR_TAGLINE)
    with st.sidebar:
        page = st.radio("Navigate", list(PAGES), label_visibility="collapsed", key=k("page"))
        st.divider()
        upload = st.file_uploader("Upload pricing evidence", type=["csv", "xlsx", "json"], key=k("upload"))
        if upload is not None:
            _handle_upload(upload)
        st.caption("Local mode · no account · no telemetry · no external AI call")
        st.divider()
        mode_for_template = str(st.session_state.get(k("contract"), {}).get("mode", "randomized"))
        st.download_button(
            "Download starter workbook",
            dataframe_to_xlsx(starter_template(mode_for_template)),
            f"tagsignal-{mode_for_template}-template.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=k("download_starter"),
        )
    return page


def render() -> None:
    """Draw the whole Tag Signal app on the current page. Never calls st.set_page_config or st.navigation."""
    sig.apply(NS)
    _ensure_state()
    page = _sidebar()
    sig.masthead(NS, MASTHEAD_PROMISES, MASTHEAD_KICKER)
    try:
        PAGES[page]()
    except Exception as exc:
        show_error(exc)
    sig.footer(NS, __version__, FOOTER_LINE)
