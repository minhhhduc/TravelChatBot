from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple


IMG_BLOCK_RE = re.compile(r"\[img\]\s*(.*?)\s*\[img\]", flags=re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"[\t\f\v\r ]+")
MANY_DOTS_RE = re.compile(r"\.{3,}")


def normalize_text(text: str) -> str:
    """Clean and normalize text while keeping Vietnamese characters."""
    if not isinstance(text, str):
        return ""

    s = unicodedata.normalize("NFC", text)
    s = HTML_TAG_RE.sub(" ", s)

    cleaned_chars: List[str] = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in {"Cc", "Cs"}:
            continue
        # Drop "other symbols" (emoji, pictographs) which add noise
        if cat == "So":
            continue
        cleaned_chars.append(ch)
    s = "".join(cleaned_chars)

    s = MANY_DOTS_RE.sub("...", s)
    s = s.replace("…", "...")
    s = s.replace("–", "-").replace("—", "-")

    # Normalize common list bullets
    s = s.replace("•", "-")

    s = s.replace("\u00a0", " ")
    s = WHITESPACE_RE.sub(" ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extract_images_and_strip(context: str) -> Tuple[List[str], str]:
    if not isinstance(context, str) or not context:
        return [], ""
    images = [m.group(1).strip() for m in IMG_BLOCK_RE.finditer(context) if m.group(1).strip()]
    stripped = IMG_BLOCK_RE.sub(" ", context)
    stripped = normalize_text(stripped)
    return images, stripped


def reattach_images(text_without_images: str, images: List[str]) -> str:
    """Attach images as canonical blocks at the end of the text."""
    base = normalize_text(text_without_images)
    if not images:
        return base
    img_blocks = "\n".join([f"[img] {p} [img]" for p in images if isinstance(p, str) and p.strip()])
    if not img_blocks:
        return base
    if not base:
        return img_blocks
    return base + "\n" + img_blocks


def simplify_title(title: str) -> str:
    if not isinstance(title, str):
        return ""
    s = title.strip()
    # Common suffix patterns from ivivu pages
    for suffix in (
        " - iVIVU.com",
        " | iVIVU.com",
        " – iVIVU.com",
        " — iVIVU.com",
        "- iVIVU.com",
        "| iVIVU.com",
    ):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    # Sometimes the title is just the domain
    if s.lower() in {"ivivu.com", "www.ivivu.com"}:
        s = ""
    return normalize_text(s)
