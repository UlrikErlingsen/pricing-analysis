from __future__ import annotations

import os

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import base64
import hashlib
import inspect
from pathlib import Path
import sys
import traceback

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from pricesignal import __version__
from pricesignal.analysis import PriceConfig, analyze_price, audit_price_data
from pricesignal.errors import DataProblem, friendly_message
from pricesignal.examples import demo_contract, historical_demo, randomized_demo, starter_template, valuation_demo
from pricesignal.io import (
    build_evidence_pack,
    build_gate_bridge,
    dataframe_to_xlsx,
    evidence_to_csv_zip,
    evidence_to_excel,
    evidence_to_json,
    read_table,
)


PAGES = [
    "Welcome",
    "1 · Evidence contract",
    "2 · Data & support audit",
    "3 · Demand & economics",
    "4 · Decision & export",
    "Methods & limits",
]
MODE_LABELS = {
    "randomized": "Randomized assigned-price test",
    "historical": "Historical price–quantity series",
    "valuation": "Respondent-level willingness to pay",
}
COLORS = {
    "ink": "#17322E",
    "deep": "#102C2A",
    "coral": "#D95B40",
    "mint": "#83D2B4",
    "gold": "#F2C66D",
    "paper": "#F8F5ED",
    "muted": "#59716C",
}
CAUTION = (
    "**PriceSignal bounds a pricing scenario; it does not turn a model into market truth.** Historical coefficients can "
    "be confounded, assigned-price tests support only their tested range, and WTP is not the same as realized demand. "
    "Contribution uses the cost and planning scale you declare."
)
mark_path = ROOT / "assets" / "pricesignal-mark.svg"
MARK_URI = (
    "data:image/svg+xml;base64," + base64.b64encode(mark_path.read_bytes()).decode("ascii")
    if mark_path.exists()
    else ""
)


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


st.set_page_config(page_title="PriceSignal | Pricing evidence", page_icon="◇", layout="wide")
st.markdown(
    """
    <style>
    :root{--ps-ink:#17322e;--ps-deep:#102c2a;--ps-coral:#d95b40;--ps-mint:#83d2b4;
          --ps-gold:#f2c66d;--ps-paper:#f8f5ed;--ps-line:rgba(23,50,46,.14)}
    [data-testid="stAppViewContainer"]{background:radial-gradient(circle at 94% 3%,rgba(242,198,109,.19),transparent 29rem),
      radial-gradient(circle at 2% 94%,rgba(131,210,180,.14),transparent 26rem),linear-gradient(180deg,#fbf9f3,var(--ps-paper))}
    [data-testid="stHeader"]{background:rgba(248,245,237,.78)}
    [data-testid="stSidebar"]{background:linear-gradient(165deg,#173c3a,#102c2a 68%,#0c2422)}
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span{color:#f8f5ed}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p{color:#b9cbc5}
    [data-testid="stSidebar"] button{background:rgba(255,255,255,.08);color:#f8f5ed!important;border-color:rgba(255,255,255,.23)}
    [data-testid="stSidebar"] button *{color:#f8f5ed!important}
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{background:rgba(255,255,255,.06);border-color:rgba(242,198,109,.32)}
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button{background:#f8f5ed;color:#17322e!important}
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button *{color:#17322e!important}
    .block-container{max-width:1240px;padding-top:4.4rem;padding-bottom:4rem} h1,h2,h3{color:var(--ps-ink);letter-spacing:-.025em} a{color:#9b3e2b}
    [data-testid="stMetric"]{background:rgba(255,255,255,.76);border:1px solid var(--ps-line);border-radius:16px;padding:1rem;box-shadow:0 8px 28px rgba(23,50,46,.045)}
    [data-testid="stMetricValue"]{color:var(--ps-ink);font-size:clamp(1.3rem,2.3vw,1.9rem)}
    .stButton>button[kind="primary"]{background:linear-gradient(135deg,#e26748,#c94c34);color:white;border:0;box-shadow:0 8px 20px rgba(217,91,64,.22);font-weight:750}
    button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #f2c66d!important;outline-offset:2px}
    .ps-lockup{display:flex;align-items:center;gap:.65rem}.ps-mark{width:40px;height:40px}.ps-name{color:white;font-size:1.28rem;font-weight:850;letter-spacing:-.04em}.ps-name span{color:#f2c66d!important}
    .ps-tag{margin:.5rem 0 0!important;color:#b9cbc5!important;font-size:.76rem;line-height:1.4}
    .ps-masthead{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.72rem 1rem .72rem .78rem;margin-bottom:1.35rem;background:rgba(255,255,255,.66);border:1px solid var(--ps-line);border-radius:18px;box-shadow:0 10px 36px rgba(23,50,46,.05)}
    .ps-masthead .ps-mark{width:48px;height:48px}.ps-wordmark{color:var(--ps-ink);font-weight:850;letter-spacing:-.045em;font-size:1.55rem}.ps-wordmark span{color:var(--ps-coral)}
    .ps-kicker{margin-top:.3rem;color:#59716c;font-size:.67rem;font-weight:800;letter-spacing:.13em}.ps-promise{color:#47645e;font-size:.78rem;font-weight:700;white-space:nowrap}.ps-promise span{color:var(--ps-coral);padding:0 .3rem}
    .ps-hero{position:relative;overflow:hidden;padding:clamp(1.7rem,4vw,3.4rem);margin-bottom:1.3rem;background:linear-gradient(135deg,#173c3a,#102c2a 75%);border-radius:26px;box-shadow:0 18px 50px rgba(23,50,46,.17)}
    .ps-hero:after{content:"";position:absolute;width:335px;height:335px;right:-110px;top:-150px;border-radius:50%;border:56px solid rgba(242,198,109,.13)}
    .ps-eyebrow{color:#83d2b4;font-size:.72rem;font-weight:850;letter-spacing:.16em}.ps-hero h1{color:white;font-size:clamp(2.25rem,5vw,4.7rem);line-height:.97;margin:.75rem 0 1rem;max-width:980px}.ps-hero h1 em{color:#f2c66d;font-style:normal}
    .ps-hero p{color:#d7e3df;font-size:1.06rem;line-height:1.6;max-width:850px}.ps-pills{display:flex;flex-wrap:wrap;gap:.55rem;margin-top:1.15rem}.ps-pill{padding:.4rem .72rem;border:1px solid rgba(255,255,255,.16);border-radius:999px;color:#f8f5ed;font-size:.78rem;font-weight:700;background:rgba(255,255,255,.055)}
    .ps-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.ps-card{height:100%;padding:1.2rem;background:rgba(255,255,255,.68);border:1px solid var(--ps-line);border-radius:18px}.ps-card b{color:var(--ps-coral);font-size:.72rem;letter-spacing:.12em}.ps-card h3{margin:.4rem 0 .5rem}.ps-card p{color:#59716c;font-size:.9rem;line-height:1.55}
    .ps-decision{padding:1.3rem 1.4rem;margin:1rem 0;color:white;border-radius:18px;background:linear-gradient(135deg,#173c3a,#102c2a);box-shadow:0 12px 34px rgba(23,50,46,.14)}.ps-decision b{color:#f2c66d;font-size:.78rem;letter-spacing:.14em}.ps-decision h2{color:white;margin:.35rem 0 .4rem}.ps-decision p{color:#d7e3df;margin:.35rem 0 0}
    .ps-note{padding:1rem 1.1rem;margin:.75rem 0 1rem;border-left:4px solid var(--ps-mint);background:rgba(255,255,255,.62);border-radius:0 14px 14px 0;color:#47645e}.ps-footer{margin-top:3.2rem;padding-top:1rem;border-top:1px solid var(--ps-line);color:#617670;font-size:.76rem;text-align:center}.ps-footer span{color:var(--ps-coral);padding:0 .38rem}
    @media(max-width:1050px){.ps-grid{grid-template-columns:1fr}}@media(max-width:760px){.ps-promise{display:none}.ps-hero{border-radius:20px}.block-container{padding-top:3.5rem}}
    </style>
    """,
    unsafe_allow_html=True,
)


def show_error(exc: Exception) -> None:
    st.error(friendly_message(exc))
    if not isinstance(exc, (DataProblem, ValueError)) and os.getenv("PRICESIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def reset_results() -> None:
    st.session_state.pop("audit", None)
    st.session_state.pop("analysis", None)


def load_demo(mode: str) -> None:
    frames = {"randomized": randomized_demo, "historical": historical_demo, "valuation": valuation_demo}
    names = {
        "randomized": "pricesignal-fictional-randomized-demo.csv",
        "historical": "pricesignal-fictional-historical-demo.csv",
        "valuation": "pricesignal-fictional-valuation-demo.csv",
    }
    st.session_state["data"] = frames[mode]()
    st.session_state["source"] = {
        "source_filename": names[mode],
        "source_sheet": "",
        "source_sha256": hashlib.sha256(f"pricesignal-{mode}-fictional-v1".encode()).hexdigest(),
        "source_type": "deterministic synthetic demonstration",
    }
    st.session_state["contract"] = demo_contract(mode)
    reset_results()


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


def masthead() -> None:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f"""<div class="ps-masthead"><div class="ps-lockup">{mark}<div><div class="ps-wordmark">Price<span>Signal</span></div>
        <div class="ps-kicker">EVIDENCE → RESPONSE → ECONOMICS</div></div></div>
        <div class="ps-promise">Bound the range <span>◆</span> Preserve uncertainty <span>◆</span> Name the evidence</div></div>""",
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        f'<div class="ps-footer">PriceSignal {__version__} <span>◆</span> local-first <span>◆</span> '
        "open methods <span>◆</span> accountable pricing decisions</div>",
        unsafe_allow_html=True,
    )


def money(value: float, currency: str) -> str:
    return f"{value:,.0f} {currency}"


def render_welcome() -> None:
    st.markdown(
        """
        <section class="ps-hero"><div class="ps-eyebrow">PRICING EVIDENCE & DECISION SUPPORT</div>
        <h1>What price range is supported—and how does <em>profit move?</em></h1>
        <p>Bring an assigned-price test, a historical price–quantity series, or respondent-level valuations. PriceSignal
        audits the evidence, estimates only what that design can support, and compares a declared candidate with a
        reference price using demand, margin, contribution, and uncertainty.</p>
        <div class="ps-pills"><span class="ps-pill">price elasticity</span><span class="ps-pill">stratified bootstrap</span>
        <span class="ps-pill">HAC / HC3 uncertainty</span><span class="ps-pill">empirical WTP curve</span>
        <span class="ps-pill">candidate vs reference</span><span class="ps-pill">privacy-minimized evidence</span></div></section>
        """,
        unsafe_allow_html=True,
    )
    st.warning(CAUTION)
    st.markdown(
        """<div class="ps-grid"><article class="ps-card"><b>01 / DECLARE</b><h3>Write the price decision first</h3>
        <p>Name the reference, candidate, unit cost, planning scale, and minimum worthwhile contribution before reading the model.</p></article>
        <article class="ps-card"><b>02 / SEPARATE</b><h3>Keep evidence tiers visible</h3><p>A randomized price assignment,
        a historical association, and stated WTP do not earn the same interpretation.</p></article>
        <article class="ps-card"><b>03 / BOUND</b><h3>Stay inside observed support</h3><p>The app shows extrapolation, boundary optima,
        weak variation, and intervals rather than presenting one magical price.</p></article></div>""",
        unsafe_allow_html=True,
    )
    st.subheader("Start with fictional evidence")
    left, middle, right = st.columns(3)
    with left:
        st.button("Load randomized price test", key="load_random_demo", type="primary", on_click=load_demo, args=("randomized",))
    with middle:
        st.button("Load historical series", key="load_historical_demo", on_click=load_demo, args=("historical",))
    with right:
        st.button("Load stated-WTP sample", key="load_valuation_demo", on_click=load_demo, args=("valuation",))


def render_contract() -> None:
    st.title("Evidence contract")
    st.write("Declare what generated the data and what economic comparison matters. Saving the contract clears old results.")
    data = st.session_state.get("data")
    if not isinstance(data, pd.DataFrame):
        st.info("Load a fictional example or upload a table from the sidebar first.")
        return
    current = dict(st.session_state.get("contract", {}))
    mode_options = list(MODE_LABELS)
    current_mode = str(current.get("mode", "randomized"))
    mode = st.selectbox(
        "Evidence route",
        mode_options,
        index=mode_options.index(current_mode) if current_mode in mode_options else 0,
        format_func=MODE_LABELS.get,
    )
    columns = list(map(str, data.columns))
    numeric_columns = [column for column in columns if pd.to_numeric(data[column], errors="coerce").notna().mean() >= 0.8]
    if not numeric_columns:
        show_error(
            DataProblem(
                "The loaded table has no mostly-numeric columns. PriceSignal needs numeric price and quantity "
                "columns, or a numeric willingness-to-pay column. Check the data guide and load a numeric table."
            )
        )
        return
    values: dict[str, object] = {"mode": mode}
    st.subheader("Data roles")
    if mode in {"randomized", "historical"}:
        c1, c2 = st.columns(2)
        price_default = current.get("price_col") if current.get("price_col") in columns else numeric_columns[0]
        quantity_default = current.get("quantity_col") if current.get("quantity_col") in columns else numeric_columns[min(1, len(numeric_columns) - 1)]
        with c1:
            values["price_col"] = st.selectbox("Price", columns, index=columns.index(price_default))
        with c2:
            values["quantity_col"] = st.selectbox("Quantity or purchase outcome", columns, index=columns.index(quantity_default))
        if mode == "historical":
            role_columns = {values["price_col"], values["quantity_col"]}
            control_options = [column for column in numeric_columns if column not in role_columns]
            defaults = [column for column in current.get("controls", []) if column in control_options]
            values["controls"] = st.multiselect("Numeric controls", control_options, default=defaults)
            c1, c2 = st.columns(2)
            with c1:
                values["covariance"] = st.selectbox(
                    "Uncertainty estimator", ["HAC", "HC3"], index=0 if current.get("covariance", "HAC") == "HAC" else 1
                )
            with c2:
                values["hac_lags"] = st.number_input("HAC lags", 0, 52, int(current.get("hac_lags", 4)))
        else:
            values["randomized_confirmed"] = st.checkbox(
                "I confirm price was assigned by a valid random process before the outcome",
                value=bool(current.get("randomized_confirmed", False)),
            )
    else:
        default = current.get("wtp_col") if current.get("wtp_col") in columns else numeric_columns[0]
        values["wtp_col"] = st.selectbox("Respondent-level maximum WTP", columns, index=columns.index(default))
        valuation_options = ["Stated hypothetical WTP", "Incentive-compatible BDM or auction"]
        previous = current.get("valuation_method", valuation_options[0])
        values["valuation_method"] = st.selectbox(
            "Elicitation class", valuation_options, index=valuation_options.index(previous) if previous in valuation_options else 0
        )
    st.subheader("Economic comparison")
    c1, c2, c3 = st.columns(3)
    with c1:
        values["unit_cost"] = st.number_input("Declared unit cost", min_value=0.0, value=float(current.get("unit_cost", 0.0)), step=1.0)
    with c2:
        values["reference_price"] = st.number_input("Reference price", min_value=0.01, value=float(current.get("reference_price", 29.0)), step=1.0)
    with c3:
        values["candidate_price"] = st.number_input("Candidate price", min_value=0.01, value=float(current.get("candidate_price", 34.0)), step=1.0)
    c1, c2, c3 = st.columns(3)
    with c1:
        label = "Planning multiplier" if mode == "historical" else "Addressable customers / opportunities"
        values["planning_units"] = st.number_input(label, min_value=0.01, value=float(current.get("planning_units", 1.0)), step=1.0)
    with c2:
        values["minimum_worthwhile_contribution"] = st.number_input(
            "Minimum worthwhile incremental contribution",
            min_value=0.01,
            value=max(float(current.get("minimum_worthwhile_contribution", 1.0)), 0.01),
            step=1.0,
            help=(
                "The smallest total incremental contribution that would make the candidate price worth adopting. "
                "It must be above zero — with zero, the reading collapses into a bare significance statement, "
                "which PriceSignal refuses to present as a decision."
            ),
        )
    with c3:
        values["currency"] = st.text_input("Currency label", value=str(current.get("currency", "NOK")), max_chars=12)
    values["bootstrap_iterations"] = int(current.get("bootstrap_iterations", 500))
    values["seed"] = int(current.get("seed", 20260716))
    st.caption(
        "Historical quantity is interpreted in its existing planning unit and then multiplied by the planning multiplier. "
        "Randomized quantity is per assigned unit; WTP becomes an acceptance share."
    )
    if st.button("Save evidence contract", type="primary", key="save_contract"):
        try:
            config_from_contract(values)
            st.session_state["contract"] = values
            reset_results()
            st.success("Contract saved. Continue to the data and support audit.")
        except Exception as exc:
            show_error(exc)


def render_audit() -> None:
    st.title("Data and support audit")
    data = st.session_state.get("data")
    contract = st.session_state.get("contract")
    if not isinstance(data, pd.DataFrame) or not isinstance(contract, dict):
        st.info("Load data and save an evidence contract first.")
        return
    try:
        config = config_from_contract(contract)
        audit = audit_price_data(data, config)
        st.session_state["audit"] = audit
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
        if st.button("Run pricing analysis", type="primary", key="run_analysis", disabled=bool(audit.blockers)):
            analysis = analyze_price(data, config)
            st.session_state["analysis"] = analysis
            st.success("Analysis complete. Continue to demand and economics.")
    except Exception as exc:
        show_error(exc)


def _analysis_or_message():
    analysis = st.session_state.get("analysis")
    if analysis is None:
        st.info("Run the pricing analysis on page 2 first.")
        return None
    return analysis


def render_effects() -> None:
    st.title("Demand and economics")
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
    grid = analysis.price_grid
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(
            x=grid["price"],
            y=grid["projected_volume"],
            name="Projected volume",
            line={"color": COLORS["mint"], "width": 3},
            hovertemplate="Price %{x:.2f}<br>Volume %{y:,.1f}<extra></extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=pd.concat([grid["price"], grid["price"].iloc[::-1]]),
            y=pd.concat([grid["volume_high"], grid["volume_low"].iloc[::-1]]),
            fill="toself",
            fillcolor="rgba(131,210,180,.16)",
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
            line={"color": COLORS["coral"], "width": 3},
            hovertemplate="Price %{x:.2f}<br>Contribution %{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )
    for price, label in [(config.reference_price, "Reference"), (config.candidate_price, "Candidate")]:
        figure.add_vline(x=price, line_dash="dot", line_color=COLORS["gold"], annotation_text=label)
    figure.update_layout(
        height=540,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,.6)",
        legend={"orientation": "h", "y": 1.08},
        hovermode="x unified",
    )
    figure.update_xaxes(title="Price")
    figure.update_yaxes(title="Projected volume / acceptance", secondary_y=False)
    figure.update_yaxes(title=f"Contribution ({config.currency})", secondary_y=True)
    full_width(st.plotly_chart, figure)
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
        full_width(st.dataframe, grid, hide_index=True)
    for warning in analysis.warnings:
        st.warning(warning)


def render_decision() -> None:
    st.title("Decision and export")
    analysis = _analysis_or_message()
    if analysis is None:
        return
    comparison = analysis.comparison
    config = analysis.config
    st.markdown(
        f"""<section class="ps-decision"><b>{analysis.evidence_tier}</b><h2>{comparison['status']}</h2>
        <p>{comparison['explanation']}</p></section>""",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reference contribution", money(comparison["reference_contribution"], config.currency))
    c2.metric("Candidate contribution", money(comparison["candidate_contribution"], config.currency))
    c3.metric("Incremental", money(comparison["incremental_contribution"], config.currency))
    c4.metric(
        "95% interval",
        f"{comparison['incremental_low']:,.0f} to {comparison['incremental_high']:,.0f}",
    )
    st.markdown(
        f"""<div class="ps-note"><b>Decision contract:</b> compare {config.candidate_price:,.2f} with
        {config.reference_price:,.2f} {config.currency}; require at least
        {config.minimum_worthwhile_contribution:,.0f} {config.currency} incremental contribution. The candidate
        {'is' if comparison['within_observed_support'] else 'is not'} inside observed support.</div>""",
        unsafe_allow_html=True,
    )
    source = st.session_state.get("source", {})
    contract = st.session_state.get("contract", {})
    pack = build_evidence_pack(source=source, contract=contract, analysis=analysis)
    bridge = build_gate_bridge(analysis)
    st.subheader("Portable, aggregate evidence")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.download_button("Evidence JSON", evidence_to_json(pack), "pricesignal-evidence.json", "application/json")
    with d2:
        st.download_button(
            "Evidence workbook",
            evidence_to_excel(pack),
            "pricesignal-evidence.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with d3:
        st.download_button("CSV evidence pack", evidence_to_csv_zip(pack), "pricesignal-evidence.zip", "application/zip")
    with d4:
        st.download_button("GateSignal bridge", evidence_to_json(bridge), "pricesignal-gate-bridge.json", "application/json")
    st.caption("Exports exclude uploaded row-level records, identifiers, fitted values, residuals, and free text.")


def render_methods() -> None:
    st.title("Methods and limits")
    st.warning(CAUTION)
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
        At each supported price, PriceSignal calculates `projected volume × (price − declared unit cost)`. It then
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
        "PriceSignal is independently designed from public literature. It does not reproduce lecture slides, classroom cases, "
        "exam material, proprietary pricing templates, or institution-specific wording."
    )


with st.sidebar:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f'<div class="ps-lockup">{mark}<div><div class="ps-name">Price<span>Signal</span></div>'
        '<p class="ps-tag">Pricing evidence without false precision.</p></div></div>',
        unsafe_allow_html=True,
    )
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.divider()
    upload = st.file_uploader("Upload pricing evidence", type=["csv", "xlsx", "json"])
    if upload is not None:
        fingerprint = hashlib.sha256(upload.getvalue()).hexdigest()
        if st.session_state.get("uploaded_sha256") != fingerprint:
            try:
                data, source = read_table(upload.getvalue(), upload.name)
                st.session_state["data"] = data
                st.session_state["source"] = source
                st.session_state["uploaded_sha256"] = fingerprint
                st.session_state.pop("contract", None)
                reset_results()
                st.success(f"Loaded {len(data):,} rows.")
            except Exception as exc:
                show_error(exc)
    st.caption("Local mode · no account · no telemetry · no external AI call")
    st.divider()
    mode_for_template = str(st.session_state.get("contract", {}).get("mode", "randomized"))
    st.download_button(
        "Download starter workbook",
        dataframe_to_xlsx(starter_template(mode_for_template)),
        f"pricesignal-{mode_for_template}-template.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


masthead()
renderers = {
    "Welcome": render_welcome,
    "1 · Evidence contract": render_contract,
    "2 · Data & support audit": render_audit,
    "3 · Demand & economics": render_effects,
    "4 · Decision & export": render_decision,
    "Methods & limits": render_methods,
}
renderers[page]()
footer()
