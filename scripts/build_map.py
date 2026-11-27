"""Project the pinned open map layers into compact SVG paths.

Usage: python scripts/build_map.py /path/to/chn/global
Build only: requires pyproj and shapely. Website runtime has no dependencies.
"""
from hashlib import sha256
from pathlib import Path
import json
import sys

from pyproj import Transformer
from shapely.geometry import shape
from shapely import transform

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets"
SOURCE = Path(sys.argv[1])
SOURCE_HASH = {
    1: "11c45e97b70165dfb2bc0c5c8e428108a4723d055e8ffa1663b5eb05783e15d3",
    2: "f22a0c64f9db010b82ef22f1301bee20f0bfb7501acb13e05038d21b882e6f34",
}
CITY_PREFIX = "window.atlasData = "
city_path = ASSETS / "data.js"
city_data = json.loads(city_path.read_text().strip().removeprefix(CITY_PREFIX).removesuffix(";"))

def project_at(meridian, latitude, parallels):
    projection = Transformer.from_crs(
        4490,
        f"+proj=aea +lon_0={meridian} +lat_0={latitude} "
        f"+lat_1={parallels[0]} +lat_2={parallels[1]} +ellps=GRS80 +units=m",
        always_xy=True,
    )
    def project(x, y):
        east, north = projection.transform(x, y)
        return east / 4000, -north / 4000
    return project

main = project_at(105, 36, (25, 47))
inset = project_at(114, 14, (5, 24))

def path_line(coordinates, close=False):
    points = [(round(x, 2), round(y, 2)) for x, y in coordinates]
    # Keep small islands even if all source vertices round to one SVG pixel.
    if close:
        points = points[:-1]
        if len(set(points)) < 3:
            points = [(round(x, 3), round(y, 3)) for x, y in coordinates[:-1]]
    numbers = lambda x, y: f"{x:g},{y:g}"
    return "M" + " ".join(numbers(x, y) for x, y in points) + ("Z" if close else "")

def path(shape):
    if shape.geom_type == "Polygon":
        return "".join(path_line(ring.coords, True) for ring in (shape.exterior, *shape.interiors))
    if shape.geom_type == "LineString":
        return path_line(shape.coords)
    return "".join(map(path, shape.geoms))

def read_layer(level):
    content = (SOURCE / f"chn-level-{level}.json").read_bytes()
    if sha256(content).hexdigest() != SOURCE_HASH[level]:
        raise ValueError(f"Level {level} does not match the documented map revision")
    layer = json.loads(content)
    assert layer["crs"]["properties"]["name"].endswith("4490")
    for feature in layer["features"]:
        yield feature["properties"].get("gb", "")[3:9], shape(feature["geometry"])

def items(area):
    return list(area.geoms) if area.geom_type == "MultiPolygon" else [area]

def combine_bounds(bounds):
    return [min(b[0] for b in bounds), min(b[1] for b in bounds),
            max(b[2] for b in bounds), max(b[3] for b in bounds)]

provinces = {}
province_bounds = {}
districts = {}
lines = []
inset_paths = []
inset_lines = []
national_bounds = []
sea_bounds = []
for code, area in read_layer(1):
    if not code:
        if len(area.geoms) == 10 and area.bounds[1] < 5:
            projected = transform(area, inset, interleaved=False)
            assert len(projected.geoms) == 10
            inset_lines.extend(path(line) for line in projected.geoms)
            sea_bounds.append(projected.bounds)
        else:
            lines.append(path(transform(area, main, interleaved=False)))
        continue
    key = code[:2]
    parts = items(area)
    # The south inset carries the offshore islands. Keep the full source
    # geometry across the two views, including the eastern island groups.
    local = [part for part in parts if key != "46" or part.bounds[3] >= 18]
    projected = [transform(part, main, interleaved=False) for part in local]
    bounds = combine_bounds([part.bounds for part in projected])
    anchor = max(projected, key=lambda part: part.area).representative_point()
    provinces[key] = ["".join(map(path, projected)), [round(anchor.x, 1), round(anchor.y, 1)]]
    province_bounds[key] = bounds
    national_bounds.append(bounds)
    if key in {"44", "45", "35", "46", "71", "81", "82"}:
        inset_paths.append("".join(path(transform(part, inset, interleaved=False)) for part in parts))

seen = set()
sea_cities = {}
for code, area in read_layer(2):
    if not code or code.endswith("0000") or code[:2] not in provinces:
        continue
    if area.geom_type not in {"Polygon", "MultiPolygon"}:
        continue
    province = code[:2]
    if province in {"71", "81", "82"}:
        continue
    seen.add(code)
    parts = [part for part in items(area) if province != "46" or part.bounds[3] >= 18]
    if parts:
        districts.setdefault(province, {})[code] = "".join(
            path(transform(part, main, interleaved=False)) for part in parts
        )
    if code == "460300":
        sea_cities[code] = "".join(
            path(transform(part, inset, interleaved=False)) for part in items(area)
        )

assert set(provinces) == set(city_data["provinces"])
assert len(inset_lines) == 10
assert len(lines) == 7
for city in city_data["cities"]:
    name, code, province, tier, rank, reference, coordinates = city[:7]
    fallback = city[8]
    city[:] = [name, code, province, tier, rank, reference, coordinates,
               [round(n, 2) for n in (inset if code == "460300" else main)(*coordinates)], fallback]

compact = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
city_rows = ",\n".join("    " + compact(row) for row in city_data["cities"])
meta_block = (
    '  "meta": ' + json.dumps(city_data["meta"], ensure_ascii=False, indent=2).replace("\n", "\n  ") + ",\n"
    if "meta" in city_data else ""
)
city_path.write_text(CITY_PREFIX + "{\n" + meta_block + '  "cities": [\n' + city_rows +
                     '\n  ],\n  "provinces": ' + compact(city_data["provinces"]) + "\n};\n", encoding="utf-8")
rounded = lambda box: [round(float(n), 1) for n in box]
map_data = {
    "provinces": provinces,
    "bounds": {code: rounded(box) for code, box in province_bounds.items()},
    "frame": rounded(combine_bounds(national_bounds)),
    "seaFrame": rounded(combine_bounds(sea_bounds)),
    "boundary": "".join(lines),
    "seaBoundary": "".join(inset_lines),
    "seaLand": "".join(inset_paths),
    "districts": districts,
    "seaCities": sea_cities,
}
map_path = ASSETS / "map-data.js"
map_path.write_text("window.atlasMap = {\n" + ",\n".join(
    "  " + compact(key) + ": " + compact(value) for key, value in map_data.items()
) + "\n};\n")

from split_map_assets import write_progressive_map_assets
base_path, chunks = write_progressive_map_assets(map_data, ASSETS)
print(f"{len(provinces)} province polygons, {len(seen)} prefecture features, "
      f"{len(inset_lines)} maritime segments, {map_path.stat().st_size:,} bytes "
      f"(base={base_path.stat().st_size:,} bytes, {len(chunks)} district shards)")
