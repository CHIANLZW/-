# -*- coding: utf-8 -*-
from pathlib import Path
root = Path(__file__).resolve().parent.parent / "空域文件" / "公司申请空域基础文件"
for p in sorted(root.rglob("*.pdf")):
  if "申请" in p.name or "空域" in p.name:
    print(p.relative_to(root))
