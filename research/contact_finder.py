"""Find professional contacts for a company via web research."""

from __future__ import annotations

import re
from typing import Optional

from config import HUNTER_API_KEY, logger
from research.search_engine import search_web


# Seniority levels in descending order of priority
SENIORITY_MAP: dict[str, str] = {
    "chief executive": "C-level",
    "ceo": "C-level",
    "coo": "C-level",
    "cfo": "C-level",
    "cto": "C-level",
    "cmo": "C-level",
    "chief": "C-level",
    "president": "C-level",
    "founder": "C-level",
    "owner": "C-level",
    "vice president": "VP",
    "vp ": "VP",
    "svp": "VP",
    "evp": "VP",
    "director": "Director",
    "head of": "Director",
    "manager": "Manager",
    "supervisor": "Manager",
    "engineer": "Individual",
    "analyst": "Individual",
    "specialist": "Individual",
    "coordinator": "Individual",
}

TARGET_DEPARTMENTS = [
    "operations", "manufacturing", "production", "supply chain",
    "procurement", "purchasing", "engineering", "plant", "facilities",
    "maintenance", "quality", "logistics", "sales", "business development",
]


def classify_seniority(title: str) -> str:
    lower = title.lower()
    for keyword, level in SENIORITY_MAP.items():
        if keyword in lower:
            return level
    return "Individual"


def classify_department(title: str) -> str:
    lower = title.lower()
    for dept in TARGET_DEPARTMENTS:
        if dept in lower:
            return dept.title()
    return "General"


def find_contacts_web(company_name: str, domain: Optional[str] = None) -> list[dict]:
    """
    Search the web for key contacts at a company.
    Returns list of dicts: full_name, title, email, seniority, department, source.
    """
    contacts: list[dict] = []
    seen_names: set[str] = set()

    queries = [
        f'"{company_name}" CEO OR "Chief Executive" OR President site:linkedin.com',
        f'"{company_name}" "VP" OR "Director" manufacturing OR operations',
        f'"{company_name}" leadership team management',
    ]

    for query in queries[:2]:
        results = search_web(query, max_results=8, sleep=0.5)
        for r in results:
            text = r.get("title", "") + " " + r.get("body", "")
            extracted = _extract_contacts_from_text(text, company_name, r.get("href", ""))
            for c in extracted:
                name = c.get("full_name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    contacts.append(c)

    # If Hunter.io API key is configured, use it
    if HUNTER_API_KEY and domain:
        hunter_contacts = _hunter_find(domain)
        for c in hunter_contacts:
            name = c.get("full_name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                contacts.append(c)

    return contacts[:15]


def _extract_contacts_from_text(text: str, company_name: str, source_url: str) -> list[dict]:
    """Parse contact info from raw text."""
    contacts = []
    # Pattern: "Name, Title at Company" or "Name | Title"
    patterns = [
        r"([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)[,\s\-–|]+([A-Z][^,.\n]{5,60})",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            name = m.group(1).strip()
            title = m.group(2).strip()
            # Filter out non-person matches
            if any(skip in name.lower() for skip in ("the ", "and ", "for ", "this ")):
                continue
            if len(name.split()) < 2 or len(name.split()) > 4:
                continue
            # Only keep if title mentions relevant roles
            if not any(kw in title.lower() for kw in list(SENIORITY_MAP.keys()) + TARGET_DEPARTMENTS):
                continue

            email = _guess_email(name, company_name)
            contacts.append({
                "full_name": name,
                "title": title[:100],
                "email": email,
                "seniority": classify_seniority(title),
                "department": classify_department(title),
                "source": "web_search",
                "source_url": source_url,
                "confidence_score": 0.4,
            })
    return contacts


def _guess_email(full_name: str, company_name: str) -> str:
    """Generate a guessed email address using common corporate patterns."""
    parts = full_name.lower().split()
    if len(parts) < 2:
        return ""
    first, last = parts[0], parts[-1]
    domain_guess = company_name.lower().replace(" ", "").replace(",", "")[:15] + ".com"
    return f"{first}.{last}@{domain_guess}"


def _hunter_find(domain: str) -> list[dict]:
    """Use Hunter.io domain search API."""
    import requests as req

    try:
        resp = req.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 10},
            timeout=10,
        )
        data = resp.json()
        contacts = []
        for email_data in data.get("data", {}).get("emails", []):
            name = f"{email_data.get('first_name','')} {email_data.get('last_name','')}".strip()
            if not name:
                continue
            contacts.append({
                "full_name": name,
                "title": email_data.get("position", ""),
                "email": email_data.get("value", ""),
                "seniority": classify_seniority(email_data.get("position", "")),
                "department": classify_department(email_data.get("position", "")),
                "linkedin_url": email_data.get("linkedin", ""),
                "source": "hunter.io",
                "confidence_score": email_data.get("confidence", 50) / 100,
            })
        return contacts
    except Exception as exc:
        logger.debug("Hunter.io failed for %r: %s", domain, exc)
        return []
