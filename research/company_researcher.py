"""Main research orchestrator – coordinates all sub-modules for one company."""

from __future__ import annotations

from typing import Callable, Optional

from config import logger
from research.contact_finder import find_contacts_web
from research.data_enricher import get_wikipedia_summary, get_yfinance_data, guess_ticker
from research.search_engine import find_domain, search_web
from research.site_finder import find_job_posting_locations, find_sites_from_news, find_sites_from_search
from research.web_scraper import scrape_about_page, scrape_homepage, scrape_locations_page, scrape_team_page


def research_company(
    company_name: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Orchestrate all research for a single company.

    Returns a rich dict with:
        company    – company-level data
        subsidiaries – list of subsidiary dicts
        plants       – list of plant/site dicts
        contacts     – list of contact dicts
        raw_news     – list of recent news snippets
    """
    def _log(msg: str) -> None:
        logger.info("[%s] %s", company_name, msg)
        if progress_callback:
            progress_callback(msg)

    result: dict = {
        "company": {"name": company_name},
        "subsidiaries": [],
        "plants": [],
        "contacts": [],
        "raw_news": [],
    }

    # ── 1. Find domain ────────────────────────────────────────────────────────
    _log("🔍 Finding company domain...")
    domain = find_domain(company_name)
    if domain:
        result["company"]["domain"] = domain
        _log(f"✅ Domain: {domain}")

    # ── 2. Scrape homepage ────────────────────────────────────────────────────
    if domain:
        _log("🌐 Scraping company website...")
        homepage = scrape_homepage(domain)
        if homepage:
            result["company"].setdefault("description", homepage.get("description", ""))
            result["company"]["emails"] = homepage.get("emails", [])
            result["company"]["phones"] = homepage.get("phones", [])
            if homepage.get("social_links", {}).get("linkedin"):
                result["company"]["linkedin_url"] = homepage["social_links"]["linkedin"]

        # Scrape about page for richer description
        about_text = scrape_about_page(domain)
        if about_text and len(about_text) > len(result["company"].get("description", "")):
            result["company"]["description"] = about_text[:800]

    # ── 3. Wikipedia enrichment ───────────────────────────────────────────────
    _log("📖 Checking Wikipedia...")
    wiki = get_wikipedia_summary(company_name)
    if wiki:
        if wiki.get("summary"):
            result["company"].setdefault("description", wiki["summary"])
        if wiki.get("founded_year"):
            result["company"]["founded_year"] = wiki["founded_year"]
        if wiki.get("employee_count"):
            result["company"]["employee_count"] = wiki["employee_count"]
        result["company"]["wikipedia_url"] = wiki.get("url", "")

    # ── 4. Financial data (yfinance) ──────────────────────────────────────────
    _log("📊 Looking up financial data...")
    ticker = guess_ticker(company_name)
    if ticker:
        yf_data = get_yfinance_data(ticker)
        if yf_data:
            _merge(result["company"], yf_data)
            _log(f"✅ Found ticker: {ticker}")

    # ── 5. General web search for company profile ─────────────────────────────
    _log("🔎 Searching web for company profile...")
    profile_results = search_web(f"{company_name} company overview industry employees", max_results=5)
    for r in profile_results[:3]:
        body = r.get("body", "")
        result["raw_news"].append({"title": r.get("title", ""), "snippet": body[:200], "url": r.get("href", "")})

    # Try to extract industry from snippets
    if not result["company"].get("industry"):
        industry = _extract_industry(profile_results)
        if industry:
            result["company"]["industry"] = industry

    # ── 6. Find subsidiaries ──────────────────────────────────────────────────
    _log("🏢 Searching for subsidiaries...")
    subsidiary_results = search_web(
        f"{company_name} subsidiaries divisions brands owned companies", max_results=8
    )
    subsidiaries = _extract_subsidiaries(subsidiary_results, company_name)
    result["subsidiaries"] = subsidiaries
    if subsidiaries:
        _log(f"✅ Found {len(subsidiaries)} subsidiaries/brands")

    # ── 7. Find production sites ──────────────────────────────────────────────
    _log("🏭 Searching for production sites & plants...")
    plants = find_sites_from_search(company_name)
    news_sites = find_sites_from_news(company_name)
    job_sites = find_job_posting_locations(company_name)

    # Also scrape the company website locations page
    if domain:
        website_locations = scrape_locations_page(domain)
        for loc in website_locations:
            plants.append({
                "name": f"Location – {domain}",
                "city": "",
                "country": "",
                "site_type": "office",
                "source_url": loc.get("source_url", ""),
                "notes": loc.get("raw_text", "")[:200],
                "status": "active",
            })

    # Deduplicate and merge all site sources
    all_plants = _deduplicate_sites(plants + news_sites + job_sites)
    result["plants"] = all_plants[:25]
    _log(f"✅ Found {len(result['plants'])} sites/plants")

    # ── 8. Find contacts ──────────────────────────────────────────────────────
    _log("👥 Searching for contacts...")
    contacts = find_contacts_web(company_name, domain=domain)
    if domain:
        team_data = scrape_team_page(domain)
        for td in team_data:
            raw = td.get("raw_text", "")
            contacts.append({
                "full_name": raw[:40],
                "title": "",
                "email": td.get("email"),
                "seniority": "Individual",
                "department": "General",
                "source": "website",
                "confidence_score": 0.5,
            })
    result["contacts"] = contacts[:20]
    _log(f"✅ Found {len(result['contacts'])} contacts")

    # ── 9. Final cleanup ──────────────────────────────────────────────────────
    _log("✅ Research complete")
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────


def _merge(target: dict, source: dict) -> None:
    """Merge source into target, not overwriting existing non-empty values."""
    for k, v in source.items():
        if v and not target.get(k):
            target[k] = v


def _extract_industry(results: list[dict]) -> str:
    """Heuristically extract industry from search result snippets."""
    industry_keywords = [
        "pharmaceuticals", "manufacturing", "automotive", "technology",
        "chemicals", "food & beverage", "consumer goods", "energy",
        "aerospace", "defense", "healthcare", "semiconductors",
        "logistics", "construction", "mining", "retail",
    ]
    combined = " ".join(r.get("body", "") + r.get("title", "") for r in results).lower()
    for ind in industry_keywords:
        if ind.replace("&", "and") in combined or ind in combined:
            return ind.title()
    return ""


def _extract_subsidiaries(results: list[dict], parent_name: str) -> list[dict]:
    """Parse subsidiary/brand names from search results."""
    import re

    subsidiaries: list[dict] = []
    seen: set[str] = set()

    combined = " ".join(r.get("body", "") + r.get("title", "") for r in results)
    # Look for patterns like "X, Y and Z are subsidiaries of CompanyName"
    matches = re.findall(
        r"([A-Z][A-Za-z0-9\s&\-]+?)(?:\s*,\s*|\s+and\s+|\s*\|\s*)(?=[A-Z]|are|is\s+a\s+subsidiary)",
        combined,
    )
    for m in matches:
        name = m.strip().rstrip(",").strip()
        if (
            3 < len(name) < 60
            and name not in seen
            and name.lower() != parent_name.lower()
            and not any(skip in name.lower() for skip in ("the", "and", "for", "that", "which"))
        ):
            seen.add(name)
            subsidiaries.append({
                "name": name,
                "relationship_type": "subsidiary",
            })

    return subsidiaries[:10]


def _deduplicate_sites(sites: list[dict]) -> list[dict]:
    """Remove duplicate sites based on city+country combination."""
    seen: set[str] = set()
    unique: list[dict] = []
    for site in sites:
        city = site.get("city", "").lower().strip()
        country = site.get("country", "").lower().strip()
        key = f"{city}_{country}"
        if key and key not in seen:
            seen.add(key)
            unique.append(site)
        elif not key:
            unique.append(site)  # Keep sites without location data (from website scraping)
    return unique
