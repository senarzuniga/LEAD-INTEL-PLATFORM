"""Contacts page – view and filter professional contacts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from database.crud import list_companies, list_contacts


def render(db) -> None:
    st.title("👥 Contacts")

    contacts = list_contacts(db)
    companies = {c.id: c.name for c in list_companies(db)}

    if not contacts:
        st.info("No contacts in the database yet. Research companies first.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    company_opts = ["All"] + sorted(companies.values())
    company_filter = col1.selectbox("Company", company_opts)
    seniority_opts = ["All", "C-level", "VP", "Director", "Manager", "Individual"]
    seniority_filter = col2.selectbox("Seniority", seniority_opts)
    dept_opts = ["All"] + sorted({c.department for c in contacts if c.department})
    dept_filter = col3.selectbox("Department", dept_opts)
    has_email = col4.checkbox("Has email", value=False)

    filtered = contacts
    if company_filter != "All":
        cid = next((k for k, v in companies.items() if v == company_filter), None)
        if cid:
            filtered = [c for c in filtered if c.company_id == cid]
    if seniority_filter != "All":
        filtered = [c for c in filtered if c.seniority == seniority_filter]
    if dept_filter != "All":
        filtered = [c for c in filtered if c.department == dept_filter]
    if has_email:
        filtered = [c for c in filtered if c.email]

    st.caption(f"Showing {len(filtered)} of {len(contacts)} contacts")

    # ── Table ─────────────────────────────────────────────────────────────────
    rows = []
    for c in filtered:
        rows.append({
            "Company": companies.get(c.company_id, "—"),
            "Name": c.full_name,
            "Title": c.title or "—",
            "Department": c.department or "—",
            "Seniority": c.seniority or "—",
            "Email": c.email or "—",
            "Phone": c.phone or "—",
            "LinkedIn": c.linkedin_url or "—",
            "Source": c.source or "—",
            "Confidence": f"{c.confidence_score:.0%}" if c.confidence_score else "—",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Quick export ──────────────────────────────────────────────────────────
    if rows:
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download contacts as CSV",
            data=csv,
            file_name="contacts.csv",
            mime="text/csv",
        )
