# TravelChatBot

## Crawler

Crawl dữ liệu thô từ iVIVU Blog (https://www.ivivu.com/blog) vào `data/raw/ivivu_blog/`.

### Cài dependencies

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Chạy crawl

```powershell
python -m crawler.ivivu_blog_crawler --max-pages 2 --max-articles 30
```

Xem thêm: `crawler/README.md`

## Preprocess dataset

Sau khi crawl (hoặc khi đã có `data/raw/raw.jsonl`), chạy preprocess để tạo dataset chuẩn cho ingestion:

```powershell
.\.venv\Scripts\Activate.ps1

# (optional) cài editable để dùng console script
python -m pip install -e .

# tạo dataset dùng cho ingestion + metadata
travelchatbot-preprocess --format article `
	--input data\raw\raw.jsonl `
	--output data\processed\preprocessed_data.jsonl `
	--stats-out data\features\metadata.json
```

Tài liệu chi tiết pipeline/workflow: `docs/DataPipeline.md`.

## API v1

Lumi Travel AI API v1 nằm dưới prefix `/api/v1` và đã được tách theo router domain:

- `backend/routers/api_v1/auth.py`
- `backend/routers/api_v1/voice.py`
- `backend/routers/api_v1/destinations.py`
- `backend/routers/api_v1/planner.py`
- `backend/routers/api_v1/evidence.py`
- `backend/routers/api_v1/dashboard.py`
- `backend/routers/api_v1/images.py`

Tài liệu endpoint chi tiết: `docs/API_V1.md`.
