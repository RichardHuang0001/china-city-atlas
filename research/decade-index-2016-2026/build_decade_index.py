"""Build 2016-2026 (11-edition) national ranking trajectories for all 337 cities.

Methodology:
- Uses all 11 complete editions (2016..2026) of Yicai's City Charm overall_rank
  (1..337) and tier classification, where every city is plotted inside its own
  historical rank envelope [yTop..yBottom] on the left Y-axis (smaller rank = higher bar).
- Also attaches 2016-2025 constant-2025-price real GDP and real growth multiplier as
  secondary hover/summary context without distorting the rank bar height.

Outputs:
- research/decade-index-2016-2026/city_decade_index_337.json
- research/decade-index-2016-2026/city_decade_index_337.csv
- tools/decade-index-preview-data.js
"""
from collections import defaultdict
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "research" / "datayicai-mcp"
OUT_DIR = Path(__file__).resolve().parent
PREVIEW_JS = ROOT / "tools" / "decade-index-preview-data.js"

YEARS = list(range(2016, 2027))  # 11 columns: '16 through '26


def main() -> None:
    with open(MCP_DIR / "charm-history" / "city_charm_2016_2026_panel.csv", encoding="utf-8-sig") as f:
        charm = defaultdict(dict)
        meta_city = {}
        for row in csv.DictReader(f):
            pid = row["place_id"]
            charm[pid][int(row["year"])] = row
            meta_city[pid] = {
                "name": row["canonical_name"].removesuffix("市"),
                "fullName": row["canonical_name"],
                "province": row["province"],
            }

    with open(MCP_DIR / "city-stats" / "macro_panel_2016_2025_337.csv", encoding="utf-8-sig") as f:
        macro = defaultdict(dict)
        for row in csv.DictReader(f):
            macro[row["place_id"]][int(row["year"])] = row

    # Optional constant-price real GDP multiplier 2016->2025 for hover/reference only
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
        (ROOT / "site" / "assets" / "data.js")
        .read_text(encoding="utf-8")
        .strip()
        .removeprefix("window.atlasData = ")
        .removesuffix(";")
    )
    assert len(site_data["cities"]) == 337

    records = {}
    csv_rows = []
    compact_js = {}

    for pid in sorted(charm.keys()):
        ranks = [int(float(charm[pid][y]["overall_rank"])) for y in YEARS]
        tiers = [charm[pid][y]["tier"] for y in YEARS]
        best_rank = min(ranks)
        worst_rank = max(ranks)
        rank_delta = ranks[0] - ranks[-1]  # positive = improved (rank number got smaller)
        real_mult = real_mult_by_id.get(pid)

        records[pid] = {
            "code": pid,
            "name": meta_city[pid]["fullName"],
            "province": meta_city[pid]["province"],
            "tier2016": tiers[0],
            "tier2026": tiers[-1],
            "rank2016": ranks[0],
            "rank2026": ranks[-1],
            "rankDelta": rank_delta,
            "bestRank": best_rank,
            "worstRank": worst_rank,
            "rankSpan": worst_rank - best_rank,
            "realGdpMult2016_2025": real_mult,
            "series": [
                {"year": y, "rank": ranks[i], "tier": tiers[i]}
                for i, y in enumerate(YEARS)
            ],
        }

        # Compact array: [ranks[11], tiers[11], realGdpMult]
        compact_js[pid] = [ranks, tiers, real_mult]

        csv_rows.append({
            "place_id": pid,
            "name": meta_city[pid]["fullName"],
            "province": meta_city[pid]["province"],
            "tier_2016": tiers[0],
            "tier_2026": tiers[-1],
            "rank_2016": ranks[0],
            "rank_2026": ranks[-1],
            "rank_delta": rank_delta,
            "best_rank": best_rank,
            "worst_rank": worst_rank,
            "real_gdp_mult_16_25": real_mult,
            **{f"r_{y}": ranks[i] for i, y in enumerate(YEARS)},
        })

    (OUT_DIR / "city_decade_index_337.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fieldnames = list(csv_rows[0].keys())
    with open(OUT_DIR / "city_decade_index_337.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(csv_rows)

    compact_dump = json.dumps(compact_js, ensure_ascii=False, separators=(",", ":"))
    PREVIEW_JS.write_text(
        "window.atlasDecadeIndex = " + compact_dump + ";\n", encoding="utf-8"
    )
    up = sum(1 for r in records.values() if r["rankDelta"] > 0)
    down = sum(1 for r in records.values() if r["rankDelta"] < 0)
    flat = sum(1 for r in records.values() if r["rankDelta"] == 0)
    print(
        f"Built 2016-2026 rank dataset (337 cities: up={up}, down={down}, flat={flat}), "
        f"JS={PREVIEW_JS.stat().st_size:,} bytes"
    )


if __name__ == "__main__":
    main()
