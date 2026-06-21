# -*- coding: utf-8 -*-
"""
整理证件素材到桌面：按公司统一命名、去重、乱码文件名 OCR 识别公司名。
输出：~/Desktop/苍凌工作室证件整理/
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import fitz
from PIL import Image, ImageOps

PROJECT = Path(__file__).resolve().parent.parent
DESKTOP_OUT = Path.home() / "Desktop" / "苍凌工作室证件整理"
SOURCES = [
    PROJECT / "_source" / "photos" / "credentials",
    PROJECT / "空域文件",
]
REPORT = PROJECT / "_source" / "organize_report.json"

EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
SKIP_PARTS = (
    "身份证", "法人电话", "手机号", "账号密码", "申请坐标",
    "uom运营人信息", "uom账号", "UOM账号", "UOM信息", "UOM平台",
    "desktop.ini", "教员执照", "电子执照", "法人身份证",
    "公司法人及经办人联系方式", "法人身份证正反面",
)
HASH_NAME = re.compile(
    r"^[0-9a-f]{8,}([\-][0-9a-f]+)*$|^[0-9a-f]{8}-[0-9a-f]{4}-", re.I
)
COMPANY_RE = re.compile(
    r"([\u4e00-\u9fff（）()·A-Za-z0-9]{2,50}"
    r"(?:有限公司|有限责任公司|职业技术学院|职业培训学校|培训中心|职业学校|驾校|科技公司))"
)
DOC_TYPES = [
    ("培训合格证", ("培训合格证", "合格证申请书", "合格证.png", "合格证.jpg", "训练机构合格证")),
    ("运营合格证", ("运营合格证",)),
    ("空域批复", ("空域批复", "空域批件", "空域批文", "空域文件", "飞行空域", "空域申请", "临时空域", "批复表", "批件")),
    ("培训手册", ("培训手册", "训练手册")),
    ("训练大纲", ("训练大纲",)),
    ("营业执照", ("营业执照",)),
    ("场地合同", ("场地租赁", "场地合同", "使用协议", "使用证明")),
    ("UAS识别码", ("UAS", "uas", "实名登记")),
    ("申请函", ("空域申请函", "申请函")),
]

FOLDER_ALIASES: dict[str, str] = {
    "捷翼其他资料": "杭州捷翼智控科技有限公司",
    "初果其他资料": "石家庄初果信息科技有限公司",
    "农机其他资料": "甘肃河西吉峰农机有限公司",
    "空翼智飞其他资料": "青岛空翼智飞科技有限公司",
    "云航其他资料": "重庆云航通用航空有限责任公司",
    "南通其他资料": "南通爱夏航空科技有限公司",
    "靖边其他资料": "靖边县智科低空经济发展有限公司",
    "金华其他资料": "金华交投机动车驾驶人服务有限公司",
    "广州飞律普 其他资料": "广州飞律普无人机技术有限公司",
    "广州北明科技有限公司申请资质材料 - 副本": "广州北明科技有限公司",
    "浙江富龙低空产业发展有限公司 资料": "浙江富龙低空产业发展有限公司",
    "智飞航空科技(兰州)有限公司 (4)": "智飞航空科技(兰州)有限公司",
    "智飞航空科技(兰州)有限公司资料": "智飞航空科技(兰州)有限公司",
    "中科星源科技发展有限公司资料": "中科星源科技发展有限公司",
    "中科星源科技发展有限公司运营合格证": "中科星源科技发展有限公司",
    "杭州捷翼智控科技有限公司运营合格证": "杭州捷翼智控科技有限公司",
    "石家庄初果信息科技有限公司运营合格证": "石家庄初果信息科技有限公司",
    "武义顺通驾驶员培训有限公司运营合格证": "武义顺通驾驶员培训有限公司",
    "四川岷霄科技服务有限公司运营合格证": "四川岷霄科技服务有限公司",
    "重庆军峰航空科技有限公司运营合格证": "重庆军峰航空科技有限公司运营合格证",
    "重庆畅飞无人机科技有限公司运营合格证": "重庆畅飞无人机科技有限公司",
    "AOPA武义顺通驾驶员培训有限公司": "武义顺通驾驶员培训有限公司",
    "AOPA江苏星链航空有限公司": "江苏星链航空有限公司",
    "江苏星链航空有限公司（ALPA)": "江苏星链航空有限公司",
    "石家庄展翼航空科技有限公司ALPA": "石家庄展翼航空科技有限公司",
    "韶关市中科瀚悦科技有限责任公司AOPA": "韶关市中科瀚悦科技有限责任公司",
    "广州飞律普无人机技术有限公司AOPA": "广州飞律普无人机技术有限公司",
    "湖北三峡职业技术学院（1）": "湖北三峡职业技术学院",
    "深圳市特区建工职业技能培训学": "深圳市特区建工职业技能培训学校",
    "广东惠飞低空科技发展有限公司": "广东惠飞低空科技发展有限公司",
    "广东省旷世飞扬通用航空科技有限公司 (2)": "广东省旷世飞扬通用航空科技有限公司",
    "重庆市江北区融媒体中心 - 副本": "重庆市江北区融媒体中心",
    "重庆苍珀科技有限公司(1)": "重庆苍珀科技有限公司",
    "爱夏航空中国地理信息协会无人机申请培训机构材料": "南通爱夏航空科技有限公司",
    "AAAAAAAAAAA正在处理": "",
    "运营合格证证申请材料": "",
}

NOT_COMPANY = re.compile(
    r"正确|劳动合同|训练飞机|理论教室|实训场地|教员|营业执照|其他材料|"
    r"培训手册|训练大纲|空域批文|申请|照片|劳务|设备|法人|UAS|uom|"
    r"^\d+\.|新建文件夹|其他资料$|证申请材料$",
    re.I,
)

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


def file_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def should_skip(path: Path) -> bool:
    if path.suffix.lower() in {".txt", ".docx", ".doc", ".xlsx"}:
        return True
    if any(p in str(path) for p in SKIP_PARTS):
        return True
    if re.search(r"账号|密码", path.name):
        return True
    return False


def normalize_company(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw in FOLDER_ALIASES:
        return FOLDER_ALIASES[raw]
    name = re.sub(r"\s+", "", raw)
    name = re.sub(r"\s*\(\d+\)$", "", name)
    name = re.sub(r"\s*-\s*副本$", "", name)
    for suf in ("资料", "AOPA", "ALPA", "其他资料", "申请材料", "（正确）", "(正确)", "运营合格证证"):
        name = name.replace(suf, "")
    if NOT_COMPANY.search(name) and "有限公司" not in name and "学院" not in name:
        return ""
    if len(name) < 4:
        return ""
    return name.strip()


def company_from_path(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    candidates: list[str] = []
    for part in rel.parts[:-1]:
        if part in ("caac培训资质", "已获证", "未获证", "其他", "运营合格证",
                    "已批复", "公司申请空域基础文件", "申请文件", "空域申请要求",
                    "申报资料", "电子保函", "合同", "空域文件"):
            continue
        if part.startswith(tuple(f"{i}." for i in range(1, 20))):
            continue
        c = normalize_company(part)
        if c:
            candidates.append(c)
    if candidates:
        return max(candidates, key=len)
    return ""


def company_from_filename(name: str) -> str:
    stem = Path(name).stem
    if COMPANY_RE.search(stem):
        return normalize_company(COMPANY_RE.search(stem).group(1))
    for kw in ("有限公司", "有限责任公司", "职业技术学院", "职业培训学校"):
        if kw in stem:
            idx = stem.find(kw)
            start = max(0, idx - 30)
            frag = stem[start : idx + len(kw)]
            m = COMPANY_RE.search(frag)
            if m:
                return normalize_company(m.group(1))
    return normalize_company(stem) if "有限公司" in stem or "学院" in stem else ""


def ocr_company(path: Path) -> str:
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
        text = " ".join(str(x[1]) for x in result if len(x) > 1)
        found = COMPANY_RE.findall(text)
        if found:
            return normalize_company(max(found, key=len))
    except Exception:
        pass
    return ""


def needs_ocr(name: str) -> bool:
    stem = Path(name).stem
    if HASH_NAME.match(stem):
        return True
    if re.match(r"^(扫描|企业微信|IMG_|DSC_|微信)", stem, re.I):
        return True
    if len(stem) <= 3:
        return True
    return False


def classify_category(path: Path) -> str:
    t = str(path) + path.name
    if "运营合格证" in t and "培训" not in t:
        return "03_运营合格证"
    if any(k in t for k in ("空域", "批件", "批文", "批复", "飞行申请", "临时空域")):
        return "02_空域批复"
    if any(k in t for k in ("培训", "训练", "AOPA", "ALPA", "合格证申请书", "训练机构")):
        return "01_培训资质"
    if "caac培训资质" in t:
        return "01_培训资质"
    return "04_其他材料"


def detect_doc_type(path: Path) -> str:
    text = path.name + str(path)
    for label, keys in DOC_TYPES:
        if any(k in text for k in keys):
            return label
    if path.suffix.lower() == ".pdf":
        return "材料"
    return "附件"


def safe_filename(company: str, doc_type: str, ext: str) -> str:
    c = re.sub(r'[<>:"/\\|?*]', "", company)[:60]
    d = re.sub(r'[<>:"/\\|?*]', "", doc_type)[:20]
    return f"{d}_{c}{ext.lower()}"


def resolve_company(path: Path, root: Path) -> str:
    c = company_from_path(path, root)
    if c:
        return c
    c = company_from_filename(path.name)
    if c:
        return c
    if needs_ocr(path.name):
        c = ocr_company(path)
        if c:
            return c
    if "已批复" in str(path):
        c = company_from_filename(path.name)
        if c:
            return c
        stem = path.stem
        if len(stem) > 4:
            return stem[:40]
    return "未识别公司"


def main() -> None:
    if DESKTOP_OUT.exists():
        shutil.rmtree(DESKTOP_OUT)

    seen_hash: set[str] = set()
    seen_name: set[str] = set()
    stats = {"copied": 0, "skipped_dup": 0, "skipped_sensitive": 0, "ocr_used": 0}
    companies: dict[str, dict[str, int]] = {}
    training_companies: set[str] = set()

    for root in SOURCES:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTS:
                continue
            if should_skip(path):
                stats["skipped_sensitive"] += 1
                continue

            h = file_hash(path)
            if h in seen_hash:
                stats["skipped_dup"] += 1
                continue

            company = resolve_company(path, root)
            if company == "未识别公司" or HASH_NAME.match(company):
                ocr_c = ocr_company(path)
                if ocr_c:
                    company = ocr_c
                    stats["ocr_used"] += 1
            if HASH_NAME.match(company) or company in ("未识别公司", ""):
                continue
            if company in ("场地使用证明（场地租赁合同）", "线下培训"):
                continue
            if company.endswith("材料"):
                company = company.replace("材料", "").strip()

            category = classify_category(path)
            doc_type = detect_doc_type(path)
            out_dir = DESKTOP_OUT / category / company
            out_dir.mkdir(parents=True, exist_ok=True)

            fname = safe_filename(company, doc_type, path.suffix)
            dest = out_dir / fname
            n = 2
            while dest.name in seen_name and dest.exists():
                fname = safe_filename(company, f"{doc_type}_{n}", path.suffix)
                dest = out_dir / fname
                n += 1

            shutil.copy2(path, dest)
            seen_hash.add(h)
            seen_name.add(dest.name)
            stats["copied"] += 1
            companies.setdefault(company, {})
            companies[company][doc_type] = companies[company].get(doc_type, 0) + 1
            if category == "01_培训资质":
                training_companies.add(company)

    report = {
        "output": str(DESKTOP_OUT),
        "stats": stats,
        "training_company_count": len(training_companies),
        "training_companies": sorted(training_companies),
        "all_companies": {k: v for k, v in sorted(companies.items())},
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["stats"], ensure_ascii=False))
    print(f"培训资质公司: {len(training_companies)}")
    print(f"输出: {DESKTOP_OUT}")


if __name__ == "__main__":
    main()
