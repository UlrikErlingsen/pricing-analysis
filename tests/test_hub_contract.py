"""Signal Hub contract: importable UI entry point, Streamlit only under ui/, slug-namespaced state, packaged install."""

import ast
from pathlib import Path
import re
import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

from tagsignal import __version__


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "tagsignal"
UI = PACKAGE / "ui"
UI_ONLY_LIBRARIES = {"streamlit", "plotly"}
PAGES = [
    "Welcome",
    "1 · Evidence contract",
    "2 · Data & support audit",
    "3 · Demand & economics",
    "4 · Decision & export",
    "Methods & limits",
]
RENDER_SCRIPT = """
from tagsignal.ui import render

render()
"""


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _rendered_with_demo() -> AppTest:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    app.button(key="tag:load_random_demo").click().run()
    return app


def test_ui_entry_point_matches_the_hub_contract() -> None:
    from tagsignal.ui import APP_INFO, render

    assert callable(render)
    assert APP_INFO == {"product": "Tag Signal", "version": __version__, "repo": "pricing-analysis", "slug": "tag"}


def test_only_the_ui_package_imports_streamlit_or_plotly() -> None:
    offenders = {
        str(path.relative_to(PACKAGE)): sorted(_imported_roots(path) & UI_ONLY_LIBRARIES)
        for path in PACKAGE.rglob("*.py")
        if UI not in path.parents and _imported_roots(path) & UI_ONLY_LIBRARIES
    }
    assert not offenders, offenders


def test_core_package_imports_without_streamlit_or_plotly() -> None:
    # A fresh interpreter, so modules already imported by other tests cannot hide a stray import.
    code = (
        f"import sys\nsys.path.insert(0, {str(ROOT / 'src')!r})\n"
        "import tagsignal, tagsignal.analysis, tagsignal.errors, tagsignal.examples, tagsignal.io\n"
        "loaded = sorted(name for name in ('streamlit', 'plotly') if name in sys.modules)\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_render_never_sets_page_config_or_navigation() -> None:
    for path in UI.glob("*.py"):
        if path.name == "signal_theme.py":
            continue
        source = path.read_text(encoding="utf-8")
        for call in ("st.set_page_config(", "st.navigation(", "st.Page("):
            assert call not in source, (path.name, call)


def test_render_runs_from_a_script_without_set_page_config() -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()

    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].key == "tag:page"
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "PRICING EVIDENCE &amp; DECISION SUPPORT" in body
    assert f"Tag Signal v{__version__}" in body

    app.button(key="tag:load_random_demo").click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert "tag:data" in app.session_state
    assert "data" not in app.session_state


@pytest.mark.parametrize("page", PAGES)
def test_every_widget_key_is_namespaced(page: str) -> None:
    app = _rendered_with_demo()
    app.sidebar.radio[0].set_value(page).run()
    if page == "2 · Data & support audit":
        app.button(key="tag:run_analysis").click().run()

    assert not app.exception, [error.value for error in app.exception]
    widgets = [
        *app.radio,
        *app.selectbox,
        *app.multiselect,
        *app.checkbox,
        *app.button,
        *app.number_input,
        *app.text_input,
    ]
    assert widgets
    unkeyed = [(type(widget).__name__, widget.label) for widget in widgets if widget.key is None]
    assert not unkeyed, unkeyed
    assert all(widget.key.startswith("tag:") for widget in widgets)
    assert all(key.startswith("tag:") for key in app.session_state), list(app.session_state)


def test_session_state_and_widget_keys_go_through_the_namespace_helper() -> None:
    source = (UI / "app.py").read_text(encoding="utf-8")
    state_keys = re.findall(r"session_state(?:\[|\.get\(|\.pop\()\s*([^,\])]+)", source)
    widget_keys = re.findall(r"\bkey=([^,)\n]+)", source)
    assert state_keys and widget_keys
    assert all(key.startswith("k(") for key in state_keys), state_keys
    assert all(key.startswith("k(") for key in widget_keys), widget_keys
    assert 'NS = "tag"' in source


def test_ui_reads_no_repository_root_files() -> None:
    # Signal Hub installs the release as a normal package: only src/tagsignal/ and its package data exist there.
    # Demos and starter templates are generated in code; the marks are package data next to the theme.
    for path in UI.glob("*.py"):
        if path.name == "signal_theme.py":
            continue
        source = path.read_text(encoding="utf-8")
        for marker in ("__file__", "open(", "read_bytes(", "read_text(", "read_csv(", "read_excel("):
            assert marker not in source, (path.name, marker)

    from tagsignal.ui import signal_theme as sig

    assets = sig.ASSETS.resolve()
    assert assets.is_relative_to(PACKAGE.resolve())
    for name in ("tagsignal-mark.svg", "tagsignal-mark-64.png"):
        assert (assets / "marks" / name).is_file(), name
    assert sig.page_config("tag")["page_icon"].endswith("tagsignal-mark-64.png")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[tool.setuptools.package-data]\n"tagsignal.ui" = ["assets/marks/*"]' in pyproject


def test_demo_loading_does_not_depend_on_repository_files() -> None:
    app = _rendered_with_demo()

    assert not app.exception, [error.value for error in app.exception]
    source = app.session_state["tag:source"]
    assert source["source_type"] == "deterministic synthetic demonstration"
    assert len(app.session_state["tag:data"]) == 720
