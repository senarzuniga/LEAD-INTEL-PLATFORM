"""Export page – download full dataset as CSV or Excel."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from database.crud import list_companies, list_contacts, list_plants, list_subsidiaries


def render(db) -> None:
    st.title("📤 Export Data")

    companies = list_companies(db)
    if not companies:
        st.info("No data to export. Research some companies first.")
        return

    st.markdown("Download your research data in CSV or Excel format.")

    col1, col2, col3 = st.columns(3)

    # ── Companies export ──────────────────────────────────────────────────────
    with col1:
        st.subheader("🏢 Companies")
        companies_df = _build_companies_df(companies)
        st.caption(f"{len(companies_df)} records")
        _download_buttons(companies_df, "companies")

    # ── Plants export ─────────────────────────────────────────────────────────
    with col2:
        st.subheader("🏭 Plants & Sites")
        company_map = {c.id: c.name for c in companies}
        plants = list_plants(db)
        plants_df = _build_plants_df(plants, company_map)
        st.caption(f"{len(plants_df)} records")
        _download_buttons(plants_df, "plants")

    # ── Contacts export ───────────────────────────────────────────────────────
    with col3:
        st.subheader("👥 Contacts")
        contacts = list_contacts(db)
        contacts_df = _build_contacts_df(contacts, company_map)
        st.caption(f"{len(contacts_df)} records")
        _download_buttons(contacts_df, "contacts")

    # ── Full Excel workbook ───────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Full Excel Workbook")
    st.markdown("Download all data in a single Excel file with separate sheets.")

    subsidiaries = []
    for c in companies:
        subsidiaries.extend(list_subsidiaries(db, c.id))
    subsidiaries_df = _build_subsidiaries_df(subsidiaries, {c.id: c.name for c in companies})

    if st.button("Generate Excel Workbook", type="primary"):
        xlsx_bytes = _build_excel({
            "Companies": companies_df,
            "Plants": plants_df,
            "Contacts": contacts_df,
            "Subsidiaries": subsidiaries_df,
        })
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "📥 Download Excel",
            data=xlsx_bytes,
            file_name=f"lead_intel_export_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ── Builders ──────────────────────────────────────────────────────────────────


def _build_companies_df(companies) -> pd.DataFrame:
    return pd.DataFrame([{
        "ID": c.id,
        "Company Name": c.name,
        "Domain": c.domain or "",
        "Industry": c.industry or "",
        "Sub-Industry": c.sub_industry or "",
        "Description": (c.description or "")[:200],
        "Employees": c.employee_count or "",
        "Size Range": c.size_range or "",
        "Annual Revenue": c.annual_revenue or "",
        "HQ City": c.headquarters_city or "",
        "HQ Country": c.headquarters_country or "",
        "HQ Address": c.headquarters_address or "",
        "Founded Year": c.founded_year or "",
        "Stock Ticker": c.stock_ticker or "",
        "LinkedIn URL": c.linkedin_url or "",
        "Parent Company": c.parent_company or "",
        "Qualification Score": c.qualification_score or 0,
        "Qualification Tier": c.qualification_tier or "",
        "Research Status": c.research_status or "",
        "Created At": c.created_at,
    } for c in companies])


def _build_plants_df(plants, company_map: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "ID": p.id,
        "Company": company_map.get(p.company_id, ""),
        "Site Name": p.name,
        "Type": p.site_type or "",
        "Address": p.address or "",
        "City": p.city or "",
        "State": p.state or "",
        "Country": p.country or "",
        "Postal Code": p.postal_code or "",
        "Latitude": p.latitude or "",
        "Longitude": p.longitude or "",
        "Employees": p.employee_count or "",
        "Area (sqft)": p.area_sqft or "",
        "Products": p.products_produced or "",
        "Certifications": p.certifications or "",
        "Year Established": p.year_established or "",
        "Status": p.status or "",
        "Source URL": p.source_url or "",
        "Notes": p.notes or "",
        "Created At": p.created_at,
    } for p in plants])


def _build_contacts_df(contacts, company_map: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "ID": c.id,
        "Company": company_map.get(c.company_id, ""),
        "Full Name": c.full_name,
        "Title": c.title or "",
        "Department": c.department or "",
        "Seniority": c.seniority or "",
        "Email": c.email or "",
        "Phone": c.phone or "",
        "LinkedIn URL": c.linkedin_url or "",
        "Location": c.location or "",
        "Source": c.source or "",
        "Confidence Score": c.confidence_score or "",
        "Notes": c.notes or "",
        "Created At": c.created_at,
    } for c in contacts])


def _build_subsidiaries_df(subsidiaries, company_map: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "ID": s.id,
        "Parent Company": company_map.get(s.parent_id, ""),
        "Subsidiary Name": s.name,
        "Relationship Type": s.relationship_type or "",
        "Country": s.country or "",
        "Industry": s.industry or "",
        "Notes": s.notes or "",
        "Created At": s.created_at,
    } for s in subsidiaries])


def _download_buttons(df: pd.DataFrame, label: str) -> None:
    timestamp = datetime.now().strftime("%Y%m%d")
    csv_data = df.to_csv(index=False)
    st.download_button(
        f"📥 CSV",
        data=csv_data,
        file_name=f"lead_intel_{label}_{timestamp}.csv",
        mime="text/csv",
        key=f"csv_{label}",
    )


def _build_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()
