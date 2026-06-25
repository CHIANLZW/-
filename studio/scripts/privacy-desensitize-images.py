# -*- coding: utf-8 -*-
"""
工作室官网图片隐私脱敏：对公司名/联系人单字打小面积马赛克
依赖：pip install rapidocr-onnxruntime opencv-python-headless pillow numpy
用法：python studio/scripts/privacy-desensitize-images.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    print("请先安装: pip install rapidocr-onnxruntime opencv-python-headless pillow numpy")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
IMG_ROOT = ROOT / "assets" / "images"
DATA = ROOT / "assets" / "data"

COMPANY_SUFFIXES = ("有限责任公司", "股份有限公司", "有限公司", "培训学校")
PHONE_RE = re.compile(r"1[3-9]\d{9}")
COMPANY_RE = re.compile(
    r"[\u4e00-\u9fff（(][\u4e00-\u9fff]{1,28}(?:有限责任公司|股份有限公司|有限公司|培训学校)"
)
PERSON_RE = re.compile(r"([\u4e00-\u9fff]{1,3})(老师|先生|女士|经理)")


def hash_seed(s: str) -> int:
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h


def mask_company(name: str) -> str:
    body, suffix = name.strip(), ""
    for s in COMPANY_SUFFIXES:
        if body.endswith(s):
            suffix, body = s, body[: -len(s)]
            break
    chars = list(body)
    if len(chars) <= 1:
        return name
    if len(chars) == 2:
        chars[1] = "*"
        return "".join(chars) + suffix
    h = hash_seed(name)
    i1 = 1 + (h % (len(chars) - 1))
    i2 = 1 + ((h >> 8) % (len(chars) - 1))
    if i1 == i2:
        i2 = i1 + 1 if i1 < len(chars) - 1 else i1 - 1
    chars[i1] = chars[i2] = "*"
    return "".join(chars) + suffix


def collect_keywords() -> set[str]:
    keys: set[str] = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    if k in ("name", "company", "title", "source") and any(
                        x in v for x in COMPANY_SUFFIXES
                    ):
                        keys.add(v)
                        keys.add(mask_company(v))
                    for m in COMPANY_RE.findall(v):
                        keys.add(m)
                    for prefix, suffix in PERSON_RE.findall(v):
                        keys.add(prefix + suffix)
                        if len(prefix) == 1:
                            keys.add("*" + suffix)
                        else:
                            chars = list(prefix)
                            idx = 1 + (hash_seed(prefix) % max(1, len(chars) - 1))
                            chars[idx] = "*"
                            keys.add("".join(chars) + suffix)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for i in obj:
                walk(i)

    for p in DATA.glob("*.json"):
        try:
            walk(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return {k for k in keys if k and len(k) >= 2 and not PHONE_RE.search(k)}


def mosaic(img: np.ndarray, x1: int, y1: int, x2: int, y2: int, block: int = 6) -> None:
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return
    roi = img[y1:y2, x1:x2]
    rh, rw = roi.shape[:2]
    small = cv2.resize(roi, (max(1, rw // block), max(1, rh // block)), interpolation=cv2.INTER_LINEAR)
    img[y1:y2, x1:x2] = cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)


def mosaic_char_span(img: np.ndarray, box, text: str, span: str) -> None:
    x1, y1, x2, y2 = box
    idx = text.find(span)
    if idx < 0:
        return
    n = max(len(text), 1)
    w = x2 - x1
    char_w = w / n
    sx1 = int(x1 + idx * char_w)
    sx2 = int(x1 + (idx + len(span)) * char_w)
    mosaic(img, sx1, y1, sx2, y2, block=5)


def process_image(path: Path, ocr: RapidOCR, keywords: set[str]) -> bool:
    data = path.read_bytes()
    arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        return False
    changed = False
    result, _ = ocr(arr)
    if not result:
        return False
    for item in result:
        box, text, _score = item[0], item[1], item[2]
        if not text or PHONE_RE.search(text):
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        rect = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
        for kw in keywords:
            if kw in text:
                mosaic_char_span(arr, rect, text, kw)
                changed = True
        for m in COMPANY_RE.findall(text):
            masked = mask_company(m)
            for frag in {m, masked}:
                if frag in text:
                    for ch in frag:
                        if ch == "*":
                            continue
                        idx = text.find(frag)
                        if idx >= 0:
                            pos = text.find(ch, idx, idx + len(frag))
                            if pos >= 0:
                                mosaic_char_span(arr, rect, text, ch)
                                changed = True
        for prefix, suffix in PERSON_RE.findall(text):
            token = prefix + suffix
            if token in text:
                target = "*" + suffix if len(prefix) == 1 else prefix[0] + "*" + suffix[1:] if len(prefix) > 1 else token
                for ch in prefix:
                    if ch in text:
                        mosaic_char_span(arr, rect, text, ch)
                        changed = True
    if changed:
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])[1].tofile(path)
        elif ext == ".png":
            cv2.imencode(".png", arr)[1].tofile(path)
        else:
            Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)).save(path)
    return changed


def main():
    if not IMG_ROOT.is_dir():
        print("图片目录不存在:", IMG_ROOT)
        return
    print("收集关键词…")
    keywords = collect_keywords()
    print(f"关键词 {len(keywords)} 个，初始化 OCR…")
    ocr = RapidOCR()
    files = [p for p in IMG_ROOT.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    done = 0
    for i, p in enumerate(files, 1):
        try:
            if process_image(p, ocr, keywords):
                done += 1
                print(f"[{i}/{len(files)}] OK {p.relative_to(ROOT)}", flush=True)
        except Exception as e:
            print(f"[{i}/{len(files)}] SKIP {p.name}: {e}")
    print(f"图片脱敏完成：{done}/{len(files)} 张有修改")


if __name__ == "__main__":
    main()
