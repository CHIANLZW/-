# -*- coding: utf-8 -*-
"""将审核通过的素材入库网站（复制文件 + 更新 manifest + 可选重新生成证件图）。"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REVIEW_JSON = PROJECT / "assets" / "data" / "materials-review.json"
SITE_MANIFEST = PROJECT / "assets" / "data" / "site-materials-manifest.json"
CREDENTIALS_MANIFEST = PROJECT / "assets" / "data" / "credentials-manifest.json"
ORGANIZED = Path.home() / "Desktop" / "苍凌工作室证件整理"

DEST = {
    "training": PROJECT / "assets" / "images" / "site" / "training",
    "operation": PROJECT / "assets" / "images" / "site" / "operation",
    "airspace": PROJECT / "assets" / "images" / "site" / "airspace",
    "airworthiness": PROJECT / "assets" / "images" / "site" / "airworthiness",
    "regulation": PROJECT / "assets" / "data" / "regulations",
    "portfolio": PROJECT / "assets" / "images" / "portfolio",
    "site": PROJECT / "assets" / "images" / "site",
    "unknown": PROJECT / "assets" / "images" / "site" / "pending",
}

ORGANIZED_CAT = {
    "training": "01_培训资质",
    "operation": "03_运营合格证",
    "airspace": "02_空域批复",
}


def slug(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\s]+', "_", name)
    return re.sub(r"_+", "_", name).strip("_")[:80]


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def next_index(folder: Path, prefix: str, ext: str) -> int:
    nums = []
    for p in folder.glob(f"{prefix}-*.{ext.lstrip('.')}"):
        m = re.search(r"-(\d+)$", p.stem)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def copy_to_site(item: dict, src: Path) -> tuple[str, Path]:
    category = item.get("category", "unknown")
    ext = src.suffix.lower()
    folder = DEST.get(category, DEST["unknown"])
    folder.mkdir(parents=True, exist_ok=True)

    if ext in {".txt", ".md"}:
        reg_dir = DEST["regulation"]
        reg_dir.mkdir(parents=True, exist_ok=True)
        out = reg_dir / f"{slug(item['proposed_name'].rsplit('.', 1)[0])}.json"
        text = src.read_text(encoding="utf-8", errors="ignore")
        payload = {
            "title": item.get("title") or item["proposed_name"],
            "category": category,
            "doc_type": item.get("doc_type"),
            "body": text.strip(),
            "ingested_from": item["original"],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        rel = str(out.relative_to(PROJECT)).replace("\\", "/")
        return rel, out

    prefix = {
        "training": "train-scene",
        "operation": "oc-scene",
        "airspace": "airspace-scene",
        "airworthiness": "airworth-scene",
        "portfolio": "work",
        "site": "site",
    }.get(category, "material")

    idx = next_index(folder, prefix, ext.lstrip("."))
    out_name = f"{prefix}-{idx:02d}{ext}"
    out = folder / out_name
    shutil.copy2(src, out)
    rel = str(out.relative_to(PROJECT)).replace("\\", "/")
    return rel, out


def maybe_copy_organized(item: dict, src: Path) -> None:
    category = item.get("category")
    if category not in ORGANIZED_CAT:
        return
    doc_type = item.get("doc_type", "材料")
    company = item.get("company") or "未识别公司"
    if company == "未识别公司":
        return
    folder = ORGANIZED / ORGANIZED_CAT[category] / company
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{doc_type}_{company}{src.suffix.lower()}"
    if not target.exists():
        shutil.copy2(src, target)


def append_site_manifest(entry: dict) -> None:
    data = load_json(SITE_MANIFEST, {"items": []})
    ids = {x["id"] for x in data["items"]}
    if entry["id"] not in ids:
        data["items"].append(entry)
    else:
        data["items"] = [entry if x["id"] == entry["id"] else x for x in data["items"]]
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_json(SITE_MANIFEST, data)


def run_credential_refresh(categories: set[str]) -> None:
    scripts = PROJECT / "scripts"
    if "operation" in categories and (scripts / "process_operation_only.py").exists():
        subprocess.run([sys.executable, str(scripts / "process_operation_only.py")], check=False)
    if categories & {"training", "airspace"} and (scripts / "process_credentials.py").exists():
        print("提示：培训/空域证件图需完整重建时可手动运行 py scripts/process_credentials.py")


def main() -> None:
    if not REVIEW_JSON.exists():
        print(f"未找到审核清单，请先运行 py scripts/identify_materials.py")
        raise SystemExit(1)

    review = load_json(REVIEW_JSON, {"items": []})
    approved = [it for it in review.get("items", []) if it.get("status") == "approved"]
    if not approved:
        pending = sum(1 for it in review.get("items", []) if it.get("status") == "pending")
        print(f"无 approved 项（待审核 {pending} 项）。请编辑 {REVIEW_JSON} 或在 review.html 中通过审核。")
        raise SystemExit(0)

    touched_categories: set[str] = set()
    ingested = 0

    for item in approved:
        src_rel = item.get("identified_copy") or item.get("original")
        src = PROJECT / src_rel.replace("/", "\\")
        if not src.exists():
            print(f"SKIP 文件不存在: {src_rel}")
            continue

        site_path, out_path = copy_to_site(item, src)
        maybe_copy_organized(item, src)
        touched_categories.add(item.get("category", ""))

        append_site_manifest(
            {
                "id": item["id"],
                "file": site_path,
                "title": item.get("title") or item["proposed_name"],
                "category": item.get("category"),
                "doc_type": item.get("doc_type"),
                "company": item.get("company", ""),
                "site_target": item.get("site_target", ""),
                "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": item.get("original"),
            }
        )
        item["ingested_file"] = site_path
        item["ingested_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ingested += 1
        print(f"OK {item['proposed_name']} -> {site_path}")

    review["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_json(REVIEW_JSON, review)
    save_json(SITE_MANIFEST, load_json(SITE_MANIFEST, {"items": []}))

    if touched_categories & {"operation", "training", "airspace"}:
        run_credential_refresh(touched_categories)

    print(f"\n已入库 {ingested} 项 -> {SITE_MANIFEST}")


if __name__ == "__main__":
    main()
