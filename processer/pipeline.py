from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .destination import infer_destination_from_title
from .ivivu_index import load_ivivu_index_map
from .jsonl_utils import iter_jsonl
from .text_cleaning import extract_images_and_strip, normalize_text, reattach_images, simplify_title


@dataclass
class PreprocessStats:
    articles: int = 0
    spots: int = 0
    skipped_articles: int = 0
    skipped_spots: int = 0
    json_errors: int = 0
    destinations: Counter = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.destinations is None:
            self.destinations = Counter()


def parse_iso_date_to_epoch(date_str: str) -> Tuple[Optional[float], str]:
    """Parse common date formats into epoch seconds and normalized date string."""
    from datetime import datetime

    if not isinstance(date_str, str):
        return None, ""
    s = date_str.strip()
    if not s:
        return None, ""

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt in ("%Y-%m", "%Y/%m"):
                dt = dt.replace(day=1)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp(), dt.date().isoformat()
        except Exception:
            continue

    try:
        v = float(s)
        if v > 10_000_000_000:
            v = v / 1000.0
        dt = datetime.fromtimestamp(v, tz=timezone.utc)
        return float(v), dt.date().isoformat()
    except Exception:
        return None, s


def preprocess_raw_to_spots(
    input_path: Path,
    output_path: Path,
    *,
    max_articles: Optional[int] = None,
    max_errors: int = 10_000,
    stats_out: Optional[Path] = None,
    source_name: str = "ivivu_blog",
) -> PreprocessStats:
    """Flatten each keypoint into one spot record (one JSON per keypoint)."""
    stats = PreprocessStats()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_out:
        stats_out.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out:
        for line_no, article in iter_jsonl(input_path):
            if max_articles is not None and stats.articles >= max_articles:
                break

            if article.get("__parse_error__"):
                stats.json_errors += 1
                if stats.json_errors <= 5:
                    print(f"[warn] JSON parse error at line {line_no}, skipping")
                if stats.json_errors >= max_errors:
                    print(f"[error] Too many JSON errors (>= {max_errors}). Stop.")
                    break
                continue

            stats.articles += 1
            raw_title = article.get("title", "")
            article_title = simplify_title(raw_title)
            url = article.get("url") or article.get("URL") or ""

            epoch, time_str = parse_iso_date_to_epoch(str(article.get("time", "") or ""))
            destination = infer_destination_from_title(article_title)
            if destination:
                stats.destinations[destination] += 1

            keypoints = article.get("keypoint") or []
            if not isinstance(keypoints, list) or not keypoints:
                stats.skipped_articles += 1
                continue

            for kp in keypoints:
                try:
                    idx_info = (kp or {}).get("idx") or {}
                    kp_idx = int(idx_info.get("idx") or 0)
                    kp_title = normalize_text(str(idx_info.get("title") or "")).strip()
                    kp_context_raw = str(idx_info.get("context") or "")
                    images, kp_context = extract_images_and_strip(kp_context_raw)

                    if not kp_context:
                        stats.skipped_spots += 1
                        continue

                    evaluate = (kp or {}).get("evaluate") or {}
                    evaluate_mean = float(evaluate.get("mean") or 0.0)
                    items = evaluate.get("items") or []
                    evaluate_count = int(len(items)) if isinstance(items, list) else 0

                    spot_title = kp_title or article_title

                    spot_id = f"{line_no}_keypoint_{kp_idx or 0}"
                    out_obj = {
                        "id": spot_id,
                        "title": spot_title,
                        "context": kp_context,
                        "destination": destination,
                        "time": epoch if epoch is not None else 0.0,
                        "time_str": time_str,
                        "evaluate_mean": evaluate_mean,
                        "evaluate_count": evaluate_count,
                        "images": images,
                        "url": url,
                        "article_title": article_title,
                        "keypoint_title": kp_title,
                        "keypoint_idx": kp_idx,
                        "source": source_name,
                    }

                    out.write(json.dumps(out_obj, ensure_ascii=False) + "\n")
                    stats.spots += 1
                except Exception:
                    stats.skipped_spots += 1
                    continue

            if stats.articles % 200 == 0:
                print(f"[info] articles={stats.articles} spots={stats.spots} skipped_spots={stats.skipped_spots}")

    if stats_out:
        top_dest = stats.destinations.most_common(50)
        meta = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input": str(input_path.as_posix()),
            "output": str(output_path.as_posix()),
            "format": "spot",
            "articles": stats.articles,
            "spots": stats.spots,
            "skipped_articles": stats.skipped_articles,
            "skipped_spots": stats.skipped_spots,
            "json_errors": stats.json_errors,
            "top_destinations": [{"destination": k, "count": v} for k, v in top_dest],
        }
        stats_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return stats


def preprocess_raw_to_articles(
    input_path: Path,
    output_path: Path,
    *,
    max_articles: Optional[int] = None,
    max_errors: int = 10_000,
    stats_out: Optional[Path] = None,
    source_name: str = "ivivu_blog",
    ivivu_index_path: Optional[Path] = None,
) -> PreprocessStats:
    """Produce article-compatible JSONL that current ingestion can consume."""
    stats = PreprocessStats()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_out:
        stats_out.parent.mkdir(parents=True, exist_ok=True)

    title_to_index = load_ivivu_index_map(ivivu_index_path) if ivivu_index_path else {}

    with output_path.open("w", encoding="utf-8") as out:
        for line_no, article in iter_jsonl(input_path):
            if max_articles is not None and stats.articles >= max_articles:
                break

            if article.get("__parse_error__"):
                stats.json_errors += 1
                if stats.json_errors <= 5:
                    print(f"[warn] JSON parse error at line {line_no}, skipping")
                if stats.json_errors >= max_errors:
                    print(f"[error] Too many JSON errors (>= {max_errors}). Stop.")
                    break
                continue

            stats.articles += 1
            raw_title = article.get("title", "")
            article_title = simplify_title(raw_title)
            destination = infer_destination_from_title(article_title)
            if destination:
                stats.destinations[destination] += 1

            idx_meta = title_to_index.get(article_title, {})
            url = str(article.get("url") or article.get("URL") or idx_meta.get("url") or "")
            time_value = str(article.get("time") or idx_meta.get("published_date") or "")

            keypoints_in = article.get("keypoint") or []
            if not isinstance(keypoints_in, list) or not keypoints_in:
                stats.skipped_articles += 1
                continue

            keypoints_out: List[Dict[str, Any]] = []
            for kp in keypoints_in:
                try:
                    idx_info = (kp or {}).get("idx") or {}
                    kp_idx = int(idx_info.get("idx") or 0)
                    kp_title = normalize_text(str(idx_info.get("title") or "")).strip()

                    context_raw = str(idx_info.get("context") or "")
                    images, text_wo_images = extract_images_and_strip(context_raw)
                    context_clean = reattach_images(text_wo_images, images)
                    if not context_clean:
                        stats.skipped_spots += 1
                        continue

                    evaluate = (kp or {}).get("evaluate") or {}
                    mean = evaluate.get("mean")
                    items = evaluate.get("items")
                    try:
                        mean_f = float(mean) if mean is not None else 0.0
                    except Exception:
                        mean_f = 0.0
                    if not isinstance(items, list):
                        items = []

                    keypoints_out.append(
                        {
                            "idx": {
                                "idx": kp_idx,
                                "title": kp_title,
                                "context": context_clean,
                            },
                            "evaluate": {
                                "mean": mean_f,
                                "items": items,
                            },
                        }
                    )
                    stats.spots += 1
                except Exception:
                    stats.skipped_spots += 1
                    continue

            if not keypoints_out:
                stats.skipped_articles += 1
                continue

            out_obj: Dict[str, Any] = {
                "title": article_title,
                "time": time_value,
                "url": url,
                "destination": destination,
                "keypoint": keypoints_out,
                "source": source_name,
            }
            out.write(json.dumps(out_obj, ensure_ascii=False) + "\n")

            if stats.articles % 200 == 0:
                print(f"[info] articles={stats.articles} keypoints={stats.spots} skipped_kp={stats.skipped_spots}")

    if stats_out:
        top_dest = stats.destinations.most_common(50)
        meta = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input": str(input_path.as_posix()),
            "output": str(output_path.as_posix()),
            "format": "article",
            "articles": stats.articles,
            "keypoints": stats.spots,
            "skipped_articles": stats.skipped_articles,
            "skipped_keypoints": stats.skipped_spots,
            "json_errors": stats.json_errors,
            "top_destinations": [{"destination": k, "count": v} for k, v in top_dest],
        }
        stats_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return stats
