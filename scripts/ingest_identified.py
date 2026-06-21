# -*- coding: utf-8 -*-
"""从 素材/已识别/ 入库（支持用户手动重命名后的文件）。"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
IDENTIFIED = PROJECT / "素材" / "已识别"
SITE_MANIFEST = PROJECT / "assets" / "data" / "site-materials-manifest.json"
ORGANIZED = Path.home() / "Desktop" / "苍凌工作室证件整理"

PREFIX_MAP = {
    "培训资质": "training",
    "运营合格证": "operation",
    "空域申请": "airspace",
    "适航审定": "airworthiness",
    "创意项目": "portfolio",
}

CUSTOM_MAP: dict[str, tuple[str, str]] = {
    "caac部队培训": ("training", "培训现场"),
    "宣传材料": ("training", "培训教材"),
    "改装车": ("portfolio", "活动影像"),
    "最新团表关于caac培训场地要求": ("training", "团体标准"),
}

SKIP_PARTS = ("待确认", "审核清单", "review.html")
MEDIA = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov", ".txt", ".md"}

DEST = {
    "training": PROJECT / "assets" / "images" / "site" / "training",
    "operation": PROJECT / "assets" / "images" / "site" / "operation",
    "airspace": PROJECT / "assets" / "images" / "site" / "airspace",
    "airworthiness": PROJECT / "assets" / "images" / "site" / "airworthiness",
    "portfolio": PROJECT / "assets" / "images" / "portfolio",
    "regulation": PROJECT / "assets" / "data" / "regulations",
}

VIDEO_DEST = PROJECT / "assets" / "videos" / "training"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_item(path: Path) -> dict | None:
    name = path.stem
    if any(s in name for s in SKIP_PARTS):
        return None

    category = "unknown"
    doc_type = "其他材料"
    title = name

    for key, (cat, dtype) in CUSTOM_MAP.items():
        if name.startswith(key) or name == key:
            category, doc_type, title = cat, dtype, name
            break
    else:
        for prefix, cat in PREFIX_MAP.items():
            if name.startswith(prefix + "_"):
                category = cat
                rest = name[len(prefix) + 1 :]
                doc_type = rest.split("_")[0] if rest else "材料"
                title = rest.replace("_", " · ")
                break

    if category == "unknown":
        return None

    company = ""
    m = re.search(
        r"([\u4e00-\u9fff（）()·A-Za-z0-9]{2,40}(?:有限公司|有限责任公司|科技股份有限公司|职业技术学院))",
        name,
    )
    if m:
        company = m.group(1)

    return {
        "id": uuid.uuid5(uuid.NAMESPACE_URL, str(path)).hex[:12],
        "source": str(path.relative_to(PROJECT)).replace("\\", "/"),
        "filename": path.name,
        "category": category,
        "doc_type": doc_type,
        "company": company,
        "title": title,
        "media_type": "video" if path.suffix.lower() in {".mp4", ".webm", ".mov"} else ("text" if path.suffix.lower() in {".txt", ".md"} else "image"),
    }


def next_idx(folder: Path, prefix: str, ext: str) -> int:
    nums = [int(m.group(1)) for p in folder.glob(f"{prefix}-*") if (m := re.search(r"-(\d+)\.", p.name))]
    return max(nums, default=0) + 1


def ingest_file(item: dict, src: Path) -> str:
    cat = item["category"]
    ext = src.suffix.lower()

    if ext in {".txt", ".md"} and cat == "airspace":
        out_dir = DEST["regulation"]
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r'[<>:"/\\|?*\s]+', "_", item["title"])[:60]
        out = out_dir / f"{safe}.json"
        body = src.read_text(encoding="utf-8", errors="ignore").strip()
        out.write_text(
            json.dumps(
                {
                    "title": item["title"],
                    "category": cat,
                    "doc_type": item["doc_type"],
                    "body": body,
                    "source": item["source"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return str(out.relative_to(PROJECT)).replace("\\", "/")

    if item["media_type"] == "video":
        VIDEO_DEST.mkdir(parents=True, exist_ok=True)
        idx = next_idx(VIDEO_DEST, "training", ext.lstrip("."))
        out = VIDEO_DEST / f"training-{idx:02d}{ext}"
        shutil.copy2(src, out)
        return str(out.relative_to(PROJECT)).replace("\\", "/")

    folder = DEST.get(cat, DEST["training"])
    folder.mkdir(parents=True, exist_ok=True)
    prefix = {
        "training": "train",
        "operation": "oc",
        "airspace": "airspace",
        "airworthiness": "airworth",
        "portfolio": "work",
    }.get(cat, "material")
    idx = next_idx(folder, prefix, ext.lstrip("."))
    out = folder / f"{prefix}-{idx:02d}{ext}"
    shutil.copy2(src, out)
    return str(out.relative_to(PROJECT)).replace("\\", "/")


def maybe_organized(item: dict, src: Path) -> None:
    cat_map = {"training": "01_培训资质", "operation": "03_运营合格证", "airspace": "02_空域批复"}
    if item["category"] not in cat_map:
        return
    company = item.get("company") or "网站素材"
    folder = ORGANIZED / cat_map[item["category"]] / company
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{item['doc_type']}_{company}{src.suffix.lower()}"
    if not target.exists():
        shutil.copy2(src, target)


def dedupe_files(files: list[Path]) -> list[Path]:
    """同内容只保留文件名更短/无待确认的一条；用户重命名优先。"""
    by_hash: dict[str, Path] = {}
    for path in files:
        h = file_hash(path)
        prev = by_hash.get(h)
        if not prev:
            by_hash[h] = path
            continue
        score = lambda p: (("待确认" in p.stem) * 100, len(p.stem), p.name)
        if score(path) < score(prev):
            by_hash[h] = path
    return sorted(by_hash.values(), key=lambda p: p.name)


def main() -> None:
    if not IDENTIFIED.exists():
        print(f"目录不存在: {IDENTIFIED}")
        raise SystemExit(1)

    candidates = [p for p in IDENTIFIED.iterdir() if p.is_file() and p.suffix.lower() in MEDIA]
    files = dedupe_files(candidates)

    manifest = json.loads(SITE_MANIFEST.read_text(encoding="utf-8")) if SITE_MANIFEST.exists() else {"items": []}
    existing_sources = {x.get("source") for x in manifest.get("items", [])}
    touched: set[str] = set()
    count = 0

    for path in files:
        item = parse_item(path)
        if not item:
            print(f"SKIP {path.name}")
            continue
        if item["source"] in existing_sources:
            print(f"EXIST {path.name}")
            continue

        site_file = ingest_file(item, path)
        maybe_organized(item, path)
        touched.add(item["category"])

        body = ""
        if item["media_type"] == "text":
            body = path.read_text(encoding="utf-8", errors="ignore").strip()

        manifest.setdefault("items", []).append(
            {
                **item,
                "file": site_file,
                "body": body,
                "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
        count += 1
        print(f"OK {path.name} -> {site_file}")

    manifest["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    SITE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    SITE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    scripts = PROJECT / "scripts"
    if "operation" in touched and (scripts / "process_operation_only.py").exists():
        subprocess.run([sys.executable, str(scripts / "process_operation_only.py")], check=False)

    print(f"\n入库 {count} 项，合计 {len(manifest['items'])} 项 -> {SITE_MANIFEST}")


if __name__ == "__main__":
    main()
