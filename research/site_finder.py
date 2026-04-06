"""Discover production sites, plants, and offices from public data."""

from __future__ import annotations

import re
from typing import Optional

from config import logger
from research.search_engine import search_web, search_news

# Keywords that suggest a physical production/facility site
SITE_KEYWORDS = [
    "plant", "factory", "manufacturing", "facility", "warehouse",
    "distribution center", "production site", "assembly", "refinery",
    "mill", "foundry", "forge", "hub", "campus", "site",
]

# Country name → ISO code (partial list for geo display)
COUNTRY_CODES: dict[str, str] = {
    "united states": "US", "usa": "US", "us": "US",
    "united kingdom": "GB", "uk": "GB",
    "germany": "DE", "france": "FR", "china": "CN",
    "india": "IN", "japan": "JP", "canada": "CA",
    "australia": "AU", "brazil": "BR", "mexico": "MX",
    "italy": "IT", "spain": "ES", "netherlands": "NL",
    "south korea": "KR", "singapore": "SG",
    "sweden": "SE", "switzerland": "CH",
}


def find_sites_from_search(company_name: str) -> list[dict]:
    """
    Use web search to discover facility/plant locations for a company.
    Returns list of dicts: name, city, state, country, site_type, source_url.
    """
    sites: list[dict] = []

    queries = [
        f"{company_name} manufacturing plants locations worldwide",
        f"{company_name} production facilities sites",
        f"{company_name} factory warehouse locations",
        f"{company_name} global operations facilities",
    ]

    seen: set[str] = set()
    for query in queries[:2]:
        results = search_web(query, max_results=8, sleep=0.5)
        for r in results:
            text = (r.get("body", "") + " " + r.get("title", "")).lower()
            url = r.get("href", "")
            extracted = _extract_sites_from_text(text, company_name, url)
            for site in extracted:
                key = f"{site.get('city','').lower()}_{site.get('country','').lower()}"
                if key and key not in seen:
                    seen.add(key)
                    sites.append(site)
        if len(sites) >= 5:
            break

    return sites[:20]


def find_sites_from_news(company_name: str) -> list[dict]:
    """Search news for mentions of new plants, expansions, or closures."""
    sites: list[dict] = []
    queries = [
        f"{company_name} new plant opening",
        f"{company_name} factory expansion",
        f"{company_name} facility investment",
    ]
    seen: set[str] = set()
    for query in queries[:2]:
        results = search_news(query, max_results=5)
        for r in results:
            text = (r.get("body", "") + " " + r.get("title", "")).lower()
            url = r.get("url", "")
            extracted = _extract_sites_from_text(text, company_name, url)
            for site in extracted:
                key = f"{site.get('city','').lower()}_{site.get('country','').lower()}"
                if key and key not in seen:
                    seen.add(key)
                    site["status"] = _detect_status(text)
                    sites.append(site)
    return sites[:10]


def find_job_posting_locations(company_name: str) -> list[dict]:
    """
    Mine job posting searches to find cities where the company is active.
    Returns list of dicts: city, country, site_type, source_url.
    """
    sites: list[dict] = []
    queries = [
        f"site:jobs.lever.co OR site:greenhouse.io OR site:workday.com \"{company_name}\" manufacturing",
        f"\"{company_name}\" jobs manufacturing engineer location",
    ]
    seen: set[str] = set()
    for query in queries[:1]:
        results = search_web(query, max_results=10, sleep=0.5)
        for r in results:
            text = (r.get("body", "") + " " + r.get("title", "")).lower()
            url = r.get("href", "")
            extracted = _extract_sites_from_text(text, company_name, url)
            for site in extracted:
                key = f"{site.get('city','').lower()}_{site.get('country','').lower()}"
                if key and key not in seen:
                    seen.add(key)
                    site["site_type"] = "office"
                    sites.append(site)
    return sites[:5]


def _extract_sites_from_text(text: str, company_name: str, source_url: str) -> list[dict]:
    """Parse raw text for city/country mentions near site keywords."""
    sites: list[dict] = []
    # Tokenize into sentences
    sentences = re.split(r"[.\n!?;]", text)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15:
            continue
        # Check if sentence contains a site keyword
        has_keyword = any(kw in sentence for kw in SITE_KEYWORDS)
        if not has_keyword:
            continue
        site = _parse_location_from_sentence(sentence, source_url)
        if site:
            sites.append(site)
    return sites


_CITY_PATTERN = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
_STATE_PATTERN = re.compile(r"\b([A-Z]{2})\b")


def _parse_location_from_sentence(sentence: str, source_url: str) -> Optional[dict]:
    """Extract location info from a sentence containing a site keyword."""
    # Common US cities and countries heuristic
    # Detect country
    country = ""
    country_code = ""
    for name, code in COUNTRY_CODES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", sentence, re.I):
            country = name.title()
            country_code = code
            break

    # Detect US state abbreviations
    state = ""
    us_state = _STATE_PATTERN.search(sentence)
    if us_state and not country:
        country = "United States"
        country_code = "US"
        state = us_state.group(1)

    # Detect city (capitalised word before state/country)
    city = ""
    city_match = _CITY_PATTERN.search(sentence)
    if city_match:
        candidate = city_match.group(1)
        # Skip company-like words
        if len(candidate) > 2 and candidate.lower() not in (
            "the", "and", "for", "inc", "llc", "new", "plant", "factory"
        ):
            city = candidate

    if not city and not country:
        return None

    # Detect site type
    site_type = "facility"
    for kw in SITE_KEYWORDS:
        if kw in sentence:
            site_type = kw
            break

    return {
        "name": f"{city} {site_type.capitalize()}".strip() if city else f"{country} {site_type.capitalize()}",
        "city": city,
        "state": state,
        "country": country,
        "country_code": country_code,
        "site_type": site_type,
        "source_url": source_url,
        "status": "active",
    }


def _detect_status(text: str) -> str:
    if any(w in text for w in ("closed", "shutdown", "closing", "shutting")):
        return "closed"
    if any(w in text for w in ("planned", "announced", "upcoming", "will open")):
        return "planned"
    return "active"
