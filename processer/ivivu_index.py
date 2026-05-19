from __future__ import annotations

from pathlib import Path
from typing import Dict

from .jsonl_utils import safe_json_loads
from .text_cleaning import simplify_title


def load_ivivu_index_map(index_path: Path) -> Dict[str, Dict[str, str]]:
    """Load ivivu index.jsonl to enrich url/paths by title.

    Returns a map: simplified_title -> {"url": ..., "published_date": ..., "html": ..., "meta": ...}
    """
    if not index_path.exists():
        return {}
    out: Dict[str, Dict[str, str]] = {}
    with index_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            obj = safe_json_loads(line)
            if not obj:
                continue
            title = simplify_title(str(obj.get("title") or ""))
            if not title:
                continue
            if title in out:
                continue
            paths = obj.get("paths") or {}
            out[title] = {
                "url": str(obj.get("url") or ""),
                "published_date": str(obj.get("published_date") or ""),
                "html": str(paths.get("html") or ""),
                "meta": str(paths.get("meta") or ""),
            }
    return out
