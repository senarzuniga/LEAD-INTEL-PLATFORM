"""Pipeline processor: converts raw research results into database records."""

from __future__ import annotations

from typing import Callable, Optional

from sqlalchemy.orm import Session

from config import logger
from database import crud
from pipeline.qualifier import score_company
from research.company_researcher import research_company
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import traceback

MIN_CONTACT_NAME_LENGTH = 3


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def run_pipeline(
    company_name: str,
    db: Session,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Full pipeline for one company:
    1. Research (web, Wikipedia, yfinance, scraping)
    2. Persist to database
    3. Score and qualify
    Returns a summary dict.
    """
    def _log(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    _log(f"▶ Starting pipeline for: {company_name}")

    try:
        # ── Research ──────────────────────────────────────────────────────────────
        data = research_company(company_name, progress_callback=progress_callback)
        company_data = data.get("company", {})

        # ── Persist company ───────────────────────────────────────────────────────
        _log("💾 Saving company to database...")
        company = crud.upsert_company(
            db,
            name=company_name,
            domain=company_data.get("domain"),
            description=company_data.get("description"),
            industry=company_data.get("industry"),
            employee_count=company_data.get("employee_count"),
            annual_revenue=company_data.get("annual_revenue"),
            headquarters_city=company_data.get("headquarters_city"),
            headquarters_country=company_data.get("headquarters_country"),
            founded_year=company_data.get("founded_year"),
            stock_ticker=company_data.get("stock_ticker"),
            linkedin_url=company_data.get("linkedin_url"),
            research_status="done",
            research_notes=_build_notes(data),
        )

        # ── Persist subsidiaries ──────────────────────────────────────────────────
        for sub in data.get("subsidiaries", []):
            try:
                crud.add_subsidiary(
                    db,
                    parent_id=company.id,
                    name=sub.get("name", "")[:255],
                    relationship_type=sub.get("relationship_type", "subsidiary"),
                    country=sub.get("country"),
                    notes=sub.get("notes"),
                )
            except Exception as exc:
                logger.error("Could not save subsidiary %r: %s", sub.get("name"), exc)
                logger.debug(traceback.format_exc())

        # ── Persist plants ────────────────────────────────────────────────────────
        for plant in data.get("plants", []):
            try:
                crud.add_plant(
                    db,
                    company_id=company.id,
                    name=plant.get("name", f"{plant.get('city', '')} Facility")[:255],
                    site_type=plant.get("site_type", "facility"),
                    city=plant.get("city"),
                    state=plant.get("state"),
                    country=plant.get("country"),
                    latitude=plant.get("latitude"),
                    longitude=plant.get("longitude"),
                    employee_count=plant.get("employee_count"),
                    status=plant.get("status", "active"),
                    source_url=plant.get("source_url"),
                    notes=plant.get("notes"),
                )
            except Exception as exc:
                logger.error("Could not save plant %r: %s", plant.get("name"), exc)
                logger.debug(traceback.format_exc())

        # ── Persist contacts ──────────────────────────────────────────────────────
        for contact in data.get("contacts", []):
            if not contact.get("full_name") or len(contact["full_name"].strip()) < MIN_CONTACT_NAME_LENGTH:
                continue
            try:
                crud.add_contact(
                    db,
                    company_id=company.id,
                    full_name=contact["full_name"][:255],
                    title=contact.get("title", "")[:255],
                    department=contact.get("department", ""),
                    seniority=contact.get("seniority", "Individual"),
                    email=contact.get("email"),
                    phone=contact.get("phone"),
                    linkedin_url=contact.get("linkedin_url"),
                    source=contact.get("source", "web_search"),
                    confidence_score=contact.get("confidence_score", 0.4),
                )
            except Exception as exc:
                logger.error("Could not save contact %r: %s", contact.get("full_name"), exc)
                logger.debug(traceback.format_exc())

        # Refresh company with relationships loaded for scoring
        db.refresh(company)

        # ── Score & qualify ───────────────────────────────────────────────────────
        score, tier = score_company(company)
        company.qualification_score = score
        company.qualification_tier = tier
        db.flush()

        _log(f"✅ Pipeline complete. Score: {score}/100 | Tier: {tier}")

        return {
            "company_id": company.id,
            "name": company.name,
            "score": score,
            "tier": tier,
            "plants_found": len(data.get("plants", [])),
            "contacts_found": len(data.get("contacts", [])),
            "subsidiaries_found": len(data.get("subsidiaries", [])),
        }

    except Exception as e:
        logger.error("An error occurred in the pipeline: %s", e)
        logger.debug(traceback.format_exc())
        raise


def _build_notes(data: dict) -> str:
    news = data.get("raw_news", [])
    if not news:
        return ""
    snippets = [f"• {n['title']}" for n in news[:5]]
    return "Recent news:\n" + "\n".join(snippets)
