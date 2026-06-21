# -*- coding: utf-8 -*-
"""识别 素材/ 中的照片、视频、文字，生成建议文件名与审核清单。"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

PROJECT = Path(__file__).resolve().parent.parent
INBOX = PROJECT / "素材"
IDENTIFIED = INBOX / "已识别"
REVIEW_JSON = PROJECT / "assets" / "data" / "materials-review.json"
REVIEW_MD = INBOX / "审核清单.md"

MEDIA_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pdf"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"}
TEXT_EXT = {".txt", ".md"}

COMPANY_RE = re.compile(
    r"([\u4e00-\u9fff（）()·A-Za-z0-9]{2,40}"
    r"(?:有限公司|有限责任公司|职业技术学院|职业培训学校|培训中心|职业学校|科技公司|科技股份有限公司))"
)

CATEGORY_LABEL = {
    "training": "培训资质",
    "operation": "运营合格证",
    "airspace": "空域申请",
    "airworthiness": "适航审定",
    "regulation": "法规政策",
    "portfolio": "创意项目",
    "site": "网站配图",
    "unknown": "待确认",
}

DOC_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("运营合格证", "operation", ("民用无人驾驶航空器运营合格证", "AIR OPERATOR CERTIFICATE", "UAOC-O")),
    ("培训合格证", "training", ("训练机构合格证", "训练机构 合格证", "AOPA CHINA", "民用无人机驾驶员训练机构")),
    ("证件合集", "training", ("ASFC", "遥控模型", "飞行员执照", "飞行活动报告", "驾驶员合格证")),
    ("空域批复", "airspace", ("空域批", "飞行管制", "南部战区", "北部战区", "中部战区", "飞行活动报备表")),
    ("空域申请函", "airspace", ("申请函", "申请在", "临时空域")),
    ("团体标准", "training", ("团体标准", "T/AOPA", "T/CAGIS", "T/CHALPA", "训练机构规范", "实践飞行场地", "旋翼飞行器类别", "9.2.1", "9.3.1")),
    ("培训通知", "airworthiness", ("适航人员", "型号合格", "设计保证系统", "DAS", "适航管理", "民航明传电报", "民航管理干部学院")),
    ("培训通知", "training", ("培训通知", "培训班", "培训班的通知", "操控员训练")),
    ("政策通知", "training", ("训练机构", "云系统", "机载计时", "地理信息产业协会")),
    ("政策解读", "airspace", ("适飞空域", "低空飞行服务", "空域范围", "jfsc.cn")),
    ("培训教材", "training", ("航空知识手册", "训练大纲", "培训手册", "驾驶员手册", "无人机驾驶员")),
    ("培训现场", "training", ("实操", "训练场", "课堂", "概述", "无人机的定义", "多旋翼", "室外")),
    ("行业动态", "training", ("慧飞", "UTC", "关停", "公告")),
    ("平台截图", "airspace", ("NOTAM", "AIRSPACE", "Navigation Warning")),
    ("活动影像", "portfolio", ("车友", "夜", "overpass", "停车")),
]

SITE_TARGET = {
    "training": "low-altitude.html#sector-training",
    "operation": "low-altitude.html#sector-operations",
    "airspace": "low-altitude.html#sector-operations",
    "airworthiness": "low-altitude.html#sector-airworthiness",
    "regulation": "low-altitude.html",
    "portfolio": "portfolio.html",
    "site": "index.html",
    "unknown": "",
}

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is False:
        return None
    if _ocr is None:
        try:
            from rapidocr_onnxruntime import RapidOCR

            _ocr = RapidOCR()
        except Exception:
            _ocr = False
    return _ocr if _ocr else None


def read_text(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXT:
        for enc in ("utf-8", "utf-8-sig", "gbk"):
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="ignore")

    if path.suffix.lower() not in MEDIA_EXT:
        return ""

    ocr = get_ocr()
    if not ocr:
        return ""

    try:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        result, _ = ocr(img)
        if not result:
            return ""
        return "\n".join(line[1] for line in result if len(line) > 1)
    except Exception:
        return ""


def extract_company(text: str) -> str:
    hits = COMPANY_RE.findall(text)
    if hits:
        return max(hits, key=len)[:40]
    return ""


def classify(text: str, path: Path) -> tuple[str, str, str, float]:
    blob = text + "\n" + path.name
    best_cat = "unknown"
    best_doc = "其他材料"
    best_score = 0

    for doc_type, category, keywords in DOC_RULES:
        score = sum(3 for kw in keywords if kw.lower() in blob.lower() or kw in blob)
        if score > best_score:
            best_score = score
            best_doc = doc_type
            best_cat = category

    if path.suffix.lower() in VIDEO_EXT:
        if best_score < 3:
            return "training", "培训现场", "", 0.55

    if path.suffix.lower() in TEXT_EXT:
        if "适飞空域" in blob or "低空飞行服务" in blob:
            return "airspace", "政策解读", extract_company(blob) or "江苏省", 0.9
        return "regulation", "文字素材", "", 0.7

    confidence = min(0.95, 0.35 + best_score * 0.08) if best_score else 0.2
    company = extract_company(blob)
    return best_cat, best_doc, company, confidence


def make_title(doc_type: str, company: str, text: str, path: Path) -> str:
    if path.suffix.lower() in TEXT_EXT:
        first = text.strip().splitlines()[0][:60] if text.strip() else path.stem
        return first

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if len(ln) >= 8 and any(k in ln for k in ("通知", "标准", "规范", "合格证", "报备", "电报")):
            return ln[:80]
    if company:
        return f"{doc_type} · {company}"
    return doc_type


def safe_slug(*parts: str) -> str:
    raw = "_".join(p for p in parts if p)
    raw = re.sub(r'[<>:"/\\|?*\s]+', "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw[:120] or "未命名素材"


def proposed_filename(category: str, doc_type: str, company: str, title: str, path: Path) -> str:
    short = path.stem[:8] if len(path.stem) > 12 else path.stem
    parts = [CATEGORY_LABEL.get(category, category), doc_type]
    if company:
        parts.append(company[:20])
    elif title and title != doc_type:
        parts.append(title[:24])
    parts.append(short)
    return safe_slug(*parts) + path.suffix.lower()


def scan_inbox() -> list[Path]:
    if not INBOX.exists():
        return []
    skip_dirs = {"已识别", "_ingested"}
    files: list[Path] = []
    for path in sorted(INBOX.iterdir()):
        if path.is_dir():
            if path.name not in skip_dirs:
                for sub in path.rglob("*"):
                    if sub.is_file() and sub.suffix.lower() in MEDIA_EXT | VIDEO_EXT | TEXT_EXT:
                        files.append(sub)
            continue
        if path.suffix.lower() in MEDIA_EXT | VIDEO_EXT | TEXT_EXT:
            files.append(path)
    return files


def load_review() -> dict:
    if REVIEW_JSON.exists():
        return json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    return {"version": 1, "updated": "", "items": []}


def main() -> None:
    IDENTIFIED.mkdir(parents=True, exist_ok=True)
    REVIEW_JSON.parent.mkdir(parents=True, exist_ok=True)

    existing = load_review()
    by_original = {item["original"]: item for item in existing.get("items", [])}

    items: list[dict] = []
    for path in scan_inbox():
        rel_original = str(path.relative_to(PROJECT)).replace("\\", "/")
        text = read_text(path)
        category, doc_type, company, confidence = classify(text, path)
        title = make_title(doc_type, company, text, path)
        proposed = proposed_filename(category, doc_type, company, title, path)

        prev = by_original.get(rel_original)
        item_id = prev["id"] if prev else uuid.uuid4().hex[:12]
        status = prev.get("status", "pending") if prev else "pending"

        identified_copy = IDENTIFIED / proposed
        if not identified_copy.exists() or identified_copy.stat().st_size != path.stat().st_size:
            shutil.copy2(path, identified_copy)

        items.append(
            {
                "id": item_id,
                "original": rel_original,
                "identified_copy": str(identified_copy.relative_to(PROJECT)).replace("\\", "/"),
                "proposed_name": proposed,
                "category": category,
                "category_label": CATEGORY_LABEL.get(category, category),
                "doc_type": doc_type,
                "company": company,
                "title": title,
                "summary": (text[:240] + "…") if len(text) > 240 else text,
                "site_target": SITE_TARGET.get(category, ""),
                "status": status,
                "confidence": round(confidence, 2),
                "media_type": "video" if path.suffix.lower() in VIDEO_EXT else ("text" if path.suffix.lower() in TEXT_EXT else "image"),
            }
        )
        print(f"[{category}/{doc_type}] {path.name} -> {proposed} ({confidence:.0%})")

    payload = {
        "version": 1,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "status: pending=待审核 | approved=已通过 | rejected=已拒绝。审核后运行 py scripts/ingest_materials.py",
        "items": items,
    }
    REVIEW_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 素材审核清单",
        "",
        f"更新时间：{payload['updated']}",
        "",
        "识别结果已复制到 `素材/已识别/`，请核对建议文件名。",
        "",
        "**审核方式**",
        "1. 打开 `素材/review.html` 在浏览器中勾选通过/拒绝",
        "2. 或直接编辑 `assets/data/materials-review.json` 把 `status` 改为 `approved`",
        "3. 确认后运行：`py scripts/ingest_materials.py`",
        "",
        "---",
        "",
    ]
    for i, it in enumerate(items, 1):
        lines += [
            f"## {i}. {it['proposed_name']}",
            "",
            f"- **分类**：{it['category_label']} / {it['doc_type']}",
            f"- **建议上线位置**：{it['site_target'] or '—'}",
            f"- **置信度**：{it['confidence']:.0%}",
            f"- **状态**：{it['status']}",
            f"- **原文件**：`{it['original']}`",
            f"- **识别副本**：`{it['identified_copy']}`",
        ]
        if it.get("company"):
            lines.append(f"- **企业/机构**：{it['company']}")
        if it.get("title"):
            lines.append(f"- **标题**：{it['title']}")
        if it.get("summary"):
            lines.append(f"- **摘要**：{it['summary'][:200]}")
        lines.append("")

    REVIEW_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n共 {len(items)} 项 -> {REVIEW_JSON}")
    print(f"审核清单 -> {REVIEW_MD}")
    print(f"识别副本 -> {IDENTIFIED}")


if __name__ == "__main__":
    main()
