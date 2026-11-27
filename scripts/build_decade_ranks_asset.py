"""Generate site/assets/city-decade-ranks.js with 2016-2026 ranks and 2016-2025 CRITIC EDI.

Outputs a compact lazy-loadable JS file setting window.atlasDecadeRanks:
    {
      "meta": {
        "natGr": [g2016, ..., g2025],
        "weights": { "x_scale": ..., "x_pc": ..., "x_rev": ..., "x_gr": ..., "x_rel": ... }
      },
      "cities": {
        "<6-digit-code>": [
          ranks[11],   // 2016..2026 national Charm overall_rank
          tiers[11],   // 2016..2026 tier names
          edis[10],    // 2016..2025 Economic Development Index (0..100) or null
          rawGrs[10],  // 2016..2025 official real GDP growth rate (%) or null
          flags[10]    // 0=normal, 1=notable slowdown or lagging national, 2=contraction
        ], ...
      }
    }

Run:
    python3 scripts/build_decade_ranks_asset.py
"""
from collections import defaultdict
from pathlib import Path
import csv
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "research" / "datayicai-mcp"
ASSETS = ROOT / "site" / "assets"

MACRO_YEARS = list(range(2016, 2026))
CHARM_YEARS = list(range(2016, 2027))
LOSS_AVERSION = 2.25


def corr(xs: list[float], ys: list[float]) -> float:
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / den if den > 0 else 0.0


def main() -> None:
    with open(MCP_DIR / "charm-history" / "city_charm_2016_2026_panel.csv", encoding="utf-8-sig") as f:
        charm = defaultdict(dict)
        for row in csv.DictReader(f):
            charm[row["place_id"]][int(row["year"])] = row

    with open(MCP_DIR / "city-stats" / "macro_panel_2016_2025_337.csv", encoding="utf-8-sig") as f:
        macro = defaultdict(dict)
        for row in csv.DictReader(f):
            macro[row["place_id"]][int(row["year"])] = row

    site_data = json.loads(
        (ASSETS / "data.js")
        .read_text(encoding="utf-8")
        .strip()
        .removeprefix("window.atlasData = ")
        .removesuffix(";")
    )
    city_codes = sorted(city[1] for city in site_data["cities"])
    assert set(city_codes) == set(charm.keys()), "Mismatch between data.js and charm panel"

    # 1. Backward-chain constant-2025-price GDP
    real_gdp: dict[str, dict[int, float]] = defaultdict(dict)
    for pid, ym in macro.items():
        g25 = ym[2025]["地区生产总值 (亿元)"]
        g24 = ym[2024]["地区生产总值 (亿元)"]
        gr25 = ym[2025]["地区生产总值实际增长率 (%)"]
        if g25 != "":
            real_gdp[pid][2025] = float(g25)
        elif g24 != "" and gr25 != "":
            real_gdp[pid][2025] = float(g24) * (1.0 + float(gr25) / 100.0)
        else:
            continue
        cur = real_gdp[pid][2025]
        for y in range(2025, 2016, -1):
            cur = cur / (1.0 + float(ym[y]["地区生产总值实际增长率 (%)"]) / 100.0)
            real_gdp[pid][y - 1] = cur

    agg = {y: sum(real_gdp[pid][y] for pid in real_gdp) for y in MACRO_YEARS}
    nat_gr: dict[int, float] = {
        y: (agg[y] / agg[y - 1] - 1.0) * 100.0 for y in range(2017, 2026)
    }
    nat_gr[2016] = (
        sum(
            real_gdp[pid][2016] * float(macro[pid][2016]["地区生产总值实际增长率 (%)"])
            for pid in real_gdp
        )
        / agg[2016]
    )

    # 2. Resident population (carry-nearest only for boundary 2016/2025 gaps)
    pop: dict[str, dict[int, float]] = defaultdict(dict)
    for pid, ym in macro.items():
        avail = {y: float(ym[y]["常住人口 (万人)"]) for y in MACRO_YEARS if ym[y]["常住人口 (万人)"] != ""}
        if not avail:
            continue
        for y in MACRO_YEARS:
            pop[pid][y] = avail[y] if y in avail else avail[min(avail.keys(), key=lambda k: abs(k - y))]

    # 3. 5-indicator panel features & CRITIC objective weighting
    complete_obs = []
    partial_map: dict[tuple[str, int], dict[str, float | None]] = {}
    for pid in city_codes:
        rel_hist: list[float | None] = []
        for y in MACRO_YEARS:
            rg = real_gdp.get(pid, {}).get(y)
            pp = pop.get(pid, {}).get(y)
            rev_s = macro[pid][y]["一般公共预算收入 (亿元)"]
            gr_s = macro[pid][y]["地区生产总值实际增长率 (%)"]
            rev = float(rev_s) if rev_s != "" and float(rev_s) > 0 else None
            gr = float(gr_s) if gr_s != "" else None

            if gr is not None:
                u_abs = gr if gr >= 0 else LOSS_AVERSION * gr
                rel = gr - nat_gr[y]
                u_rel = rel if rel >= 0 else LOSS_AVERSION * rel
                prior_rels = [r for r in rel_hist[-2:] if r is not None]
                if prior_rels:
                    dec = rel - (sum(prior_rels) / len(prior_rels))
                    u_dec = 0.65 * dec if dec >= 0 else 2.0 * dec
                else:
                    dec = 0.0
                    u_dec = 0.0
                rel_hist.append(rel)
                u_dyn = 0.55 * u_rel + 0.45 * u_dec
            else:
                u_abs = rel = dec = u_dyn = None
                rel_hist.append(None)

            row_feats = {
                "x_scale": math.log(rg) if rg else None,
                "x_pc": math.log((rg * 10000.0) / pp) if (rg and pp) else None,
                "x_rev": math.log(rev) if rev else None,
                "x_gr": u_abs,
                "x_rel": u_dyn,
                "raw_gr": gr,
                "rel_vs_nat": rel,
                "rel_dec": dec,
            }
            partial_map[(pid, y)] = row_feats
            if all(row_feats[k] is not None for k in ("x_scale", "x_pc", "x_rev", "x_gr", "x_rel")):
                complete_obs.append(row_feats)

    cols = ["x_scale", "x_pc", "x_rev", "x_gr", "x_rel"]
    bounds = {}
    for c in cols:
        vals = sorted(o[c] for o in complete_obs)
        if c in ("x_gr", "x_rel"):
            bounds[c] = (vals[int(0.02 * len(vals))], vals[int(0.98 * len(vals))])
        else:
            bounds[c] = (vals[0], vals[-1])

    def norm_val(col: str, val: float) -> float:
        lo, hi = bounds[col]
        return max(0.0, min(1.0, (val - lo) / (hi - lo)))

    vecs = {c: [norm_val(c, o[c]) for o in complete_obs] for c in cols}
    stds = {c: statistics.pstdev(vecs[c]) for c in cols}
    critic_c = {
        c1: stds[c1] * sum(1.0 - corr(vecs[c1], vecs[c2]) for c2 in cols)
        for c1 in cols
    }
    tot_c = sum(critic_c.values())
    weights = {c: critic_c[c] / tot_c for c in cols}

    cities_out = {}
    for code in city_codes:
        ranks = [int(float(charm[code][y]["overall_rank"])) for y in CHARM_YEARS]
        tiers = [charm[code][y]["tier"] for y in CHARM_YEARS]
        edis = []
        raw_grs = []
        flags = []
        for y in MACRO_YEARS:
            feats = partial_map[(code, y)]
            avail = [c for c in cols if feats[c] is not None]
            if len(avail) >= 4:
                w_sum = sum(weights[c] for c in avail)
                edi = round(100.0 * sum(weights[c] * norm_val(c, feats[c]) for c in avail) / w_sum, 1)
            else:
                edi = None
            gr = round(feats["raw_gr"], 2) if feats["raw_gr"] is not None else None
            rel = feats["rel_vs_nat"]
            dec = feats["rel_dec"]
            if gr is None:
                flag = 0
            elif gr < 0:
                flag = 2
            elif (rel is not None and rel <= -2.0) or (dec is not None and dec <= -2.5):
                flag = 1
            else:
                flag = 0
            edis.append(edi)
            raw_grs.append(gr)
            flags.append(flag)
        cities_out[code] = [ranks, tiers, edis, raw_grs, flags]

    payload_obj = {
        "meta": {
            "natGr": [round(nat_gr[y], 1) for y in MACRO_YEARS],
            "weights": {k: round(v, 4) for k, v in weights.items()},
        },
        "cities": cities_out,
    }
    out_path = ASSETS / "city-decade-ranks.js"
    out_path.write_text(
        "window.atlasDecadeRanks = "
        + json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path.name}: {len(cities_out)} cities, {out_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
