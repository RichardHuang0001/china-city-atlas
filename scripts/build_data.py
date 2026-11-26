"""Generate site/assets/data.js from the archived 2026 Zhicheng CSV and existing city coordinates."""
from collections import Counter
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_JS = ROOT / "site" / "assets" / "data.js"
CSV_2026 = ROOT / "research" / "datayicai-mcp" / "charm-2026" / "city_charm_2026_scores_wide.csv"

TIERS_META = [
    {"name": "一线", "color": "#9b3454", "scale": 1.09},
    {"name": "新一线", "color": "#ad5141", "scale": 1.04},
    {"name": "二线", "color": "#936820", "scale": 1.0},
    {"name": "三线", "color": "#926074", "scale": 0.95},
    {"name": "四线", "color": "#6c6279", "scale": 0.9},
    {"name": "五线", "color": "#82674e", "scale": 0.85},
]
TIER_INDEX = {item["name"]: idx for idx, item in enumerate(TIERS_META)}


def load_existing_data():
    text = DATA_JS.read_text(encoding="utf-8").strip()
    prefix = "window.atlasData = "
    assert text.startswith(prefix) and text.endswith(";")
    return json.loads(text[len(prefix):-1])


def main():
    existing = load_existing_data()
    coords_by_code = {
        city[1]: (city[0], city[2], city[5], city[6], city[7], city[8])
        for city in existing["cities"]
    }

    with CSV_2026.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == len(coords_by_code) == 337
    rows.sort(key=lambda row: int(row["rank_2026"]))

    tier_pos = Counter()
    tier_total = Counter()
    tier_main = Counter()
    cities = []
    reference_names = []

    for row in rows:
        code = row["place_id"]
        short_name, province, is_mun, lonlat, point, urban_ref = coords_by_code[code]
        tier = TIER_INDEX[row["tier_2026"]]
        tier_pos[tier] += 1
        tier_total[tier] += 1
        if is_mun:
            reference_names.append(short_name)
        else:
            tier_main[tier] += 1
        cities.append([
            short_name,
            code,
            province,
            tier,
            tier_pos[tier],
            is_mun,
            lonlat,
            point,
            urban_ref,
        ])

    tiers_config = [
        {
            **item,
            "total": tier_total[idx],
            "main": tier_main[idx],
        }
        for idx, item in enumerate(TIERS_META)
    ]

    payload = {
        "meta": {
            "year": 2026,
            "editionLabel": "2026 年版",
            "title": "中国城市分级地图 · 2026",
            "subtitle": "按第一财经·新一线知城数据库 2026 版，查看六档城市在各省份的分布。",
            "description": "按地图、省份和知城 2026 版线级查阅中国 337 座地级及以上城市分布。",
            "rankLabel": "线内序",
            "rankSortLabel": "榜单排序",
            "rankUnit": "位（线内序）",
            "tiers": tiers_config,
            "referenceNames": reference_names,
            "sourceTitle": "城市线级（2026）",
            "sourceNote": (
                "采用第一财经·新一线城市研究所知城数据库 2026 版（city_charm.2026）分层归档与总榜次序"
                "（覆盖中国内地全部 337 座地级及以上城市）。注：2026 年 5 月公开报告正文不再单独发布综合排名与分级名单，"
                "本页线级与线内序取自官方知城数据库同期归档，与当年 1–337 总榜分段一致。"
            ),
            "sourceLinks": [
                {"label": "第一财经 2026 报告原文 ↗", "url": "https://www.yicai.com/news/103204902.html"},
                {"label": "新一线知城 2026 榜单概览 ↗", "url": "https://www.datayicai.com/data/rankings/charm/2026"},
            ],
        },
        "cities": cities,
        "provinces": existing["provinces"],
    }

    lines = [
        "window.atlasData = {",
        '  "meta": ' + json.dumps(payload["meta"], ensure_ascii=False, indent=2).replace("\n", "\n  ") + ",",
        '  "cities": [',
    ]
    for index, city in enumerate(cities):
        comma = "," if index < len(cities) - 1 else ""
        lines.append("    " + json.dumps(city, ensure_ascii=False, separators=(",", ":")) + comma)
    lines.append("  ],")
    lines.append('  "provinces": ' + json.dumps(payload["provinces"], ensure_ascii=False, separators=(",", ":")))
    lines.append("};")
    DATA_JS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {DATA_JS.relative_to(ROOT)} with {len(cities)} cities for {payload['meta']['year']}.")


if __name__ == "__main__":
    main()
