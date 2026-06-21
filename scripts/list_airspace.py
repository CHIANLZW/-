# -*- coding: utf-8 -*-
from pathlib import Path
import json

PROJECT = Path(__file__).resolve().parent.parent
root = PROJECT / "空域文件"

out = {"顶层": [], "批复件": [], "公司申请": [], "区域要求": []}

for p in sorted(root.iterdir()):
    out["顶层"].append(p.name + ("/" if p.is_dir() else ""))

pifu = None
for p in root.iterdir():
    if p.is_dir() and "批复" in p.name:
        pifu = p
        break
if pifu is None:
    pifu = root / "批复件"

if pifu.exists():
    for p in sorted(pifu.iterdir()):
        out["批复件"].append(p.name + ("/" if p.is_dir() else ""))

base = None
for p in root.iterdir():
    if p.is_dir() and "公司" in p.name and "空域" in p.name:
        base = p
        break
if base is None:
    base = root / "公司申请空域基础文件"

quyu = None
for p in root.iterdir():
    if p.is_dir() and ("区域" in p.name or "申请要求" in p.name):
        quyu = p
        break
if quyu is None:
    quyu = root / "各区域要求"
if base and base.exists():
    for p in sorted(base.iterdir()):
        out["公司申请"].append(p.name)

if quyu and quyu.exists():
    for p in sorted(quyu.iterdir()):
        out["区域要求"].append(p.name)

inv = PROJECT / "_source" / "airspace_inventory.json"
inv.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
