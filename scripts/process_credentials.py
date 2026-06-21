# -*- coding: utf-8 -*-
"""Classify credential assets, minimal privacy redaction, export for website."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageFilter, ImageOps

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "_source" / "photos" / "credentials"
AIRSPACE_ROOT = PROJECT / "空域文件"
ORGANIZED_ROOT = Path.home() / "Desktop" / "苍凌工作室证件整理"
OUT = PROJECT / "assets" / "images" / "credentials"
MANIFEST = PROJECT / "assets" / "data" / "credentials-manifest.json"

SKIP_PARTS = (
    "身份证",
    "法人电话",
    "手机号",
    "账号密码",
    "申请坐标",
    "uom运营人信息",
    "uom账号",
    "UOM账号",
    "UOM信息",
    "UOM平台",
    "desktop.ini",
    "教员执照",
    "电子执照",
    "法人身份证",
    "公司法人及经办人联系方式",
    "法人身份证正反面",
)

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
PER_CATEGORY = 8
PER_OPERATION = 12
PER_AIRSPACE = 40
PER_TRAINING = 80
TRAINING_SKIP_COMPANIES = {
    "场地使用证明（场地租赁合同）",
    "线下培训",
    "未识别公司",
    "重庆军峰航空科技有限公司运营合格证",
}
HASH_COMPANY = re.compile(r"^[0-9a-f]{8,}|^企业微信|^扫描", re.I)
MAX_WIDTH = 2000
PDF_MIN_ZOOM = 2.5

PHONE_RE = re.compile(r"1[3-9]\d{9}")
NAME_HINTS = ("姓名", "联系人", "负责人", "法人代表", "操作员", "驾驶员")
NAME_VALUE_RE = re.compile(r"^[\u4e00-\u9fff]{2,4}$")

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
            return None
    return _ocr


def should_skip(path: Path) -> bool:
    if any(part in str(path) for part in SKIP_PARTS):
        return True
    if path.suffix.lower() in {".txt", ".docx"}:
        return True
    if re.search(r"账号|密码", path.name):
        return True
    return False


def source_rel(path: Path, base: Path) -> str:
    if base == ORGANIZED_ROOT:
        return ("证件整理/" + str(path.relative_to(base))).replace("\\", "/")
    if base == AIRSPACE_ROOT:
        return ("空域文件/" + str(path.relative_to(base))).replace("\\", "/")
    return str(path.relative_to(base)).replace("\\", "/")


def airspace_client_key(path: Path, base: Path) -> str:
    rel = path.relative_to(base)
    parts = rel.parts
    if "已批复" in parts:
        return path.stem
    skip_dirs = {
        "空域文件",
        "公司申请空域基础文件",
        "申请文件",
        "空域申请要求",
        "申报资料",
        "电子保函",
    }
    for part in reversed(parts[:-1]):
        if part in skip_dirs:
            continue
        if part.endswith((".pdf", ".jpg")):
            continue
        cleaned = re.sub(r"\s*\(\d+\)$", "", part)
        cleaned = cleaned.replace("空域申请材料", "").replace("空域申请资料", "").replace("空域申请函", "").strip()
        if len(cleaned) >= 4:
            return cleaned
    return path.stem


def pick_airspace_files() -> list[Path]:
    """One best document per company; prioritize 已批复 folder."""
    ranked: dict[str, tuple[int, Path, Path]] = {}
    roots = [r for r in (AIRSPACE_ROOT, ROOT) if r.exists()]
    for base in roots:
        for path in base.rglob("*"):
            if path.suffix.lower() not in EXTS or should_skip(path):
                continue
            if classify(path) != "airspace":
                continue
            key = airspace_client_key(path, base)
            score = score_file(path, "airspace")
            if "已批复" in str(path):
                score += 50
            if "空域申请函" in path.name or "批件" in path.name or "批复" in path.name:
                score += 20
            prev = ranked.get(key)
            if not prev or score > prev[0]:
                ranked[key] = (score, path, base)
    ordered = sorted(ranked.values(), key=lambda x: (-x[0], x[1].name))
    return [p for _, p, _ in ordered[:PER_AIRSPACE]]


def classify(path: Path) -> str | None:
    text = str(path)
    name = path.name
    if "运营合格证" in text or "运营合格证" in name:
        return "operation"
    if any(k in text or k in name for k in ("空域", "飞行申请", "临时空域", "批件", "批文", "批复", "放飞", "飞行计划")):
        return "airspace"
    if any(k in text or k in name for k in ("空域申请", "申请函", "空域使用")):
        return "airspace"
    if any(
        k in text or k in name
        for k in ("合格证", "培训", "训练大纲", "培训手册", "已获证", "AOPA", "ALPA", "训练手册")
    ):
        return "training"
    if "已获证" in text:
        return "training"
    return None


def score_file(path: Path, category: str) -> int:
    score = 0
    name = path.name
    text = str(path)
    suffix = path.suffix.lower()

    if category == "training":
        if any(k in name for k in ("合格证", "培训手册", "训练大纲", "训练手册")):
            score += 30
        if "培训无人机" in name or "训练飞机" in text:
            score -= 40
        if "培训场地" in name:
            score += 5
    elif category == "airspace":
        if any(k in name for k in ("批件", "批文", "批复", "空域文件", "空域批")):
            score += 30
    elif category == "operation":
        if "运营合格证" in name:
            score += 30
        if re.search(r"运营合格证[_\s]?[^_.]*\.(pdf|jpg|jpeg|png)$", name, re.I):
            score += 25
        if any(k in name for k in ("代办", "劳务合同", "合同", "申请材料", "UOM", "uom")):
            score -= 40

    if suffix in {".png", ".jpg", ".jpeg"}:
        score += 10
    elif suffix == ".pdf":
        score += 8
    if "扫描" in name:
        score -= 1
    return score


def load_image(path: Path) -> Image.Image:
    if path.suffix.lower() == ".pdf":
        doc = fitz.open(path)
        page = doc[0]
        zoom = max(PDF_MIN_ZOOM, MAX_WIDTH / page.rect.width)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
    else:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")

    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.Resampling.LANCZOS)
    return img


def quad_to_box(quad, pad_ratio: float = 0.06) -> tuple[int, int, int, int]:
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
    pad = int(max(x2 - x1, y2 - y1) * pad_ratio) + 2
    return x1 - pad, y1 - pad, x2 + pad, y2 + pad


def mosaic_region(img: Image.Image, box: tuple[int, int, int, int], block: int = 10) -> None:
    x1, y1, x2, y2 = box
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.width, x2), min(img.height, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return
    region = img.crop((x1, y1, x2, y2))
    w, h = region.size
    small = region.resize((max(1, w // block), max(1, h // block)), Image.Resampling.NEAREST)
    region = small.resize((w, h), Image.Resampling.NEAREST)
    img.paste(region, (x1, y1))


def detect_qr_boxes(rgb: np.ndarray) -> list[tuple[int, int, int, int]]:
    boxes: list[tuple[int, int, int, int]] = []
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    detector = cv2.QRCodeDetector()

    ok, points = detector.detect(gray)
    if ok and points is not None:
        pts = points[0].astype(int)
        boxes.append(quad_to_box(pts.tolist(), pad_ratio=0.05))

    try:
        retval, _, pts, _ = detector.detectAndDecodeMulti(gray)
        if retval and pts is not None:
            for quad in pts:
                boxes.append(quad_to_box(quad.astype(int).tolist(), pad_ratio=0.05))
    except Exception:
        pass
    return boxes


def detect_ocr_boxes(rgb: np.ndarray) -> list[tuple[int, int, int, int]]:
    boxes: list[tuple[int, int, int, int]] = []
    ocr = get_ocr()
    if not ocr:
        return boxes

    try:
        result, _ = ocr(rgb)
    except Exception:
        return boxes
    if not result:
        return boxes

    lines: list[tuple[list, str]] = []
    for item in result:
        if len(item) < 2:
            continue
        box, text = item[0], str(item[1]).strip()
        if not text:
            continue
        lines.append((box, text))

    for box, text in lines:
        compact = re.sub(r"\s+", "", text)
        if PHONE_RE.search(compact):
            for match in PHONE_RE.finditer(compact):
                # blur whole OCR line containing phone
                boxes.append(quad_to_box(box, pad_ratio=0.08))
                break

    for i, (box, text) in enumerate(lines):
        compact = re.sub(r"\s+", "", text)
        if any(h in compact for h in NAME_HINTS):
            # blur value on same line after colon or next line
            if "：" in compact or ":" in compact:
                boxes.append(quad_to_box(box, pad_ratio=0.05))
            elif i + 1 < len(lines):
                nbox, ntext = lines[i + 1]
                ncompact = re.sub(r"\s+", "", ntext)
                if NAME_VALUE_RE.match(ncompact) or len(ncompact) <= 6:
                    boxes.append(quad_to_box(nbox, pad_ratio=0.08))
        elif NAME_VALUE_RE.match(compact) and i > 0:
            prev = re.sub(r"\s+", "", lines[i - 1][1])
            if any(h in prev for h in NAME_HINTS):
                boxes.append(quad_to_box(box, pad_ratio=0.08))

    return boxes


def merge_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []
    merged = boxes[:]
    changed = True
    while changed:
        changed = False
        out: list[tuple[int, int, int, int]] = []
        used = [False] * len(merged)
        for i, a in enumerate(merged):
            if used[i]:
                continue
            x1, y1, x2, y2 = a
            for j in range(i + 1, len(merged)):
                if used[j]:
                    continue
                bx1, by1, bx2, by2 = merged[j]
                if not (bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2):
                    x1, y1, x2, y2 = min(x1, bx1), min(y1, by1), max(x2, bx2), max(y2, by2)
                    used[j] = True
                    changed = True
            used[i] = True
            out.append((x1, y1, x2, y2))
        merged = out
    return merged


def redact_privacy(img: Image.Image) -> Image.Image:
    rgb = np.array(img)
    boxes = detect_qr_boxes(rgb) + detect_ocr_boxes(rgb)
    boxes = merge_boxes(boxes)
    for box in boxes:
        mosaic_region(img, box, block=12)
    return img


def display_title(path: Path, category: str) -> str:
    mapping = {
        "training": "培训资质",
        "airspace": "空域申请",
        "operation": "运营合格证",
    }
  # organized: 培训合格证_公司名.pdf
    stem = path.stem
    if "_" in stem:
        doc, company = stem.split("_", 1)
        return f"{mapping[category]} · {doc} · {company[:24]}"
    name = stem
    if "批件" in name or "批文" in name or "批复" in name:
        suffix = name
    elif "运营合格证" in name:
        suffix = "运营合格证"
    elif "合格证" in name:
        suffix = "培训合格证"
    elif "培训手册" in name or "训练大纲" in name or "训练手册" in name:
        suffix = name
    else:
        suffix = name if len(name) <= 28 else name[:28] + "…"
    return f"{mapping[category]} · {suffix}"


def pick_training_files() -> list[Path]:
    """One primary doc per training company from organized desktop folder."""
    folder = ORGANIZED_ROOT / "01_培训资质"
    if not folder.exists():
        return _pick_training_legacy()

    by_company: dict[str, list[tuple[int, Path]]] = {}
    for path in folder.rglob("*"):
        if path.suffix.lower() not in EXTS or should_skip(path):
            continue
        company = path.parent.name
        if company in TRAINING_SKIP_COMPANIES or HASH_COMPANY.match(company):
            continue
        if "运营合格证" in path.name and "培训" not in path.name:
            continue
        score = score_file(path, "training")
        if "培训合格证" in path.name:
            score += 50
        elif "培训手册" in path.name or "训练手册" in path.name:
            score += 35
        elif "训练大纲" in path.name:
            score += 30
        by_company.setdefault(company, []).append((score, path))

    picked: list[Path] = []
    for company in sorted(by_company.keys()):
        ranked = sorted(by_company[company], key=lambda x: -x[0])
        picked.append(ranked[0][1])
        for score, p in ranked[1:]:
            if len(picked) >= PER_TRAINING:
                break
            if any(k in p.name for k in ("培训手册", "训练大纲")) and sum(
                1 for x in picked if x.parent.name == company
            ) < 2:
                picked.append(p)
        if len(picked) >= PER_TRAINING:
            break
    return picked[:PER_TRAINING]


def _pick_training_legacy() -> list[Path]:
    buckets: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.suffix.lower() not in EXTS or should_skip(path):
            continue
        if classify(path) == "training":
            buckets.append(path)
    ranked = sorted(buckets, key=lambda p: score_file(p, "training"), reverse=True)
    return ranked[:PER_CATEGORY]


def operation_client_key(path: Path) -> str:
    stem = path.stem
    if "运营合格证" in stem:
        company = re.sub(r"^[\d._\-]+", "", stem.replace("运营合格证", "")).strip()
        if len(company) >= 4:
            return company
    for part in reversed(path.parts):
        if part in ("运营合格证", "03_运营合格证", "caac培训资质"):
            continue
        cleaned = re.sub(r"运营合格证.*", "", part).strip()
        if len(cleaned) >= 4 and not HASH_COMPANY.match(cleaned):
            return cleaned
    return path.parent.name


def pick_operation_files() -> list[Path]:
    ranked: dict[str, tuple[int, Path]] = {}

    def consider(path: Path) -> None:
        if path.suffix.lower() not in EXTS or should_skip(path):
            return
        if classify(path) != "operation":
            return
        company = operation_client_key(path)
        if HASH_COMPANY.match(company):
            return
        score = score_file(path, "operation")
        prev = ranked.get(company)
        if not prev or score > prev[0]:
            ranked[company] = (score, path)

    folder = ORGANIZED_ROOT / "03_运营合格证"
    if folder.exists():
        for path in folder.rglob("*"):
            consider(path)

    if ROOT.exists():
        for path in ROOT.rglob("*"):
            consider(path)

    return [p for _, p in sorted(ranked.values(), key=lambda x: -x[0])][:PER_OPERATION]


def pick_airspace_from_organized() -> list[Path]:
    folder = ORGANIZED_ROOT / "02_空域批复"
    if not folder.exists():
        return pick_airspace_files()
    ranked: dict[str, tuple[int, Path]] = {}
    for path in folder.rglob("*"):
        if path.suffix.lower() not in EXTS or should_skip(path):
            continue
        company = path.parent.name
        if HASH_COMPANY.match(company):
            continue
        score = score_file(path, "airspace")
        if "批复" in path.name or "批件" in path.name:
            score += 20
        prev = ranked.get(company)
        if not prev or score > prev[0]:
            ranked[company] = (score, path)
    ordered = sorted(ranked.values(), key=lambda x: -x[0])
    return [p for _, p in ordered[:PER_AIRSPACE]]


def pick_files() -> dict[str, list[Path]]:
    return {
        "training": pick_training_files(),
        "operation": pick_operation_files(),
        "airspace": pick_airspace_from_organized(),
    }


def file_base(src: Path) -> Path:
    if ORGANIZED_ROOT.exists():
        try:
            src.relative_to(ORGANIZED_ROOT)
            return ORGANIZED_ROOT
        except ValueError:
            pass
    if AIRSPACE_ROOT.exists():
        try:
            src.relative_to(AIRSPACE_ROOT)
            return AIRSPACE_ROOT
        except ValueError:
            pass
    return ROOT


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    for cat in ("training", "airspace", "operation"):
        (OUT / cat).mkdir(parents=True, exist_ok=True)

    selected = pick_files()
    manifest: dict[str, list[dict]] = {"training": [], "airspace": [], "operation": []}

    for cat, files in selected.items():
        for idx, src in enumerate(files, start=1):
            out_name = f"{cat}-{idx:02d}.jpg"
            out_path = OUT / cat / out_name
            base = file_base(src)
            try:
                img = load_image(src)
                img = redact_privacy(img)
                img.save(out_path, "JPEG", quality=92, optimize=True)
                manifest[cat].append(
                    {
                        "file": f"assets/images/credentials/{cat}/{out_name}",
                        "title": display_title(src, cat),
                        "source": source_rel(src, base),
                    }
                )
                print(f"OK {cat} {out_name} <- {src.name}")
            except Exception as exc:
                print(f"FAIL {src}: {exc}")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifest:", MANIFEST)


if __name__ == "__main__":
    main()
