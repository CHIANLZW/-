"""Monitor Douyin live status and orchestrate record -> transcribe -> summarize."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

import config

SCRIPT_DIR = Path(__file__).resolve().parent
RECORDER_SCRIPT = SCRIPT_DIR / "recorder.py"
TRANSCRIBER_SCRIPT = SCRIPT_DIR / "transcriber.py"
SUMMARIZER_SCRIPT = SCRIPT_DIR / "summarizer.py"


def decode_json_string(value: str) -> str:
    """Decode JSON-style escaped strings from Douyin page payloads."""
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


class LiveMonitor:
    """Poll Douyin room; start/stop recorder; run post-processing pipeline."""

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id.strip()
        self.recorder_proc: subprocess.Popen | None = None
        self.current_wav: Path | None = None
        self.live_title: str | None = None
        self.was_live = False

    def check_live(self) -> tuple[bool, str | None]:
        """Return (is_live, title). Uses web page + enter API fallback."""
        if not self.room_id:
            return False, None

        title: str | None = None
        is_live = False

        # Primary: live page HTML
        try:
            url = f"https://live.douyin.com/{self.room_id}"
            resp = requests.get(url, headers=config.REQUEST_HEADERS, timeout=15)
            text = resp.text

            title_match = re.search(r'"title"\s*:\s*"([^"\\]+)"', text)
            if title_match:
                title = title_match.group(1).encode("utf-8").decode("unicode_escape", errors="ignore")

            # status 2 = broadcasting; Living string also appears when live
            if re.search(r'"status"\s*:\s*2\b', text) or '"Living"' in text:
                is_live = True
            elif re.search(r'"room_status"\s*:\s*0\b', text) and '"stream_url"' in text:
                is_live = True
        except requests.RequestException as exc:
            print(f"[monitor] Page check failed: {exc}", flush=True)

        # Fallback: webcast enter API
        if not is_live:
            try:
                api_url = (
                    "https://live.douyin.com/webcast/room/web/enter/"
                    f"?aid=6383&live_id=1&device_platform=web&room_id={self.room_id}"
                )
                resp = requests.get(api_url, headers=config.REQUEST_HEADERS, timeout=15)
                data = resp.json()
                room = data.get("data", {}).get("data", [{}])
                room_info = room[0] if isinstance(room, list) and room else data.get("data", {})
                status = room_info.get("status") or room_info.get("room_status")
                if status in (2, 0):
                    is_live = True
                if not title:
                    title = room_info.get("title")
            except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as exc:
                print(f"[monitor] API check failed: {exc}", flush=True)

        return is_live, title

    def start_recording(self) -> None:
        """Launch recorder.py as subprocess."""
        if self.recorder_proc and self.recorder_proc.poll() is None:
            return

        config.ensure_dirs()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_wav = config.RECORDINGS_DIR / f"live_{self.room_id}_{stamp}.wav"

        cmd = [sys.executable, str(RECORDER_SCRIPT), "-o", str(self.current_wav)]
        print(f"[monitor] Starting recorder: {self.current_wav.name}", flush=True)

        self.recorder_proc = subprocess.Popen(
            cmd,
            cwd=str(SCRIPT_DIR),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )

    def stop_recording(self) -> Path | None:
        """Stop recorder subprocess and return WAV path."""
        if not self.recorder_proc:
            return self.current_wav

        proc = self.recorder_proc
        self.recorder_proc = None

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

        wav = self.current_wav
        if wav and wav.exists() and wav.stat().st_size > 44:
            print(f"[monitor] Recording complete: {wav}", flush=True)
            return wav

        print("[monitor] No valid recording produced", flush=True)
        return None

    def run_pipeline(self, wav_path: Path, title: str | None) -> None:
        """Transcribe locally, then summarize with one API call."""
        print("[monitor] Running transcription (local)...", flush=True)
        tx_cmd = [sys.executable, str(TRANSCRIBER_SCRIPT), str(wav_path)]
        tx_result = subprocess.run(tx_cmd, cwd=str(SCRIPT_DIR), check=False)
        if tx_result.returncode != 0:
            print("[monitor] Transcription failed", flush=True)
            return

        transcript_path = config.TRANSCRIPTS_DIR / f"{wav_path.stem}.txt"
        if not transcript_path.exists():
            print(f"[monitor] Transcript not found: {transcript_path}", flush=True)
            return

        print("[monitor] Running summarizer (1 API call)...", flush=True)
        sum_cmd = [
            sys.executable,
            str(SUMMARIZER_SCRIPT),
            str(transcript_path),
            "-o",
            str(config.MEETING_MINUTES_PATH),
        ]
        if title:
            sum_cmd.extend(["-t", title])

        sum_result = subprocess.run(sum_cmd, cwd=str(SCRIPT_DIR), check=False)
        if sum_result.returncode == 0:
            print(f"[monitor] Done -> {config.MEETING_MINUTES_PATH}", flush=True)
        else:
            print("[monitor] Summarization failed", flush=True)

    def tick(self) -> None:
        """Single poll iteration."""
        is_live, title = self.check_live()
        if title:
            self.live_title = title

        if is_live and not self.was_live:
            print(f"[monitor] LIVE detected (room {self.room_id})", flush=True)
            if title:
                print(f"[monitor] Title: {title}", flush=True)
            self.start_recording()
            self.was_live = True

        elif not is_live and self.was_live:
            print("[monitor] Stream ended", flush=True)
            wav = self.stop_recording()
            self.was_live = False
            if wav:
                self.run_pipeline(wav, self.live_title)

        elif is_live:
            print(f"[monitor] Still live... ({datetime.now():%H:%M:%S})", flush=True)

        else:
            print(f"[monitor] Waiting for live... ({datetime.now():%H:%M:%S})", flush=True)

    def run_forever(self) -> None:
        """Main monitoring loop."""
        print(f"[monitor] Watching room {self.room_id}", flush=True)
        print(f"[monitor] Output: {config.OUTPUT_DIR}", flush=True)
        print(f"[monitor] Poll every {config.CHECK_INTERVAL_SEC}s", flush=True)

        try:
            while True:
                self.tick()
                time.sleep(config.CHECK_INTERVAL_SEC)
        except KeyboardInterrupt:
            print("\n[monitor] Shutting down...", flush=True)
            if self.was_live:
                wav = self.stop_recording()
                if wav:
                    self.run_pipeline(wav, self.live_title)


def main() -> int:
    config.ensure_dirs()

    room_id = config.ROOM_ID
    if len(sys.argv) > 1:
        room_id = sys.argv[1]

    if not room_id:
        print(
            "Usage: python monitor.py <room_id>\n"
            "Or set DOUYIN_ROOM_ID environment variable.\n"
            "Room ID is the number in https://live.douyin.com/<room_id>",
            file=sys.stderr,
        )
        return 1

    monitor = LiveMonitor(room_id)
    monitor.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
