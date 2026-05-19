from __future__ import annotations

import re

from .text_cleaning import simplify_title


def infer_destination_from_title(title: str) -> str:
    """Heuristic destination inference from Vietnamese article titles."""
    t = simplify_title(title)
    if not t:
        return ""

    m = re.search(r"(?i)^\s*du\s*l\u1ecbch\s+([^:–\-]+)", t)
    if m:
        cand = m.group(1).strip()
        if re.search(r"(?i)ivivu\.com|\bwww\b|\.(com|vn|net)\b", cand):
            return ""
        return cand

    matches = list(re.finditer(r"(?i)du\s*l\u1ecbch\s+([^:–\-]+)", t))
    if matches:
        cand = matches[-1].group(1).strip()
        if re.search(r"(?i)ivivu\.com|\bwww\b|\.(com|vn|net)\b", cand):
            return ""
        return cand

    for sep in (":", " - ", " -", "- "):
        if sep in t:
            head = t.split(sep, 1)[0].strip()
            if head:
                if re.search(r"(?i)ivivu\.com|\bwww\b|\.(com|vn|net)\b", head):
                    return ""
                return head

    return ""
