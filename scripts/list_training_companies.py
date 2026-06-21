# -*- coding: utf-8 -*-
from pathlib import Path
import json

root = Path(r"C:\Users\28295\Desktop\inchian.top\_source\photos\credentials\caac培训资质")
companies = {}
for p in root.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
        continue
    rel = p.relative_to(root)
    top = rel.parts[0]  # 已获证/其他/未获证
    company = None
    for part in rel.parts[1:-1]:
        if len(part) >= 6 and "手册" not in part and "大纲" not in part:
            if not part[0].isdigit() and part not in ("运营合格证", "合格证", "培训手册", "训练大纲", "训练手册"):
                company = part
                break
    if not company and len(rel.parts) > 2:
        company = rel.parts[1]
    companies.setdefault(company or "未知", []).append(str(rel).replace("\\", "/"))

# filter real company names
real = {k: v for k, v in companies.items() if k and len(k) >= 4 and "正确" not in k and not k.startswith(("1.", "2.", "3."))}
print("company folders:", len(real))
for k in sorted(real.keys())[:50]:
    print(len(real[k]), k)
print("...")
for k in sorted(real.keys())[-20:]:
    print(len(real[k]), k)

Path(r"C:\Users\28295\Desktop\inchian.top\_source\training_companies.json").write_text(
    json.dumps({k: len(v) for k, v in sorted(real.items())}, ensure_ascii=False, indent=2), encoding="utf-8"
)
