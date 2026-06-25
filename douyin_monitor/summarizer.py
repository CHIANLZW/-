"""Generate meeting_minutes.md from transcript or stream metadata."""

from __future__ import annotations

import argparse
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from lib_common import ensure_dirs, load_config, read_json, resolve_base_dir, setup_logging, write_json


SUMMARY_PROMPT = """你是直播会议纪要助手。根据以下直播信息，输出 Markdown，包含四个章节：
## 话题总结
## 关键观点
## 数据亮点
## 行动项

要求：简洁中文，条目化，不要编造未提供的数据。"""


class Summarizer:
    """Build meeting minutes from transcript and/or metadata."""

    def __init__(self, config: dict, session_id: str):
        self.config = config
        self.session_id = session_id or ""
        self.base_dir = resolve_base_dir(config)
        self.paths = ensure_dirs(self.base_dir)
        self.logger = setup_logging("summarizer", self.paths["logs"])
        self.output_dir = self.paths["output"]
        self.state_dir = self.paths["state"]
        self.transcript_path = self.output_dir / "transcript.txt"
        self.minutes_path = self.output_dir / "meeting_minutes.md"

    def _session_metadata(self) -> dict:
        session = read_json(self.state_dir / "current_session.json") or {}
        if not session:
            session = read_json(self.output_dir / "session_snapshot.json") or {}
        transcript_meta = read_json(self.output_dir / "transcript_meta.json") or {}
        manifest = read_json(self.state_dir / f"recording_manifest_{self.session_id}.json") or {}

        return {
            "session_id": self.session_id or session.get("session_id", "unknown"),
            "title": session.get("title") or "未知标题",
            "anchor_name": session.get("anchor_name") or self.config.get("streamer_name", "未知主播"),
            "started_at": session.get("started_at"),
            "ended_at": session.get("ended_at"),
            "viewer_count_at_start": session.get("viewer_count_at_start"),
            "viewer_count_latest": session.get("viewer_count_latest"),
            "viewer_count_at_end": session.get("viewer_count_at_end"),
            "stream_url": self.config.get("stream_url"),
            "recording_files": manifest.get("files") or [],
            "transcript_status": transcript_meta.get("status"),
            "transcript_chars": transcript_meta.get("char_count", 0),
        }

    def _duration_text(self, metadata: dict) -> str:
        start = metadata.get("started_at")
        end = metadata.get("ended_at")
        if not start or not end:
            return "未知"

        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            minutes = max(1, int((end_dt - start_dt).total_seconds() // 60))
            return f"{minutes} 分钟"
        except ValueError:
            return "未知"

    def _read_transcript_excerpt(self) -> str:
        if not self.transcript_path.exists():
            return ""
        text = self.transcript_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            return ""
        limit = int(self.config.get("transcript_max_chars_for_summary", 2000))
        return text[:limit]

    def _call_llm(self, metadata: dict, transcript_excerpt: str) -> str | None:
        api_key = (self.config.get("openai_api_key") or "").strip()
        if not api_key:
            return None

        try:
            from openai import OpenAI
        except ImportError as exc:
            self.logger.error("openai 包未安装: %s", exc)
            return None

        user_content = textwrap.dedent(
            f"""
            直播标题: {metadata.get('title')}
            主播: {metadata.get('anchor_name')}
            时长: {self._duration_text(metadata)}
            观看数据: 开始={metadata.get('viewer_count_at_start')} 最新={metadata.get('viewer_count_latest')} 结束={metadata.get('viewer_count_at_end')}
            链接: {metadata.get('stream_url')}

            转写摘录:
            {transcript_excerpt or '(无转写内容)'}
            """
        ).strip()

        client = OpenAI(api_key=api_key, base_url=self.config.get("openai_base_url"))
        try:
            response = client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4o-mini"),
                temperature=float(self.config.get("summary_temperature", 0.3)),
                max_tokens=int(self.config.get("summary_max_tokens", 800)),
                messages=[
                    {"role": "system", "content": SUMMARY_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as exc:  # noqa: BLE001
            self.logger.error("LLM 调用失败，回退到模板摘要: %s", exc)
            return None

    def _metadata_summary(self, metadata: dict, transcript_excerpt: str) -> str:
        duration = self._duration_text(metadata)
        title = metadata.get("title") or "未知标题"
        anchor = metadata.get("anchor_name") or "未知主播"
        viewers = metadata.get("viewer_count_at_end") or metadata.get("viewer_count_latest") or "未知"

        if transcript_excerpt:
            preview_lines = [line.strip() for line in transcript_excerpt.splitlines() if line.strip()][:5]
            topic_hint = preview_lines[0][:120] if preview_lines else "未能从转写中识别明确主题"
            key_points = preview_lines[:3] or ["无可用转写内容"]
        else:
            topic_hint = f"{anchor} 的直播「{title}」"
            key_points = [
                "未获取到有效转写文本，以下为基于元数据的摘要",
                f"直播链接: {metadata.get('stream_url')}",
            ]

        action_items = [
            "复核录音/转写质量，必要时手动补充纪要",
            "如需完整 AI 摘要，请在 config.json 配置 openai_api_key",
        ]

        lines = [
            f"# 直播会议纪要 - {title}",
            "",
            f"- 主播: {anchor}",
            f"- 场次: {metadata.get('session_id')}",
            f"- 时长: {duration}",
            f"- 观看人数(结束时): {viewers}",
            f"- 转写状态: {metadata.get('transcript_status') or ('有内容' if transcript_excerpt else '无转写')}",
            "",
            "## 话题总结",
            f"- {topic_hint}",
            "",
            "## 关键观点",
        ]
        lines.extend(f"- {point}" for point in key_points)
        lines.extend(
            [
                "",
                "## 数据亮点",
                f"- 开播观看: {metadata.get('viewer_count_at_start') or '未知'}",
                f"- 峰值/最新观看: {metadata.get('viewer_count_latest') or '未知'}",
                f"- 结束观看: {metadata.get('viewer_count_at_end') or '未知'}",
                f"- 录音片段数: {len(metadata.get('recording_files') or [])}",
                "",
                "## 行动项",
            ]
        )
        lines.extend(f"- {item}" for item in action_items)
        lines.append("")
        return "\n".join(lines)

    def _normalize_markdown(self, content: str, metadata: dict) -> str:
        content = content.strip()
        if content.startswith("#"):
            return content + "\n"
        title = metadata.get("title") or "直播会议纪要"
        return f"# 直播会议纪要 - {title}\n\n{content}\n"

    def run(self) -> int:
        metadata = self._session_metadata()
        transcript_excerpt = self._read_transcript_excerpt()

        llm_summary = None
        if transcript_excerpt or metadata.get("title"):
            llm_summary = self._call_llm(metadata, transcript_excerpt)

        if llm_summary:
            minutes = self._normalize_markdown(llm_summary, metadata)
            source = "llm"
        else:
            minutes = self._metadata_summary(metadata, transcript_excerpt)
            source = "metadata_fallback"

        self.minutes_path.write_text(minutes, encoding="utf-8")
        write_json(
            self.output_dir / "summary_meta.json",
            {
                "session_id": metadata.get("session_id"),
                "source": source,
                "transcript_chars_used": len(transcript_excerpt),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.logger.info("会议纪要已写入 %s (source=%s)", self.minutes_path, source)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Douyin livestream summarizer")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    summarizer = Summarizer(config, args.session_id)
    return summarizer.run()


if __name__ == "__main__":
    raise SystemExit(main())
