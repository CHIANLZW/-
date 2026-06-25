"""Poll Douyin reflow API and orchestrate recording, transcription, and summarization."""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

from lib_common import (
    ensure_dirs,
    extract_room_id,
    free_disk_if_needed,
    load_config,
    read_json,
    resolve_base_dir,
    setup_logging,
    utc_now_iso,
    write_json,
)


LIVE_STATUS = 2
ENDED_STATUSES = {4}


class DouyinApiClient:
    """Fetch live room status via reflow API with HTML fallback."""

    def __init__(self, config: dict[str, Any], logger):
        self.config = config
        self.logger = logger
        self.room_id = extract_room_id(config.get("stream_url", ""))
        self.blocked = False
        self.consecutive_failures = 0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.get(
                    "user_agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ),
                "Referer": config.get("stream_url", "https://live.douyin.com/"),
                "Accept": "application/json, text/plain, */*",
            }
        )

    def _timeout(self) -> int:
        return int(self.config.get("request_timeout_seconds", 20))

    def _looks_blocked(self, response: requests.Response | None, exc: Exception | None = None) -> bool:
        if response is not None:
            if response.status_code in {403, 429, 503}:
                return True
            text = (response.text or "").lower()
            if any(token in text for token in ("验证码", "captcha", "blocked", "访问频繁", "risk")):
                return True
        if exc is not None:
            message = str(exc).lower()
            if "403" in message or "429" in message:
                return True
        return False

    def _parse_room_payload(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = payload.get("data") or {}
        room = data.get("room") or data.get("data", [{}])[0] if isinstance(data.get("data"), list) else None
        if room is None and isinstance(data, dict):
            room = data
        if not isinstance(room, dict):
            return None

        status = room.get("status")
        owner = room.get("owner") or {}
        stats = room.get("stats") or room.get("user_count") or {}
        if isinstance(stats, (int, str)):
            stats = {"user_count_str": str(stats)}

        title = room.get("title") or room.get("room_title") or ""
        viewer_count = (
            stats.get("total_user_str")
            or stats.get("user_count_str")
            or stats.get("total_user")
            or room.get("user_count_str")
            or ""
        )

        return {
            "status": int(status) if status is not None else 4,
            "title": title,
            "anchor_name": owner.get("nickname") or self.config.get("streamer_name", ""),
            "viewer_count": str(viewer_count),
            "room_id": str(room.get("id_str") or room.get("id") or self.room_id or ""),
            "raw": room,
        }

    def _fetch_reflow(self) -> dict[str, Any] | None:
        if not self.room_id:
            self.logger.error("无法从 stream_url 解析 room_id: %s", self.config.get("stream_url"))
            return None

        params = {
            "type_id": "0",
            "live_id": "1",
            "room_id": self.room_id,
            "app_id": "6383",
            "version_code": "180800",
            "webcast_sdk_version": "2640",
        }
        url = self.config.get("reflow_api_url", "https://webcast.amemv.com/webcast/room/reflow/info/")
        response = self.session.get(url, params=params, timeout=self._timeout())
        response.raise_for_status()
        payload = response.json()
        if payload.get("status_code") not in (0, None) and "data" not in payload:
            raise RuntimeError(f"reflow API 返回异常: {payload.get('status_code')}")
        return self._parse_room_payload(payload)

    def _fetch_web_enter(self) -> dict[str, Any] | None:
        if not self.room_id:
            return None
        url = self.config.get("fallback_api_url", "https://live.douyin.com/webcast/room/web/enter/")
        params = {"web_rid": self.room_id}
        response = self.session.get(url, params=params, timeout=self._timeout())
        response.raise_for_status()
        payload = response.json()
        return self._parse_room_payload(payload)

    def _fetch_html_fallback(self) -> dict[str, Any] | None:
        if not self.room_id or not self.config.get("use_html_fallback", True):
            return None

        page_url = self.config.get("stream_url") or f"https://live.douyin.com/{self.room_id}"
        response = self.session.get(page_url, timeout=self._timeout())
        response.raise_for_status()
        html = response.text

        import re

        status_match = re.search(r'"status"\s*:\s*(\d+)', html)
        title_match = re.search(r'"title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', html)
        nickname_match = re.search(r'"nickname"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', html)
        viewer_match = re.search(r'"user_count_str"\s*:\s*"([^"]+)"', html)

        status = int(status_match.group(1)) if status_match else 4
        title = title_match.group(1).encode("utf-8").decode("unicode_escape") if title_match else ""
        anchor = nickname_match.group(1).encode("utf-8").decode("unicode_escape") if nickname_match else ""
        viewers = viewer_match.group(1) if viewer_match else ""

        return {
            "status": status,
            "title": title,
            "anchor_name": anchor or self.config.get("streamer_name", ""),
            "viewer_count": viewers,
            "room_id": self.room_id,
            "raw": {"source": "html_fallback"},
        }

    def fetch_room_status(self) -> dict[str, Any] | None:
        retry_count = int(self.config.get("api_retry_count", 3))
        retry_delay = float(self.config.get("api_retry_delay_seconds", 5))
        methods = [
            ("reflow", self._fetch_reflow),
            ("web_enter", self._fetch_web_enter),
            ("html", self._fetch_html_fallback),
        ]

        last_error: Exception | None = None
        for attempt in range(1, retry_count + 1):
            for name, method in methods:
                try:
                    result = method()
                    if result is not None:
                        self.blocked = False
                        self.consecutive_failures = 0
                        return result
                except Exception as exc:  # noqa: BLE001 - aggregate API failures
                    last_error = exc
                    response = getattr(exc, "response", None)
                    if self._looks_blocked(response, exc):
                        self.blocked = True
                        self.logger.warning("API 可能被限制 (%s/%s, %s): %s", attempt, retry_count, name, exc)
                    else:
                        self.logger.warning("API 请求失败 (%s/%s, %s): %s", attempt, retry_count, name, exc)

            if attempt < retry_count:
                time.sleep(retry_delay * attempt)

        self.consecutive_failures += 1
        if last_error:
            self.logger.error("所有 API 尝试均失败: %s", last_error)
        return None


class LivestreamMonitor:
    """Main monitor loop."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_dir = resolve_base_dir(config)
        self.paths = ensure_dirs(self.base_dir)
        self.logger = setup_logging("monitor", self.paths["logs"])
        self.api = DouyinApiClient(config, self.logger)
        self.state_dir = self.paths["state"]
        self.recorder_proc: subprocess.Popen | None = None
        self.live_detected = False
        self.session_file = self.state_dir / "current_session.json"
        self.recorder_pid_file = self.state_dir / "recorder.pid"
        self.stop_flag = self.state_dir / "stop_recording.flag"
        self.done_file = self.base_dir / "DONE.txt"
        self.recorder_restarts = 0
        self.running = True
        self.recorder_was_running = False

    def _python_executable(self) -> str:
        return sys.executable

    def _script_path(self, name: str) -> Path:
        return self.base_dir / name

    def _poll_interval(self) -> float:
        base = float(self.config.get("poll_interval_seconds", 60))
        if not self.api.blocked:
            return base
        multiplier = float(self.config.get("api_blocked_retry_multiplier", 3))
        max_interval = float(self.config.get("api_blocked_max_interval_seconds", 600))
        scaled = base * multiplier * max(1, self.api.consecutive_failures)
        return min(scaled, max_interval)

    def _is_recorder_running(self) -> bool:
        if self.recorder_proc and self.recorder_proc.poll() is None:
            return True

        pid_data = read_json(self.recorder_pid_file)
        if not pid_data:
            return False

        pid = pid_data.get("pid")
        if not pid:
            return False

        try:
            if sys.platform == "win32":
                import ctypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return True
                return False

            import os

            os.kill(int(pid), 0)
            return True
        except (OSError, AttributeError, ValueError):
            return False

    def _start_recorder(self, room_info: dict[str, Any]) -> None:
        if self._is_recorder_running():
            self.logger.info("录音进程已在运行，跳过启动")
            return

        session = read_json(self.session_file) or {}
        if not session.get("session_id"):
            session = {
                "session_id": time.strftime("%Y%m%d_%H%M%S"),
                "started_at": utc_now_iso(),
                "room_id": room_info.get("room_id"),
                "title": room_info.get("title"),
                "anchor_name": room_info.get("anchor_name"),
                "viewer_count_at_start": room_info.get("viewer_count"),
            }
            write_json(self.session_file, session)

        if self.stop_flag.exists():
            self.stop_flag.unlink(missing_ok=True)

        cmd = [
            self._python_executable(),
            str(self._script_path("audio_recorder.py")),
            "--session-id",
            session["session_id"],
        ]
        self.logger.info("启动录音: %s", " ".join(cmd))
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        self.recorder_proc = subprocess.Popen(
            cmd,
            cwd=str(self.base_dir),
            creationflags=creationflags,
        )
        write_json(self.recorder_pid_file, {"pid": self.recorder_proc.pid, "started_at": utc_now_iso()})

    def _maybe_restart_recorder(self, room_info: dict[str, Any]) -> None:
        if self._is_recorder_running():
            return

        max_restarts = int(self.config.get("recorder_max_restarts", 5))
        if self.recorder_restarts >= max_restarts:
            self.logger.error("录音进程重启次数过多 (%s)，暂停自动重启", max_restarts)
            return

        if self.recorder_restarts > 0:
            delay = float(self.config.get("recorder_restart_delay_seconds", 10))
            self.logger.warning("录音进程崩溃，%ss 后重启 (#%s)", delay, self.recorder_restarts)
            time.sleep(delay)

        self._start_recorder(room_info)

    def _ensure_recorder(self, room_info: dict[str, Any]) -> None:
        running = self._is_recorder_running()
        if running:
            self.recorder_was_running = True
            return

        if self.recorder_was_running:
            self.recorder_restarts += 1
            self.logger.warning("录音进程意外退出 (restart_count=%s)", self.recorder_restarts)

        self._maybe_restart_recorder(room_info)
        self.recorder_was_running = self._is_recorder_running()

    def _stop_recorder(self) -> None:
        self.stop_flag.write_text("stop\n", encoding="utf-8")
        if self.recorder_proc and self.recorder_proc.poll() is None:
            try:
                self.recorder_proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.logger.warning("录音进程未在 30s 内退出，强制终止")
                self.recorder_proc.terminate()
                try:
                    self.recorder_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.recorder_proc.kill()

        deadline = time.time() + 45
        while time.time() < deadline and self._is_recorder_running():
            time.sleep(1)

        self.recorder_proc = None
        self.recorder_pid_file.unlink(missing_ok=True)

    def _run_subprocess(self, script: str, extra_args: list[str] | None = None) -> int:
        cmd = [self._python_executable(), str(self._script_path(script))]
        if extra_args:
            cmd.extend(extra_args)
        self.logger.info("执行: %s", " ".join(cmd))
        result = subprocess.run(cmd, cwd=str(self.base_dir))
        if result.returncode != 0:
            self.logger.error("%s 退出码: %s", script, result.returncode)
        return result.returncode

    def _handle_live(self, room_info: dict[str, Any]) -> None:
        if not self.live_detected:
            self.logger.info(
                "检测到直播: title=%s anchor=%s viewers=%s",
                room_info.get("title"),
                room_info.get("anchor_name"),
                room_info.get("viewer_count"),
            )
            self.live_detected = True
            self.recorder_restarts = 0

        session = read_json(self.session_file) or {}
        session.update(
            {
                "last_seen_live_at": utc_now_iso(),
                "title": room_info.get("title") or session.get("title"),
                "anchor_name": room_info.get("anchor_name") or session.get("anchor_name"),
                "viewer_count_latest": room_info.get("viewer_count"),
            }
        )
        write_json(self.session_file, session)

        removed = free_disk_if_needed(self.base_dir, self.config)
        if removed:
            self.logger.warning("磁盘空间不足，已删除 %s 个旧录音", len(removed))

        self._ensure_recorder(room_info)

    def _handle_ended(self, room_info: dict[str, Any] | None) -> None:
        if not self.live_detected:
            return

        self.logger.info("检测到直播结束，开始收尾流程")
        self._stop_recorder()

        session = read_json(self.session_file) or {}
        session.update(
            {
                "ended_at": utc_now_iso(),
                "title": (room_info or {}).get("title") or session.get("title"),
                "anchor_name": (room_info or {}).get("anchor_name") or session.get("anchor_name"),
                "viewer_count_at_end": (room_info or {}).get("viewer_count"),
            }
        )
        write_json(self.session_file, session)
        write_json(self.paths["output"] / "session_snapshot.json", session)

        self._run_subprocess("transcriber.py", ["--session-id", session.get("session_id", "")])
        self._run_subprocess("summarizer.py", ["--session-id", session.get("session_id", "")])

        self.done_file.write_text(
            f"DONE\nsession_id={session.get('session_id')}\nfinished_at={utc_now_iso()}\n",
            encoding="utf-8",
        )
        self.logger.info("流程完成，已写入 DONE.txt")

        self.live_detected = False
        self.recorder_was_running = False
        self.session_file.unlink(missing_ok=True)

    def _handle_room_info(self, room_info: dict[str, Any]) -> None:
        status = int(room_info.get("status", 4))
        if status == LIVE_STATUS:
            self._handle_live(room_info)
        elif self.live_detected and status in ENDED_STATUSES:
            self._handle_ended(room_info)

    def run(self) -> None:
        self.logger.info("监控启动 base_dir=%s room_id=%s", self.base_dir, self.api.room_id)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        while self.running:
            room_info = self.api.fetch_room_status()
            if room_info is None:
                if self.api.blocked:
                    self.logger.warning("API 受限，将在更长间隔后重试")
                if self.live_detected:
                    session = read_json(self.session_file) or {}
                    self._ensure_recorder(
                        {
                            "room_id": session.get("room_id"),
                            "title": session.get("title"),
                            "anchor_name": session.get("anchor_name"),
                            "viewer_count": session.get("viewer_count_latest"),
                        }
                    )
            else:
                self._handle_room_info(room_info)

            time.sleep(self._poll_interval())

        self.logger.info("监控已停止")
        if self.live_detected:
            self._stop_recorder()

    def _signal_handler(self, signum, _frame) -> None:
        self.logger.info("收到信号 %s，准备退出", signum)
        self.running = False


def main() -> int:
    parser = argparse.ArgumentParser(description="Douyin livestream monitor")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    monitor = LivestreamMonitor(config)
    monitor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
