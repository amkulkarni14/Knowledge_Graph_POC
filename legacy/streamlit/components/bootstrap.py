"""Makes `src/` importable and keeps one PipelineContext per browser session."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data_pipeline" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st  # noqa: E402

from kg_pipeline.core.context import PipelineContext  # noqa: E402


def get_ctx() -> PipelineContext:
    if "ctx" not in st.session_state:
        st.session_state["ctx"] = PipelineContext()
    return st.session_state["ctx"]


def reset_ctx() -> None:
    old = st.session_state.get("ctx")
    if old is not None and old.source is not None:
        try:
            old.source.close()
        except Exception:  # noqa: BLE001
            pass
    st.session_state["ctx"] = PipelineContext()
    for k in [k for k in st.session_state if k != "ctx"]:
        del st.session_state[k]
