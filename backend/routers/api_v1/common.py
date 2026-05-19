"""Shared helpers for Lumi Travel AI API v1 routers."""
from __future__ import annotations

import json
import shutil
import uuid
import wave
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from fastapi import UploadFile

from ai_module.models import config

UPLOAD_ROOT = config.BASE_DIR / "data" / "uploads"
IMAGE_UPLOAD_DIR = UPLOAD_ROOT / "images"
AUDIO_UPLOAD_DIR = UPLOAD_ROOT / "audio"
IMAGE_MANIFEST_PATH = config.BASE_DIR / "data" / "metadata" / "images.json"

for directory in (IMAGE_UPLOAD_DIR, AUDIO_UPLOAD_DIR, IMAGE_MANIFEST_PATH.parent):
    directory.mkdir(parents=True, exist_ok=True)


def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_metadata() -> Dict[str, Any]:
    path = config.BASE_DIR / "data" / "features" / "metadata.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_image_manifest() -> List[Dict[str, Any]]:
    if not IMAGE_MANIFEST_PATH.exists():
        return []
    with IMAGE_MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_image_manifest(items: List[Dict[str, Any]]) -> None:
    with IMAGE_MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def save_upload(upload: UploadFile, directory: Path) -> Path:
    suffix = Path(upload.filename or "").suffix or ".bin"
    target = directory / f"{uuid.uuid4()}{suffix}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return target


def sources_from_rag(rag_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources = []
    for index, source in enumerate(rag_context.get("sources", []), start=1):
        metadata = source.get("metadata", {}) or {}
        sources.append(
            {
                "id": metadata.get("keypoint_title") or metadata.get("article_title") or f"source-{index}",
                "title": metadata.get("keypoint_title") or metadata.get("article_title") or "Travel guide",
                "url": source.get("url") or metadata.get("url") or "",
                "relevance_score": source.get("relevance_score", 0.0),
                "metadata": metadata,
            }
        )
    return sources


def silent_wav_response() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 1600)
    return buffer.getvalue()
