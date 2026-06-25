"""Capture system audio via PyAudio into 10-minute WAV chunks."""

from __future__ import annotations

import argparse
import struct
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

from lib_common import (
    ensure_dirs,
    free_disk_if_needed,
    load_config,
    resolve_base_dir,
    setup_logging,
    write_json,
)


class AudioRecorder:
    """Record loopback/system audio with chunked WAV output."""

    def __init__(self, config: dict, session_id: str):
        self.config = config
        self.session_id = session_id
        self.base_dir = resolve_base_dir(config)
        self.paths = ensure_dirs(self.base_dir)
        self.logger = setup_logging("audio_recorder", self.paths["logs"])
        self.recordings_dir = self.paths["recordings"]
        self.state_dir = self.paths["state"]
        self.stop_flag = self.state_dir / "stop_recording.flag"
        self.pid_file = self.state_dir / "recorder.pid"
        self.chunk_index = 0
        self.started_at = datetime.now(timezone.utc)
        self._pyaudio = None
        self._stream = None

    def _max_seconds(self) -> float:
        return float(self.config.get("max_recording_hours", 8)) * 3600

    def _chunk_seconds(self) -> int:
        return int(self.config.get("chunk_duration_seconds", 600))

    def _sample_rate(self) -> int:
        return int(self.config.get("sample_rate", 44100))

    def _channels(self) -> int:
        return int(self.config.get("channels", 2))

    def _should_stop(self) -> bool:
        if self.stop_flag.exists():
            return True
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed >= self._max_seconds()

    def _chunk_path(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.recordings_dir / f"{self.session_id}_{ts}_part{self.chunk_index:03d}.wav"

    def _import_pyaudio(self):
        try:
            import pyaudio
        except ImportError as exc:
            raise RuntimeError("PyAudio 未安装，请运行 install_deps.bat") from exc
        return pyaudio

    def _list_devices(self, pyaudio_module) -> list[dict]:
        pa = pyaudio_module.PyAudio()
        devices: list[dict] = []
        try:
            for idx in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(idx)
                devices.append(
                    {
                        "index": idx,
                        "name": info.get("name", ""),
                        "max_input_channels": int(info.get("maxInputChannels", 0)),
                        "host_api": int(info.get("hostApi", -1)),
                    }
                )
        finally:
            pa.terminate()
        return devices

    def _select_device_index(self, pyaudio_module) -> int | None:
        configured = self.config.get("audio_device_index")
        if configured is not None:
            return int(configured)

        devices = self._list_devices(pyaudio_module)
        if not devices:
            return None

        preferred_keywords = (
            "loopback",
            "stereo mix",
            "立体声混音",
            "what u hear",
            "wave out",
            "混音",
            "cable output",
            "virtual",
        )

        candidates = [d for d in devices if d["max_input_channels"] > 0]
        for keyword in preferred_keywords:
            for device in candidates:
                if keyword in device["name"].lower():
                    self.logger.info("选用音频设备 [%s] %s", device["index"], device["name"])
                    return device["index"]

        default = next((d for d in candidates if "default" in d["name"].lower()), None)
        if default:
            self.logger.info("选用默认输入设备 [%s] %s", default["index"], default["name"])
            return default["index"]

        if candidates:
            device = candidates[0]
            self.logger.warning("未找到 loopback 设备，回退到 [%s] %s", device["index"], device["name"])
            return device["index"]

        return None

    def _open_stream(self, pyaudio_module, device_index: int | None):
        pa = pyaudio_module.PyAudio()
        sample_rate = self._sample_rate()
        channels = self._channels()
        frames_per_buffer = 1024

        open_kwargs = {
            "format": pyaudio_module.paInt16,
            "channels": channels,
            "rate": sample_rate,
            "input": True,
            "frames_per_buffer": frames_per_buffer,
        }
        if device_index is not None:
            open_kwargs["input_device_index"] = device_index

        try:
            stream = pa.open(**open_kwargs)
        except OSError as exc:
            pa.terminate()
            raise RuntimeError(f"无法打开音频设备 index={device_index}: {exc}") from exc

        return pa, stream, frames_per_buffer

    def _write_wav(self, path: Path, frames: list[bytes], sample_rate: int, channels: int) -> bool:
        if not frames:
            return False

        pcm = b"".join(frames)
        if len(pcm) < sample_rate * channels * 2 // 10:
            self.logger.warning("音频片段过短，跳过写入: %s", path.name)
            return False

        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)

        if path.stat().st_size <= 44:
            path.unlink(missing_ok=True)
            self.logger.warning("写入的 WAV 为空，已删除: %s", path.name)
            return False

        return True

    def _validate_wav_header(self, path: Path) -> bool:
        try:
            with path.open("rb") as fh:
                header = fh.read(12)
            if len(header) < 12:
                return False
            riff, size, wave_tag = struct.unpack("<4sI4s", header)
            return riff == b"RIFF" and wave_tag == b"WAVE" and size > 0
        except (OSError, struct.error):
            return False

    def run(self) -> int:
        write_json(self.pid_file, {"pid": __import__("os").getpid(), "session_id": self.session_id})

        pyaudio_module = self._import_pyaudio()
        device_index = self._select_device_index(pyaudio_module)
        if device_index is None:
            self.logger.error("未找到可用音频输入设备，跳过录音")
            marker = self.recordings_dir / f"{self.session_id}_NO_AUDIO.marker"
            marker.write_text("no_audio_device\n", encoding="utf-8")
            return 0

        try:
            pa, stream, frames_per_buffer = self._open_stream(pyaudio_module, device_index)
        except RuntimeError as exc:
            self.logger.error("%s", exc)
            marker = self.recordings_dir / f"{self.session_id}_NO_AUDIO.marker"
            marker.write_text(f"open_failed: {exc}\n", encoding="utf-8")
            return 0

        self._pyaudio = pa
        self._stream = stream

        sample_rate = self._sample_rate()
        channels = self._channels()
        chunk_target_frames = max(1, int(sample_rate / frames_per_buffer * self._chunk_seconds()))
        written_files: list[str] = []

        self.logger.info(
            "开始录音 session=%s device=%s rate=%s channels=%s",
            self.session_id,
            device_index,
            sample_rate,
            channels,
        )

        try:
            while not self._should_stop():
                removed = free_disk_if_needed(self.base_dir, self.config)
                if removed:
                    self.logger.warning("磁盘空间不足，已清理 %s 个旧录音", len(removed))

                frames: list[bytes] = []
                for _ in range(chunk_target_frames):
                    if self._should_stop():
                        break
                    try:
                        data = stream.read(frames_per_buffer, exception_on_overflow=False)
                        frames.append(data)
                    except OSError as exc:
                        self.logger.error("读取音频失败: %s", exc)
                        raise

                if not frames:
                    break

                path = self._chunk_path()
                if self._write_wav(path, frames, sample_rate, channels) and self._validate_wav_header(path):
                    written_files.append(path.name)
                    self.logger.info("已保存片段: %s (%.1f MB)", path.name, path.stat().st_size / (1024 * 1024))
                    self.chunk_index += 1
                else:
                    self.logger.warning("片段无效，未递增 chunk 索引")

        except Exception as exc:  # noqa: BLE001
            self.logger.exception("录音异常: %s", exc)
            return 1
        finally:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
            if self._pyaudio is not None:
                self._pyaudio.terminate()
            self.pid_file.unlink(missing_ok=True)
            self.stop_flag.unlink(missing_ok=True)

        manifest = self.state_dir / f"recording_manifest_{self.session_id}.json"
        write_json(
            manifest,
            {
                "session_id": self.session_id,
                "files": written_files,
                "started_at": self.started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "no_audio": len(written_files) == 0,
            },
        )

        if not written_files:
            marker = self.recordings_dir / f"{self.session_id}_NO_AUDIO.marker"
            marker.write_text("empty_recording\n", encoding="utf-8")
            self.logger.warning("未录到有效音频")
        else:
            self.logger.info("录音结束，共 %s 个片段", len(written_files))

        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Douyin livestream audio recorder")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    recorder = AudioRecorder(config, args.session_id)
    return recorder.run()


if __name__ == "__main__":
    raise SystemExit(main())
