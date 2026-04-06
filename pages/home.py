"""Home / Research Input page."""

from __future__ import annotations

import streamlit as st

from database.crud import get_stats


def render(db) -> None:
    st.title("🎯 Lead Intelligence & Customer Qualification Platform")
    st.markdown(
        """
        **Research companies at scale.** Enter a list of company names below and the platform
        will automatically discover corporate structures, global production sites,
        and key contacts — then score each lead.
        """
    )

    stats = get_stats(db)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏢 Companies", stats["companies"])
    col2.metric("🏭 Plants / Sites", stats["plants"])
    col3.metric("👥 Contacts", stats["contacts"])
    col4.metric("🔗 Subsidiaries", stats["subsidiaries"])

    st.divider()

    # ── Input section ─────────────────────────────────────────────────────────
    st.subheader("🔍 Research New Companies")

    col_input, col_opts = st.columns([3, 1])
    with col_input:
        companies_raw = st.text_area(
            "Company names (one per line)",
            height=200,
            placeholder="e.g.\nSiemens\nBosch\nCaterpillar\nABB",
            help="Enter one company name per line. You can also paste a CSV column.",
        )
    with col_opts:
        st.markdown("**Upload CSV**")
        uploaded = st.file_uploader("CSV with company names", type=["csv", "txt"])
        if uploaded:
            import pandas as pd
            try:
                df = pd.read_csv(uploaded, header=None)
                # Use first column
                companies_raw = "\n".join(df.iloc[:, 0].dropna().astype(str).tolist())
                st.success(f"Loaded {len(df)} companies")
            except Exception:
                st.error("Could not parse file. Ensure one company per row.")

    companies = [c.strip() for c in companies_raw.splitlines() if c.strip()]
    if companies:
        st.info(f"**{len(companies)}** compan{'y' if len(companies) == 1 else 'ies'} ready to research")

    if st.button("🚀 Start Research", type="primary", disabled=not companies):
        _run_research(companies, db)

    # ── Recent activity ───────────────────────────────────────────────────────
    st.divider()
    _recent_activity(db)


def _run_research(companies: list[str], db) -> None:
    from pipeline.processor import run_pipeline

    progress_bar = st.progress(0, text="Initialising...")
    log_placeholder = st.empty()
    results_placeholder = st.empty()

    logs: list[str] = []
    results: list[dict] = []

    def callback(msg: str) -> None:
        logs.append(msg)
        log_placeholder.markdown(
            "**Research log:**\n```\n" + "\n".join(logs[-12:]) + "\n```"
        )

    total = len(companies)
    for idx, name in enumerate(companies):
        progress_bar.progress((idx) / total, text=f"Researching {name}… ({idx+1}/{total})")
        try:
            summary = run_pipeline(name, db, progress_callback=callback)
            results.append(summary)
        except Exception as exc:
            st.warning(f"⚠️ Pipeline error for {name!r}: {exc}")

    progress_bar.progress(1.0, text="✅ Research complete!")
    log_placeholder.empty()

    if results:
        import pandas as pd

        st.success(f"✅ Researched {len(results)} companies successfully.")
        df = pd.DataFrame(results).rename(columns={
            "name": "Company",
            "score": "Score",
            "tier": "Tier",
            "plants_found": "Plants Found",
            "contacts_found": "Contacts Found",
            "subsidiaries_found": "Subsidiaries Found",
        })
        results_placeholder.dataframe(df, use_container_width=True, hide_index=True)
        st.balloons()


def _recent_activity(db) -> None:
    from database.crud import list_companies
    import pandas as pd

    companies = list_companies(db)
    if not companies:
        st.info("No companies researched yet. Use the form above to get started.")
        return

    st.subheader("📋 Recently Researched Companies")
    rows = []
    for c in companies[:10]:
        rows.append({
            "Company": c.name,
            "Industry": c.industry or "—",
            "HQ": f"{c.headquarters_city or ''}, {c.headquarters_country or ''}".strip(", ") or "—",
            "Score": c.qualification_score,
            "Tier": c.qualification_tier or "—",
            "Plants": len(c.plants),
            "Contacts": len(c.contacts),
            "Status": c.research_status,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
