"""API v1 travel planner endpoints."""
from fastapi import APIRouter

from backend.routers.chat import get_chatbot
from .schemas import PlannerRequest

router = APIRouter(prefix="/planner", tags=["API v1 - Planner"])


@router.post("/generate")
def planner_generate(payload: PlannerRequest):
    prompt = (
        f"Lập lịch trình {payload.days} ngày ở {payload.destination}. "
        f"Ngân sách: {payload.budget or 'chưa rõ'}. "
        f"Sở thích: {', '.join(payload.interests) if payload.interests else 'linh hoạt'}. "
        f"Số khách: {payload.travelers}."
    )
    answer = get_chatbot().get_response(prompt)
    return {
        "destination": payload.destination,
        "days": payload.days,
        "itinerary": answer,
        "inputs": payload.model_dump(),
    }
