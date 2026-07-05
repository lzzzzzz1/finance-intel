from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from html.parser import HTMLParser


TICKER_PATTERNS = [
    re.compile(r"\b(?:SH|SZ|BJ)?[0-9]{6}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{1,5}\b"),
]

BLOCK_TAGS = {"article", "main", "section", "p", "li", "h1", "h2", "h3", "td", "div"}
SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "nav", "footer", "header", "form", "button", "select"}
BOILERPLATE_TERMS = [
    "版权所有",
    "网站地图",
    "联系我们",
    "隐私",
    "copyright",
    "cookie",
    "登录",
    "注册",
    "分享到",
]


class ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._stack: list[str] = []
        self._skip_depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        if tag in BLOCK_TAGS:
            self._flush()
            self._stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in BLOCK_TAGS:
            self._flush()
            if self._stack:
                self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = normalize_space(data)
        if text:
            self._buffer.append(text)

    def _flush(self) -> None:
        if not self._buffer:
            return
        text = normalize_space(" ".join(self._buffer))
        self._buffer = []
        if is_content_block(text):
            self.blocks.append(text)

    def close(self) -> None:
        super().close()
        self._flush()


def clean_html(raw: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_space(text)


def is_content_block(text: str) -> bool:
    if len(text) < 24:
        return False
    lower = text.lower()
    if any(term in lower for term in BOILERPLATE_TERMS):
        return False
    punctuation = len(re.findall(r"[，。；：、,.%;:]", text))
    digit_or_cjk = len(re.findall(r"[\u4e00-\u9fff0-9]", text))
    return punctuation >= 1 and digit_or_cjk >= 12


def readable_html_text(raw: str) -> str:
    parser = ReadableHTMLParser()
    try:
        parser.feed(raw or "")
        parser.close()
    except Exception:
        return clean_html(raw)

    seen: set[str] = set()
    blocks: list[str] = []
    for block in parser.blocks:
        key = block[:120]
        if key in seen:
            continue
        seen.add(key)
        blocks.append(block)

    text = "\n".join(blocks)
    if len(text) < 120 and len(blocks) < 2:
        return clean_html(raw)
    return text


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
    haystack = text or ""
    haystack_lower = haystack.lower()
    matched: list[str] = []
    for theme in themes:
        keywords = theme.get("keywords", [])
        if any(keyword_matches(haystack, haystack_lower, str(keyword)) for keyword in keywords):
            matched.append(theme["name"])
    return matched


def keyword_matches(text: str, text_lower: str, keyword: str) -> bool:
    keyword = keyword.strip()
    if not keyword:
        return False
    if keyword.isascii() and len(keyword) <= 3:
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None
    return keyword.lower() in text_lower


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
