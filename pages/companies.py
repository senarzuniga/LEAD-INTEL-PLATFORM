"""Companies page – browse, search, and view individual company profiles."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.crud import list_companies, delete_company, list_subsidiaries


def render(db) -> None:
    st.title("🏢 Companies")

    companies = list_companies(db)
    if not companies:
        st.info("No companies in the database yet. Go to **Home** to start researching.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    search = col1.text_input("🔎 Search", placeholder="Company name…")
    tier_filter = col2.multiselect("Tier", ["A", "B", "C", "D"], default=[])
    industry_filter = col3.selectbox(
        "Industry",
        ["All"] + sorted({c.industry for c in companies if c.industry}),
    )

    filtered = companies
    if search:
        filtered = [c for c in filtered if search.lower() in c.name.lower()]
    if tier_filter:
        filtered = [c for c in filtered if c.qualification_tier in tier_filter]
    if industry_filter != "All":
        filtered = [c for c in filtered if c.industry == industry_filter]

    st.caption(f"Showing {len(filtered)} of {len(companies)} companies")

    # ── Summary table ─────────────────────────────────────────────────────────
    rows = []
    for c in filtered:
        rows.append({
            "ID": c.id,
            "Company": c.name,
            "Domain": c.domain or "—",
            "Industry": c.industry or "—",
            "HQ": (
                f"{c.headquarters_city or ''}, {c.headquarters_country or ''}".strip(", ") or "—"
            ),
            "Employees": f"{c.employee_count:,}" if c.employee_count else "—",
            "Revenue": c.annual_revenue or "—",
            "Score": c.qualification_score,
            "Tier": c.qualification_tier or "—",
            "Plants": len(c.plants),
            "Contacts": len(c.contacts),
        })

    df = pd.DataFrame(rows)
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # ── Detail panel ──────────────────────────────────────────────────────────
    selected = event.selection.rows if event.selection else []
    if selected:
        company = filtered[selected[0]]
        _render_company_detail(company, db)


def _render_company_detail(company, db) -> None:
    st.divider()
    col_title, col_delete = st.columns([5, 1])
    col_title.subheader(f"📋 {company.name}")
    if col_delete.button("🗑 Delete", key=f"del_{company.id}"):
        delete_company(db, company.id)
        st.rerun()

    # Tier badge colour
    tier_colours = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🔴"}
    tier_icon = tier_colours.get(company.qualification_tier or "D", "⚪")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Qualification Score", f"{company.qualification_score:.0f}/100")
    col2.metric("Tier", f"{tier_icon} {company.qualification_tier or '—'}")
    col3.metric("Plants / Sites", len(company.plants))
    col4.metric("Contacts", len(company.contacts))

    tabs = st.tabs(["ℹ️ Overview", "🏭 Plants", "👥 Contacts", "🔗 Subsidiaries", "📰 Notes"])

    with tabs[0]:
        _render_overview(company)
    with tabs[1]:
        _render_plants(company)
    with tabs[2]:
        _render_contacts(company)
    with tabs[3]:
        _render_subsidiaries(company, db)
    with tabs[4]:
        st.text(company.research_notes or "No notes.")


def _render_overview(company) -> None:
    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"**Domain:** {company.domain or '—'}")
        st.markdown(f"**Industry:** {company.industry or '—'}")
        st.markdown(f"**Sub-industry:** {company.sub_industry or '—'}")
        st.markdown(f"**Founded:** {company.founded_year or '—'}")
        st.markdown(f"**Employees:** {f'{company.employee_count:,}' if company.employee_count else '—'}")
        st.markdown(f"**Revenue:** {company.annual_revenue or '—'}")
    with cols[1]:
        st.markdown(f"**HQ City:** {company.headquarters_city or '—'}")
        st.markdown(f"**HQ Country:** {company.headquarters_country or '—'}")
        st.markdown(f"**Stock Ticker:** {company.stock_ticker or '—'}")
        if company.linkedin_url:
            st.markdown(f"**LinkedIn:** [Profile]({company.linkedin_url})")
        if company.domain:
            st.markdown(f"**Website:** [Visit](https://{company.domain})")

    if company.description:
        st.markdown("**Description:**")
        st.markdown(company.description[:600])


def _render_plants(company) -> None:
    if not company.plants:
        st.info("No plants / sites found.")
        return
    rows = []
    for p in company.plants:
        rows.append({
            "Name": p.name,
            "Type": p.site_type or "—",
            "City": p.city or "—",
            "State": p.state or "—",
            "Country": p.country or "—",
            "Employees": f"{p.employee_count:,}" if p.employee_count else "—",
            "Status": p.status or "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_contacts(company) -> None:
    if not company.contacts:
        st.info("No contacts found.")
        return
    rows = []
    for c in company.contacts:
        rows.append({
            "Name": c.full_name,
            "Title": c.title or "—",
            "Department": c.department or "—",
            "Seniority": c.seniority or "—",
            "Email": c.email or "—",
            "Phone": c.phone or "—",
            "Source": c.source or "—",
            "Confidence": f"{c.confidence_score:.0%}" if c.confidence_score else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_subsidiaries(company, db) -> None:
    subs = list_subsidiaries(db, company.id)
    if not subs:
        st.info("No subsidiaries found.")
        return
    rows = [{"Name": s.name, "Type": s.relationship_type, "Country": s.country or "—"} for s in subs]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
