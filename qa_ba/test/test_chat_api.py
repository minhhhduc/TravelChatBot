"""Integration test module for the TravelChatBot API.

This module uses FastAPI's TestClient so it can verify the REST API
without running uvicorn or calling the external Gemini API.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import get_db
from backend.auth_utils import get_current_user
from backend.models import Base, User, UserPreference
from backend.routers.chat import get_chatbot


class FakeChatbot:
    """Small fake chatbot used to verify API wiring end-to-end."""

    def __init__(self):
        self.conversation_buffer = []

    def get_response(self, user_query, image_path=None, audio_path=None, sort_by=None, sort_order="desc"):
        return f"FAKE RESPONSE: {user_query} | sort_by={sort_by} | sort_order={sort_order}"


def build_test_app_client():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "api_test.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed_session = TestingSessionLocal()
    try:
        user = User(username="api_tester", email="api_tester@example.com", role="user", is_active=True)
        user.set_password("password123")
        seed_session.add(user)
        seed_session.flush()
        seed_session.add(
            UserPreference(
                user_id=user.id,
                dietary_goals=[],
                preferred_ingredients=[],
                avoided_ingredients=[],
                cuisine_types=[],
                destinations=[],
            )
        )
        seed_session.commit()
        user_id = user.id
    finally:
        seed_session.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        return SimpleNamespace(
            id=user_id,
            username="api_tester",
            email="api_tester@example.com",
            role="user",
            is_active=True,
        )

    def override_get_chatbot():
        return FakeChatbot()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_chatbot] = override_get_chatbot

    client = TestClient(app)
    return client, temp_dir, engine


def test_health_endpoint():
    client, temp_dir, engine = build_test_app_client()
    try:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "online"
    finally:
        app.dependency_overrides.clear()
        client.close()
        engine.dispose()
        temp_dir.cleanup()


def test_chat_session_and_message_flow():
    client, temp_dir, engine = build_test_app_client()
    try:
        session_response = client.post("/chat/sessions", json={"title": "Test trip"})
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        message_response = client.post(
            f"/chat/sessions/{session_id}/message",
            data={"content": "Xin chào Đà Nẵng", "sort_by": "time", "sort_order": "desc"},
        )
        assert message_response.status_code == 200
        payload = message_response.json()
        assert "FAKE RESPONSE" in payload["content"]

        history_response = client.get(f"/chat/sessions/{session_id}/messages")
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    finally:
        app.dependency_overrides.clear()
        client.close()
        engine.dispose()
        temp_dir.cleanup()


def main():
    test_health_endpoint()
    test_chat_session_and_message_flow()
    print("API test module completed successfully.")


if __name__ == "__main__":
    main()