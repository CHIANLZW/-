"""Local speech-to-text using faster-whisper (no API calls)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import config


def transcribe_audio(
    audio_path: Path,
    output_dir: Path | None = None,
    model_name: str | None = None,
) -> Path:
    """Transcribe WAV file and write plain-text + JSON sidecar."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "faster-whisper is required. Install with: pip install faster-whisper"
        ) from exc

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    config.ensure_dirs()
    out_dir = output_dir or config.TRANSCRIPTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = audio_path.stem
    txt_path = out_dir / f"{stem}.txt"
    json_path = out_dir / f"{stem}.json"

    model = WhisperModel(
        model_name or config.WHISPER_MODEL,
        device=config.WHISPER_DEVICE,
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )

    print(
        f"[transcriber] Transcribing {audio_path.name} "
        f"(model={model_name or config.WHISPER_MODEL})...",
        flush=True,
    )

    segments_iter, info = model.transcribe(
        str(audio_path),
        language="zh",
        vad_filter=True,
        beam_size=1,
    )

    lines: list[str] = []
    segment_records: list[dict] = []

    for seg in segments_iter:
        text = seg.text.strip()
        if not text:
            continue
        line = f"[{seg.start:06.1f}s] {text}"
        lines.append(line)
        segment_records.append(
            {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text,
            }
        )

    transcript = "\n".join(lines)
    txt_path.write_text(transcript, encoding="utf-8")

    meta = {
        "source_audio": str(audio_path),
        "language": info.language,
        "duration": round(info.duration, 2),
        "model": model_name or config.WHISPER_MODEL,
        "transcribed_at": datetime.now().isoformat(timespec="seconds"),
        "segments": segment_records,
    }
    json_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[transcriber] Wrote {txt_path} ({len(lines)} segments)", flush=True)
    return txt_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe WAV with local faster-whisper")
    parser.add_argument("audio", type=Path, help="Input WAV file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for transcript files",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Whisper model size (tiny, base, ...)",
    )
    args = parser.parse_args()

    transcribe_audio(args.audio, args.output_dir, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
