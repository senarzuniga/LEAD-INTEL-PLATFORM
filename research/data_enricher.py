"""Enrichment from Wikipedia and yfinance for company data."""

from __future__ import annotations

import re
from typing import Optional

from config import logger


def get_wikipedia_summary(company_name: str) -> dict:
    """
    Fetch Wikipedia summary for a company.
    Returns dict with: summary, url, categories, employees, revenue, founded
    """
    try:
        import wikipediaapi

        wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="LeadIntelPlatform/1.0 (https://github.com/lead-intel)",
        )
        page = wiki.page(company_name)
        if not page.exists():
            # Try with "company" appended
            page = wiki.page(f"{company_name} (company)")
        if not page.exists():
            return {}

        summary = page.summary[:800] if page.summary else ""
        data: dict = {
            "summary": summary,
            "url": page.fullurl,
            "categories": [c for c in list(page.categories.keys())[:10]],
        }

        # Extract structured data from infobox text using regex patterns
        text = page.text
        if founded := re.search(r"[Ff]ounded\s*[:\s]+(\d{4})", text):
            data["founded_year"] = int(founded.group(1))
        if employees := re.search(
            r"[Ee]mployees?\s*[:\s]+([0-9,]+)", text
        ):
            try:
                data["employee_count"] = int(employees.group(1).replace(",", ""))
            except ValueError:
                pass

        return data
    except Exception as exc:
        logger.debug("Wikipedia lookup failed for %r: %s", company_name, exc)
        return {}


def get_yfinance_data(ticker: str) -> dict:
    """
    Fetch company info from Yahoo Finance via yfinance.
    Returns dict with financial and corporate data.
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            if not info.get("longName"):
                return {}

        return {
            "name": info.get("longName", ""),
            "domain": info.get("website", "").replace("https://", "").replace("http://", "").rstrip("/"),
            "description": info.get("longBusinessSummary", "")[:800],
            "industry": info.get("industry", ""),
            "sector": info.get("sector", ""),
            "employee_count": info.get("fullTimeEmployees"),
            "headquarters_city": info.get("city", ""),
            "headquarters_country": info.get("country", ""),
            "annual_revenue": _format_number(info.get("totalRevenue")),
            "stock_ticker": ticker.upper(),
            "market_cap": _format_number(info.get("marketCap")),
        }
    except Exception as exc:
        logger.debug("yfinance lookup failed for %r: %s", ticker, exc)
        return {}


def guess_ticker(company_name: str) -> Optional[str]:
    """
    Try to guess a stock ticker from a company name using a DDG search.
    Returns None if not found.
    """
    from research.search_engine import search_web

    results = search_web(f"{company_name} stock ticker symbol NYSE NASDAQ", max_results=5, sleep=0.3)
    for r in results:
        body = r.get("body", "") + r.get("title", "")
        # Look for ticker pattern like (AAPL) or NYSE: AAPL or TICKER: AAPL
        matches = re.findall(r"\b([A-Z]{2,5})\b", body)
        # Filter out common false positives
        skip = {"THE", "AND", "FOR", "INC", "LLC", "LTD", "CORP", "CO", "PLC", "NYSE", "NASDAQ", "SEC"}
        candidates = [m for m in matches if m not in skip and 2 <= len(m) <= 5]
        if candidates:
            return candidates[0]
    return None


def _format_number(n: Optional[int]) -> str:
    if n is None:
        return ""
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    return f"${n:,}"
