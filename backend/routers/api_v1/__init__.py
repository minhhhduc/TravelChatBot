"""Aggregated Lumi Travel AI API v1 router."""
from fastapi import APIRouter

from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .destinations import router as destinations_router
from .evidence import router as evidence_router
from .images import router as images_router
from .planner import router as planner_router
from .voice import router as voice_router

router = APIRouter(prefix="/api/v1", tags=["Lumi Travel AI API v1"])

router.include_router(auth_router)
router.include_router(voice_router)
router.include_router(destinations_router)
router.include_router(planner_router)
router.include_router(evidence_router)
router.include_router(dashboard_router)
router.include_router(images_router)

__all__ = ["router"]
