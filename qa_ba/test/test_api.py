"""Integration test script for TravelChatBot FastAPI Backend REST API.
"""
import sys
import time
import requests
from pathlib import Path

# Force stdout to UTF-8 to prevent Windows CP1252 print crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://127.0.0.1:8000"


def test_api():
    print("====== TRAVELCHATBOT REST API VERIFICATION ======")
    
    # 1. Health Check
    print("Testing / health check...")
    res = requests.get(f"{API_URL}/")
    if res.status_code == 200:
        print("✅ Health check SUCCESS:", res.json())
    else:
        print("❌ Health check FAILED:", res.status_code)
        return

    # Generate unique test username
    test_user = f"tester_{int(time.time())}"
    test_pass = "testerpassword"

    # 2. Register
    print(f"\nRegistering new user '{test_user}'...")
    res = requests.post(
        f"{API_URL}/auth/register",
        json={
            "username": test_user,
            "password": test_pass,
            "email": f"{test_user}@example.com"
        }
    )
    if res.status_code == 201:
        print("✅ Register SUCCESS:", res.json())
    else:
        print("❌ Register FAILED:", res.status_code, res.text)
        return

    # 3. Login
    print(f"\nLogging in as '{test_user}'...")
    res = requests.post(
        f"{API_URL}/auth/login",
        data={
            "username": test_user,
            "password": test_pass
        }
    )
    if res.status_code == 200:
        token_data = res.json()
        print("✅ Login SUCCESS:", token_data)
        token = token_data["access_token"]
    else:
        print("❌ Login FAILED:", res.status_code, res.text)
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 4. Get Profile /me
    print("\nRetrieving self profile...")
    res = requests.get(f"{API_URL}/auth/me", headers=headers)
    if res.status_code == 200:
        print("✅ Me profile SUCCESS:", res.json())
    else:
        print("❌ Me profile FAILED:", res.status_code, res.text)
        return

    # 5. Get Preferences
    print("\nRetrieving user preferences...")
    res = requests.get(f"{API_URL}/user/preferences", headers=headers)
    if res.status_code == 200:
        print("✅ Get preferences SUCCESS:", res.json())
    else:
        print("❌ Get preferences FAILED:", res.status_code, res.text)
        return

    # Update Preferences
    print("Updating user preferences...")
    res = requests.put(
        f"{API_URL}/user/preferences",
        headers=headers,
        json={
            "destinations": ["Hạ Long", "Nha Trang"],
            "cuisine_types": ["Hải sản"]
        }
    )
    if res.status_code == 200:
        print("✅ Update preferences SUCCESS:", res.json())
    else:
        print("❌ Update preferences FAILED:", res.status_code, res.text)
        return

    # 6. Create Chat Session
    print("\nCreating new chat session...")
    res = requests.post(
        f"{API_URL}/chat/sessions",
        headers=headers,
        json={"title": "Hành trình Nha Trang"}
    )
    if res.status_code == 201:
        session_data = res.json()
        print("✅ Create session SUCCESS:", session_data)
        session_id = session_data["id"]
    else:
        print("❌ Create session FAILED:", res.status_code, res.text)
        return

    # 7. Post Message with RAG Coordinator Execution
    print(f"\nSending RAG query to session {session_id}...")
    res = requests.post(
        f"{API_URL}/chat/sessions/{session_id}/message",
        headers=headers,
        data={
            "content": "VinWonders Nha Trang có những show diễn nào nổi bật buổi tối?",
            "sort_by": "time"
        }
    )
    if res.status_code == 200:
        print("✅ Post message (RAG) SUCCESS!")
        msg_data = res.json()
        print(f"\nAssistant Response Preview:\n{msg_data['content'][:500]}...")
    else:
        print("❌ Post message (RAG) FAILED:", res.status_code, res.text)
        return

    print("\n====== ALL REST API INTEGRATION TESTS COMPLETED SUCCESSFULLY! ======")


if __name__ == "__main__":
    test_api()
