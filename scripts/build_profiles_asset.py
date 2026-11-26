"""Generate compact runtime data file site/assets/city-profiles.js from research/city-profiles-2026/.

Usage: python3 scripts/build_profiles_asset.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research" / "city-profiles-2026" / "city_profiles_337.json"
DST = ROOT / "site" / "assets" / "city-profiles.js"


def clean_cjk_spaces(text: str) -> str:
    text = re.sub(r"(?<=[\u4e00-\u9fff（）—·])\s+(?=[\u4e00-\u9fff（）—·])", "", text)
    return text.replace("（ ", "（").replace(" ）", "）").replace(" - ", "—").strip()


def round_opt(val, digits=1):
    if val is None:
        return None
    return round(val, digits)


def main():
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    assert len(rows) == 337

    packed = {}
    for r in rows:
        pid = r["place_id"]
        # Dedup tourism highlights vs 5A scenic list while keeping 5A priority
        s5 = [clean_cjk_spaces(x) for x in r["scenic_5a_list"]]
        th = [clean_cjk_spaces(x) for x in r["tourism_highlights"] if clean_cjk_spaces(x) not in s5]
        packed[pid] = {
            "p": r["city_positioning"],
            "i": r["intro_30_50"],
            "h": r["history_culture_tags"],
            "hc": r["historic_city_names"] if r["is_historic_city"] else [],
            "a5": s5,
            "th": th,
            # [gdp_yi, pop_wan, retail_yi, mall_cnt, commercial_score_2026, charm_index_2026]
            "ec": [
                round_opt(r["gdp_yi"], 1),
                round_opt(r["pop_wan"], 1),
                round_opt(r["retail_yi"], 1),
                r["mall_cnt"],
                round_opt(r["commercial_score_2026"], 1),
                round_opt(r["charm_index_2026"], 1),
            ],
            # [ap_cnt, ap_pax_wan, ap_grade, hsr_stns, hsr_trains, hsr_reach, has_metro, cross_metro, other_ur, ur_modes, ur_lines, ur_km, ur_pax_wan, cr_sc_stns]
            "tr": [
                r["airport_count_2026"],
                round(r["airport_pax_2025"] / 10000, 1) if r["airport_pax_2025"] else 0,
                "",  # populated below from transport dataset
                r["hsr_stations_gdc_2026"],
                round_opt(r["hsr_daily_trains_gdc"], 0),
                r["hsr_direct_cities_gdc"],
                r["has_metro"],
                r["has_cross_city_metro_ext"],
                r["has_other_urban_rail"],
                r["urban_rail_modes"],
                r["ur_lines_latest"],
                round_opt(r["ur_km_latest"], 1),
                round_opt(r["ur_pax_2025_wan"], 1),
                0,
            ],
        }

    # Pull airport_max_grade and cr_cs_stations directly from transport JSON
    tr_rows = {
        t["place_id"]: t
        for t in json.loads(
            (ROOT / "research" / "transport-2025-2026" / "city_transport_337_2025_2026.json").read_text(encoding="utf-8")
        )
    }
    for pid, obj in packed.items():
        t = tr_rows[pid]
        obj["tr"][2] = t["airport_max_grade"]
        obj["tr"][13] = t["cr_cs_stations"]

    payload = "window.atlasProfiles = " + json.dumps(packed, ensure_ascii=False, separators=(",", ":")) + ";\n"
    DST.write_text(payload, encoding="utf-8")
    print(f"Wrote {DST} ({DST.stat().st_size / 1024:.1f} KB) for {len(packed)} cities")


if __name__ == "__main__":
    main()
