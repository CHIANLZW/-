"""Shared helpers for the Douyin livestream monitor."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or (script_dir() / "config.json")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_base_dir(config: dict[str, Any]) -> Path:
    configured = config.get("base_dir")
    if configured:
        candidate = Path(configured)
        if candidate.exists():
            return candidate.resolve()
    return script_dir()


def ensure_dirs(base_dir: Path) -> dict[str, Path]:
    paths = {
        "base": base_dir,
        "recordings": base_dir / "recordings",
        "logs": base_dir / "logs",
        "state": base_dir / "state",
        "output": base_dir / "output",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def setup_logging(name: str, logs_dir: Path, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_file = logs_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(path)


def extract_room_id(stream_url: str) -> str | None:
    if not stream_url:
        return None
    match = re.search(r"live\.douyin\.com/(\d+)", stream_url)
    if match:
        return match.group(1)
    match = re.search(r"(\d{6,})", stream_url)
    return match.group(1) if match else None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def disk_free_mb(path: Path) -> float:
    try:
        usage = os.statvfs(path) if hasattr(os, "statvfs") else None
        if usage:
            free = usage.f_bavail * usage.f_frsize
            return free / (1024 * 1024)
    except OSError:
        pass

    try:
        import shutil

        total, used, free = shutil.disk_usage(path)
        return free / (1024 * 1024)
    except OSError:
        return float("inf")


def prune_old_recordings(recordings_dir: Path, keep: int) -> list[Path]:
    files = sorted(
        recordings_dir.glob("*.wav"),
        key=lambda p: p.stat().st_mtime,
    )
    removed: list[Path] = []
    while len(files) > keep:
        oldest = files.pop(0)
        try:
            oldest.unlink()
            removed.append(oldest)
        except OSError:
            pass
    return removed


def free_disk_if_needed(base_dir: Path, config: dict[str, Any]) -> list[Path]:
    min_mb = float(config.get("min_disk_space_mb", 500))
    keep = int(config.get("max_recording_files_to_keep", 50))
    recordings_dir = base_dir / "recordings"
    removed: list[Path] = []

    while disk_free_mb(recordings_dir) < min_mb:
        wav_files = sorted(recordings_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        if not wav_files:
            break
        try:
            wav_files[0].unlink()
            removed.append(wav_files[0])
        except OSError:
            break

    removed.extend(prune_old_recordings(recordings_dir, keep))
    return removed
