from pathlib import Path

from streamlit.testing.v1 import AppTest

from tagsignal import __version__


ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
UI = ROOT / "src" / "tagsignal" / "ui"


def test_shared_signal_shell_renders() -> None:
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()

    assert not app.exception, [error.value for error in app.exception]
    body = "\n".join(str(item.value) for item in app.markdown)
    sidebar = "\n".join(str(item.value) for item in app.sidebar.markdown)
    sidebar_captions = "\n".join(str(item.value) for item in app.sidebar.caption)
    assert "EVIDENCE → RESPONSE → ECONOMICS" in body
    assert "PRICING EVIDENCE &amp; DECISION SUPPORT" in body
    assert f"Tag Signal v{__version__}" in body
    assert "scenario bounds, not market truth" in body
    assert "Part of the Signal suite" in body
    assert "AGPL-3.0-or-later" in body
    assert "sg-mast" in body  # the shared Signal masthead
    assert "sg-foot" in body  # the shared Signal footer
    assert "Pricing evidence without false precision." in sidebar
    assert "sg-side" in sidebar  # the shared Signal sidebar lockup
    assert "no telemetry" in sidebar_captions


def test_app_uses_shared_signal_theme_instead_of_pasted_styles() -> None:
    standalone = (ROOT / "app.py").read_text(encoding="utf-8")
    ui_source = (UI / "app.py").read_text(encoding="utf-8")
    theme = (UI / "signal_theme.py").read_text(encoding="utf-8")
    assert 'st.set_page_config(**sig.page_config("tag"))' in standalone
    assert "sig.apply(NS)" in ui_source
    assert "template=sig.template(NS)" in ui_source
    assert "st.plotly_chart(" not in ui_source  # charts go through sig.chart (template + theme=None)
    assert "<style>" not in standalone + ui_source
    assert "unsafe_allow_html" not in ui_source
    for old_colour in ("#173c3a", "#d95b40", "#83d2b4", "#f2c66d", "#17322e", "#102c2a", "#f8f5ed", "#59716c"):
        assert old_colour not in (standalone + ui_source).lower()
    assert "131,210,180" not in ui_source  # the old mint interval band
    assert (UI / "assets" / "marks" / "tagsignal-mark-64.png").exists()
    assert ":focus-visible" in theme
    assert "@media (max-width:760px)" in theme
    assert "@media (prefers-reduced-motion:reduce)" in theme
    assert "friendly_message" in ui_source


def test_runtime_scaffolding_is_private_and_health_checked() -> None:
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    launcher = (ROOT / "run_app.command").read_text(encoding="utf-8")

    assert "gatherUsageStats = false" in config
    assert "maxUploadSize = 50" in config  # the original upload limit, matching the 50 MB check in io.py
    assert 'base = "light"' in config
    assert 'primaryColor = "#a06f1f"' in config  # Signal Research family, 600 step
    assert "USER tagsignal" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "8588" in dockerfile
    assert "--browser.gatherUsageStats=false" in launcher
    assert "TAGSIGNAL_PORT" in launcher


def test_readme_matches_suite_information_architecture() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Signal README template order: readers find the same section in the same place in every repo.
    sections = [
        "## Read this first",
        "## Scope",
        "## Try the demo in three minutes",
        "## Data contract",
        "## Analysis contract",
        "## Methods",
        "## Decision statuses",
        "## Exports",
        "## Run locally",
        "## Privacy",
        "## No install? Give this file to an AI",
        "## Development",
        "## Where this fits in Signal",
        "## References",
        "## Originality and license",
    ]
    positions = [readme.find(f"\n{heading}\n") for heading in sections]
    assert all(position >= 0 for position in positions), dict(zip(sections, positions, strict=True))
    assert positions == sorted(positions)
    assert readme.startswith('<p align="center">\n  <img src="assets/tagsignal-banner.png"')
    assert "assets/tagsignal-banner.svg" not in readme
    assert "Signal-Research-a06f1f" in readme  # family badge in the Research 600 colour
    assert "github.com/UlrikErlingsen/pricing-analysis/actions" in readme  # tests badge
    assert "**Tag Signal**" in readme
    assert "TagSignal**" not in readme
    assert '<img src="assets/tagsignal-mark-64.png"' in readme  # suite footer
    assert "Creator Signal" not in readme
    assert "does not turn a model into market truth" in readme
    assert "ASSOCIATION ONLY" in readme
    assert "not trademark clearance" in readme
    assert "signal.price-evidence.v1" in readme
    for path in ("assets/tagsignal-banner.png", "assets/tagsignal-mark-64.png", "assets/tagsignal-social.png"):
        assert (ROOT / path).exists()
    assert not (ROOT / "assets" / "tagsignal-banner.svg").exists()
