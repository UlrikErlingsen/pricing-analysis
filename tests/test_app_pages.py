from __future__ import annotations

from streamlit.testing.v1 import AppTest


def app() -> AppTest:
    return AppTest.from_file("app.py", default_timeout=40).run()


def test_welcome_page_and_brand_render() -> None:
    at = app()
    assert not at.exception
    assert any("TagSignal" in markdown.value for markdown in at.markdown)
    assert any("does not turn a model into market truth" in warning.value for warning in at.warning)


def test_brand_wordmark_persists_across_pages() -> None:
    at = app()
    at.radio[0].set_value("Methods & limits").run()
    assert not at.exception
    assert any("TagSignal" in markdown.value for markdown in at.markdown)


def test_every_page_renders_with_randomized_demo() -> None:
    at = app()
    at.button(key="load_random_demo").click().run()
    for page in [
        "1 · Evidence contract",
        "2 · Data & support audit",
        "3 · Demand & economics",
        "4 · Decision & export",
        "Methods & limits",
    ]:
        at.radio[0].set_value(page).run()
        assert not at.exception, page


def test_demo_analysis_flow_produces_evidence_exports() -> None:
    at = app()
    at.button(key="load_random_demo").click().run()
    at.radio[0].set_value("2 · Data & support audit").run()
    at.button(key="run_analysis").click().run()
    assert "analysis" in at.session_state
    assert at.session_state["analysis"].evidence_tier == "RANDOMIZED PRICE EVIDENCE"
    at.radio[0].set_value("3 · Demand & economics").run()
    assert not at.exception
    assert len(at.metric) >= 4
    at.radio[0].set_value("4 · Decision & export").run()
    assert not at.exception
    assert len(at.download_button) >= 5
