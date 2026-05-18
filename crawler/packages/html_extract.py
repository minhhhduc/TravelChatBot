from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup


_IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp)(?:$|[?#])", re.IGNORECASE)

_NOISE_SELECTORS = [
    ".post-rating-wrap",
    ".post-ratings",
    ".related-posts",
    ".jp-relatedposts",
    ".entry-nav",
    ".entry-footer",
    ".sharedaddy",
    ".addtoany_share_save_container",
    ".top-sns-wrap",
    ".ltt-contentbox",
    "form",
]

_STOP_LINE_RE = re.compile(
    r"^(theo\s+ivivu\.com|xem\s+thêm\s+bài\s+viết\s*:|click\s+đặt\s+ngay|đánh\s+giá\s+bài\s+viết\s+này|loading\.{3,}|tham\s+khảo\s*:|\*\*\*)$",
    re.IGNORECASE,
)

_DROP_LINE_RE = re.compile(
    r"^(\|+|\s*\|\s*|\d+\s*views?|\.+|[-–—•]+)$",
    re.IGNORECASE,
)

_CTA_LINE_RE = re.compile(
    r"^(tại\s+đây[.!]?$|ivivu\.com$|đặt\s+(ngay|vé|phòng|combo|tour)\b.*|tham\s+khảo\s+(ngay\s+)?(bảng\s+giá|giá\s+vé|giá)\b.*)$",
    re.IGNORECASE,
)

_NOISE_IMAGE_RE = re.compile(
    r"/wp-postratings/images/|/wp-includes/images/|rating_(on|off|half)\.gif$|/loading\.gif$",
    re.IGNORECASE,
)


def extract_main_content_element(soup: BeautifulSoup):
    # iVIVU blog posts are WordPress; main content is typically here.
    main = soup.select_one("div.entry-content")
    if main is not None:
        return main

    article = soup.find("article")
    if article is not None:
        return article

    body = soup.body
    return body if body is not None else soup


def extract_canonical_url(article_html: str) -> Optional[str]:
    soup = BeautifulSoup(article_html, "lxml")

    og = soup.find("meta", attrs={"property": "og:url"})
    if og and og.get("content"):
        url = str(og.get("content")).strip()
        return url or None

    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        url = str(canonical.get("href")).strip()
        return url or None

    return None


def _prune_content_text(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines()]
    cleaned: list[str] = []
    prev_blank = False

    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
            continue

        prev_blank = False

        if _DROP_LINE_RE.match(line):
            continue

        if _CTA_LINE_RE.match(line):
            continue

        if _STOP_LINE_RE.match(line):
            break

        cleaned.append(line)

    # Trim leading/trailing blank lines
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned).strip()


def extract_content_text(article_html: str) -> str:
    soup = BeautifulSoup(article_html, "lxml")
    main = extract_main_content_element(soup)

    # Remove noisy elements.
    for tag in main.find_all(["script", "style", "noscript"]):
        tag.decompose()

    for sel in _NOISE_SELECTORS:
        for tag in main.select(sel):
            tag.decompose()

    text = main.get_text("\n", strip=True)
    return _prune_content_text(text)


def _clean_main_for_extraction(main) -> None:
    # Remove noisy elements.
    for tag in main.find_all(["script", "style", "noscript"]):
        tag.decompose()

    for sel in _NOISE_SELECTORS:
        for tag in main.select(sel):
            tag.decompose()


def _img_local_path(img, base_url: str, url_to_local_path: dict[str, str]) -> Optional[str]:
    candidates: list[str] = []

    parent = img.parent
    if parent and getattr(parent, "name", None) == "a":
        href = parent.get("href")
        if isinstance(href, str) and href.strip() and _IMAGE_EXT_RE.search(href):
            candidates.append(urljoin(base_url, href.strip()))

    src = img.get("data-src") or img.get("src")
    if isinstance(src, str) and src.strip():
        candidates.append(urljoin(base_url, src.strip()))

    for u in candidates:
        local = url_to_local_path.get(u)
        if local:
            return local

        # Try matching without query/fragment when the downloader stored a canonical form.
        local = url_to_local_path.get(u.split("#", 1)[0].split("?", 1)[0])
        if local:
            return local

    return None


def extract_keypoint_sections(
    article_html: str,
    *,
    base_url: str,
    url_to_local_path: dict[str, str],
) -> list[dict]:
    """Extract sections (title/context) from an article.

    Sections are split by headings (h2/h3). Image placeholders are injected as
    `[img] <local_path> [img]` using the provided URL→local_path mapping.
    """

    soup = BeautifulSoup(article_html, "lxml")
    main = extract_main_content_element(soup)
    _clean_main_for_extraction(main)

    nodes = main.find_all(["h2", "h3", "p", "ul", "ol", "img", "figure"], recursive=True)

    sections: list[dict] = []
    current_title = "Mở đầu"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        raw = "\n".join(current_lines).strip()
        context = _prune_content_text(raw) if raw else ""
        if context:
            sections.append({"title": current_title, "context": context})
        current_lines = []

    for node in nodes:
        name = getattr(node, "name", None)
        if name in {"h2", "h3"}:
            flush()
            title = node.get_text(" ", strip=True)
            if title:
                current_title = title
            continue

        if name == "p":
            text = node.get_text(" ", strip=True)
            if text:
                current_lines.append(text)
            continue

        if name in {"ul", "ol"}:
            for li in node.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)
                if text:
                    current_lines.append(f"- {text}")
            continue

        if name == "figure":
            img = node.find("img")
            if img is None:
                continue
            local = _img_local_path(img, base_url, url_to_local_path)
            if local:
                current_lines.append(f"[img] {local} [img]")
            continue

        if name == "img":
            local = _img_local_path(node, base_url, url_to_local_path)
            if local:
                current_lines.append(f"[img] {local} [img]")
            continue

    flush()
    return sections


def extract_title(article_html: str) -> Optional[str]:
    soup = BeautifulSoup(article_html, "lxml")
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return str(og.get("content")).strip() or None
    if soup.title and soup.title.string:
        return str(soup.title.string).strip() or None
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(" ", strip=True)
        return text or None
    return None


def extract_published_date(article_html: str) -> Optional[str]:
    """Return ISO date YYYY-MM-DD if discoverable."""
    soup = BeautifulSoup(article_html, "lxml")

    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if meta and meta.get("content"):
        content = str(meta.get("content")).strip()
        try:
            dt = datetime.fromisoformat(content.replace("Z", "+00:00"))
            return dt.date().isoformat()
        except ValueError:
            pass

    header = soup.select_one("header.entry-header")
    haystack = header.get_text(" ", strip=True) if header else soup.get_text(" ", strip=True)
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", haystack)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        try:
            return datetime(int(yyyy), int(mm), int(dd)).date().isoformat()
        except ValueError:
            pass

    return None


def extract_image_urls(article_html: str, base_url: str) -> list[dict]:
    """Return a list of image candidates found in the main content.

    Each item: {"url": abs_url, "alt": str|None}
    """
    soup = BeautifulSoup(article_html, "lxml")
    main = extract_main_content_element(soup)

    items: list[dict] = []
    seen: set[str] = set()

    for img in main.find_all("img"):
        src = img.get("data-src") or img.get("src")
        parent = img.parent
        if parent and getattr(parent, "name", None) == "a":
            href = parent.get("href")
            if isinstance(href, str) and _IMAGE_EXT_RE.search(href):
                src = href

        if not isinstance(src, str) or not src.strip():
            continue

        abs_url = urljoin(base_url, src.strip())
        if _NOISE_IMAGE_RE.search(abs_url):
            continue
        if abs_url in seen:
            continue

        seen.add(abs_url)
        alt = img.get("alt")
        items.append({"url": abs_url, "alt": str(alt).strip() if isinstance(alt, str) and alt.strip() else None})

    return items
