"""DuckDuckGo-powered search helper with retry / rate-limit handling."""

from __future__ import annotations

import time
from typing import Optional

from ddgs import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

from config import MAX_SEARCH_RESULTS, REQUEST_DELAY, logger


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _ddg_search(query: str, max_results: int) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


def search_web(
    query: str,
    max_results: int = MAX_SEARCH_RESULTS,
    sleep: float = REQUEST_DELAY,
) -> list[dict]:
    """
    Run a DuckDuckGo web search and return a list of result dicts.

    Each dict has: title, href, body
    Returns an empty list on failure.
    """
    try:
        results = _ddg_search(query, max_results)
        time.sleep(sleep)
        return results or []
    except Exception as exc:
        logger.warning("DDG search failed for %r: %s", query, exc)
        return []


def search_news(
    query: str,
    max_results: int = 5,
    sleep: float = REQUEST_DELAY,
) -> list[dict]:
    """
    DuckDuckGo news search.

    Each dict has: date, title, body, url, image, source
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        time.sleep(sleep)
        return results or []
    except Exception as exc:
        logger.warning("DDG news search failed for %r: %s", query, exc)
        return []


def find_domain(company_name: str) -> Optional[str]:
    """Best-effort attempt to find the official website domain of a company."""
    from urllib.parse import urlparse

    _SKIP_DOMAINS = {
        "wikipedia.org", "linkedin.com", "facebook.com", "twitter.com",
        "bloomberg.com", "crunchbase.com", "glassdoor.com", "indeed.com",
        "reuters.com", "youtube.com", "x.com",
    }

    def _is_skip(netloc: str) -> bool:
        host = netloc.lower().lstrip("www.")
        return any(host == s or host.endswith("." + s) for s in _SKIP_DOMAINS)

    results = search_web(f"{company_name} official website", max_results=5, sleep=0.5)
    for r in results:
        href = r.get("href", "")
        parsed = urlparse(href)
        if not parsed.netloc:
            continue
        if _is_skip(parsed.netloc):
            continue
        domain = parsed.netloc.lstrip("www.")
        # Sanity check: domain must contain part of company name
        name_parts = company_name.lower().split()
        if any(part in domain.lower() for part in name_parts if len(part) > 3):
            return domain
    # Fallback: return first non-skip domain
    for r in results:
        href = r.get("href", "")
        parsed = urlparse(href)
        if parsed.netloc and not _is_skip(parsed.netloc):
            return parsed.netloc.lstrip("www.")
    return None
