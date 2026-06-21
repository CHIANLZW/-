# -*- coding: utf-8 -*-
"""Scan all video files for classic projects inventory."""
from __future__ import annotations

import json
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = [
    PROJECT / "assets" / "videos",
    PROJECT / "_source" / "videos",
    PROJECT,
    Path.home() / "Desktop",
]
VIDEO_EXT = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".MP4", ".MOV"}

# pages that reference videos
SITE_REFS = {
    "assets/videos/fpv/fpv-showreel.mp4": ["index.html 经典项目", "portfolio.html#fpv"],
    "assets/videos/film/film-behind.mp4": ["index.html 经典项目", "portfolio.html#film"],
    "assets/videos/fpv/fpv-flight.mp4": ["portfolio.html#fpv"],
}

SKIP_DIRS = {"node_modules", ".git", "_archive", "苍凌工作室证件整理", "mcps"}


def scan_dir(root: Path, max_depth: int = 6) -> list[dict]:
    items = []
    if not root.exists():
        return items
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > max_depth:
            dirnames.clear()
            continue
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix not in VIDEO_EXT and p.suffix.lower() not in {e.lower() for e in VIDEO_EXT}:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            rel_site = None
            try:
                rel_site = str(p.relative_to(PROJECT)).replace("\\", "/")
            except ValueError:
                pass
            refs = SITE_REFS.get(rel_site or "", [])
            items.append({
                "path": str(p),
                "relative_to_project": rel_site,
                "size_mb": round(size / (1024 * 1024), 2),
                "on_site": bool(refs),
                "site_pages": refs,
                "suggested_category": guess_category(p),
            })
    return items


def guess_category(p: Path) -> str:
    t = str(p).lower()
    if "fpv" in t or "穿越" in t:
        return "fpv"
    if "film" in t or "影视" in t or "毕业" in t:
        return "film"
    if "car" in t or "mazda" in t or "改装" in t:
        return "automotive"
    return "other"


def main() -> None:
    all_items: list[dict] = []
    seen_paths: set[str] = set()
    for root in SCAN_ROOTS:
        for item in scan_dir(root):
            if item["path"] in seen_paths:
                continue
            seen_paths.add(item["path"])
            all_items.append(item)

    all_items.sort(key=lambda x: (x["on_site"], x["suggested_category"], x["path"]))

    out_json = PROJECT / "assets" / "data" / "video-inventory.json"
    out_txt = Path.home() / "Desktop" / "经典项目-视频清单.txt"

    data = {
        "note": "勾选要上线的视频后告知，将写入 assets/data/videos-manifest.json 并更新首页/项目集",
        "site_current": [i for i in all_items if i["on_site"]],
        "candidates": [i for i in all_items if not i["on_site"]],
        "all": all_items,
    }
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "重庆苍凌工作室 — 经典项目视频清单",
        "=" * 50,
        "",
        "【当前网站已引用】",
    ]
    for i in data["site_current"]:
        lines.append(f"  [站点] {i['relative_to_project']}")
        lines.append(f"         路径: {i['path']}")
        lines.append(f"         大小: {i['size_mb']} MB | 分类: {i['suggested_category']}")
        lines.append(f"         页面: {', '.join(i['site_pages']) or '—'}")
        lines.append("")

    lines.append("【候选素材（未上线 / 可筛选）】")
    for i in data["candidates"]:
        lines.append(f"  [{i['suggested_category']}] {Path(i['path']).name}")
        lines.append(f"         路径: {i['path']}")
        lines.append(f"         大小: {i['size_mb']} MB")
        lines.append("")

    lines += [
        "",
        "使用说明：",
        "  1. 删除或标注不要的视频",
        "  2. 把要用的视频复制到 inchian.top/assets/videos/{fpv|film|other}/",
        "  3. 告诉我文件名与标题，我会更新网站「经典项目」区块",
        "",
        f"机器可读清单: {out_json}",
    ]
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f"total={len(all_items)} site={len(data['site_current'])} candidates={len(data['candidates'])}")
    print(f"txt: {out_txt}")
    print(f"json: {out_json}")


if __name__ == "__main__":
    main()
