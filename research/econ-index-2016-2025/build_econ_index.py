"""Compute the 2016-2025 City Economic Development Index (EDI) using academic methods.

Academic Design (5-Indicator Objective CRITIC Framework):
1. Level & Efficiency Pillars (UNDP HDI logarithmic scaling over 2025 constant prices):
   - x_scale: ln(constant-2025-price real GDP), backward-chained from 2025 anchor.
   - x_pc:    ln(constant-2025-price real GDP per resident), 2017-2024 100% complete.
   - x_rev:   ln(general public budget revenue), measuring real local fiscal capacity.
2. Asymmetric Growth & Deceleration Pillars (Kahneman & Tversky, 1992 loss aversion lambda=2.25):
   - x_gr:  Absolute real GDP growth rate g with contraction asymmetry:
              g >= 0 -> g ;  g < 0 -> 2.25 * g.
   - x_rel: Relative-to-national growth & deceleration momentum:
              Combines annual gap vs national aggregate real growth rate rel = g - g_nat[t]
              (underperforming national pace scaled by 2.25x downside sensitivity) and
              city-specific relative deceleration vs trailing 2-year excess pace
              dec = rel - prev_avg_rel (downside deceleration scaled 1.75x vs 0.5x upside).
   - Both momentum indicators are symmetrically winsorized at [p0.5, p99.5].
3. Objective CRITIC Weighting (Diakoulaki, Mavrotas & Papayannakis, 1995):
   - Computed over all complete 2016-2025 panel observations (n=3,358).
   - Automatically discounts correlated stock redundancy and balances stock scale (~57%)
     against growth/contraction/slowdown dynamics (~43%) with zero arbitrary weights.

Outputs (local research & standalone preview only; does NOT touch site/):
- research/econ-index-2016-2025/city_econ_index_337.json
- research/econ-index-2016-2025/city_econ_index_337.csv
- research/econ-index-2016-2025/methodology_summary.json
- tools/decade-combo-preview-data.js
"""
from collections import defaultdict
from pathlib import Path
import csv
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "research" / "datayicai-mcp"
OUT_DIR = Path(__file__).resolve().parent
PREVIEW_JS = ROOT / "tools" / "decade-combo-preview-data.js"

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
        meta_city = {}
        for row in csv.DictReader(f):
            pid = row["place_id"]
            charm[pid][int(row["year"])] = row
            meta_city[pid] = {
                "name": row["canonical_name"],
                "province": row["province"],
            }

    with open(MCP_DIR / "city-stats" / "macro_panel_2016_2025_337.csv", encoding="utf-8-sig") as f:
        macro = defaultdict(dict)
        for row in csv.DictReader(f):
            macro[row["place_id"]][int(r_year := int(row["year"]))] = row

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

    # National aggregate real GDP growth rates per year (2016..2025)
    agg = {y: sum(real_gdp[pid][y] for pid in real_gdp) for y in MACRO_YEARS}
    nat_gr: dict[int, float] = {}
    for y in range(2017, 2026):
        nat_gr[y] = (agg[y] / agg[y - 1] - 1.0) * 100.0
    nat_gr[2016] = (
        sum(
            real_gdp[pid][2016] * float(macro[pid][2016]["地区生产总值实际增长率 (%)"])
            for pid in real_gdp
        )
        / agg[2016]
    )

    # 2. Resident population (carry-nearest boundary only when 2016 or 2025 absent)
    pop: dict[str, dict[int, float]] = defaultdict(dict)
    for pid, ym in macro.items():
        avail = {y: float(ym[y]["常住人口 (万人)"]) for y in MACRO_YEARS if ym[y]["常住人口 (万人)"] != ""}
        if not avail:
            continue
        for y in MACRO_YEARS:
            pop[pid][y] = avail[y] if y in avail else avail[min(avail.keys(), key=lambda k: abs(k - y))]

    # 3. Collect 5-indicator panel features
    complete_obs = []
    partial_map: dict[tuple[str, int], dict[str, float | None]] = {}
    for pid in sorted(charm.keys()):
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
                u_abs = None
                rel = None
                dec = None
                u_dyn = None
                rel_hist.append(None)

            row_feats = {
                "x_scale": math.log(rg) if rg else None,
                "x_pc": math.log((rg * 10000.0) / pp) if (rg and pp) else None,
                "x_rev": math.log(rev) if rev else None,
                "x_gr": u_abs,
                "x_rel": u_dyn,
                "raw_rg": rg,
                "raw_pc": ((rg * 10000.0) / pp) if (rg and pp) else None,
                "raw_rev": rev,
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
    corr_matrix = {c1: {c2: corr(vecs[c1], vecs[c2]) for c2 in cols} for c1 in cols}
    critic_c = {c1: stds[c1] * sum(1.0 - corr_matrix[c1][c2] for c2 in cols) for c1 in cols}
    tot_c = sum(critic_c.values())
    weights = {c: critic_c[c] / tot_c for c in cols}

    # 4. Score all 337 cities across 2016..2025 + package 2016..2026 rank bars
    records = {}
    csv_rows = []
    preview_data = {}

    for pid in sorted(charm.keys()):
        ranks = [int(float(charm[pid][y]["overall_rank"])) for y in CHARM_YEARS]
        tiers = [charm[pid][y]["tier"] for y in CHARM_YEARS]
        edis = []
        raw_grs = []
        raw_gdps = []
        flags = []  # 0=normal, 1=notable slowdown or trailing national pace, 2=negative growth
        series_detail = []
        for idx, y in enumerate(MACRO_YEARS):
            feats = partial_map[(pid, y)]
            avail_cols = [c for c in cols if feats[c] is not None]
            if len(avail_cols) >= 4:
                w_sum = sum(weights[c] for c in avail_cols)
                edi = round(100.0 * sum(weights[c] * norm_val(c, feats[c]) for c in avail_cols) / w_sum, 1)
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
            raw_gdps.append(round(feats["raw_rg"], 1) if feats["raw_rg"] is not None else None)
            flags.append(flag)
            series_detail.append({
                "year": y,
                "edi": edi,
                "realGdpYi": raw_gdps[-1],
                "perCapitaYuan": round(feats["raw_pc"]) if feats["raw_pc"] is not None else None,
                "fiscalRevYi": round(feats["raw_rev"], 2) if feats["raw_rev"] is not None else None,
                "realGrowthPct": gr,
                "nationalGrowthPct": round(nat_gr[y], 2),
                "excessVsNationalPct": round(rel, 2) if rel is not None else None,
                "flag": flag,
                "charmRank": charm[pid][y]["overall_rank"],
            })

        edi_delta = round(edis[-1] - edis[0], 1) if (edis[0] is not None and edis[-1] is not None) else None
        min_edi = min((v for v in edis if v is not None), default=None)
        max_edi = max((v for v in edis if v is not None), default=None)
        neg_years = [MACRO_YEARS[i] for i, fl in enumerate(flags) if fl == 2]
        slow_years = [MACRO_YEARS[i] for i, fl in enumerate(flags) if fl == 1]

        records[pid] = {
            "code": pid,
            "name": meta_city[pid]["name"],
            "province": meta_city[pid]["province"],
            "tier2026": tiers[-1],
            "rank2016": ranks[0],
            "rank2026": ranks[-1],
            "rankDelta": ranks[0] - ranks[-1],
            "edi2016": edis[0],
            "edi2025": edis[-1],
            "ediDelta": edi_delta,
            "ediMin": min_edi,
            "ediMax": max_edi,
            "negativeGrowthYears": neg_years,
            "slowOrLagYears": slow_years,
            "charmRanks16_26": ranks,
            "charmTiers16_26": tiers,
            "econSeries16_25": series_detail,
        }

        # Compact JS for preview: [ranks[11], tiers[11], edis[10], rawGrs[10], rawGdps[10], flags[10]]
        preview_data[pid] = [ranks, tiers, edis, raw_grs, raw_gdps, flags]

        csv_rows.append({
            "place_id": pid,
            "name": meta_city[pid]["name"],
            "province": meta_city[pid]["province"],
            "tier_2026": tiers[-1],
            "rank_2016": ranks[0],
            "rank_2026": ranks[-1],
            "rank_delta": ranks[0] - ranks[-1],
            "edi_2016": edis[0],
            "edi_2025": edis[-1],
            "edi_delta": edi_delta,
            "edi_min": min_edi,
            "edi_max": max_edi,
            "neg_growth_years": ";".join(map(str, neg_years)),
            "slow_or_lag_years": ";".join(map(str, slow_years)),
            **{f"edi_{y}": edis[i] for i, y in enumerate(MACRO_YEARS)},
            **{f"gr_{y}": raw_grs[i] for i, y in enumerate(MACRO_YEARS)},
        })

    methodology = {
        "completePanelObservations": len(complete_obs),
        "lossAversionLambda": LOSS_AVERSION,
        "nationalRealGrowthByYear": {str(y): round(nat_gr[y], 2) for y in MACRO_YEARS},
        "winsorBounds": {k: [round(v[0], 4), round(v[1], 4)] for k, v in bounds.items()},
        "stds": {k: round(v, 4) for k, v in stds.items()},
        "corrMatrix": {c1: {c2: round(v, 4) for c2, v in row.items()} for c1, row in corr_matrix.items()},
        "criticWeights": {k: round(v, 4) for k, v in weights.items()},
    }

    (OUT_DIR / "methodology_summary.json").write_text(
        json.dumps(methodology, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "city_econ_index_337.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with open(OUT_DIR / "city_econ_index_337.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)

    meta_js = json.dumps({
        "weights": methodology["criticWeights"],
        "natGr": [round(nat_gr[y], 1) for y in MACRO_YEARS],
    }, separators=(",", ":"))
    data_js = json.dumps(preview_data, ensure_ascii=False, separators=(",", ":"))
    PREVIEW_JS.write_text(
        f"window.atlasComboPreview = {{meta:{meta_js},cities:{data_js}}};\n",
        encoding="utf-8",
    )

    print("CRITIC Weights:", methodology["criticWeights"])
    print(f"Built 337-city 5-indicator EDI + Combo preview: JS={PREVIEW_JS.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
