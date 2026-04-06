"""Plants & Sites page – global map and filterable table of all production sites."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from database.crud import list_companies, list_plants


def render(db) -> None:
    st.title("🏭 Plants & Production Sites")

    plants = list_plants(db)
    companies = {c.id: c.name for c in list_companies(db)}

    if not plants:
        st.info("No plants in the database yet. Research companies first.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    company_opts = ["All"] + sorted(companies.values())
    company_filter = col1.selectbox("Company", company_opts)
    country_opts = ["All"] + sorted({p.country for p in plants if p.country})
    country_filter = col2.selectbox("Country", country_opts)
    type_opts = ["All"] + sorted({p.site_type for p in plants if p.site_type})
    type_filter = col3.selectbox("Type", type_opts)
    status_opts = ["All"] + sorted({p.status for p in plants if p.status})
    status_filter = col4.selectbox("Status", status_opts)

    filtered = plants
    if company_filter != "All":
        cid = next((k for k, v in companies.items() if v == company_filter), None)
        if cid:
            filtered = [p for p in filtered if p.company_id == cid]
    if country_filter != "All":
        filtered = [p for p in filtered if p.country == country_filter]
    if type_filter != "All":
        filtered = [p for p in filtered if p.site_type == type_filter]
    if status_filter != "All":
        filtered = [p for p in filtered if p.status == status_filter]

    st.caption(f"Showing {len(filtered)} of {len(plants)} sites")

    # ── Map ───────────────────────────────────────────────────────────────────
    geo_plants = [p for p in filtered if p.latitude and p.longitude]
    if geo_plants:
        _render_map(geo_plants, companies)
    else:
        st.info("No geo-coordinates available for the current filter. Showing table only.")

    # ── Table ─────────────────────────────────────────────────────────────────
    st.subheader("📋 All Sites")
    rows = []
    for p in filtered:
        rows.append({
            "Company": companies.get(p.company_id, "—"),
            "Site Name": p.name,
            "Type": p.site_type or "—",
            "City": p.city or "—",
            "State": p.state or "—",
            "Country": p.country or "—",
            "Employees": f"{p.employee_count:,}" if p.employee_count else "—",
            "Status": p.status or "—",
            "Source": p.source_url or "—",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_map(plants, companies: dict) -> None:
    try:
        import folium
        from streamlit_folium import st_folium

        m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")

        color_map = {
            "manufacturing": "red",
            "warehouse": "blue",
            "office": "green",
            "R&D": "purple",
            "HQ": "darkred",
            "lab": "cadetblue",
            "facility": "orange",
            "plant": "darkred",
        }

        for p in plants:
            color = color_map.get(p.site_type or "facility", "gray")
            popup_html = f"""
            <b>{p.name}</b><br>
            Company: {companies.get(p.company_id, '—')}<br>
            Type: {p.site_type or '—'}<br>
            {p.city or ''}{', ' + p.country if p.country else ''}<br>
            Status: {p.status or '—'}
            """
            folium.CircleMarker(
                location=[p.latitude, p.longitude],
                radius=8,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{p.name} ({companies.get(p.company_id, '?')})",
            ).add_to(m)

        st.subheader("🗺️ Global Site Map")
        st_folium(m, width=None, height=450, returned_objects=[])

    except Exception as exc:
        st.warning(f"Map could not be rendered: {exc}")
