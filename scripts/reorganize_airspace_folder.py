# -*- coding: utf-8 -*-
"""Reorganize 空域文件 into 已批复 / 公司申请空域基础文件 / 空域申请要求."""
from __future__ import annotations

import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "空域文件"

APPROVED_FILES = {
    "临沂军创云翼无人机科技有限公司.pdf",
    "南通爱夏航空科技有限公司无人驾驶航空器飞行空域使用申请批复表2026.pdf",
    "四川君柠航空模板.pdf",
    "山东云玉航空科技有限公司.jpg",
    "广东惠飞低空科技发展有限公司 (1).jpg",
    "广东惠飞低空科技发展有限公司 (2).jpg",
    "智飞航空科技（兰州）有限公司 空域飞行审批表.pdf",
    "河北石家庄.pdf",
    "浙江富龙低空产业空域批复表.Jpg",
    "浙江金华交投.pdf",
    "湖北三峡职业技术学院.pdf",
    "石家庄展翼航空科技有限公司.pdf",
    "腾瑞（重庆）无人机科技有限公司重庆苍凌.pdf",
    "重庆同汇.pdf",
    "重庆天擎羲合培训.pdf",
    "重庆畅飞重庆苍珀 北京安邮(1).pdf",
    "重庆空域智租.pdf",
    "重庆苍凌.pdf",
    "重庆鑫欧博教育重庆渝飞四川凌云无人机科技有限公司.pdf",
    "靖边县智科低空经济发展有限公司 (1).jpg",
    "靖边县智科低空经济发展有限公司 (2).jpg",
    "0c94058e17e4714b37a185ede35283f.jpg",
    "251668ac-8de9-4f7a-b54e-af5da69d6e4e.jpg",
    "b5a990f93b0aa34a4e9cef63ff1ad1c.jpg",
    "企业微信截图_17791179161011.png",
}

COMPANY_DIRS = {
    "四川辉铖新能源科技有限公司空域申请材料 (4)",
    "大竹华创职业",
    "成都恒晟通空域申请资料",
    "遂宁天擎工程项目管理有限公司",
    "重庆光之晟科技有限公司空域申请函",
    "重庆苍凌",
    "重庆赛迦无人机有限公司",
}

COMPANY_FILES = {
    "重庆昌德无人机科技有限公司编号〔2026〕 1472号.pdf",
}


def ensure(*parts: str) -> Path:
    p = ROOT.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def move_if_exists(src: Path, dst: Path) -> None:
    if not src.exists() or src.resolve() == dst.resolve():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    shutil.move(str(src), str(dst))
    print("move", src.name, "->", dst.parent.name)


def main() -> None:
    if not ROOT.exists():
        print("missing", ROOT)
        return

    approved = ensure("已批复")
    applications = ensure("公司申请空域基础文件")
    requirements = ensure("空域申请要求")

    for name in APPROVED_FILES:
        move_if_exists(ROOT / name, approved / name)

    # loose approvals at root matching keywords
    for f in list(ROOT.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
            continue
        if any(k in f.name for k in ("批复", "批件", "批文", "空域智租", "重庆同汇", "重庆苍凌")):
            move_if_exists(f, approved / f.name)

    for name in COMPANY_DIRS:
        move_if_exists(ROOT / name, applications / name)

    for name in COMPANY_FILES:
        move_if_exists(ROOT / name, applications / name)

    apply_dir = ROOT / "申请文件"
    if apply_dir.is_dir():
        move_if_exists(apply_dir, applications / "申请文件")

    req_dir = ROOT / "空域申请要求"
    if req_dir.is_dir() and req_dir.resolve() != requirements.resolve():
        for child in req_dir.iterdir():
            move_if_exists(child, requirements / child.name)
        if not any(req_dir.iterdir()):
            req_dir.rmdir()

    # other loose pdfs at root that look like approvals
    for f in list(ROOT.iterdir()):
        if f.is_file() and f.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png"}:
            if f.name not in COMPANY_FILES:
                move_if_exists(f, approved / f.name)

    print("done")


if __name__ == "__main__":
    main()
