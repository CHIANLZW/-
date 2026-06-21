# -*- coding: utf-8 -*-
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
src = PROJECT / "_source" / "photos" / "credentials" / "空域文件"
dst = PROJECT / "空域文件"
if src.exists() and not dst.exists():
    shutil.move(str(src), str(dst))
    print("moved to", dst)
elif dst.exists():
    print("already at", dst)
else:
    print("missing", src)
