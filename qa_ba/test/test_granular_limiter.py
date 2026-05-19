"""Integration tests for granular per-user media-type specific rate limits.
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
    """Mock chatbot that returns immediate responses to avoid calling Gemini APIs."""
    def get_response(self, user_query, image_path=None, audio_path=None, sort_by=None, sort_order="desc"):
        return f"Mock response for {user_query}"


def build_test_app_client():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "granular_test.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed_session = TestingSessionLocal()
    try:
        user = User(username="granular_tester", email="granular_tester@example.com", role="user", is_active=True)
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
            username="granular_tester",
            email="granular_tester@example.com",
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


def reset_limiter_for_user(user_id: int):
    """Resets all sliding windows for a clean test environment."""
    chat_rate_limiter.text_requests[user_id] = []
    chat_rate_limiter.speech_requests[user_id] = []
    chat_rate_limiter.vision_requests[user_id] = []


def test_granular_rate_limiting():
    client, temp_dir, engine, user_id = build_test_app_client()
    try:
        print("====== STARTING GRANULAR RATE LIMIT TESTS ======")
        
        # Create test chat session
        session_response = client.post("/chat/sessions", json={"title": "Granular Session"})
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # ----------------------------------------------------
        # TEST 1: Standard Text Limit (Threshold = 15)
        # ----------------------------------------------------
        reset_limiter_for_user(user_id)
        print("\n--- Test 1: Testing Standard Text Limits (15 requests/min) ---")
        for i in range(15):
            res = client.post(
                f"/chat/sessions/{session_id}/message",
                data={"content": f"Text query {i+1}"}
            )
            assert res.status_code == 200, f"Text query {i+1} failed: {res.text}"

        blocked_text = client.post(
            f"/chat/sessions/{session_id}/message",
            data={"content": "Blocked Text query"}
        )
        assert blocked_text.status_code == 429
        assert "Text rate limit exceeded" in blocked_text.json()["detail"]
        print("✅ Text Rate Limiting verified successfully!")

        # ----------------------------------------------------
        # TEST 2: Speech Limit (Threshold = 5)
        # ----------------------------------------------------
        reset_limiter_for_user(user_id)
        print("\n--- Test 2: Testing Speech/Audio Limits (5 requests/min) ---")
        mock_audio = ("test.wav", b"fake wave sound content", "audio/wav")
        for i in range(5):
            res = client.post(
                f"/chat/sessions/{session_id}/message",
                data={"content": f"Voice query {i+1}"},
                files={"audio": mock_audio}
            )
            assert res.status_code == 200, f"Audio query {i+1} failed: {res.text}"

        blocked_audio = client.post(
            f"/chat/sessions/{session_id}/message",
            data={"content": "Blocked Voice query"},
            files={"audio": mock_audio}
        )
        assert blocked_audio.status_code == 429
        assert "Speech rate limit exceeded" in blocked_audio.json()["detail"]
        print("✅ Speech Rate Limiting verified successfully!")

        # ----------------------------------------------------
        # TEST 3: Vision Limit (Threshold = 3)
        # ----------------------------------------------------
        reset_limiter_for_user(user_id)
        print("\n--- Test 3: Testing Vision/Image Limits (3 requests/min) ---")
        mock_image = ("test.png", b"fake png pixel content", "image/png")
        for i in range(3):
            res = client.post(
                f"/chat/sessions/{session_id}/message",
                data={"content": f"Image query {i+1}"},
                files={"image": mock_image}
            )
            assert res.status_code == 200, f"Image query {i+1} failed: {res.text}"

        blocked_image = client.post(
            f"/chat/sessions/{session_id}/message",
            data={"content": "Blocked Image query"},
            files={"image": mock_image}
        )
        assert blocked_image.status_code == 429
        assert "Vision rate limit exceeded" in blocked_image.json()["detail"]
        print("✅ Vision Rate Limiting verified successfully!")

        print("\n🎉 All granular per-user media rate limiting tests PASSED successfully!")

    finally:
        app.dependency_overrides.clear()
        client.close()
        engine.dispose()
        temp_dir.cleanup()


if __name__ == "__main__":
    test_granular_rate_limiting()
