"""Split site/assets/map-data.js into progressive core + per-province district chunks.

Uses only the Python standard library. Run after scripts/build_map.py, or anytime
site/assets/map-data.js is updated:
    python3 scripts/split_map_assets.py
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets"
DISTRICTS_DIR = ASSETS / "districts"
MAP_PREFIX = "window.atlasMap = "


def round_svg_path(path_str: str, decimals: int = 1) -> str:
    """Deterministically round SVG path coordinates while preserving tiny rings."""
    if not path_str:
        return ""
    parts = []
    for sub in path_str.split("M"):
        if not sub:
            continue
        closed = sub.endswith("Z")
        body = sub[:-1] if closed else sub
        coords = []
        for token in body.split(" "):
            if not token:
                continue
            x_s, y_s = token.split(",")
            coords.append((float(x_s), float(y_s)))
        rounded = [(round(x, decimals), round(y, decimals)) for x, y in coords]
        dedup = []
        for pt in rounded:
            if not dedup or pt != dedup[-1]:
                dedup.append(pt)
        if closed and len(dedup) > 1 and dedup[-1] == dedup[0]:
            dedup.pop()
        if closed and len(set(dedup)) < 3:
            pts_hi = [(round(x, 3), round(y, 3)) for x, y in coords]
            dedup = []
            for pt in pts_hi:
                if not dedup or pt != dedup[-1]:
                    dedup.append(pt)
            if len(dedup) > 1 and dedup[-1] == dedup[0]:
                dedup.pop()
        if not dedup:
            continue
        parts.append("M" + " ".join(f"{x:g},{y:g}" for x, y in dedup) + ("Z" if closed else ""))
    return "".join(parts)


def collect_subdistrict_bounds(assets_dir: Path) -> dict[str, list[float]]:
    """Read bounding boxes from generated site/assets/subdistricts/*.js shards."""
    sub_dir = assets_dir / "subdistricts"
    if not sub_dir.is_dir():
        return {}
    bounds = {}
    for shard_path in sorted(sub_dir.glob("*.js")):
        code = shard_path.stem
        prefix = f'window.atlasSubdistricts["{code}"] = '
        for line in shard_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(prefix) and line.endswith(";"):
                payload = json.loads(line[len(prefix):-1])
                if isinstance(payload.get("bounds"), list) and len(payload["bounds"]) == 4:
                    bounds[code] = payload["bounds"]
                break
    return bounds


def write_progressive_map_assets(map_data: dict, assets_dir: Path = ASSETS) -> tuple[Path, list[Path]]:
    """Write critical core map-base.js and lazy per-province districts/*.js."""
    compact = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    provinces_base = {
        code: [round_svg_path(outline, 1), anchor]
        for code, (outline, anchor) in map_data["provinces"].items()
    }
    districts = map_data["districts"]
    district_provinces = sorted(districts.keys())

    base_payload = {
        "provinces": provinces_base,
        "bounds": map_data["bounds"],
        "frame": map_data["frame"],
        "seaFrame": map_data["seaFrame"],
        "boundary": round_svg_path(map_data["boundary"], 1),
        "seaBoundary": round_svg_path(map_data["seaBoundary"], 1),
        "seaLand": round_svg_path(map_data["seaLand"], 1),
        "seaCities": map_data["seaCities"],
        "districtProvinces": district_provinces,
        "subdistrictBounds": collect_subdistrict_bounds(assets_dir),
    }
    base_path = assets_dir / "map-base.js"
    base_path.write_text(
        "window.atlasMap = {\n"
        + ",\n".join("  " + compact(k) + ": " + compact(v) for k, v in base_payload.items())
        + "\n};\n",
        encoding="utf-8",
    )

    out_dir = assets_dir / "districts"
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = {f"{prov}.js" for prov in district_provinces}
    for old in out_dir.glob("*.js"):
        if old.name not in expected:
            old.unlink()

    written = []
    for prov in district_provinces:
        chunk_path = out_dir / f"{prov}.js"
        chunk_path.write_text(
            "window.atlasDistricts = window.atlasDistricts || {};\n"
            + f"window.atlasDistricts[{compact(prov)}] = {compact(districts[prov])};\n",
            encoding="utf-8",
        )
        written.append(chunk_path)
    return base_path, written


def main() -> None:
    map_path = ASSETS / "map-data.js"
    raw = map_path.read_text(encoding="utf-8").strip()
    assert raw.startswith(MAP_PREFIX) and raw.endswith(";"), "Unexpected map-data.js format"
    map_data = json.loads(raw[len(MAP_PREFIX):-1])
    base_path, chunks = write_progressive_map_assets(map_data, ASSETS)
    total_chunk_bytes = sum(p.stat().st_size for p in chunks)
    print(
        f"Wrote {base_path.name} ({base_path.stat().st_size:,} bytes) + "
        f"{len(chunks)} district chunks ({total_chunk_bytes:,} bytes total)"
    )


if __name__ == "__main__":
    main()
