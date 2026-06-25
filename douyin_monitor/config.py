"""Simple configuration for Douyin live monitor."""

import os
from pathlib import Path

# Output root (Windows default per project spec)
OUTPUT_DIR = Path(os.environ.get("DOUYIN_OUTPUT_DIR", "D:/mimocod/douyin_monitor"))
RECORDINGS_DIR = OUTPUT_DIR / "recordings"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
MEETING_MINUTES_PATH = OUTPUT_DIR / "meeting_minutes.md"

# Douyin live room to monitor (numeric room id from live.douyin.com URL)
ROOM_ID = os.environ.get("DOUYIN_ROOM_ID", "")

# Poll interval when waiting for live / while live
CHECK_INTERVAL_SEC = int(os.environ.get("DOUYIN_CHECK_INTERVAL", "30"))

# Local transcription (zero API cost)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")  # tiny | base
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

# Summarization (single API call only)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
SUMMARIZER_MODEL = os.environ.get("SUMMARIZER_MODEL", "gpt-4o-mini")

# Max characters sent to summarizer (token saving)
MAX_TRANSCRIPT_CHARS = int(os.environ.get("MAX_TRANSCRIPT_CHARS", "6000"))
KEY_CHUNK_COUNT = int(os.environ.get("KEY_CHUNK_COUNT", "12"))

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def ensure_dirs() -> None:
    """Create output directories if missing."""
    for path in (OUTPUT_DIR, RECORDINGS_DIR, TRANSCRIPTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
