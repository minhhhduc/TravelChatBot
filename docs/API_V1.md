# Lumi Travel AI API v1

Base URL: `/api/v1`

API v1 được chia theo từng router domain trong `backend/routers/api_v1/`:

```text
backend/routers/api_v1/
├── __init__.py          # gom toàn bộ router dưới /api/v1
├── auth.py              # đăng nhập và thông tin user
├── voice.py             # query, STT, TTS, suggestions, SSE status
├── destinations.py      # explorer điểm đến
├── planner.py           # tạo lịch trình
├── evidence.py          # phân tích evidence/RAG
├── dashboard.py         # dashboard metrics
├── images.py            # phân tích/upload/quản lý ảnh
├── schemas.py           # Pydantic schemas
└── common.py            # helper dùng chung
```

## Auth

Các endpoint public không cần token. Các endpoint dashboard và quản lý ảnh CMS cần JWT Bearer token:

```http
Authorization: Bearer <access_token>
```

Login API v1 nhận JSON, khác với endpoint legacy `/auth/login` đang nhận form-data OAuth2.

## Endpoint Summary

| Method | Endpoint | Auth | Router | Mục đích |
|---|---|---:|---|---|
| POST | `/api/v1/auth/login` | No | `auth.py` | Đăng nhập, trả JWT và user |
| GET | `/api/v1/auth/me` | Yes | `auth.py` | Lấy thông tin user hiện tại |
| POST | `/api/v1/voice/query` | No | `voice.py` | Gửi câu hỏi text, nhận answer + sources + citations |
| POST | `/api/v1/voice/stt` | No | `voice.py` | Upload audio, trả transcript |
| POST | `/api/v1/voice/tts` | No | `voice.py` | Text to audio WAV placeholder |
| GET | `/api/v1/voice/suggestions` | No | `voice.py` | Gợi ý follow-up |
| GET | `/api/v1/voice/status` | No | `voice.py` | SSE pipeline status |
| GET | `/api/v1/destinations` | No | `destinations.py` | Danh sách điểm đến, search/filter |
| GET | `/api/v1/destinations/{id}` | No | `destinations.py` | Chi tiết điểm đến + relation graph |
| POST | `/api/v1/planner/generate` | No | `planner.py` | Tạo lịch trình |
| POST | `/api/v1/evidence/analyze` | No | `evidence.py` | Intent/entities/chunks/relations/scores |
| GET | `/api/v1/dashboard/overview` | Yes | `dashboard.py` | Tổng quan metrics |
| GET | `/api/v1/dashboard/dataops` | Yes | `dashboard.py` | Raw -> processed -> chunks -> embeddings |
| GET | `/api/v1/dashboard/rag-graphrag` | Yes | `dashboard.py` | RAG/GraphRAG stats |
| GET | `/api/v1/dashboard/mlops` | Yes | `dashboard.py` | MLOps evaluation status |
| GET | `/api/v1/dashboard/advanced-ai` | Yes | `dashboard.py` | Trạng thái module AI nâng cao |
| GET | `/api/v1/dashboard/cms-bi` | Yes | `dashboard.py` | CMS/BI integration status |
| POST | `/api/v1/images/analyze` | No | `images.py` | Upload ảnh du lịch, AI mô tả/gợi ý |
| POST | `/api/v1/images/upload` | Yes | `images.py` | Admin upload ảnh CMS |
| GET | `/api/v1/images` | Yes | `images.py` | Danh sách ảnh CMS |
| DELETE | `/api/v1/images/{id}` | Yes | `images.py` | Xóa ảnh CMS |

## Request Examples

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "username": "traveler",
  "password": "adventure"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 6,
    "username": "traveler",
    "email": null,
    "role": "user",
    "is_active": true
  }
}
```

### Voice Query

```http
POST /api/v1/voice/query
Content-Type: application/json
```

```json
{
  "query": "Đi Nha Trang 3 ngày nên đi đâu?",
  "conversation_id": "optional-client-id",
  "sort_by": "time",
  "sort_order": "desc"
}
```

Response shape:

```json
{
  "answer": "Markdown answer from TravelChatBot",
  "conversation_id": "optional-client-id",
  "sources": [
    {
      "id": "VinWonders Nha Trang",
      "title": "VinWonders Nha Trang",
      "url": "https://...",
      "relevance_score": 0.42,
      "metadata": {}
    }
  ],
  "citations": [
    {
      "index": 1,
      "source_id": "VinWonders Nha Trang",
      "url": "https://..."
    }
  ],
  "meta": {
    "documents_found": 3,
    "candidates_found": 5,
    "similarity_threshold": 0.5
  }
}
```

### Destinations

```http
GET /api/v1/destinations?search=Nha&limit=10
```

Response:

```json
{
  "items": [
    {
      "id": "Nha Trang",
      "name": "Nha Trang",
      "type": "destination",
      "document_count": 20
    }
  ],
  "total": 1
}
```

### Planner

```http
POST /api/v1/planner/generate
Content-Type: application/json
```

```json
{
  "destination": "Đà Nẵng",
  "days": 3,
  "budget": "5 triệu",
  "interests": ["biển", "ẩm thực", "check-in"],
  "travelers": 2
}
```

### Evidence Analyze

```http
POST /api/v1/evidence/analyze
Content-Type: application/json
```

```json
{
  "query": "Nha Trang có điểm vui chơi nào cho gia đình?",
  "limit": 5
}
```

Response gồm:

- `intent`: intent tạm thời của query.
- `entities`: keyword/entity trích từ query.
- `chunks`: nguồn retrieve từ ChromaDB.
- `relations`: relation query -> chunk.
- `scores`: số lượng docs/candidates và similarity threshold.

## Upload APIs

### STT

```http
POST /api/v1/voice/stt
Content-Type: multipart/form-data
```

Field:

- `audio`: file audio `.wav`, `.mp3`, `.ogg`.

### Image Analyze

```http
POST /api/v1/images/analyze
Content-Type: multipart/form-data
```

Field:

- `image`: file ảnh `.jpg`, `.jpeg`, `.png`.

### CMS Image Upload

```http
POST /api/v1/images/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Fields:

- `image`: file ảnh.
- `destination`: optional.
- `category`: optional.

Metadata ảnh admin upload được lưu ở:

```text
data/metadata/images.json
```

## Dashboard Auth

Dashboard endpoints hiện yêu cầu login JWT:

```text
/api/v1/dashboard/*
/api/v1/images/upload
/api/v1/images
/api/v1/images/{id}
```

Role trong DB hiện có `user` và `admin`; `root` và role enforcement chi tiết chưa được implement đầy đủ. Cần bổ sung `require_roles("admin", "root")` nếu muốn khóa dashboard/CMS chỉ cho admin/root.

## Current Implementation Notes

- `/api/v1/voice/query` gọi `Chatbot.get_response()` và trả `sources/citations` từ ChromaDB.
- `/api/v1/voice/tts` hiện trả WAV placeholder để frontend có contract ổn định. Chưa tích hợp TTS thật.
- `/api/v1/dashboard/mlops` trả trạng thái placeholder vì chưa có offline benchmark/eval store.
- `/api/v1/dashboard/advanced-ai` đánh dấu `GraphRAG`, `Edge AI` là `planned`.
- Similarity threshold hiện lấy từ `ai_module.models.config.MIN_RELEVANCE_SCORE`, default đang là `0.5`.

## Smoke Test

Lệnh smoke test đã dùng:

```powershell
.\.venv\Scripts\python.exe -m py_compile backend ai_module

.\.venv\Scripts\python.exe qa_ba\test\test_chat_api.py
.\.venv\Scripts\python.exe qa_ba\test\test_rate_limiter.py
```

Kết quả gần nhất:

```text
missing_routes=[]
/api/v1/auth/login -> 200
/api/v1/auth/me -> 200
/api/v1/destinations -> 200
/api/v1/evidence/analyze -> 200
/api/v1/dashboard/overview -> 200
/api/v1/voice/tts -> 200 audio/wav
```
