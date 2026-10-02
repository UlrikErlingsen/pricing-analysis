from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest
APP = str(Path(__file__).parents[1] / "app.py")
# Renders the app with st.file_uploader stubbed to return a small table, as if the user uploaded it.
UPLOAD_SCRIPT = r"""
import streamlit as st
from tagsignal.ui import render


class _Upload:
    name = "my-prices.csv"

    def getvalue(self):
        return b"price,quantity\n24,120\n29,104\n34,90\n39,71\n"


real_uploader = st.file_uploader
if st.session_state.get("simulate_upload"):
    st.file_uploader = lambda *args, **kwargs: _Upload()
try:
    render()
finally:
    st.file_uploader = real_uploader
"""

def app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=40).run()


def _body(at: AppTest) -> str:
    return "\n".join(str(markdown.value) for markdown in at.markdown)


def test_welcome_page_and_brand_render() -> None:
    at = app()
    assert not at.exception
    assert "Tag <span>Signal</span>" in _body(at)
    assert "does not turn a model into market truth" in _body(at)


def test_brand_wordmark_persists_across_pages() -> None:
    at = app()
    at.radio(key="tag:page").set_value("Methods & limits").run()
    assert not at.exception
    assert "Tag <span>Signal</span>" in _body(at)
    assert "does not turn a model into market truth" in _body(at)


def test_every_page_renders_with_randomized_demo() -> None:
    at = app()
    at.button(key="tag:load_random_demo").click().run()
    for page in [
        "1 · Evidence contract",
        "2 · Data & support audit",
        "3 · Demand & economics",
        "4 · Decision & export",
        "Methods & limits",
    ]:
        at.radio(key="tag:page").set_value(page).run()
        assert not at.exception, page


def test_demo_analysis_flow_produces_evidence_exports() -> None:
    at = app()
    at.button(key="tag:load_random_demo").click().run()
    at.radio(key="tag:page").set_value("2 · Data & support audit").run()
    at.button(key="tag:run_analysis").click().run()
    assert "tag:analysis" in at.session_state
    assert at.session_state["tag:analysis"].evidence_tier == "RANDOMIZED PRICE EVIDENCE"
    at.radio(key="tag:page").set_value("3 · Demand & economics").run()
    assert not at.exception
    assert len(at.metric) >= 4
    at.radio(key="tag:page").set_value("4 · Decision & export").run()
    assert not at.exception
    assert len(at.download_button) >= 5


def test_fresh_run_opens_with_the_fictional_demo_preloaded() -> None:
    at = app()
    assert not at.exception
    assert "fictional randomized price test" in _body(at)
    source = at.session_state["tag:source"]
    assert source["source_type"] == "deterministic synthetic demonstration"
    assert source["source_filename"] == "tagsignal-fictional-randomized-demo.csv"
    assert at.session_state["tag:contract"]["mode"] == "randomized"
    assert at.session_state["tag:analysis"].evidence_tier == "RANDOMIZED PRICE EVIDENCE"
    # No button clicks: every analysis page already shows demo-backed results.
    at.radio(key="tag:page").set_value("2 · Data & support audit").run()
    assert not at.exception
    assert len(at.metric) >= 4
    at.radio(key="tag:page").set_value("3 · Demand & economics").run()
    assert not at.exception
    assert "Run the pricing analysis on page 2 first." not in [info.value for info in at.info]
    assert len(at.metric) >= 4
    at.radio(key="tag:page").set_value("4 · Decision & export").run()
    assert not at.exception
    assert len(at.download_button) >= 5


def test_demo_buttons_still_switch_routes_after_the_preload() -> None:
    at = app()
    at.button(key="tag:load_valuation_demo").click().run()
    assert not at.exception
    assert at.session_state["tag:contract"]["mode"] == "valuation"
    assert "tag:analysis" not in at.session_state
    at.button(key="tag:load_random_demo").click().run()
    assert at.session_state["tag:contract"]["mode"] == "randomized"


def test_an_upload_replaces_the_preloaded_demo() -> None:
    at = AppTest.from_string(UPLOAD_SCRIPT, default_timeout=40).run()
    assert at.session_state["tag:source"]["source_type"] == "deterministic synthetic demonstration"
    at.session_state["simulate_upload"] = True
    at.run()
    assert not at.exception
    assert at.session_state["tag:source"]["source_filename"] == "my-prices.csv"
    assert len(at.session_state["tag:data"]) == 4
    assert "tag:contract" not in at.session_state
    assert "tag:analysis" not in at.session_state
    # Later reruns keep the upload; the demo is never reloaded over it.
    at.radio(key="tag:page").set_value("1 · Evidence contract").run()
    assert not at.exception
    assert at.session_state["tag:source"]["source_filename"] == "my-prices.csv"
