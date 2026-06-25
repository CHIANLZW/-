"""Generate meeting minutes from transcript using a single compact API call."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import config

# Common filler / low-value phrases to down-rank
FILLER_PATTERN = re.compile(
    r"^(嗯|啊|哦|呃|那个|这个|好的|谢谢|欢迎|点赞|关注|刷礼物)[。！？]?$",
    re.IGNORECASE,
)


def load_segments(transcript_path: Path) -> list[dict]:
    """Load timed segments from JSON sidecar or parse plain transcript."""
    json_path = transcript_path.with_suffix(".json")
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return data.get("segments", [])

    segments: list[dict] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\[(\d+\.\d+)s\]\s*(.+)$", line.strip())
        if match:
            segments.append({"start": float(match.group(1)), "text": match.group(2)})
        elif line.strip():
            segments.append({"start": 0.0, "text": line.strip()})
    return segments


def score_segment(text: str) -> float:
    """Heuristic score: prefer substantive, longer utterances."""
    cleaned = text.strip()
    if not cleaned or FILLER_PATTERN.match(cleaned):
        return 0.0
    score = min(len(cleaned), 120) / 10.0
    if any(k in cleaned for k in ("总结", "结论", "重点", "第一", "第二", "因为", "所以", "但是")):
        score += 3.0
    if re.search(r"\d+", cleaned):
        score += 1.0
    return score


def select_key_chunks(segments: list[dict], max_chars: int, top_n: int) -> str:
    """Pick highest-value segments, evenly spaced as fallback."""
    if not segments:
        return ""

    ranked = sorted(
        segments,
        key=lambda s: (score_segment(s.get("text", "")), s.get("start", 0)),
        reverse=True,
    )

    chosen: list[dict] = []
    seen_text: set[str] = set()
    for seg in ranked:
        text = seg.get("text", "").strip()
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        chosen.append(seg)
        if len(chosen) >= top_n:
            break

    # Ensure chronological order for readability
    chosen.sort(key=lambda s: s.get("start", 0))

    lines: list[str] = []
    total = 0
    for seg in chosen:
        text = seg.get("text", "").strip()
        line = f"[{seg.get('start', 0):.0f}s] {text}"
        if total + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total += len(line) + 1

    return "\n".join(lines)


def build_prompt(chunks: str, title: str | None = None) -> str:
    """Compact summarizer prompt — only key transcript chunks."""
    heading = title or "抖音直播"
    return (
        f"直播标题:{heading}\n"
        f"摘录:\n{chunks}\n\n"
        "请输出简洁中文会议纪要，含：主题、要点(3-8条)、结论、待办(如有)。"
        "Markdown格式，不要复述无关寒暄。"
    )


def call_summarizer_api(prompt: str) -> str:
    """Single API call for summarization."""
    if not config.OPENAI_API_KEY:
        return _offline_summary(prompt)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("openai package required for summarization") from exc

    client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=config.SUMMARIZER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1200,
    )
    return response.choices[0].message.content or ""


def _offline_summary(prompt: str) -> str:
    """Fallback when no API key — structure raw chunks only."""
    return (
        "# 会议纪要（离线模式，未调用 API）\n\n"
        "## 摘录\n\n"
        + prompt.split("摘录:\n", 1)[-1].split("\n\n请输出", 1)[0]
        + "\n\n> 设置 OPENAI_API_KEY 后可自动生成摘要。\n"
    )


def summarize_transcript(
    transcript_path: Path,
    output_path: Path | None = None,
    title: str | None = None,
) -> Path:
    """Build meeting minutes from transcript file."""
    config.ensure_dirs()
    out_path = output_path or config.MEETING_MINUTES_PATH

    segments = load_segments(transcript_path)
    chunks = select_key_chunks(
        segments,
        max_chars=config.MAX_TRANSCRIPT_CHARS,
        top_n=config.KEY_CHUNK_COUNT,
    )

    if not chunks:
        chunks = transcript_path.read_text(encoding="utf-8")[: config.MAX_TRANSCRIPT_CHARS]

    prompt = build_prompt(chunks, title=title)
    print("[summarizer] Sending compact prompt (1 API call)...", flush=True)
    summary = call_summarizer_api(prompt)

    header = (
        f"# 会议纪要\n\n"
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- 来源: {transcript_path.name}\n\n"
    )
    out_path.write_text(header + summary.strip() + "\n", encoding="utf-8")
    print(f"[summarizer] Wrote {out_path}", flush=True)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize transcript into meeting minutes")
    parser.add_argument("transcript", type=Path, help="Transcript .txt file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output markdown path",
    )
    parser.add_argument("-t", "--title", default=None, help="Live stream title")
    args = parser.parse_args()

    summarize_transcript(args.transcript, args.output, args.title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
