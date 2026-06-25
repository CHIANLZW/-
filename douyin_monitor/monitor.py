#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Douyin livestream monitor — polls room status via HTTP, triggers summarizer on end."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(os.environ.get("DOUYIN_MONITOR_DIR", "D:/mimocod/douyin_monitor"))
DEFAULT_STREAM_URL = "https://v.douyin.com/15okSWnYiYs/"
DEFAULT_STREAMER = "四川低空百事通 老郭"
POLL_INTERVAL_SEC = 60
LIVE_STATUS_CODE = 2

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

STATUS_FILE = "monitor_status.json"
SESSION_FILE = "stream_session.json"
PID_FILE = "monitor.pid"
LOG_DIR_NAME = "logs"

# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_output_dir(output_dir: Path | None = None) -> Path:
    base = output_dir or OUTPUT_DIR
    base.mkdir(parents=True, exist_ok=True)
    (base / LOG_DIR_NAME).mkdir(parents=True, exist_ok=True)
    (base / "transcripts").mkdir(parents=True, exist_ok=True)
    return base


def setup_logging(output_dir: Path) -> logging.Logger:
    log_path = output_dir / LOG_DIR_NAME / "monitor.log"
    logger = logging.getLogger("douyin_monitor")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default or {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def resolve_short_url(url: str) -> str:
    """Follow redirects and return the final URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.geturl()


def parse_room_from_url(url: str) -> tuple[str, str]:
    """Extract room_id and sec_user_id from a Douyin share/reflow URL."""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)

    room_id = ""
    sec_user_id = ""

    reflow_match = re.search(r"/reflow/(\d+)", parsed.path)
    if reflow_match:
        room_id = reflow_match.group(1)

    if "sec_user_id" in query:
        sec_user_id = query["sec_user_id"][0]

    if not room_id:
        live_match = re.search(r"live\.douyin\.com/([^/?#]+)", url)
        if live_match:
            room_id = live_match.group(1)

    if not room_id or not sec_user_id:
        raise ValueError(f"无法从链接解析 room_id/sec_user_id: {url}")

    return room_id, sec_user_id


def fetch_room_info(room_id: str, sec_user_id: str) -> dict[str, Any]:
    """Query Douyin reflow API — no auth token, minimal HTTP cost."""
    params = urllib.parse.urlencode(
        {
            "type_id": "0",
            "live_id": "1",
            "room_id": room_id,
            "sec_user_id": sec_user_id,
            "version_code": "99.99.99",
            "app_id": "1128",
        }
    )
    api_url = f"https://webcast.amemv.com/webcast/room/reflow/info/?{params}"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://live.douyin.com/",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    raw = http_get(api_url, headers=headers)
    payload = json.loads(raw.decode("utf-8"))
    room = payload.get("data", {}).get("room")
    if not room:
        raise RuntimeError(f"API 未返回房间数据: {payload.get('status_code', 'unknown')}")
    return room


def room_status_label(status_code: int) -> str:
    if status_code == LIVE_STATUS_CODE:
        return "LIVE"
    return "ENDED"


def format_ts(ts: int | None) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return None


def build_snapshot(room: dict[str, Any], stream_url: str, streamer: str) -> dict[str, Any]:
    status_code = int(room.get("status", 0))
    owner = room.get("owner") or {}
    stats = room.get("stats") or {}
    return {
        "checked_at": utc_now_iso(),
        "status": room_status_label(status_code),
        "status_code": status_code,
        "room_id": str(room.get("id_str") or room.get("id") or ""),
        "title": room.get("title") or "",
        "streamer": owner.get("nickname") or streamer,
        "viewer_count": room.get("user_count") or stats.get("total_user") or 0,
        "like_count": stats.get("like_count") or 0,
        "create_time": format_ts(room.get("create_time")),
        "finish_time": format_ts(room.get("finish_time")),
        "share_url": room.get("share_url") or stream_url,
    }


def update_session(session: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Accumulate session metadata while the stream is live."""
    if snapshot["status"] != "LIVE":
        return session

    if not session.get("started_at"):
        session["started_at"] = snapshot.get("create_time") or snapshot["checked_at"]
        session["first_live_detected_at"] = snapshot["checked_at"]

    session["last_live_at"] = snapshot["checked_at"]
    session["title"] = snapshot.get("title") or session.get("title", "")
    session["streamer"] = snapshot.get("streamer") or session.get("streamer", "")
    session["room_id"] = snapshot.get("room_id") or session.get("room_id", "")
    session["share_url"] = snapshot.get("share_url") or session.get("share_url", "")

    viewer = int(snapshot.get("viewer_count") or 0)
    session["peak_viewer_count"] = max(int(session.get("peak_viewer_count") or 0), viewer)
    session["last_viewer_count"] = viewer

    polls = session.get("polls") or []
    polls.append(
        {
            "at": snapshot["checked_at"],
            "viewers": viewer,
            "title": snapshot.get("title", ""),
        }
    )
    session["polls"] = polls[-120:]
    return session


def trigger_summarizer(output_dir: Path, logger: logging.Logger) -> None:
    script = Path(__file__).resolve().parent / "summarizer.py"
    if not script.exists():
        logger.error("未找到 summarizer.py，跳过摘要生成")
        return

    logger.info("直播已结束，启动 summarizer …")
    env = os.environ.copy()
    env["DOUYIN_MONITOR_DIR"] = str(output_dir)
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(script.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.stdout.strip():
            logger.info(result.stdout.strip())
        if result.returncode != 0:
            logger.error("summarizer 退出码 %s: %s", result.returncode, result.stderr.strip())
        else:
            logger.info("会议纪要已生成")
    except subprocess.TimeoutExpired:
        logger.error("summarizer 超时（600s）")
    except OSError as exc:
        logger.error("无法启动 summarizer: %s", exc)


def write_pid(output_dir: Path) -> None:
    save_json(output_dir / PID_FILE, {"pid": os.getpid(), "started_at": utc_now_iso()})


def read_pid(output_dir: Path) -> int | None:
    data = load_json(output_dir / PID_FILE)
    pid = data.get("pid")
    return int(pid) if pid else None


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def print_status(output_dir: Path) -> int:
    status = load_json(output_dir / STATUS_FILE)
    if not status:
        print(f"未找到状态文件: {output_dir / STATUS_FILE}")
        return 1

    print("=" * 50)
    print("抖音直播监控状态")
    print("=" * 50)
    print(f"输出目录 : {output_dir}")
    print(f"主播     : {status.get('streamer', '-')}")
    print(f"标题     : {status.get('title', '-')}")
    print(f"状态     : {status.get('status', '-')}")
    print(f"上次检查 : {status.get('last_check', '-')}")
    print(f"轮询间隔 : {status.get('poll_interval_sec', POLL_INTERVAL_SEC)} 秒")
    print(f"监控链接 : {status.get('stream_url', '-')}")

    pid = read_pid(output_dir)
    if pid and is_process_running(pid):
        print(f"守护进程 : 运行中 (PID {pid})")
    else:
        print("守护进程 : 未运行")

    if status.get("ended_at"):
        print(f"下播时间 : {status.get('ended_at')}")
    if status.get("summarizer_triggered_at"):
        print(f"摘要生成 : {status.get('summarizer_triggered_at')}")
    print("=" * 50)
    return 0


def monitor_loop(
    stream_url: str,
    streamer: str,
    output_dir: Path,
    poll_interval: int,
    logger: logging.Logger,
    run_once: bool = False,
) -> None:
    status_path = output_dir / STATUS_FILE
    session_path = output_dir / SESSION_FILE

    logger.info("解析直播链接: %s", stream_url)
    final_url = resolve_short_url(stream_url)
    room_id, sec_user_id = parse_room_from_url(final_url)
    logger.info("room_id=%s streamer=%s", room_id, streamer)

    status = load_json(status_path, {})
    session = load_json(session_path, {})

    status.update(
        {
            "stream_url": stream_url,
            "resolved_url": final_url,
            "room_id": room_id,
            "sec_user_id": sec_user_id,
            "streamer": streamer,
            "poll_interval_sec": poll_interval,
            "monitor_started_at": status.get("monitor_started_at") or utc_now_iso(),
        }
    )

    previous_status = status.get("status")
    summarizer_done = bool(status.get("summarizer_triggered_at"))

    while True:
        try:
            room = fetch_room_info(room_id, sec_user_id)
            snapshot = build_snapshot(room, stream_url, streamer)
            current_status = snapshot["status"]

            status.update(snapshot)
            status["last_check"] = snapshot["checked_at"]
            status["error"] = None

            if current_status == "LIVE":
                session = update_session(session, snapshot)
                save_json(session_path, session)
                logger.info(
                    "直播中 | 标题: %s | 观众: %s",
                    snapshot.get("title", "-"),
                    snapshot.get("viewer_count", 0),
                )
            else:
                logger.info("直播未进行 (status=%s)", snapshot.get("status_code"))

            if previous_status == "LIVE" and current_status == "ENDED":
                ended_at = utc_now_iso()
                status["ended_at"] = ended_at
                session["ended_at"] = ended_at
                session["ended_detected_at"] = ended_at
                save_json(session_path, session)
                logger.info("检测到直播结束: %s", ended_at)

                if not summarizer_done:
                    trigger_summarizer(output_dir, logger)
                    status["summarizer_triggered_at"] = utc_now_iso()
                    summarizer_done = True

            previous_status = current_status
            save_json(status_path, status)

        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
            logger.warning("轮询失败: %s", exc)
            status["last_check"] = utc_now_iso()
            status["error"] = str(exc)
            save_json(status_path, status)

        if run_once:
            break
        time.sleep(poll_interval)


def daemonize(output_dir: Path, logger: logging.Logger) -> None:
    existing = read_pid(output_dir)
    if existing and is_process_running(existing):
        logger.info("监控已在运行 (PID %s)", existing)
        return

    write_pid(output_dir)
    logger.info("守护进程已启动 PID=%s", os.getpid())


def main() -> int:
    parser = argparse.ArgumentParser(description="Douyin 直播监控")
    parser.add_argument("--url", default=DEFAULT_STREAM_URL, help="抖音直播分享链接")
    parser.add_argument("--streamer", default=DEFAULT_STREAMER, help="主播名称（展示用）")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL_SEC, help="轮询间隔（秒）")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="输出目录")
    parser.add_argument("--daemon", action="store_true", help="后台守护进程模式")
    parser.add_argument("--once", action="store_true", help="仅检查一次")
    parser.add_argument("--status", action="store_true", help="显示当前监控状态")
    args = parser.parse_args()

    output_dir = Path(args.output)
    ensure_output_dir(output_dir)
    logger = setup_logging(output_dir)

    if args.status:
        return print_status(output_dir)

    if args.daemon:
        daemonize(output_dir, logger)

    monitor_loop(
        stream_url=args.url,
        streamer=args.streamer,
        output_dir=output_dir,
        poll_interval=args.interval,
        logger=logger,
        run_once=args.once,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
