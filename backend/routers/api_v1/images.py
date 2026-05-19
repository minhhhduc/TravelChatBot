"""API v1 image analysis and CMS image endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.auth_utils import get_current_user
from backend.models import User
from backend.routers.chat import get_chatbot
from .common import IMAGE_UPLOAD_DIR, load_image_manifest, save_image_manifest, save_upload

router = APIRouter(prefix="/images", tags=["API v1 - Images"])


@router.post("/analyze")
def images_analyze(image: UploadFile = File(...)):
    path = save_upload(image, IMAGE_UPLOAD_DIR)
    description = get_chatbot().vision_agent.describe_image(str(path))
    answer = get_chatbot().get_response(user_query=description or "Phân tích ảnh du lịch", image_path=str(path))
    return {"image_path": str(path), "description": description, "suggestion": answer}


@router.post("/upload")
def images_upload(
    image: UploadFile = File(...),
    destination: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    path = save_upload(image, IMAGE_UPLOAD_DIR)
    items = load_image_manifest()
    item = {
        "id": str(uuid.uuid4()),
        "filename": image.filename,
        "path": str(path),
        "destination": destination,
        "category": category,
        "uploaded_by": current_user.username,
        "created_at": datetime.utcnow().isoformat(),
    }
    items.append(item)
    save_image_manifest(items)
    return item


@router.get("")
def images_list(
    destination: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    items = load_image_manifest()
    if destination:
        items = [item for item in items if item.get("destination") == destination]
    if category:
        items = [item for item in items if item.get("category") == category]
    return {"items": items, "total": len(items)}


@router.delete("/{image_id}")
def images_delete(image_id: str, current_user: User = Depends(get_current_user)):
    items = load_image_manifest()
    kept = []
    deleted = None
    for item in items:
        if item.get("id") == image_id:
            deleted = item
        else:
            kept.append(item)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")
    image_path = Path(deleted.get("path", ""))
    if image_path.exists() and image_path.is_file():
        image_path.unlink()
    save_image_manifest(kept)
    return {"deleted": True, "id": image_id}
