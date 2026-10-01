"""Tag Signal user interface: the Signal Hub entry point.

The only package under ``tagsignal`` that imports Streamlit or Plotly. ``render()`` draws the whole app on the
current page and never calls ``st.set_page_config``; the standalone ``app.py`` or Signal Hub owns the page config.
"""

from tagsignal import __version__
from tagsignal.ui import signal_theme
from tagsignal.ui.app import render

APP_INFO = {"product": "Tag Signal", "version": __version__, "repo": "pricing-analysis", "slug": "tag"}

__all__ = ["APP_INFO", "render", "signal_theme"]
