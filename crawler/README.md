# Crawler

## iVIVU Blog

Crawl bài viết từ https://www.ivivu.com/blog và lưu dữ liệu thô vào `data/raw/ivivu_blog/`.

### Cài dependencies

Nếu bạn đang dùng `.venv` trong repo:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Chạy crawl

Ví dụ crawl 2 trang listing đầu tiên (page 1 và page 2), tối đa 30 bài:

```powershell
python -m crawler.ivivu_blog_crawler --max-pages 2 --max-articles 30
```

Output mặc định:
- `data/raw/ivivu_blog/pages/` (HTML listing pages)
- `data/raw/ivivu_blog/articles/` (HTML bài viết + metadata JSON)
- `data/raw/ivivu_blog/index.jsonl` (1 dòng / 1 bài)

### Tuỳ chọn hay dùng

- `--out-dir data/raw/ivivu_blog`
- `--delay-seconds 1.0` (delay giữa requests)
- `--no-respect-robots` (không khuyến nghị)
- `--resume` (mặc định bật, skip bài đã crawl)
