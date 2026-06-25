"""Transcribe recorded WAV files with faster-whisper."""

from __future__ import annotations

import argparse
from pathlib import Path

from lib_common import ensure_dirs, load_config, read_json, resolve_base_dir, setup_logging, write_json


class Transcriber:
    """Convert session WAV chunks into transcript.txt."""

    SILENCE_RMS_THRESHOLD = 120

    def __init__(self, config: dict, session_id: str):
        self.config = config
        self.session_id = session_id or ""
        self.base_dir = resolve_base_dir(config)
        self.paths = ensure_dirs(self.base_dir)
        self.logger = setup_logging("transcriber", self.paths["logs"])
        self.recordings_dir = self.paths["recordings"]
        self.output_dir = self.paths["output"]
        self.state_dir = self.paths["state"]
        self.transcript_path = self.output_dir / "transcript.txt"

    def _session_files(self) -> list[Path]:
        manifest_path = self.state_dir / f"recording_manifest_{self.session_id}.json"
        manifest = read_json(manifest_path)
        if manifest and manifest.get("files"):
            files = [self.recordings_dir / name for name in manifest["files"]]
            return [f for f in files if f.exists()]

        if self.session_id:
            files = sorted(self.recordings_dir.glob(f"{self.session_id}_*.wav"))
            if files:
                return files

        return sorted(self.recordings_dir.glob("*.wav"))

    def _has_audio_content(self, path: Path) -> bool:
        try:
            import wave
            import audioop

            with wave.open(str(path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sampwidth = wf.getsampwidth()
            if not frames:
                return False
            rms = audioop.rms(frames, sampwidth)
            return rms >= self.SILENCE_RMS_THRESHOLD
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("无法分析音频 %s: %s", path.name, exc)
            return False

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper 未安装，请运行 install_deps.bat") from exc

        model_size = self.config.get("whisper_model_size", "tiny")
        device = self.config.get("whisper_device", "cpu")
        compute_type = self.config.get("whisper_compute_type", "int8")
        self.logger.info("加载 Whisper 模型: size=%s device=%s", model_size, device)
        return WhisperModel(model_size, device=device, compute_type=compute_type)

    def _transcribe_file(self, model, path: Path) -> str:
        language = self.config.get("whisper_language", "zh")
        segments, info = model.transcribe(
            str(path),
            language=language,
            vad_filter=True,
            beam_size=1,
        )
        text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        joined = "\n".join(text_parts).strip()
        self.logger.info(
            "转写完成 %s: lang=%s prob=%.2f chars=%s",
            path.name,
            info.language,
            info.language_probability,
            len(joined),
        )
        return joined

    def run(self) -> int:
        marker = self.recordings_dir / f"{self.session_id}_NO_AUDIO.marker"
        if marker.exists():
            self.logger.warning("检测到 NO_AUDIO 标记，跳过转写")
            self.transcript_path.write_text("", encoding="utf-8")
            write_json(
                self.output_dir / "transcript_meta.json",
                {"session_id": self.session_id, "status": "no_audio", "files": []},
            )
            return 0

        wav_files = self._session_files()
        if not wav_files:
            self.logger.warning("未找到录音文件")
            self.transcript_path.write_text("", encoding="utf-8")
            write_json(
                self.output_dir / "transcript_meta.json",
                {"session_id": self.session_id, "status": "no_files", "files": []},
            )
            return 0

        valid_files: list[Path] = []
        corrupted: list[str] = []
        silent: list[str] = []

        for path in wav_files:
            if path.stat().st_size <= 44:
                corrupted.append(path.name)
                continue
            if not self._has_audio_content(path):
                silent.append(path.name)
                continue
            valid_files.append(path)

        if corrupted:
            self.logger.warning("损坏/空文件: %s", ", ".join(corrupted))
        if silent:
            self.logger.warning("静音文件: %s", ", ".join(silent))

        if not valid_files:
            self.logger.warning("没有可转写的有效音频")
            self.transcript_path.write_text("", encoding="utf-8")
            write_json(
                self.output_dir / "transcript_meta.json",
                {
                    "session_id": self.session_id,
                    "status": "empty_audio",
                    "files": [p.name for p in wav_files],
                    "corrupted": corrupted,
                    "silent": silent,
                },
            )
            return 0

        try:
            model = self._load_model()
        except RuntimeError as exc:
            self.logger.error("%s", exc)
            return 1

        chunks: list[str] = []
        for path in valid_files:
            try:
                text = self._transcribe_file(model, path)
                if text:
                    chunks.append(text)
            except Exception as exc:  # noqa: BLE001
                self.logger.error("转写失败 %s: %s", path.name, exc)
                corrupted.append(path.name)

        transcript = "\n\n".join(chunks).strip()
        self.transcript_path.write_text(transcript + ("\n" if transcript else ""), encoding="utf-8")

        status = "ok" if transcript else "empty_transcript"
        if transcript:
            self.logger.info("转写完成，共 %s 字符", len(transcript))
        else:
            self.logger.warning("转写结果为空")

        write_json(
            self.output_dir / "transcript_meta.json",
            {
                "session_id": self.session_id,
                "status": status,
                "files": [p.name for p in valid_files],
                "corrupted": corrupted,
                "silent": silent,
                "char_count": len(transcript),
            },
        )
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Douyin livestream transcriber")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    transcriber = Transcriber(config, args.session_id)
    return transcriber.run()


if __name__ == "__main__":
    raise SystemExit(main())
