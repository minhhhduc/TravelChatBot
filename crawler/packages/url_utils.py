from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import urlparse, urlunparse


def canonicalize_url(url: str) -> str:
    """Drop fragments and query params (utm, etc.) for stable dedupe."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def safe_slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else "item"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-")
    return slug or "item"


def ym_from_article_url(url: str) -> tuple[Optional[str], Optional[str]]:
    parts = urlparse(url).path.strip("/").split("/")
    # expected: blog/YYYY/MM/slug/
    if len(parts) >= 4 and parts[0] == "blog":
        year = parts[1]
        month = parts[2]
        if year.isdigit() and month.isdigit():
            return year, month
    return None, None


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
