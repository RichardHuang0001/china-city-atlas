"""Assemble unified 337-city hover-card profiles (intro, history/culture, tourism, transport, commerce).

Reads:
- Scratch audited 337-city descriptions (generated strictly from Wikipedia + 5A + historic city lists)
- research/transport-2025-2026/city_transport_337_2025_2026.json
- /tmp/city_commerce_macro_337.json
- /tmp/wiki_tags_337.json & /tmp/wiki_337_intros.json

Writes:
- research/city-profiles-2026/city_profiles_337.json
- research/city-profiles-2026/city_profiles_337.csv
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SCRATCH = Path("/Users/huangwei/.gemini/antigravity/brain/9a6da415-7e10-45c8-bcd3-756eea6b8626/scratch")


def format_transport_summary(t: dict) -> str:
    is_top3 = t["tier_2026"] in ("一线", "新一线", "二线", "三线")
    parts = []
    # Airport
    if t["airport_count_2026"] > 0:
        if is_top3 and t["airport_pax_2025"] > 0:
            pax_w = t["airport_pax_2025"] / 10000
            grade = f"({t['airport_max_grade']})" if t["airport_max_grade"] else ""
            parts.append(f"机场{t['airport_count_2026']}座{grade}·年吞吐{pax_w:.0f}万人次")
        else:
            parts.append(f"机场{t['airport_count_2026']}座")
    else:
        parts.append("暂无机尝".replace("尝", "场"))

    # HSR
    if t["has_hsr_gdc"]:
        if is_top3:
            parts.append(
                f"高铁/动车站{t['hsr_stations_gdc_2026']}座·日均{t['hsr_daily_trains_gdc']:.0f}班(直达{t['hsr_direct_cities_gdc']}城)"
            )
        else:
            parts.append(f"高铁/动车站{t['hsr_stations_gdc_2026']}座")
    else:
        parts.append("暂无高铁/动车")

    # Metro & Urban Rail
    if t["has_metro"]:
        if is_top3 and t["ur_pax_2025_wan"]:
            pax_y = t["ur_pax_2025_wan"] / 10000
            pax_str = f"{pax_y:.2f}亿" if pax_y >= 1 else f"{t['ur_pax_2025_wan']:.0f}万"
            parts.append(f"地铁/城轨{t['ur_lines_latest']}条({t['ur_km_latest']}km)·年客运{pax_str}人次")
        else:
            parts.append(f"地铁/城轨{t['ur_lines_latest']}条({t['ur_km_latest']}km)")
    elif t["has_cross_city_metro_ext"]:
        parts.append(f"跨市地铁/快轨接入({t['urban_rail_modes']})")
    elif t["has_other_urban_rail"]:
        parts.append(f"城轨({t['urban_rail_modes']}){t['ur_lines_latest']}条({t['ur_km_latest']}km)")
    elif t["has_cr_intercity_sc"]:
        parts.append(f"国铁城际/市域站{t['cr_cs_stations']}座")

    return "；".join(parts)


def format_commerce_summary(c: dict) -> str:
    parts = []
    if c.get("gdp_yi") is not None:
        parts.append(f"GDP {c['gdp_yi']:.0f}亿元")
    if c.get("pop_wan") is not None:
        parts.append(f"常住人口{c['pop_wan']:.0f}万人")
    if c.get("retail_yi") is not None:
        parts.append(f"社零{c['retail_yi']:.0f}亿元")
    if c.get("mall_cnt") is not None:
        parts.append(f"购物中心{int(c['mall_cnt'])}座")
    if c.get("commercial_score_2026") is not None:
        parts.append(f"商业集聚度{c['commercial_score_2026']:.1f}")
    return "，".join(parts)


def main():
    drafted = {r["place_id"]: r for r in json.loads((SCRATCH / "drafted_profiles_337.json").read_text())}
    transport = {r["place_id"]: r for r in json.loads((ROOT / "research/transport-2025-2026/city_transport_337_2025_2026.json").read_text())}
    comm = json.loads(Path("/tmp/city_commerce_macro_337.json").read_text())
    tags = json.loads(Path("/tmp/wiki_tags_337.json").read_text())
    intros = json.loads(Path("/tmp/wiki_337_intros.json").read_text())

    assert len(drafted) == 337
    assert set(drafted.keys()) == set(transport.keys()) == set(comm.keys())

    profiles = []
    for pid, c in sorted(comm.items(), key=lambda x: x[1]["rank_2026"]):
        dr = drafted[pid]
        tr = transport[pid]
        s5 = tags["spots_5a"].get(pid, [])
        hc = tags["hist_cities"].get(pid, [])
        wi = intros[pid]

        intro_txt = dr["intro_30_50"].strip()
        assert 30 <= len(intro_txt) <= 50, f"Length violation {pid} {c['short_name']}: {len(intro_txt)} {intro_txt}"

        rec = {
            "place_id": pid,
            "short_name": c["short_name"],
            "canonical_name": c["canonical_name"],
            "province": c["province"],
            "tier_2026": c["tier_2026"],
            "rank_2026": c["rank_2026"],
            "urban_agglomerations": c["urban_agglomerations"],
            # Narrative & Heritage / Tourism
            "city_positioning": dr["city_positioning"],
            "intro_30_50": intro_txt,
            "intro_char_len": len(intro_txt),
            "history_culture_tags": dr["history_culture_tags"],
            "tourism_highlights": dr["tourism_highlights"],
            "is_historic_city": 1 if hc else 0,
            "historic_city_names": hc,
            "scenic_5a_count": len(s5),
            "scenic_5a_list": s5,
            # Commerce & Macro
            "charm_index_2026": c["charm_index_2026"],
            "commercial_score_2026": c["commercial_score_2026"],
            "hub_score_2026": c["hub_score_2026"],
            "activity_score_2026": c["activity_score_2026"],
            "newecon_score_2026": c["newecon_score_2026"],
            "potential_score_2026": c["potential_score_2026"],
            "gdp_yi": c["gdp_yi"],
            "pop_wan": c["pop_wan"],
            "retail_yi": c["retail_yi"],
            "mall_cnt": int(c["mall_cnt"]) if c["mall_cnt"] is not None else None,
            "mall_area": c["mall_area"],
            "univ_wan": c["univ_wan"],
            "commerce_macro_summary": format_commerce_summary(c),
            # Transport
            "airport_count_2026": tr["airport_count_2026"],
            "airport_pax_2025": tr["airport_pax_2025"],
            "hsr_stations_gdc_2026": tr["hsr_stations_gdc_2026"],
            "hsr_daily_trains_gdc": tr["hsr_daily_trains_gdc"],
            "hsr_direct_cities_gdc": tr["hsr_direct_cities_gdc"],
            "has_metro": tr["has_metro"],
            "has_cross_city_metro_ext": tr["has_cross_city_metro_ext"],
            "has_other_urban_rail": tr["has_other_urban_rail"],
            "urban_rail_modes": tr["urban_rail_modes"],
            "ur_lines_latest": tr["ur_lines_latest"],
            "ur_km_latest": tr["ur_km_latest"],
            "ur_pax_2025_wan": tr["ur_pax_2025_wan"],
            "transport_summary": format_transport_summary(tr),
            # Attribution
            "wiki_title": wi["wiki_title"],
        }
        profiles.append(rec)

    (OUT / "city_profiles_337.json").write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    csv_rows = []
    for p in profiles:
        row = dict(p)
        for list_col in ("history_culture_tags", "tourism_highlights", "historic_city_names", "scenic_5a_list"):
            row[list_col] = ";".join(row[list_col])
        csv_rows.append(row)

    with open(OUT / "city_profiles_337.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)

    lens = [p["intro_char_len"] for p in profiles]
    print(f"Built {len(profiles)} city profiles! Char length range: {min(lens)}..{max(lens)}, avg={sum(lens)/len(lens):.1f}")
    print("Sample profiles:")
    for idx in [0, 5, 18, 48, 118, 200, 336]:
        p = profiles[idx]
        print(f"  #{p['rank_2026']:3d} {p['short_name']} ({p['tier_2026']}, {p['intro_char_len']}字): {p['intro_30_50']}")
        print(f"       交通: {p['transport_summary']}")
        print(f"       商业: {p['commerce_macro_summary']}")


if __name__ == "__main__":
    main()
