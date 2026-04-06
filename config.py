"""Central configuration for Lead Intelligence Platform."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env file if present ─────────────────────────────────────────────────
load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'lead_intel.db'}")

# ── Optional API keys ─────────────────────────────────────────────────────────
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
HUNTER_API_KEY: str | None = os.getenv("HUNTER_API_KEY")
CLEARBIT_API_KEY: str | None = os.getenv("CLEARBIT_API_KEY")

# ── Research settings ─────────────────────────────────────────────────────────
REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.5"))
REQUEST_TIMEOUT: int = 10
MAX_SEARCH_RESULTS: int = 10

# HTTP headers for web requests
REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("lead_intel")
