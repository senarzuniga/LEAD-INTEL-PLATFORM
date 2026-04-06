"""HTML scraping utilities for company websites."""

from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import REQUEST_DELAY, REQUEST_HEADERS, REQUEST_TIMEOUT, logger


def _get(url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY * 0.5)
        return BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
        return None


def _text(soup: BeautifulSoup) -> str:
    """Extract cleaned text from a BeautifulSoup object."""
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def scrape_homepage(domain: str) -> dict:
    """
    Scrape a company homepage and return a dict with:
    description, emails, phones, social_links, title
    """
    url = f"https://{domain}"
    soup = _get(url)
    if soup is None:
        url = f"http://{domain}"
        soup = _get(url)
    if soup is None:
        return {}

    text = _text(soup)
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    meta_desc = ""
    for tag in soup.find_all("meta"):
        if tag.get("name", "").lower() in ("description", "og:description"):
            meta_desc = tag.get("content", "")
            break

    emails = list(set(re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)))
    emails = [e for e in emails if not e.endswith((".png", ".jpg", ".gif", ".svg"))]

    phones = list(set(re.findall(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text
    )))

    social_links: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        try:
            netloc = urlparse(href).netloc.lower().lstrip("www.")
        except Exception:
            continue
        if netloc == "linkedin.com" or netloc.endswith(".linkedin.com"):
            social_links.setdefault("linkedin", href)
        elif netloc in ("twitter.com", "x.com") or netloc.endswith((".twitter.com", ".x.com")):
            social_links.setdefault("twitter", href)
        elif netloc == "facebook.com" or netloc.endswith(".facebook.com"):
            social_links.setdefault("facebook", href)

    return {
        "title": title,
        "description": meta_desc or text[:300],
        "emails": emails[:5],
        "phones": phones[:3],
        "social_links": social_links,
    }


def scrape_about_page(domain: str) -> str:
    """Try common about-page URLs and return extracted text."""
    for path in ("/about", "/about-us", "/company", "/who-we-are", "/our-story"):
        url = f"https://{domain}{path}"
        soup = _get(url)
        if soup:
            text = _text(soup)
            if len(text) > 200:
                return text[:1000]
    return ""


def scrape_locations_page(domain: str) -> list[dict]:
    """
    Scrape a company's locations/offices page.
    Returns a list of dicts with: name, address, city, country, type.
    """
    locations: list[dict] = []
    for path in ("/locations", "/offices", "/global-offices", "/contact",
                 "/facilities", "/plants", "/sites", "/where-we-are"):
        url = f"https://{domain}{path}"
        soup = _get(url)
        if soup is None:
            continue
        text = _text(soup)
        if len(text) < 100:
            continue

        # Look for address-like blocks
        address_blocks = soup.find_all(
            ["address", "div"],
            class_=re.compile(r"(address|location|office|city|facility)", re.I),
        )
        for block in address_blocks[:20]:
            block_text = block.get_text(" ", strip=True)
            if len(block_text) < 10:
                continue
            locations.append({"raw_text": block_text[:300], "source_url": url})

        if locations:
            break
    return locations


def scrape_team_page(domain: str) -> list[dict]:
    """
    Try to scrape team/leadership pages and extract contact info.
    Returns list of dicts: name, title, email.
    """
    contacts: list[dict] = []
    for path in ("/team", "/leadership", "/management", "/our-team",
                 "/executive-team", "/people", "/about/team"):
        url = f"https://{domain}{path}"
        soup = _get(url)
        if soup is None:
            continue

        # Look for person-like cards
        cards = soup.find_all(
            ["div", "article", "li"],
            class_=re.compile(r"(person|member|team|bio|card|profile|executive)", re.I),
        )
        for card in cards[:30]:
            text = card.get_text(" ", strip=True)
            emails_in_card = re.findall(
                r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text
            )
            # Heuristic: if a card has 10-200 chars it's likely a person card
            if 10 < len(text) < 400:
                contacts.append({
                    "raw_text": text[:200],
                    "email": emails_in_card[0] if emails_in_card else None,
                    "source_url": url,
                })
        if contacts:
            break
    return contacts
