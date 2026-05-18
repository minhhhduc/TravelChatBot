from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .packages.download_utils import download_image
from .packages.file_utils import append_jsonl, load_seen_urls, write_bytes, write_json
from .packages.html_extract import (
    extract_canonical_url,
    extract_content_text,
    extract_image_urls,
    extract_keypoint_sections,
    extract_published_date,
    extract_title,
)
from .packages.http_utils import load_robots, make_session, polite_sleep
from .packages.url_utils import (
    canonicalize_url,
    short_hash,
    safe_slug_from_url,
    ym_from_article_url,
)


DEFAULT_SEED_URL = "https://www.ivivu.com/blog/"
DEFAULT_OUT_DIR = Path("data/raw/ivivu_blog")
DEFAULT_GLOBAL_RAW_JSONL = Path("data/raw/raw.jsonl")
USER_AGENT = "TravelChatBotCrawler/0.1 (+https://www.ivivu.com/blog)"

ARTICLE_URL_RE = re.compile(r"^https?://www\.ivivu\.com/blog/\d{4}/\d{2}/[^/]+/?$")
LISTING_PAGE_RE = re.compile(r"^https?://www\.ivivu\.com/blog/(page/\d+/)?$")


@dataclass(frozen=True)
class CrawlItem:
    url: str
    discovered_from: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def extract_article_links(listing_html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "lxml")

    links: dict[str, None] = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        abs_url = canonicalize_url(urljoin(base_url, href))
        if ARTICLE_URL_RE.match(abs_url):
            links[abs_url] = None

    return list(links.keys())


def iter_listing_pages(seed_url: str, max_pages: int) -> Iterable[str]:
    seed_url = canonicalize_url(seed_url)
    if not seed_url.endswith("/"):
        seed_url += "/"

    # Page 1 is seed; page N is /blog/page/N/
    yield seed_url
    for page in range(2, max_pages + 1):
        yield urljoin(seed_url, f"page/{page}/")


def crawl_ivivu_blog(
    *,
    seed_url: str,
    out_dir: Path,
    max_pages: int,
    max_articles: int,
    delay_seconds: float,
    respect_robots: bool,
    resume: bool,
    timeout_seconds: float,
    rebuild_local: bool,
    global_raw_jsonl: Path,
) -> None:
    session = make_session(user_agent=USER_AGENT)

    rp: Optional[RobotFileParser] = None
    if respect_robots:
        rp = load_robots(session=session, base_url=seed_url)

    pages_dir = out_dir / "pages"
    articles_dir = out_dir / "articles"
    index_jsonl = out_dir / "index.jsonl"

    if rebuild_local:
        # Rebuild meta JSONs + index + global raw from local HTML files.
        articles_dir.mkdir(parents=True, exist_ok=True)
        index_jsonl.parent.mkdir(parents=True, exist_ok=True)
        global_raw_jsonl.parent.mkdir(parents=True, exist_ok=True)

        index_jsonl.write_text("", encoding="utf-8")
        global_raw_jsonl.write_text("", encoding="utf-8")

        html_files = sorted(articles_dir.glob("*.html"))
        rebuilt = 0

        for html_path in html_files:
            try:
                html_text = html_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            url = extract_canonical_url(html_text)
            if not url:
                continue

            url = canonicalize_url(url)
            file_stem = html_path.stem
            meta_path = articles_dir / f"{file_stem}.json"

            existing: dict = {}
            if meta_path.exists():
                try:
                    existing = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}

            title = extract_title(html_text)
            published_date = extract_published_date(html_text)
            if published_date is None:
                year, month = ym_from_article_url(url)
                if year and month:
                    published_date = f"{year}-{month}-01"

            content_text = extract_content_text(html_text)

            image_candidates = extract_image_urls(html_text, url)
            images_dir = out_dir / "images" / file_stem
            downloaded_images: list[dict] = []
            for idx, img in enumerate(image_candidates, start=1):
                img_url = img.get("url")
                if not isinstance(img_url, str) or not img_url:
                    continue
                result = download_image(
                    session=session,
                    url=img_url,
                    out_dir=images_dir,
                    idx=idx,
                    timeout_seconds=timeout_seconds,
                )
                result["alt"] = img.get("alt")
                downloaded_images.append(result)

            url_to_local_path: dict[str, str] = {}
            for img in downloaded_images:
                img_url = img.get("url")
                local = img.get("local_path")
                if isinstance(img_url, str) and img_url and isinstance(local, str) and local:
                    url_to_local_path[img_url] = local
                    url_to_local_path[img_url.split("#", 1)[0].split("?", 1)[0]] = local

            sections = extract_keypoint_sections(html_text, base_url=url, url_to_local_path=url_to_local_path)
            keypoints: list[dict] = []
            for i, sec in enumerate(sections, start=1):
                keypoints.append(
                    {
                        "idx": {"idx": i, "title": sec.get("title") or "", "context": sec.get("context") or ""},
                        "evaluate": {"mean": 0, "items": []},
                    }
                )

            article_obj = {
                "title": title or "",
                "time": published_date or "",
                "keypoint": keypoints,
            }

            meta = {
                "source": "ivivu_blog",
                "url": url,
                "discovered_from": existing.get("discovered_from"),
                "fetched_at_utc": existing.get("fetched_at_utc") or _utc_now_iso(),
                "http_status": existing.get("http_status"),
                "title": title,
                "published_date": published_date,
                "content_text": content_text,
                "images": downloaded_images,
                "paths": {
                    "html": str(html_path.as_posix()),
                    "meta": str(meta_path.as_posix()),
                },
            }

            write_json(meta_path, meta)
            append_jsonl(
                index_jsonl,
                {
                    "source": "ivivu_blog",
                    "url": url,
                    "title": title,
                    "published_date": published_date,
                    "images": sum(1 for x in downloaded_images if x.get("local_path")),
                    "paths": meta["paths"],
                },
            )
            append_jsonl(global_raw_jsonl, article_obj)

            rebuilt += 1

        print(f"Done. Rebuilt local articles: {rebuilt}. Output: {out_dir.as_posix()}")
        return

    seen_urls: set[str] = set()
    if resume:
        seen_urls = load_seen_urls(index_jsonl)

    crawled_count = 0

    dynamic_max_pages = max_pages
    page_idx = 1
    while True:
        if page_idx == 1:
            page_url = canonicalize_url(seed_url)
            if not page_url.endswith("/"):
                page_url += "/"
        else:
            page_url = urljoin(seed_url, f"page/{page_idx}/")

        print(f"\n[Listing Page] Processing page {page_idx} / {dynamic_max_pages or 'unknown'} ({page_url})", flush=True)

        if respect_robots and rp is not None and not rp.can_fetch(USER_AGENT, page_url):
            print(f"[robots] disallow listing: {page_url}", file=sys.stderr, flush=True)
            if page_idx == 1:
                break
            page_idx += 1
            continue

        polite_sleep(delay_seconds)
        try:
            resp = session.get(page_url, timeout=timeout_seconds)
        except requests.RequestException as e:
            print(f"[error] listing fetch failed: {page_url} ({e})", file=sys.stderr, flush=True)
            break

        if resp.status_code >= 400:
            print(f"[warn] listing status {resp.status_code}: {page_url}", file=sys.stderr, flush=True)
            break

        listing_html = resp.text
        write_bytes(pages_dir / f"page_{page_idx:04d}.html", resp.content)

        # Dynamic max pages detection on the first page
        if page_idx == 1 and max_pages <= 0:
            soup = BeautifulSoup(listing_html, "lxml")
            max_page_found = 1
            for a in soup.select("a.page-numbers"):
                text = a.text.strip().replace(".", "").replace(",", "")
                if text.isdigit():
                    max_page_found = max(max_page_found, int(text))
            dynamic_max_pages = max_page_found
            print(f"[info] Automatically detected max pages: {dynamic_max_pages}", flush=True)

        links = extract_article_links(listing_html, page_url)
        new_links = [u for u in links if u not in seen_urls]
        print(f"  [info] Found {len(new_links)} new articles to crawl (out of {len(links)} total links on page {page_idx})", flush=True)

        # Crawl each newly discovered article immediately
        stop_crawling = False
        for url in new_links:
            if max_articles > 0 and crawled_count >= max_articles:
                stop_crawling = True
                break

            if respect_robots and rp is not None and not rp.can_fetch(USER_AGENT, url):
                print(f"  [robots] disallow article: {url}", file=sys.stderr, flush=True)
                continue

            print(f"  [+] Crawling article {crawled_count + 1}: {url} ...", flush=True)
            polite_sleep(delay_seconds)
            try:
                article_resp = session.get(url, timeout=timeout_seconds)
            except requests.RequestException as e:
                print(f"  [error] article fetch failed: {url} ({e})", file=sys.stderr, flush=True)
                continue

            status = article_resp.status_code
            if status >= 400:
                print(f"  [warn] article status {status}: {url}", file=sys.stderr, flush=True)
                continue

            html_bytes = article_resp.content
            html_text = article_resp.text

            year, month = ym_from_article_url(url)
            ym = f"{year}-{month}" if year and month else "unknown"
            slug = safe_slug_from_url(url)
            file_stem = f"{ym}_{slug}__{short_hash(url)}"

            html_path = articles_dir / f"{file_stem}.html"
            meta_path = articles_dir / f"{file_stem}.json"

            write_bytes(html_path, html_bytes)

            title = extract_title(html_text)
            published_date = extract_published_date(html_text)
            if published_date is None:
                year, month = ym_from_article_url(url)
                if year and month:
                    published_date = f"{year}-{month}-01"

            content_text = extract_content_text(html_text)

            image_candidates = extract_image_urls(html_text, url)
            images_dir = out_dir / "images" / file_stem
            downloaded_images: list[dict] = []
            for idx, img in enumerate(image_candidates, start=1):
                img_url = img.get("url")
                if not isinstance(img_url, str) or not img_url:
                    continue
                result = download_image(
                    session=session,
                    url=img_url,
                    out_dir=images_dir,
                    idx=idx,
                    timeout_seconds=timeout_seconds,
                )
                result["alt"] = img.get("alt")
                downloaded_images.append(result)

            url_to_local_path: dict[str, str] = {}
            for img in downloaded_images:
                img_url = img.get("url")
                local = img.get("local_path")
                if isinstance(img_url, str) and img_url and isinstance(local, str) and local:
                    url_to_local_path[img_url] = local
                    url_to_local_path[img_url.split("#", 1)[0].split("?", 1)[0]] = local

            sections = extract_keypoint_sections(html_text, base_url=url, url_to_local_path=url_to_local_path)
            keypoints: list[dict] = []
            for i, sec in enumerate(sections, start=1):
                keypoints.append(
                    {
                        "idx": {"idx": i, "title": sec.get("title") or "", "context": sec.get("context") or ""},
                        "evaluate": {"mean": 0, "items": []},
                    }
                )

            article_obj = {
                "title": title or "",
                "time": published_date or "",
                "keypoint": keypoints,
            }

            meta = {
                "source": "ivivu_blog",
                "url": url,
                "discovered_from": page_url,
                "fetched_at_utc": _utc_now_iso(),
                "http_status": status,
                "title": title,
                "published_date": published_date,
                "content_text": content_text,
                "images": downloaded_images,
                "paths": {
                    "html": str(html_path.as_posix()),
                    "meta": str(meta_path.as_posix()),
                },
            }

            write_json(meta_path, meta)
            append_jsonl(global_raw_jsonl, article_obj)
            append_jsonl(
                index_jsonl,
                {
                    "source": "ivivu_blog",
                    "url": url,
                    "title": title,
                    "published_date": published_date,
                    "images": sum(1 for x in downloaded_images if x.get("local_path")),
                    "paths": meta["paths"],
                },
            )

            seen_urls.add(url)
            crawled_count += 1
            print(f"    [ok] Crawled successfully: '{title}' (images: {len(downloaded_images)}, keypoints: {len(keypoints)})", flush=True)

        if stop_crawling:
            break

        if dynamic_max_pages > 0 and page_idx >= dynamic_max_pages:
            break

        page_idx += 1

    print(f"\nDone. New articles crawled: {crawled_count}. Output: {out_dir.as_posix()}", flush=True)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Crawl https://www.ivivu.com/blog")
    p.add_argument("--seed-url", default=DEFAULT_SEED_URL)
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--global-raw-jsonl", default=str(DEFAULT_GLOBAL_RAW_JSONL))
    p.add_argument("--max-pages", type=int, default=50)
    p.add_argument("--max-articles", type=int, default=500)
    p.add_argument("--delay-seconds", type=float, default=0.0)

    p.add_argument(
        "--rebuild-local",
        action="store_true",
        default=False,
        help="Rebuild meta/index/global raw from local HTML files under out_dir/articles.",
    )

    robots = p.add_mutually_exclusive_group()
    robots.add_argument("--respect-robots", action="store_true", default=True)
    robots.add_argument("--no-respect-robots", action="store_false", dest="respect_robots")

    p.add_argument("--resume", action="store_true", default=True)
    p.add_argument("--no-resume", action="store_false", dest="resume")

    p.add_argument("--timeout-seconds", type=float, default=30.0)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_arg_parser().parse_args(argv)

    out_dir = Path(args.out_dir)
    global_raw_jsonl = Path(args.global_raw_jsonl)

    try:
        crawl_ivivu_blog(
            seed_url=args.seed_url,
            out_dir=out_dir,
            max_pages=max(0, args.max_pages),
            max_articles=max(0, args.max_articles),
            delay_seconds=max(0.0, args.delay_seconds),
            respect_robots=bool(args.respect_robots),
            resume=bool(args.resume),
            timeout_seconds=max(1.0, args.timeout_seconds),
            rebuild_local=bool(args.rebuild_local),
            global_raw_jsonl=global_raw_jsonl,
        )
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
