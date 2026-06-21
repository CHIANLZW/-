# -*- coding: utf-8 -*-
"""Build curated airspace company manifest from 空域文件 folder."""
from __future__ import annotations

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
AIRSPACE_ROOT = PROJECT / "空域文件"
OUT = PROJECT / "assets" / "data" / "airspace-companies.json"

# (filename, company, region) — joint approvals expanded to separate companies
APPROVED = [
    ("临沂军创云翼无人机科技有限公司.pdf", "临沂军创云翼无人机科技有限公司", "山东"),
    ("南通爱夏航空科技有限公司无人驾驶航空器飞行空域使用申请批复表2026.pdf", "南通爱夏航空科技有限公司", "江苏"),
    ("山东云玉航空科技有限公司.jpg", "山东云玉航空科技有限公司", "山东"),
    ("广东惠飞低空科技发展有限公司 (1).jpg", "广东惠飞低空科技发展有限公司", "广东"),
    ("智飞航空科技（兰州）有限公司 空域飞行审批表.pdf", "智飞航空科技（兰州）有限公司", "甘肃"),
    ("浙江富龙低空产业空域批复表.Jpg", "浙江富龙低空产业发展有限公司", "浙江"),
    ("浙江金华交投.pdf", "金华交投机动车驾驶人服务有限公司", "浙江"),
    ("湖北三峡职业技术学院.pdf", "湖北三峡职业技术学院", "湖北"),
    ("石家庄展翼航空科技有限公司.pdf", "石家庄展翼航空科技有限公司", "河北"),
    ("腾瑞（重庆）无人机科技有限公司重庆苍凌.pdf", "腾瑞（重庆）无人机科技有限公司", "重庆"),
    ("重庆同汇.pdf", "重庆同汇通用航空有限公司", "重庆"),
    ("重庆天擎羲合培训.pdf", "遂宁天擎工程项目管理有限公司", "四川"),
    ("重庆畅飞重庆苍珀 北京安邮(1).pdf", "重庆畅飞无人机科技有限公司", "重庆"),
    ("重庆畅飞重庆苍珀 北京安邮(1).pdf", "重庆苍珀科技有限公司", "重庆"),
    ("重庆畅飞重庆苍珀 北京安邮(1).pdf", "北京安邮飞讯科技有限公司", "北京"),
    ("重庆空域智租.pdf", "重庆空域智租科技有限公司", "重庆"),
    ("重庆鑫欧博教育重庆渝飞四川凌云无人机科技有限公司.pdf", "重庆鑫欧博教育科技有限公司", "重庆"),
    ("重庆鑫欧博教育重庆渝飞四川凌云无人机科技有限公司.pdf", "重庆渝飞飞低空科技有限公司", "重庆"),
    ("重庆鑫欧博教育重庆渝飞四川凌云无人机科技有限公司.pdf", "四川省凌运无人机科技有限公司", "四川"),
    ("靖边县智科低空经济发展有限公司 (1).jpg", "靖边县智科低空经济发展有限公司", "陕西"),
]

IN_PROGRESS = [
    ("四川辉铖新能源科技有限公司", "四川", "材料齐备"),
    ("大竹县华创职业培训学校", "四川", "材料齐备"),
    ("成都恒晟通科技有限公司", "四川", "材料齐备"),
    ("重庆光之晟科技有限公司", "重庆", "材料齐备"),
    ("重庆昌德无人机科技有限公司", "重庆", "批件在途"),
    ("重庆赛迦无人机有限公司", "重庆", "材料齐备"),
    ("重庆翼飞科技有限公司", "重庆", "申请中"),
    ("翼飞（重庆）航空咨询有限公司", "重庆", "申请中"),
    ("重庆苍凌信息技术咨询服务有限责任公司", "重庆", "申请中"),
]

MATERIALS = [
    "营业执照 / 事业单位法人证书",
    "民用无人驾驶航空器运营合格证（OC）",
    "无人机 UAS 识别码 / 实名登记",
    "法人及经办人身份证明（申办用）",
    "训练 / 实飞 / 起降场地租赁合同或使用协议",
    "申请空域中心点坐标、半径与真高",
    "川渝 / 区域平台账号（统一社会信用代码登录）",
    "空域申请函 / 飞行活动申请表",
    "无人机设备照片及技术参数",
]


def scan_approved() -> list[dict]:
    folder = next((p for p in AIRSPACE_ROOT.iterdir() if p.is_dir() and "批复" in p.name), None)
    if not folder:
        return []
    seen: set[str] = set()
    items: list[dict] = []
    for fname, company, region in APPROVED:
        path = folder / fname
        if not path.exists():
            continue
        if company in seen:
            continue
        seen.add(company)
        items.append({"company": company, "status": "已批复", "region": region})
    return sorted(items, key=lambda x: (x["region"], x["company"]))


def scan_in_progress() -> list[dict]:
    return [{"company": c, "status": status, "region": region} for c, region, status in IN_PROGRESS]


def main() -> None:
    approved = scan_approved()
    in_progress = scan_in_progress()
    data = {
        "materials": MATERIALS,
        "approved": approved,
        "inProgress": in_progress,
        "stats": {"approvedCount": len(approved), "inProgressCount": len(in_progress)},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"approved={len(approved)} inProgress={len(in_progress)} -> {OUT}")


if __name__ == "__main__":
    main()
