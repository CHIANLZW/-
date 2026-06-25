"""Capture system audio on Windows (WASAPI loopback) and save as WAV."""

from __future__ import annotations

import argparse
import signal
import sys
import wave
from datetime import datetime
from pathlib import Path

import config

try:
    import pyaudiowpatch as pyaudio
except ImportError as exc:
    raise SystemExit(
        "pyaudiowpatch is required for Windows system audio capture. "
        "Install with: pip install pyaudiowpatch"
    ) from exc


class AudioRecorder:
    """Record default speaker output until stop() is called."""

    def __init__(self, output_path: Path, chunk_size: int = 1024) -> None:
        self.output_path = output_path
        self.chunk_size = chunk_size
        self._running = False
        self._pa: pyaudio.PyAudio | None = None
        self._stream = None
        self._wave: wave.Wave_write | None = None

    def _resolve_loopback_device(self) -> dict:
        pa = pyaudio.PyAudio()
        try:
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

            if not default_speakers.get("isLoopbackDevice"):
                for loopback in pa.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        return loopback
                raise RuntimeError(
                    "No WASAPI loopback device found. "
                    "Enable stereo mix or use default speakers on Windows."
                )
            return default_speakers
        finally:
            pa.terminate()

    def start(self) -> None:
        device = self._resolve_loopback_device()
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._pa = pyaudio.PyAudio()
        self._wave = wave.open(str(self.output_path), "wb")
        self._wave.setnchannels(channels)
        self._wave.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
        self._wave.setframerate(rate)

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            frames_per_buffer=self.chunk_size,
            input=True,
            input_device_index=int(device["index"]),
        )
        self._running = True
        print(f"[recorder] Recording system audio -> {self.output_path}", flush=True)

    def record_loop(self) -> None:
        if not self._running or self._stream is None or self._wave is None:
            raise RuntimeError("Recorder not started")

        while self._running:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                self._wave.writeframes(data)
            except OSError:
                break

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._wave is not None:
            self._wave.close()
            self._wave = None
        if self._pa is not None:
            self._pa.terminate()
            self._pa = None
        print(f"[recorder] Saved {self.output_path}", flush=True)


def default_output_path() -> Path:
    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return config.RECORDINGS_DIR / f"live_{stamp}.wav"


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Windows system audio to WAV")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output WAV path (default: recordings/live_<timestamp>.wav)",
    )
    args = parser.parse_args()

    output_path = args.output or default_output_path()
    recorder = AudioRecorder(output_path)

    def handle_stop(signum, frame) -> None:  # noqa: ARG001
        recorder.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    try:
        recorder.start()
        recorder.record_loop()
    except KeyboardInterrupt:
        pass
    finally:
        recorder.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
