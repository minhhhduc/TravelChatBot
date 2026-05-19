"""Configuration settings for TravelChatBot.

This module contains all configuration constants and paths used throughout
the chatbot application, including database paths, RAG parameters, and
token limits.

Author: TravelChatBot Team
Version: 2.0.0
"""
from pathlib import Path
import os

# Base directory of the project (root of the workspace)
_CURRENT_FILE = Path(__file__).resolve()
BASE_DIR = _CURRENT_FILE.parents[2]
if not (BASE_DIR / "data").exists() and not (BASE_DIR / "pyproject.toml").exists():
    BASE_DIR = _CURRENT_FILE.parents[3]

# Data paths
RAW_JSONL_PATH = BASE_DIR / "data" / "raw" / "raw.jsonl"
PREPROCESSED_JSONL_PATH = BASE_DIR / "data" / "processed" / "preprocessed_data.jsonl"

# Prefer cleaned/preprocessed dataset for ingestion. Fallback to raw if needed.
if PREPROCESSED_JSONL_PATH.exists():
    PROCESSED_DATA_PATH = PREPROCESSED_JSONL_PATH
elif RAW_JSONL_PATH.exists():
    PROCESSED_DATA_PATH = RAW_JSONL_PATH
else:
    PROCESSED_DATA_PATH = BASE_DIR / "processed_data.json"

# Default persistent chroma path (project-local)
if (BASE_DIR / "data" / "chroma_db").exists() or (BASE_DIR / "data").exists():
    CHROMA_DB_PATH = BASE_DIR / "data" / "chroma_db"
else:
    CHROMA_DB_PATH = BASE_DIR / "chroma_db"

# Collection name (use env var to keep backward-compat if needed)
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "travel_spots")

# App mode
APP_MODE = os.getenv("APP_MODE", "travel")

# RAG configuration
MAX_CONTEXT_TOKENS = 4000
MAX_RESULTS = 15
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.5"))
