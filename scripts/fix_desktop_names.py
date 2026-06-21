# -*- coding: utf-8 -*-
"""OCR rename hash / unknown company folders on desktop archive."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import fitz
from PIL import Image, ImageOps

DESKTOP = Path.home() / "Desktop" / "苍凌工作室证件整理"
HASH = re.compile(r"^[0-9a-f]{8,}", re.I)
COMPANY_RE = re.compile(
    r"([\u4e00-\u9fff（）()·A-Za-z0-9]{2,50}"
    r"(?:有限公司|有限责任公司|职业技术学院|职业培训学校|培训中心|职业学校|科技公司|工作室))"
)
SKIP = {"场地使用证明（场地租赁合同）", "线下培训", "未识别公司"}

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
    return _ocr


def ocr_text(path: Path) -> str:
    ocr = get_ocr()
    if not ocr:
        return ""
    try:
        if path.suffix.lower() == ".pdf":
            doc = fitz.open(path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            doc.close()
        else:
            img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        import numpy as np
        result, _ = ocr(np.array(img))
        if not result:
            return ""
        return " ".join(str(x[1]) for x in result if len(x) > 1)
    except Exception:
        return ""


def company_from_text(text: str) -> str:
    found = COMPANY_RE.findall(text)
    if found:
        return max(found, key=len)
    return ""


def company_from_file(path: Path) -> str:
    c = company_from_text(ocr_text(path))
    if c:
        return c
    stem = path.stem
    if "有限公司" in stem or "学院" in stem:
        m = COMPANY_RE.search(stem.split("_", 1)[-1])
        if m:
            return m.group(1)
    return ""


def merge_company_dir(category: Path, bad_name: str, good_name: str) -> None:
    src = category / bad_name
    dst = category / good_name
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file():
            new_name = f.name.replace(bad_name, good_name)
            target = dst / new_name
            if target.exists():
                f.unlink()
            else:
                shutil.move(str(f), str(target))
    try:
        src.rmdir()
    except OSError:
        pass


def main() -> None:
    if not DESKTOP.exists():
        print("missing", DESKTOP)
        return
    fixed = 0
    for cat in DESKTOP.iterdir():
        if not cat.is_dir():
            continue
        for company_dir in list(cat.iterdir()):
            if not company_dir.is_dir():
                continue
            name = company_dir.name
            if name in SKIP:
                shutil.rmtree(company_dir, ignore_errors=True)
                continue
            if name.endswith("材料"):
                good = name.replace("材料", "").strip()
                merge_company_dir(cat, name, good)
                fixed += 1
                continue
            if not HASH.match(name) and "有限公司" in name or "学院" in name:
                continue
            if not HASH.match(name) and not name.startswith(("企业微信", "扫描")):
                continue
            # try OCR from files
            good = ""
            for f in company_dir.iterdir():
                if f.is_file() and f.suffix.lower() in {".pdf", ".jpg", ".png"}:
                    good = company_from_file(f)
                    if good:
                        break
            if not good:
                # try filename without hash
                for f in company_dir.iterdir():
                    part = f.stem.split("_", 1)[-1]
                    if "有限公司" in part:
                        good = part
                        break
            if good:
                merge_company_dir(cat, name, good)
                fixed += 1
                print(f"renamed {name} -> {good}")
            else:
                print(f"skip {name}")
    print(f"fixed {fixed}")


if __name__ == "__main__":
    main()
