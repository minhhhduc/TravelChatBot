from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple


def strip_json_breaking_controls(s: str) -> str:
    """Remove control chars that commonly break JSON parsing.

    JSON strings cannot contain ASCII control chars (0x00..0x1F) unescaped.
    Real-world crawls sometimes contain them.
    """
    return "".join(
        ch
        for ch in s
        if ch in ("\t", "\n", "\r")
        or ord(ch) >= 0x20
    )


def safe_json_loads(line: str) -> Optional[Dict[str, Any]]:
    """Parse a JSONL line robustly.

    Returns None if the line cannot be parsed even after simple repairs.
    """
    raw = line.strip()
    if not raw:
        return None

    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    repaired = strip_json_breaking_controls(raw)
    if repaired != raw:
        try:
            obj = json.loads(repaired)
            return obj if isinstance(obj, dict) else None
        except Exception:
            pass

    start = repaired.find("{")
    end = repaired.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = repaired[start : end + 1]
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    return None


def iter_jsonl(path: Path, encoding: str = "utf-8") -> Iterator[Tuple[int, Dict[str, Any]]]:
    """Yield (line_no, obj) from a JSONL file."""
    with path.open("r", encoding=encoding, errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            obj = safe_json_loads(line)
            if obj is None:
                yield line_no, {"__parse_error__": True, "__raw__": line}
            else:
                yield line_no, obj
