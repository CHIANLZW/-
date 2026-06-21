# -*- coding: utf-8 -*-
from pathlib import Path
root = Path(__file__).resolve().parent.parent / "空域文件"
for p in sorted(root.rglob("*")):
    if p.is_dir() and p.parent == root:
        print("[dir]", p.name)
    elif p.is_file() and len(p.relative_to(root).parts) <= 3:
        print(p.relative_to(root))
