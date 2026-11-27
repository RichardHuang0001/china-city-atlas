"""Project county/district boundaries for municipalities and Shenzhen into lazy JS shards.

Usage: python3 scripts/build_subdistricts.py /path/to/chn/global
Uses only the Python standard library; shares path rounding with split_map_assets.py.
"""
from hashlib import sha256
from pathlib import Path
import json
import re
import sys

from geo_proj import project_main
from split_map_assets import round_svg_path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets"
OUT_DIR = ASSETS / "subdistricts"
SOURCE_HASH_L3 = "cb48c4a1676bdf486f0dd2b2166a1b2a0703592a9c8e2f8701edd5f5f9655a91"

# Map 6-digit prefix -> parent city code in site/assets/data.js
SUBDISTRICT_TARGETS = {
    "11": "110000",
    "12": "120000",
    "31": "310000",
    "50": "500000",
    "4403": "440300",
}


def ring_area_centroid(pts: list[tuple[float, float]]) -> tuple[float, float, float]:
    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area *= 0.5
    if abs(area) < 1e-9:
        return abs(area), pts[0][0], pts[0][1]
    return abs(area), cx / (6 * area), cy / (6 * area)


def point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-18) + x1):
            inside = not inside
    return inside


def interior_point(poly_rings: list[list[tuple[float, float]]]) -> tuple[float, float]:
    outer = poly_rings[0]
    _, cx, cy = ring_area_centroid(outer)
    if point_in_ring(cx, cy, outer) and not any(point_in_ring(cx, cy, h) for h in poly_rings[1:]):
        return round(cx, 1), round(cy, 1)
    ys = [p[1] for p in outer]
    min_y, max_y = min(ys), max(ys)
    best = (0.0, cx, cy)
    for step in range(1, 16):
        y = min_y + (max_y - min_y) * step / 16
        xs = []
        for ring in poly_rings:
            for i in range(len(ring)):
                x1, y1 = ring[i]
                x2, y2 = ring[(i + 1) % len(ring)]
                if (y1 > y) != (y2 > y):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            span = xs[i + 1] - xs[i]
            if span > best[0]:
                best = (span, (xs[i] + xs[i + 1]) / 2, y)
    return round(best[1], 1), round(best[2], 1)


def short_district_name(full_name: str) -> str:
    if full_name in ("浦东新区", "滨海新区"):
        return full_name
    stripped = re.sub(r"(土家族苗族|苗族土家族|土家族)自治县$", "", full_name)
    if stripped != full_name:
        return stripped
    if len(full_name) > 2 and full_name.endswith(("区", "县")):
        return full_name[:-1]
    return full_name


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 scripts/build_subdistricts.py /path/to/chn/global")
    source_path = Path(sys.argv[1]) / "chn-level-3.json"
    raw_bytes = source_path.read_bytes()
    digest = sha256(raw_bytes).hexdigest()
    if digest != SOURCE_HASH_L3:
        raise ValueError(f"chn-level-3.json SHA-256 mismatch: {digest}")
    layer = json.loads(raw_bytes)
    assert layer["crs"]["properties"]["name"].endswith("4490")

    grouped: dict[str, list[tuple[str, str, str, list[float], list[float]]]] = {
        code: [] for code in SUBDISTRICT_TARGETS.values()
    }
    city_boxes: dict[str, list[list[float]]] = {code: [] for code in SUBDISTRICT_TARGETS.values()}

    for feat in layer["features"]:
        props = feat["properties"]
        gb = props.get("gb", "")[3:9]
        city_code = SUBDISTRICT_TARGETS.get(gb[:4]) or SUBDISTRICT_TARGETS.get(gb[:2])
        if not city_code:
            continue
        geom = feat["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        svg_parts = []
        best_area = -1.0
        best_poly = None
        xs_all, ys_all = [], []
        for poly in polys:
            proj_rings = [[project_main(lon, lat) for lon, lat in ring[:-1]] for ring in poly]
            area, _, _ = ring_area_centroid(proj_rings[0])
            if area > best_area:
                best_area = area
                best_poly = proj_rings
            for ring in proj_rings:
                for x, y in ring:
                    xs_all.append(x)
                    ys_all.append(y)
                svg_parts.append("M" + " ".join(f"{round(x, 2):g},{round(y, 2):g}" for x, y in ring) + "Z")
        ax, ay = interior_point(best_poly)
        box = [min(xs_all), min(ys_all), max(xs_all), max(ys_all)]
        city_boxes[city_code].append(box)
        path_str = round_svg_path("".join(svg_parts), 2)
        grouped[city_code].append((
            gb,
            short_district_name(props["full_name"]),
            path_str,
            [ax, ay],
            [round(box[2] - box[0], 1), round(box[3] - box[1], 1)],
        ))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    compact = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    for city_code, entries in sorted(grouped.items()):
        entries.sort(key=lambda item: item[0])
        boxes = city_boxes[city_code]
        bounds = [
            round(min(b[0] for b in boxes), 1),
            round(min(b[1] for b in boxes), 1),
            round(max(b[2] for b in boxes), 1),
            round(max(b[3] for b in boxes), 1),
        ]
        payload = {
            "bounds": bounds,
            "path": "".join(item[2] for item in entries),
            "items": [[item[1], item[3], item[4]] for item in entries],
        }
        shard = OUT_DIR / f"{city_code}.js"
        shard.write_text(
            "window.atlasSubdistricts = window.atlasSubdistricts || {};\n"
            + f"window.atlasSubdistricts[{compact(city_code)}] = {compact(payload)};\n",
            encoding="utf-8",
        )
        print(f"Wrote {shard.name}: {len(entries)} districts, bounds={bounds}, {shard.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
