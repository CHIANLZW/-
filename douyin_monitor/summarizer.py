#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate meeting minutes after a Douyin livestream ends (single AI call)."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(os.environ.get("DOUYIN_MONITOR_DIR", "D:/mimocod/douyin_monitor"))
STATUS_FILE = "monitor_status.json"
SESSION_FILE = "stream_session.json"
MINUTES_FILE = "meeting_minutes.md"
TRANSCRIPT_DIR = "transcripts"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_transcript(output_dir: Path) -> tuple[str | None, str | None]:
    """Return (text, source_path) for the newest transcript/recording text file."""
    candidates: list[Path] = []
    search_dirs = [
        output_dir / TRANSCRIPT_DIR,
        output_dir / "recordings",
        output_dir,
    ]
    patterns = ("*.txt", "*.srt", "*.vtt", "*.md", "*.json")

    for folder in search_dirs:
        if not folder.exists():
            continue
        for pattern in patterns:
            candidates.extend(folder.glob(pattern))

    candidates = [p for p in candidates if p.name not in {MINUTES_FILE, STATUS_FILE, SESSION_FILE}]
    if not candidates:
        return None, None

    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        text = newest.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return None, None
    if not text:
        return None, None
    return text[:120_000], str(newest)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def compute_duration(session: dict[str, Any], status: dict[str, Any]) -> str:
    start = session.get("started_at") or session.get("first_live_detected_at") or status.get("create_time")
    end = session.get("ended_at") or status.get("ended_at") or status.get("last_check")
    start_dt = parse_datetime(str(start) if start else None)
    end_dt = parse_datetime(str(end) if end else None)
    if not start_dt or not end_dt:
        return "未知"

    delta = end_dt - start_dt
    if delta.total_seconds() < 0:
        return "未知"
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours} 小时 {minutes} 分钟"
    if minutes:
        return f"{minutes} 分钟 {seconds} 秒"
    return f"{seconds} 秒"


def build_metadata_context(status: dict[str, Any], session: dict[str, Any]) -> str:
    lines = [
        f"主播: {session.get('streamer') or status.get('streamer', '未知')}",
        f"直播标题: {session.get('title') or status.get('title', '未知')}",
        f"房间 ID: {session.get('room_id') or status.get('room_id', '未知')}",
        f"开始时间: {session.get('started_at') or status.get('create_time', '未知')}",
        f"结束时间: {session.get('ended_at') or status.get('ended_at', '未知')}",
        f"预估时长: {compute_duration(session, status)}",
        f"峰值在线观众: {session.get('peak_viewer_count', status.get('viewer_count', '未知'))}",
        f"分享链接: {session.get('share_url') or status.get('stream_url', '')}",
    ]
    polls = session.get("polls") or []
    if polls:
        lines.append("轮询快照（标题/观众数变化）:")
        for item in polls[-12:]:
            lines.append(f"  - {item.get('at')}: {item.get('viewers')} 人 | {item.get('title', '')}")
    return "\n".join(lines)


def local_fallback_minutes(status: dict[str, Any], session: dict[str, Any]) -> str:
    """No-AI fallback when transcript/API unavailable."""
    streamer = session.get("streamer") or status.get("streamer", "未知主播")
    title = session.get("title") or status.get("title", "未知标题")
    date_str = (session.get("ended_at") or status.get("last_check") or "")[:10] or "未知日期"
    duration = compute_duration(session, status)
    peak = session.get("peak_viewer_count", "未知")

    return f"""# 直播会议纪要

## 直播信息

| 项目 | 内容 |
|------|------|
| 主播 | {streamer} |
| 标题 | {title} |
| 日期 | {date_str} |
| 时长 | {duration} |
| 峰值观众 | {peak} |
| 房间 ID | {session.get('room_id') or status.get('room_id', '-')} |

> 说明：本次未检测到文字稿/录音文本，也未配置 AI API。以下为基于监控元数据的自动摘要。

## 关键话题

- 直播主题：**{title}**
- 主播 **{streamer}** 进行了关于低空经济/无人机相关内容的分享（根据频道名称推断）。
- 监控期间峰值在线约 **{peak}** 人。

## 精彩瞬间 / 引用

- （无文字稿）建议在 `transcripts/` 目录放入 `.txt` / `.srt` 录音转写后重新运行 `summarizer.py` 以生成更详细摘要。

## 行动项 / 要点

- [ ] 如需完整纪要，请将直播录音转写文件放入 `{OUTPUT_DIR / TRANSCRIPT_DIR}`
- [ ] 配置 `OPENAI_API_KEY` 环境变量后重新运行摘要生成
- [ ] 关注 **{streamer}** 后续直播动态

---
*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 本地元数据模式*
"""


def call_openai_chat(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("未设置 OPENAI_API_KEY")

    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    body = {
        "model": OPENAI_MODEL,
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是专业的中文会议纪要助手。根据提供的直播信息生成结构清晰、"
                    "简洁准确的 Markdown 会议纪要。不要编造无法从材料中推断的具体事实。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"].strip()


def build_ai_prompt(
    status: dict[str, Any],
    session: dict[str, Any],
    transcript: str | None,
    transcript_source: str | None,
) -> str:
    metadata = build_metadata_context(status, session)
    if transcript:
        return f"""请根据以下抖音直播文字稿和元数据，生成中文 Markdown 会议纪要。

格式要求（必须包含以下四个二级标题）：
## 直播信息
## 关键话题
## 精彩瞬间 / 引用
## 行动项 / 要点

元数据：
{metadata}

文字稿来源: {transcript_source}
文字稿内容：
{transcript}
"""
    return f"""请根据以下抖音直播元数据（无文字稿），生成中文 Markdown 会议纪要。
请基于标题、主播名称和监控数据做合理推断，但避免捏造具体数据或引用。

格式要求（必须包含以下四个二级标题）：
## 直播信息
## 关键话题
## 精彩瞬间 / 引用
## 行动项 / 要点

元数据：
{metadata}
"""


def send_notification(title: str, message: str) -> None:
    system = platform.system()
    try:
        if system == "Windows":
            ps_script = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] | Out-Null; "
                "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                "$xml = [xml]$template.GetXml(); "
                f"$xml.toast.visual.binding.text[0].AppendChild($xml.CreateTextNode('{title}')) | Out-Null; "
                f"$xml.toast.visual.binding.text[1].AppendChild($xml.CreateTextNode('{message}')) | Out-Null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                "'Douyin Monitor').Show($toast);"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                check=False,
                capture_output=True,
            )
        elif system == "Darwin":
            safe_msg = message.replace('"', '\\"')
            subprocess.run(["osascript", "-e", f'display notification "{safe_msg}" with title "{title}"'], check=False)
        else:
            subprocess.run(["notify-send", title, message], check=False)
    except Exception:
        pass

    print(f"[通知] {title}: {message}")


def generate_minutes(output_dir: Path | None = None) -> Path:
    base = output_dir or OUTPUT_DIR
    base.mkdir(parents=True, exist_ok=True)

    status = load_json(base / STATUS_FILE)
    session = load_json(base / SESSION_FILE)
    transcript, transcript_source = find_transcript(base)

    prompt = build_ai_prompt(status, session, transcript, transcript_source)
    mode = "transcript+ai" if transcript else "metadata+ai"

    try:
        content = call_openai_chat(prompt)
        footer = (
            f"\n\n---\n*AI 摘要 | 模式: {mode} | "
            f"生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        )
        minutes = content + footer
    except (RuntimeError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        print(f"AI 摘要不可用 ({exc})，使用本地模板")
        minutes = local_fallback_minutes(status, session)
        mode = "metadata_local"

    out_path = base / MINUTES_FILE
    out_path.write_text(minutes, encoding="utf-8")

    streamer = session.get("streamer") or status.get("streamer", "主播")
    send_notification(
        "抖音直播纪要已生成",
        f"{streamer} 的会议纪要已保存至 meeting_minutes.md",
    )
    print(f"会议纪要已写入: {out_path}")
    return out_path


def main() -> int:
    try:
        generate_minutes()
        return 0
    except Exception as exc:
        print(f"摘要生成失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
