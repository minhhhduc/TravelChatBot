# TravelChatBot REST API Documentation

TravelChatBot provides a secure, fully-documented **REST API** built with **FastAPI**. It coordinates user onboarding, JWT session authentication, preference personalization, conversational history, and multimodal RAG searches.

---

## 🔒 Authentication & Headers

All non-public endpoints require standard **JWT Bearer Token** authentication. Include the following header in your API requests:

```http
Authorization: Bearer <your_jwt_token>
```

---

## 🧭 API Endpoints Reference

### 1. Authentication Router (`/auth`)

#### 📝 Register User
Creates a new user profile and generates default empty travel preferences.
*   **Method**: `POST`
*   **Path**: `/auth/register`
*   **Request Body (`application/json`)**:
    ```json
    {
      "username": "traveler",
      "password": "securepassword123",
      "email": "traveler@example.com"
    }
    ```
*   **Response (`201 Created`)**:
    ```json
    {
      "id": 5,
      "username": "traveler",
      "email": "traveler@example.com",
      "role": "user",
      "is_active": true
    }
    ```

#### 🔑 Login User
Exchanges plain credentials for a secure JWT access token.
*   **Method**: `POST`
*   **Path**: `/auth/login`
*   **Request Body (`application/x-www-form-urlencoded`)**:
    *   `username`: `traveler`
    *   `password`: `securepassword123`
*   **Response (`200 OK`)**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```

#### 👤 Fetch Current Profile
Retrieves the logged-in user's profile details.
*   **Method**: `GET`
*   **Path**: `/auth/me`
*   **Response (`200 OK`)**:
    ```json
    {
      "id": 5,
      "username": "traveler",
      "email": "traveler@example.com",
      "role": "user",
      "is_active": true
    }
    ```

---

### 2. User Preferences Router (`/user`)

#### 🔍 Get User Preferences
Retrieves the current traveler preference settings.
*   **Method**: `GET`
*   **Path**: `/user/preferences`
*   **Response (`200 OK`)**:
    ```json
    {
      "user_id": 5,
      "dietary_goals": [],
      "preferred_ingredients": [],
      "avoided_ingredients": [],
      "cuisine_types": [],
      "destinations": [],
      "updated_at": "2026-05-18T20:27:08.446932"
    }
    ```

#### ✏️ Update User Preferences
Dynamically updates traveler settings. Only provided fields are updated; unspecified fields are retained.
*   **Method**: `PUT`
*   **Path**: `/user/preferences`
*   **Request Body (`application/json`)**:
    ```json
    {
      "destinations": ["Hạ Long", "Nha Trang"],
      "cuisine_types": ["Hải sản"]
    }
    ```
*   **Response (`200 OK`)**:
    ```json
    {
      "user_id": 5,
      "dietary_goals": [],
      "preferred_ingredients": [],
      "avoided_ingredients": [],
      "cuisine_types": ["Hải sản"],
      "destinations": ["Hạ Long", "Nha Trang"],
      "updated_at": "2026-05-19T03:30:00.123456"
    }
    ```

---

### 3. Conversations & Assistant Router (`/chat`)

#### ➕ Create Chat Session
Spawns a new chat session to track conversation history.
*   **Method**: `POST`
*   **Path**: `/chat/sessions`
*   **Request Body (`application/json`)**:
    ```json
    {
      "title": "Hành trình Nha Trang"
    }
    ```
*   **Response (`201 Created`)**:
    ```json
    {
      "id": "8da8d74c-536a-41d8-9897-7c14945c5eff",
      "user_id": 5,
      "title": "Hành trình Nha Trang",
      "created_at": "2026-05-18T20:27:08.748024",
      "updated_at": "2026-05-18T20:27:08.748024"
    }
    ```

#### 📜 List Chat Sessions
Retrieves all sessions owned by the authenticated user, sorted with the latest activity first.
*   **Method**: `GET`
*   **Path**: `/chat/sessions`
*   **Response (`200 OK`)**:
    ```json
    [
      {
        "id": "8da8d74c-536a-41d8-9897-7c14945c5eff",
        "user_id": 5,
        "title": "Hành trình Nha Trang",
        "created_at": "2026-05-18T20:27:08.748024",
        "updated_at": "2026-05-18T20:27:08.748024"
      }
    ]
    ```

#### 💬 Fetch Session Messages
Retrieves complete historical message logs for a specific session.
*   **Method**: `GET`
*   **Path**: `/chat/sessions/{session_id}/messages`
*   **Response (`200 OK`)**:
    ```json
    [
      {
        "id": 12,
        "session_id": "8da8d74c-536a-41d8-9897-7c14945c5eff",
        "role": "user",
        "content": "VinWonders Nha Trang có những show diễn nào nổi bật buổi tối?",
        "image_path": null,
        "audio_path": null,
        "created_at": "2026-05-18T20:27:09.123456"
      },
      {
        "id": 13,
        "session_id": "8da8d74c-536a-41d8-9897-7c14945c5eff",
        "role": "assistant",
        "content": "VinWonders Nha Trang có những show diễn buổi tối đầy mê hoặc...",
        "image_path": null,
        "audio_path": null,
        "created_at": "2026-05-18T20:27:10.987654"
      }
    ]
    ```

#### 🚀 Post Chat Message (Multimodal RAG)
Sends a text query, optionally uploading an image or audio file. Automatically invokes the 6-agent RAG workflow.
*   **Method**: `POST`
*   **Path**: `/chat/sessions/{session_id}/message`
*   **Request Body (`multipart/form-data`)**:
    *   `content` (*string, optional*): Text query (e.g., `"Món ăn nổi bật Nha Trang"`).
    *   `sort_by` (*string, optional*): ChromaDB sort filter (`"time"`, `"evaluate_mean"`, `"evaluate_count"`).
    *   `sort_order` (*string, optional*): Order of results (`"desc"` or `"asc"`, defaults to `"desc"`).
    *   `image` (*file, optional*): Binary image attachment (e.g., benchmark.jpg).
    *   `audio` (*file, optional*): Binary audio clip (e.g., query.wav).
*   **Response (`200 OK`)**:
    ```json
    {
      "id": 14,
      "session_id": "8da8d74c-536a-41d8-9897-7c14945c5eff",
      "role": "assistant",
      "content": "### 🌟 Điểm hẹn ẩm thực Nha Trang... \n\n...",
      "image_path": null,
      "audio_path": null,
      "created_at": "2026-05-19T03:32:00.654321"
    }
    ```
