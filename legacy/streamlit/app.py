"""Streamlit entry point:  streamlit run legacy/streamlit/app.py   (run from the project root)."""
from __future__ import annotations

import streamlit as st

from components.bootstrap import get_ctx  # noqa: F401  (also puts data_pipeline/src/ on sys.path)
from components.layout import PAGE_FILES, inject_css, sidebar_status
from kg_pipeline.core.context import PARTS
from kg_pipeline.core.context import STAGES

st.set_page_config(page_title="Enterprise Knowledge Graph Studio", page_icon="🕸️", layout="wide")
inject_css()

nav = {"Overview": [st.Page("pages/home.py", title="Architecture & Quick Run", icon="🏠", default=True)]}
for part, label in PARTS.items():
    nav[f"Part {part} · {label}"] = [
        st.Page(PAGE_FILES[s["no"]], title=f"{s['no']}. {s['title']}", icon=s["icon"])
        for s in STAGES if s["part"] == part]
nav["Use"] = [st.Page("pages/explorer.py", title="Graph Store Explorer", icon="🧭")]

page = st.navigation(nav)
sidebar_status(get_ctx())
page.run()
