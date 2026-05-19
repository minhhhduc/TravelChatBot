"""Preprocess TravelChatBot raw JSONL into a cleaner, project-friendly JSONL.

Input (default): data/raw/raw.jsonl
Output (default): data/processed/preprocessed_data.jsonl

Why this exists
--------------
The crawler stores articles as JSON Lines where each article has a list of
`keypoint` sections. For RAG / ChromaDB ingestion, it is usually better to
index each keypoint as a separate document with normalized text + metadata.

This script supports two output formats:

1) format=article (DEFAULT)
	 - Keeps the same high-level schema as the crawler output: 1 JSON object per
		 article, with a `keypoint` list.
	 - Cleans titles/contexts but preserves image markers by re-attaching them as
		 `[img] <path> [img]` blocks (so existing ingestion can still extract
		 images).
	 - Enriches `url` by joining with `data/raw/ivivu_blog/index.jsonl` if present.
	 - Adds `destination` (inferred) so downstream can filter/sort more easily.

2) format=spot
	 - Flattens each keypoint into a single "spot" line (one object per keypoint).
	 - Useful for analysis, training, or a future ingestion flow.

For format=article, each line is an article with keys:
	title, time, url, destination, keypoint=[{idx:{idx,title,context}, evaluate:{...}}], source

For format=spot, each line (spot) has keys:
	id, title, context, destination, time, time_str,
	evaluate_mean, evaluate_count, images, url,
	article_title, keypoint_title, keypoint_idx, source

Usage
-----
	python processer/preprocessing.py \
		--format article \
		--input data/raw/raw.jsonl \
		--output data/processed/preprocessed_data.jsonl \
		--stats-out data/features/metadata.json

	# Optional: flattened spots
	python processer/preprocessing.py \
		--format spot \
		--input data/raw/raw.jsonl \
		--output data/processed/preprocessed_spots.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional


def _ensure_repo_root_on_syspath() -> None:
	"""Allow running as a script: `python processer/preprocessing.py ...`.

	When executed as a script, Python puts `.../processer` on sys.path, not the repo
	root, so `import processer.*` would fail. We insert the repo root.
	"""
	repo_root = Path(__file__).resolve().parents[1]
	repo_root_str = str(repo_root)
	if repo_root_str not in sys.path:
		sys.path.insert(0, repo_root_str)


try:
	# Module execution: `python -m processer.preprocessing`
	from .pipeline import preprocess_raw_to_articles, preprocess_raw_to_spots
except Exception:
	# Script execution: `python processer/preprocessing.py`
	_ensure_repo_root_on_syspath()
	from processer.pipeline import preprocess_raw_to_articles, preprocess_raw_to_spots


def build_arg_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(description="Preprocess raw.jsonl into preprocessed_data.jsonl")
	p.add_argument(
		"--format",
		default="article",
		choices=["article", "spot"],
		help="Output format: 'article' (compatible with current ingestion) or 'spot' (flattened)",
	)
	p.add_argument(
		"--input",
		default="data/raw/raw.jsonl",
		help="Input raw JSONL path (default: data/raw/raw.jsonl)",
	)
	p.add_argument(
		"--output",
		default="data/processed/preprocessed_data.jsonl",
		help="Output preprocessed JSONL path (default: data/processed/preprocessed_data.jsonl)",
	)
	p.add_argument(
		"--stats-out",
		default="",
		help="Optional metadata/stats output JSON path (e.g. data/features/metadata.json)",
	)
	p.add_argument(
		"--ivivu-index",
		default="data/raw/ivivu_blog/index.jsonl",
		help="Optional ivivu index.jsonl path for url enrichment (default: data/raw/ivivu_blog/index.jsonl)",
	)
	p.add_argument(
		"--max-articles",
		type=int,
		default=0,
		help="For debugging: stop after N articles (0 = all)",
	)
	p.add_argument(
		"--max-errors",
		type=int,
		default=10_000,
		help="Stop if JSON parse errors exceed this number",
	)
	return p


def main(argv: Optional[List[str]] = None) -> int:
	args = build_arg_parser().parse_args(argv)

	input_path = Path(args.input)
	output_path = Path(args.output)
	stats_out = Path(args.stats_out) if args.stats_out else None
	max_articles = args.max_articles if args.max_articles and args.max_articles > 0 else None

	ivivu_index_path = Path(args.ivivu_index) if args.ivivu_index else None
	if ivivu_index_path and not ivivu_index_path.exists():
		ivivu_index_path = None

	if not input_path.exists():
		print(f"[error] Input not found: {input_path}")
		return 2

	if args.format == "spot":
		stats = preprocess_raw_to_spots(
			input_path=input_path,
			output_path=output_path,
			max_articles=max_articles,
			max_errors=args.max_errors,
			stats_out=stats_out,
		)
		print(
			"[done] "
			+ f"format=spot articles={stats.articles} spots={stats.spots} "
			+ f"skipped_articles={stats.skipped_articles} skipped_spots={stats.skipped_spots} "
			+ f"json_errors={stats.json_errors}"
		)
	else:
		stats = preprocess_raw_to_articles(
			input_path=input_path,
			output_path=output_path,
			max_articles=max_articles,
			max_errors=args.max_errors,
			stats_out=stats_out,
			ivivu_index_path=ivivu_index_path,
		)
		print(
			"[done] "
			+ f"format=article articles={stats.articles} keypoints={stats.spots} "
			+ f"skipped_articles={stats.skipped_articles} skipped_keypoints={stats.skipped_spots} "
			+ f"json_errors={stats.json_errors} url_enrich={'on' if ivivu_index_path else 'off'}"
		)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

