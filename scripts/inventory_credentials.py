# -*- coding: utf-8 -*-
"""Inventory credential source files."""
from pathlib import Path
import json

PROJECT = Path(__file__).resolve().parent.parent
roots = [
    PROJECT / "_source" / "photos" / "credentials",
    PROJECT / "空域文件",
]
EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".docx", ".doc"}

out = {}
for root in roots:
    if not root.exists():
        continue
    key = str(root.relative_to(PROJECT))
    companies = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        if any(x in str(p) for x in ("desktop.ini", "账号密码", "申请坐标", "uom运营", "UOM账号", "法人电话")):
            continue
        rel = p.relative_to(root)
        parts = rel.parts
        # guess company from path
        company = None
        for part in parts[:-1]:
            if len(part) >= 4 and part not in ("caac培训资质", "已获证", "未获证", "其他", "运营合格证",
                "已批复", "公司申请空域基础文件", "申请文件", "空域申请要求", "申报资料"):
                if not part.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.")):
                    company = part
        cat = "other"
        text = str(p)
        if "培训" in text or "训练" in text or "AOPA" in text or "ALPA" in text or "合格证申请书" in text:
            cat = "training"
        elif "运营合格证" in text or "OC" in p.name:
            cat = "operation"
        elif "空域" in text or "批复" in text or "批件" in text or "批文" in text:
            cat = "airspace"
        companies.setdefault(cat, []).append({
            "path": str(rel).replace("\\", "/"),
            "company_guess": company,
            "name": p.name,
        })
    out[key] = {k: len(v) for k, v in companies.items()}
    out[key + "_training_companies"] = sorted(set(
        x["company_guess"] for x in companies.get("training", []) if x["company_guess"]
    ))

Path(PROJECT / "_source" / "inventory_report.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
# print training company count
for root in roots:
    if root.exists():
        rkey = str(root.relative_to(PROJECT))
        tc = out.get(rkey + "_training_companies", [])
        print(rkey, "training files:", out.get(rkey, {}).get("training", 0), "companies:", len(tc))
        for c in tc[:30]:
            print(" ", c)
