# Data Pipeline & Workflow

Tài liệu này mô tả luồng dữ liệu (crawler → preprocessing → ingestion) của TravelChatBot.

---

## 1) Tổng quan

Pipeline chuẩn dùng cho RAG/ChromaDB:

```mermaid
graph TD
    A[iVIVU Blog] --> B[Crawler: download HTML + images]
    B --> C[data/raw/ivivu_blog/*]
    C --> D[Raw aggregate JSONL]
    D --> E[Preprocess (clean + enrich)]
    E --> F[data/processed/preprocessed_data.jsonl]
    E --> G[data/features/metadata.json]
    F --> H[ChromaDB ingestion]
    H --> I[(ChromaDB collection)]
```

---

## 2) Input/Output chính

### Crawler output

- Folder: `data/raw/ivivu_blog/`
  - `index.jsonl`: index bài viết (url/title/paths/published_date)
  - `articles/*.json`: bài viết dạng JSON (có `keypoint`)
  - `articles/*.html`: HTML đã tải
  - `images/*`: ảnh đã tải

- File raw aggregate:
  - `data/raw/raw.jsonl`: JSON Lines, mỗi dòng là 1 article với `keypoint`.

### Preprocess output

- Dataset dùng cho ingestion:
  - `data/processed/preprocessed_data.jsonl`
  - Mỗi dòng là **1 article object** với schema:

```json
{
  "title": "...",
  "time": "...",
  "url": "...",
  "destination": "...",
  "keypoint": [
    {
      "idx": {"idx": 1, "title": "...", "context": "..."},
      "evaluate": {"mean": 4.2, "items": []}
    }
  ],
  "source": "ivivu_blog"
}
```

- Metadata/stats:
  - `data/features/metadata.json` (top destinations + counters)

- Sample nhanh để test:
  - `data/processed/preprocessed_data.sample.jsonl`
  - `data/features/metadata.sample.json`

---

## 3) Preprocessing workflow

Tool: `processer/` (đã modular hóa)

- `processer/preprocessing.py`: CLI wrapper
- `processer/pipeline.py`: pipeline chính (`article`/`spot`)
- `processer/jsonl_utils.py`: đọc JSONL robust
- `processer/text_cleaning.py`: clean text + `[img] ... [img]`
- `processer/ivivu_index.py`: join `index.jsonl` để enrich `url/published_date`
- `processer/destination.py`: infer destination từ title

### Chạy preprocessing (khuyến nghị)

Sau khi đã active venv và cài dependencies:

```powershell
# (optional) editable install để có console script
.\.venv\Scripts\Activate.ps1
python -m pip install -e .

# tạo dataset chuẩn cho ingestion
travelchatbot-preprocess --format article `
  --input data\raw\raw.jsonl `
  --output data\processed\preprocessed_data.jsonl `
  --stats-out data\features\metadata.json

# tạo sample 100 articles để debug
travelchatbot-preprocess --format article --max-articles 100 `
  --input data\raw\raw.jsonl `
  --output data\processed\preprocessed_data.sample.jsonl `
  --stats-out data\features\metadata.sample.json
```

Nếu chưa cài editable, vẫn chạy được:

```powershell
.\.venv\Scripts\Activate.ps1
python processer\preprocessing.py --format article --input data\raw\raw.jsonl --output data\processed\preprocessed_data.jsonl
```

### Output format

- `--format article` (DEFAULT): giữ schema tương thích ingestion hiện tại (article + `keypoint` list).
- `--format spot`: flatten mỗi keypoint thành 1 dòng (phù hợp phân tích/training; không phải flow ingestion mặc định).

---

## 4) Ingestion workflow (ChromaDB)

Luồng ingestion kỳ vọng đọc JSON/JSONL và tách từng `keypoint` thành một document (context) để embed.

- Input khuyến nghị cho ingestion: `data/processed/preprocessed_data.jsonl`
- Mỗi `keypoint` trở thành 1 vector document.
- Metadata thường gồm: `destination`, `time`, `evaluate_mean`, `evaluate_count`, `images`, `url`, `article_title`, `keypoint_title`, ...

Xem thêm: `docs/ChromaDB.md`.
