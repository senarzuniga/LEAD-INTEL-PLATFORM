"""Lead qualification scoring engine."""

from __future__ import annotations

from database.models import Company


# Scoring weights (must sum to 100)
SCORE_WEIGHTS = {
    "has_description": 5,
    "has_domain": 5,
    "has_industry": 10,
    "has_headquarters": 5,
    "has_employees": 10,
    "employee_count_large": 15,  # 1000+
    "has_plants": 20,
    "plant_count_high": 10,      # 5+ plants
    "has_contacts": 10,
    "contact_clevel": 10,
}

TIER_THRESHOLDS = {
    "A": 75,
    "B": 50,
    "C": 25,
    "D": 0,
}


def score_company(company: Company) -> tuple[float, str]:
    """
    Calculate a qualification score (0–100) and tier (A/B/C/D) for a company.
    Returns (score, tier).
    """
    score = 0.0

    if company.description and len(company.description) > 50:
        score += SCORE_WEIGHTS["has_description"]
    if company.domain:
        score += SCORE_WEIGHTS["has_domain"]
    if company.industry:
        score += SCORE_WEIGHTS["has_industry"]
    if company.headquarters_city or company.headquarters_country:
        score += SCORE_WEIGHTS["has_headquarters"]
    if company.employee_count:
        score += SCORE_WEIGHTS["has_employees"]
        if company.employee_count >= 1000:
            score += SCORE_WEIGHTS["employee_count_large"]

    plant_count = len(company.plants) if company.plants else 0
    if plant_count > 0:
        score += SCORE_WEIGHTS["has_plants"]
    if plant_count >= 5:
        score += SCORE_WEIGHTS["plant_count_high"]

    contact_count = len(company.contacts) if company.contacts else 0
    if contact_count > 0:
        score += SCORE_WEIGHTS["has_contacts"]
    has_clevel = any(
        c.seniority == "C-level" for c in (company.contacts or [])
    )
    if has_clevel:
        score += SCORE_WEIGHTS["contact_clevel"]

    score = min(round(score, 1), 100.0)

    tier = "D"
    for t, threshold in TIER_THRESHOLDS.items():
        if score >= threshold:
            tier = t
            break

    return score, tier
