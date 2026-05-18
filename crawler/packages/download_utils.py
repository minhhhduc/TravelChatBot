from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from .url_utils import short_hash


_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _guess_ext(*, url: str, content_type: Optional[str]) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix
    if suffix and 1 <= len(suffix) <= 5:
        return suffix

    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in _CONTENT_TYPE_EXT:
            return _CONTENT_TYPE_EXT[ct]
        guessed = mimetypes.guess_extension(ct)
        if guessed:
            return guessed

    return ".bin"


def download_image(
    *,
    session: requests.Session,
    url: str,
    out_dir: Path,
    idx: int,
    timeout_seconds: float,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_url = requests.utils.requote_uri(url)
    try:
        resp = session.get(safe_url, timeout=timeout_seconds)
        resp_status = resp.status_code
        content_type = resp.headers.get("Content-Type")
        content_bytes = resp.content
    except Exception as e:
        print(f"    [warn] Failed to download image {url}: {e}", flush=True)
        return {
            "url": url,
            "http_status": 0,
            "content_type": None,
            "local_path": None,
            "bytes": 0,
        }

    ext = _guess_ext(url=url, content_type=content_type)

    filename = f"{idx:03d}_{short_hash(url)}{ext}"
    out_path = out_dir / filename

    if resp_status < 400:
        out_path.write_bytes(content_bytes)

    return {
        "url": url,
        "http_status": resp_status,
        "content_type": content_type,
        "local_path": str(out_path.as_posix()) if resp_status < 400 else None,
        "bytes": len(content_bytes) if resp_status < 400 else 0,
    }
