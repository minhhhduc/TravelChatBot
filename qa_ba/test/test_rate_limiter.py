"""Integration test module for TravelChatBot rate limiting authentication.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

# Add project root to path
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
from backend.rate_limiter import chat_rate_limiter


class FakeChatbot:
    """Mock chatbot used to verify rate limiter without LLM calls."""
    def get_response(self, user_query, image_path=None, audio_path=None, sort_by=None, sort_order="desc"):
        return f"Mock response for {user_query}"


def build_test_app_client():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "rate_test.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed_session = TestingSessionLocal()
    try:
        user = User(username="rate_tester", email="rate_tester@example.com", role="user", is_active=True)
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
            username="rate_tester",
            email="rate_tester@example.com",
            role="user",
            is_active=True,
        )

    def override_get_chatbot():
        return FakeChatbot()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_chatbot] = override_get_chatbot

    client = TestClient(app)
    return client, temp_dir, engine, user_id


def test_rate_limiter():
    client, temp_dir, engine, user_id = build_test_app_client()
    try:
        print("Starting rate limiting tests...")
        # 1. Create a session
        session_response = client.post("/chat/sessions", json={"title": "Rate Limit Session"})
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # Reset rate limiter timestamps for this user to make test deterministic
        chat_rate_limiter.text_requests[user_id] = []

        # 2. Make 15 successful requests
        print("Sending 15 consecutive requests (should succeed)...")
        for i in range(15):
            res = client.post(
                f"/chat/sessions/{session_id}/message",
                data={"content": f"Request {i+1}"}
            )
            assert res.status_code == 200, f"Request {i+1} failed with status: {res.status_code}"

        # 3. Make the 16th request, which must trigger HTTP 429
        print("Sending 16th request (should be blocked by rate limit)...")
        blocked_res = client.post(
            f"/chat/sessions/{session_id}/message",
            data={"content": "Request 16"}
        )
        assert blocked_res.status_code == 429, f"Expected HTTP 429, got: {blocked_res.status_code}"
        
        # Verify response details and header
        response_json = blocked_res.json()
        print("✅ HTTP 429 response body:", response_json)
        assert "Text rate limit exceeded" in response_json["detail"]
        
        retry_after = blocked_res.headers.get("Retry-After")
        print("✅ HTTP Retry-After header:", retry_after)
        assert retry_after is not None
        assert int(retry_after) > 0

        print("🎉 Per-user rate-limiting auth verification test PASSED successfully!")

    finally:
        app.dependency_overrides.clear()
        client.close()
        engine.dispose()
        temp_dir.cleanup()


if __name__ == "__main__":
    test_rate_limiter()
