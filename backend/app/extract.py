from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone


TICKER_PATTERNS = [
    re.compile(r"\b(?:SH|SZ|BJ)?[0-9]{6}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{1,5}\b"),
]


def clean_html(raw: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_space(text)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def raw_hash(source_id: str, title: str, body: str, url: str) -> str:
    payload = f"{source_id}\n{title}\n{url}\n{body[:2000]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


def extract_tickers(text: str) -> list[str]:
    matches: set[str] = set()
    for pattern in TICKER_PATTERNS:
        for match in pattern.findall(text or ""):
            token = match.upper()
            if token in {"AI", "GDP", "CPI", "ETF", "IPO", "SEC", "ECB", "IMF"}:
                continue
            matches.add(token)
    return sorted(matches)[:12]


def match_themes(text: str, themes: list[dict]) -> list[str]:
    haystack = (text or "").lower()
    matched: list[str] = []
    for theme in themes:
        keywords = theme.get("keywords", [])
        if any(str(keyword).lower() in haystack for keyword in keywords):
            matched.append(theme["name"])
    return matched


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
