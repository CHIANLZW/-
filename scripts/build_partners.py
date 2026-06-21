# -*- coding: utf-8 -*-
"""Build partners list from organized credentials."""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ORG_REPORT = PROJECT / "_source" / "organize_report.json"
AIRSPACE = PROJECT / "assets" / "data" / "airspace-companies.json"
OUT = PROJECT / "assets" / "data" / "partners.json"

SKIP = re.compile(
    r"模板|青岛|石家庄地区|企业微信|称重庆|沙坪坝区融媒体|"
    r"2024八月|北部青岛|其他材料$|合格证$|华科尔|地面站|教培相关|"
    r"^服务有限责任公司$|苍凌工作室$|苍凌信息技术",
)
CHONGQING = (
    "重庆", "苍珀", "空域智租", "光之晟", "畅飞", "云航", "同汇", "腾瑞",
    "军峰", "智翔", "洲河", "苍茫", "凌九霄", "无限数创", "渝飞", "鑫欧博",
)
SICHUAN = ("四川", "成都", "遂宁", "大竹", "君柠", "辉铖", "恒晟通", "岷霄", "天立", "凌运", "三峡", "天擎")
REGION_HINT = {
    "重庆": "重庆", "四川": "四川", "广东": "广东", "浙江": "浙江", "江苏": "江苏",
    "湖北": "湖北", "河北": "河北", "山东": "山东", "甘肃": "甘肃", "陕西": "陕西",
    "北京": "北京", "新疆": "新疆", "海南": "海南", "贵州": "贵州",
}

NAME_ALIASES = {
    "浙江金华交投": "金华交投机动车驾驶人服务有限公司",
    "重庆天擎羲合培训": "遂宁天擎工程项目管理有限公司",
    "大竹华创职业": "大竹县华创职业培训学校",
    "成都恒晟通空域申请资料": "成都恒晟通科技有限公司",
    "重庆鑫欧博教育 / 渝飞 / 四川凌云无人机科技": "重庆鑫欧博教育科技有限公司",
    "重庆鑫欧博教育重庆渝飞四川凌云无人机科技有限公司": "重庆鑫欧博教育科技有限公司",
    "重庆畅飞重庆苍珀 北京安邮(1)": "重庆畅飞无人机科技有限公司",
    "称重庆苍珀科技有限公司": "重庆苍珀科技有限公司",
    "重庆市重庆市沙坪坝区虎溪街道重庆苍珀科技有限公司": "重庆苍珀科技有限公司",
    "河北石家庄地区客户": "",
    "四川君柠航空科技有限公司": "",
}

CITY_COORDS = {
    "北京": (116.41, 39.90),
    "重庆": (106.55, 29.57),
    "成都": (104.07, 30.67),
    "遂宁": (105.57, 30.52),
    "大竹": (107.20, 30.74),
    "广州": (113.27, 23.13),
    "杭州": (120.15, 30.28),
    "金华": (119.65, 29.08),
    "南京": (118.80, 32.06),
    "南通": (120.86, 32.01),
    "武汉": (114.31, 30.52),
    "宜昌": (111.29, 30.69),
    "石家庄": (114.48, 38.04),
    "临沂": (118.35, 35.05),
    "兰州": (103.82, 36.06),
    "靖边": (108.79, 37.60),
    "深圳": (114.06, 22.55),
}

REGION_CAPITAL = {
    "重庆": (106.55, 29.57),
    "四川": (104.07, 30.67),
    "广东": (113.27, 23.13),
    "浙江": (120.15, 30.28),
    "江苏": (118.80, 32.06),
    "湖北": (114.31, 30.52),
    "河北": (114.48, 38.04),
    "山东": (117.12, 36.65),
    "甘肃": (103.82, 36.06),
    "陕西": (108.95, 34.27),
    "北京": (116.41, 39.90),
    "其他": (105.0, 35.0),
}


CITY_TO_REGION = {
    "北京": "北京", "石家庄": "河北", "临沂": "山东", "济南": "山东",
    "南通": "江苏", "南京": "江苏", "杭州": "浙江", "金华": "浙江", "嘉兴": "浙江",
    "广州": "广东", "深圳": "广东", "惠州": "广东",
    "武汉": "湖北", "宜昌": "湖北", "三峡": "湖北",
    "成都": "四川", "遂宁": "四川", "大竹": "四川",
    "重庆": "重庆", "兰州": "甘肃", "靖边": "陕西", "西安": "陕西",
}


def guess_region(name: str) -> str:
    for city, region in CITY_TO_REGION.items():
        if city in name:
            return region
    for k in CHONGQING:
        if k in name:
            return "重庆"
    for k in SICHUAN:
        if k in name:
            return "四川"
    for k, v in REGION_HINT.items():
        if k in name:
            return v
    return "其他"


def guess_coords(name: str, region: str) -> tuple[float, float]:
    for city, coords in CITY_COORDS.items():
        if city in name:
            return coords
    return REGION_CAPITAL.get(region, REGION_CAPITAL["其他"])


def clean_name(name: str) -> str:
    name = NAME_ALIASES.get(name.strip(), name.strip())
    if not name:
        return ""
    if SKIP.search(name):
        return ""
    if len(name) < 6:
        return ""
    if name.endswith("2") and "科技" in name:
        name = name.rstrip("2")
    if "/" in name or " / " in name:
        return ""
    return name


def main() -> None:
    partners: dict[str, dict] = {}

    if ORG_REPORT.exists():
        data = json.loads(ORG_REPORT.read_text(encoding="utf-8"))
        for company in data.get("all_companies", {}):
            c = clean_name(company)
            if not c:
                continue
            region = guess_region(c)
            partners[c] = {"name": c, "region": region}

    if AIRSPACE.exists():
        air = json.loads(AIRSPACE.read_text(encoding="utf-8"))
        for item in air.get("approved", []) + air.get("inProgress", []):
            c = clean_name(item["company"])
            if not c:
                continue
            region = item.get("region", guess_region(c))
            if c in partners:
                if partners[c]["region"] == "其他" and region != "其他":
                    partners[c]["region"] = region
            else:
                partners[c] = {"name": c, "region": region}

    # Split joint approvals into separate companies
    extras = [
        ("重庆苍珀科技有限公司", "重庆"),
        ("北京安邮飞讯科技有限公司", "北京"),
        ("重庆渝飞飞低空科技有限公司", "重庆"),
        ("四川省凌运无人机科技有限公司", "四川"),
    ]
    for name, region in extras:
        if name not in partners:
            partners[name] = {"name": name, "region": region}

    items = []
    for p in sorted(partners.values(), key=lambda x: (x["region"], x["name"])):
        lng, lat = guess_coords(p["name"], p["region"])
        items.append({**p, "lng": lng, "lat": lat})

    result = {
        "intro": "以下为我们曾提供培训资质、空域批复、运营合格证或相关申办辅导服务的合作单位（排名不分先后，仅列公司全称）。",
        "count": len(items),
        "partners": items,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"partners={len(items)} -> {OUT}")


if __name__ == "__main__":
    main()
