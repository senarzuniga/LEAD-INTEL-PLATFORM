"""Analytics page – charts and key insights."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from database.crud import list_companies, list_contacts, list_plants


def render(db) -> None:
    st.title("📊 Analytics & Insights")

    companies = list_companies(db)
    plants = list_plants(db)
    contacts = list_contacts(db)

    if not companies:
        st.info("No data yet. Research some companies first.")
        return

    # ── KPI row ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Companies", len(companies))
    col2.metric("Plants", len(plants))
    col3.metric("Contacts", len(contacts))
    tier_a = sum(1 for c in companies if c.qualification_tier == "A")
    col4.metric("Tier A Leads", tier_a)
    avg_score = sum(c.qualification_score or 0 for c in companies) / max(len(companies), 1)
    col5.metric("Avg Score", f"{avg_score:.1f}")

    st.divider()

    # ── Row 1: Tier distribution + Industry breakdown ─────────────────────────
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Lead Tier Distribution")
        tier_counts = pd.Series([c.qualification_tier or "D" for c in companies]).value_counts()
        fig = px.pie(
            values=tier_counts.values,
            names=tier_counts.index,
            color=tier_counts.index,
            color_discrete_map={"A": "#2ecc71", "B": "#3498db", "C": "#f39c12", "D": "#e74c3c"},
            hole=0.45,
        )
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

    with row1_col2:
        st.subheader("Top Industries")
        industries = [c.industry for c in companies if c.industry]
        if industries:
            ind_counts = pd.Series(industries).value_counts().head(10)
            fig2 = px.bar(
                x=ind_counts.values,
                y=ind_counts.index,
                orientation="h",
                labels={"x": "Companies", "y": "Industry"},
                color=ind_counts.values,
                color_continuous_scale="Blues",
            )
            fig2.update_layout(showlegend=False, coloraxis_showscale=False, yaxis={"autorange": "reversed"})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No industry data available yet.")

    # ── Row 2: Score distribution + Plants per company ────────────────────────
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("Qualification Score Distribution")
        scores = [c.qualification_score or 0 for c in companies]
        fig3 = px.histogram(
            x=scores,
            nbins=20,
            labels={"x": "Score", "y": "Companies"},
            color_discrete_sequence=["#3498db"],
        )
        fig3.update_layout(bargap=0.05)
        st.plotly_chart(fig3, use_container_width=True)

    with row2_col2:
        st.subheader("Plants per Company (Top 15)")
        plant_counts = {c.name: len(c.plants) for c in companies if c.plants}
        if plant_counts:
            sorted_plants = dict(sorted(plant_counts.items(), key=lambda x: x[1], reverse=True)[:15])
            fig4 = px.bar(
                x=list(sorted_plants.values()),
                y=list(sorted_plants.keys()),
                orientation="h",
                labels={"x": "Plants", "y": "Company"},
                color=list(sorted_plants.values()),
                color_continuous_scale="Reds",
            )
            fig4.update_layout(showlegend=False, coloraxis_showscale=False, yaxis={"autorange": "reversed"})
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No plant data available yet.")

    # ── Row 3: Country distribution of plants ─────────────────────────────────
    if plants:
        st.subheader("🌍 Plant Locations by Country")
        country_counts = pd.Series([p.country for p in plants if p.country]).value_counts()
        fig5 = px.choropleth(
            locations=country_counts.index,
            locationmode="country names",
            color=country_counts.values,
            color_continuous_scale="YlOrRd",
            labels={"color": "Plants"},
        )
        fig5.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig5, use_container_width=True)

    # ── Row 4: Contacts seniority breakdown ───────────────────────────────────
    if contacts:
        st.subheader("👥 Contact Seniority Breakdown")
        seniority_counts = pd.Series([c.seniority or "Unknown" for c in contacts]).value_counts()
        fig6 = px.bar(
            x=seniority_counts.index,
            y=seniority_counts.values,
            labels={"x": "Seniority", "y": "Contacts"},
            color=seniority_counts.index,
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        st.plotly_chart(fig6, use_container_width=True)
