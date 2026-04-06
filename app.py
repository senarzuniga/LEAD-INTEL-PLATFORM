"""
Lead Intelligence & Customer Qualification Platform
====================================================
Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Lead Intel Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise database ───────────────────────────────────────────────────────
from database.database import get_db, init_db  # noqa: E402

init_db()

# ── Navigation ────────────────────────────────────────────────────────────────
PAGE_ICONS = {
    "🏠 Home": "home",
    "🏢 Companies": "companies",
    "🏭 Plants & Sites": "plants",
    "👥 Contacts": "contacts",
    "📊 Analytics": "analytics",
    "📤 Export": "export",
}

with st.sidebar:
    st.markdown("## 🎯 Lead Intel")
    st.caption("B2B Intelligence Platform")
    st.divider()

    page_label = st.radio(
        "Navigation",
        list(PAGE_ICONS.keys()),
        label_visibility="collapsed",
    )
    page_key = PAGE_ICONS[page_label]

    st.divider()
    st.caption("© 2025 Lead Intel Platform")

# ── Render selected page ──────────────────────────────────────────────────────
import importlib  # noqa: E402

page_module = importlib.import_module(f"pages.{page_key}")

with get_db() as db:
    page_module.render(db)
