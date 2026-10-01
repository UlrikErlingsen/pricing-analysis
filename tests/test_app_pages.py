from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest
APP = str(Path(__file__).parents[1] / "app.py")

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
