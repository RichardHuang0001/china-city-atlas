"""Generate site/assets/city-decade-ranks.js from 2016-2026 Yicai & macro archives.

Outputs a compact lazy-loadable JS file setting window.atlasDecadeRanks:
    {
      "<6-digit-code>": [
        [r2016, ..., r2026],      // 11 national Charm overall_rank integers
        [t2016, ..., t2026],      // 11 tier names (6-tier label)
        realGdpMult2016_2025      // constant-price 10y GDP multiplier or null
      ],
      ...
    }

Run:
    python3 scripts/build_decade_ranks_asset.py
"""
from collections import defaultdict
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "research" / "datayicai-mcp"
ASSETS = ROOT / "site" / "assets"
YEARS = list(range(2016, 2027))


def main() -> None:
    with open(MCP_DIR / "charm-history" / "city_charm_2016_2026_panel.csv", encoding="utf-8-sig") as f:
        charm = defaultdict(dict)
        for row in csv.DictReader(f):
            charm[row["place_id"]][int(row["year"])] = row

    with open(MCP_DIR / "city-stats" / "macro_panel_2016_2025_337.csv", encoding="utf-8-sig") as f:
        macro = defaultdict(dict)
        for row in csv.DictReader(f):
            macro[row["place_id"]][int(row["year"])] = row

    real_mult_by_id: dict[str, float | None] = {}
    for pid, ym in macro.items():
        g25 = ym[2025]["地区生产总值 (亿元)"]
        g24 = ym[2024]["地区生产总值 (亿元)"]
        gr25 = ym[2025]["地区生产总值实际增长率 (%)"]
        if g25 != "":
            end_v = float(g25)
        elif g24 != "" and gr25 != "":
            end_v = float(g24) * (1.0 + float(gr25) / 100.0)
        else:
            real_mult_by_id[pid] = None
            continue
        cur = end_v
        for y in range(2025, 2016, -1):
            cur = cur / (1.0 + float(ym[y]["地区生产总值实际增长率 (%)"]) / 100.0)
        real_mult_by_id[pid] = round(end_v / cur, 2)

    site_data = json.loads(
        (ASSETS / "data.js")
        .read_text(encoding="utf-8")
        .strip()
        .removeprefix("window.atlasData = ")
        .removesuffix(";")
    )
    city_codes = [city[1] for city in site_data["cities"]]
    assert set(city_codes) == set(charm.keys()), "Mismatch between data.js and charm panel"

    out = {}
    for code in sorted(city_codes):
        ranks = [int(float(charm[code][y]["overall_rank"])) for y in YEARS]
        tiers = [charm[code][y]["tier"] for y in YEARS]
        out[code] = [ranks, tiers, real_mult_by_id.get(code)]

    out_path = ASSETS / "city-decade-ranks.js"
    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    out_path.write_text("window.atlasDecadeRanks = " + payload + ";\n", encoding="utf-8")
    print(f"Wrote {out_path.name}: {len(out)} cities, {out_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
