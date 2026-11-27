"""Verify the data shipped with the static website using Python's standard library."""
from collections import Counter
from pathlib import Path
import json

assets = Path(__file__).resolve().parents[1] / "site" / "assets"
source = (assets / "data.js").read_text(encoding="utf-8").strip()
prefix = "window.atlasData = "
assert source.startswith(prefix) and source.endswith(";")
data = json.loads(source[len(prefix):-1])

cities = data["cities"]
meta = data["meta"]
tiers_meta = meta["tiers"]
tier_totals = [item["total"] for item in tiers_meta]
main_totals = [item["main"] for item in tiers_meta]
main = [city for city in cities if not city[5]]
references = [city for city in cities if city[5]]

assert isinstance(meta.get("year"), int)
assert len(tiers_meta) == 6
assert sum(tier_totals) == len(cities) == 337
assert sum(main_totals) == len(main) == 333 and len(references) == 4
assert len({city[1] for city in cities}) == len(cities)
assert len({city[0] for city in cities}) == len(cities)
assert len({(city[3], city[4]) for city in cities}) == len(cities)
assert len(data["provinces"]) == 34

# 1. Verify progressive core map-base.js + per-province district chunks
base_prefix = "window.atlasMap = "
base_path = assets / "map-base.js"
assert base_path.is_file(), "Missing site/assets/map-base.js (run scripts/split_map_assets.py)"
base_source = base_path.read_text(encoding="utf-8").strip()
assert base_source.startswith(base_prefix) and base_source.endswith(";")
atlas_base = json.loads(base_source[len(base_prefix):-1])

assert set(data["provinces"]) == set(atlas_base["bounds"]) == set(atlas_base["provinces"])
assert all(path.startswith("M") for path, _ in atlas_base["provinces"].values())
assert atlas_base["seaBoundary"].count("M") == 10
assert atlas_base["seaLand"].startswith("M")
assert atlas_base["seaCities"]["460300"].startswith("M")

districts_dir = assets / "districts"
district_provinces = atlas_base.get("districtProvinces")
assert isinstance(district_provinces, list) and len(district_provinces) == 27
loaded_districts = {}
for prov in district_provinces:
    chunk_path = districts_dir / f"{prov}.js"
    assert chunk_path.is_file(), f"Missing district chunk: {chunk_path}"
    raw_lines = [line.strip() for line in chunk_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert raw_lines[0] == "window.atlasDistricts = window.atlasDistricts || {};"
    assign_prefix = f'window.atlasDistricts["{prov}"] = '
    assert raw_lines[1].startswith(assign_prefix) and raw_lines[1].endswith(";")
    loaded_districts[prov] = json.loads(raw_lines[1][len(assign_prefix):-1])

assert loaded_districts["51"]["510100"].startswith("M")
for city in main:
    code, province = city[1], city[2]
    if code == "460300":
        continue
    assert loaded_districts[province][code].startswith("M"), code

subdistricts_dir = assets / "subdistricts"
expected_subdistricts = {"110000": 16, "120000": 16, "310000": 16, "500000": 38, "440300": 9}
for city_code, expected_cnt in expected_subdistricts.items():
    sub_path = subdistricts_dir / f"{city_code}.js"
    assert sub_path.is_file(), f"Missing subdistrict chunk: {sub_path}"
    raw_lines = [line.strip() for line in sub_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert raw_lines[0] == "window.atlasSubdistricts = window.atlasSubdistricts || {};"
    assign_prefix = f'window.atlasSubdistricts["{city_code}"] = '
    assert raw_lines[1].startswith(assign_prefix) and raw_lines[1].endswith(";")
    sub_data = json.loads(raw_lines[1][len(assign_prefix):-1])
    assert len(sub_data["bounds"]) == 4 and sub_data["path"].startswith("M")
    assert len(sub_data["items"]) == expected_cnt
    for item_name, pt, size in sub_data["items"]:
        assert item_name and len(pt) == 2 and size[0] > 0 and size[1] > 0

# 2. Verify canonical full map-data.js if present locally
full_map_path = assets / "map-data.js"
if full_map_path.is_file():
    map_source = full_map_path.read_text(encoding="utf-8").strip()
    assert map_source.startswith(base_prefix) and map_source.endswith(";")
    atlas_map = json.loads(map_source[len(base_prefix):-1])
    assert set(atlas_map["districts"].keys()) == set(district_provinces)
    for prov, mapping in atlas_map["districts"].items():
        assert set(mapping.keys()) == set(loaded_districts[prov].keys())

assert Counter(city[3] for city in main) == dict(enumerate(main_totals))
for tier, total in enumerate(tier_totals):
    assert {city[4] for city in cities if city[3] == tier} == set(range(1, total + 1)), tier
assert {city[0] for city in references} == set(meta["referenceNames"])
assert {city[0] for city in main if city[2] == "54"} == {
    "拉萨", "日喀则", "昌都", "林芝", "山南", "那曲", "阿里",
}
for name, code, province, tier, position, _, coordinates, point, _ in cities:
    assert code[:2] == province and province in data["provinces"], name
    assert 1 <= position <= tier_totals[tier], name
    assert 73 <= coordinates[0] <= 135 and 16 <= coordinates[1] <= 54, name
    frame = atlas_base["seaFrame"] if code == "460300" else atlas_base["frame"]
    assert frame[0] <= point[0] <= frame[2] and frame[1] <= point[1] <= frame[3], name

prof_path = assets / "city-profiles.js"
if prof_path.is_file():
    prof_prefix = "window.atlasProfiles = "
    prof_src = prof_path.read_text(encoding="utf-8").strip()
    assert prof_src.startswith(prof_prefix) and prof_src.endswith(";")
    profiles = json.loads(prof_src[len(prof_prefix):-1])
    assert set(profiles.keys()) == {city[1] for city in cities}
    for code, item in profiles.items():
        assert 30 <= len(item["i"]) <= 50, (code, len(item["i"]))
        assert isinstance(item["ec"], list) and len(item["ec"]) == 6, code
        assert isinstance(item["tr"], list) and len(item["tr"]) == 14, code

decade_path = assets / "city-decade-ranks.js"
if decade_path.is_file():
    decade_prefix = "window.atlasDecadeRanks = "
    decade_src = decade_path.read_text(encoding="utf-8").strip()
    assert decade_src.startswith(decade_prefix) and decade_src.endswith(";")
    decade_payload = json.loads(decade_src[len(decade_prefix):-1])
    assert isinstance(decade_payload.get("meta"), dict) and len(decade_payload["meta"].get("natGr", [])) == 10
    decade_cities = decade_payload["cities"]
    assert set(decade_cities.keys()) == {city[1] for city in cities}
    tier_set = {item["name"] for item in tiers_meta}
    for code, item in decade_cities.items():
        assert isinstance(item, list) and len(item) == 5, code
        ranks_11, tiers_11, edis_10, grs_10, flags_10 = item
        assert len(ranks_11) == 11 and all(1 <= r <= 337 for r in ranks_11), (code, ranks_11)
        assert len(tiers_11) == 11 and all(t in tier_set for t in tiers_11), (code, tiers_11)
        assert len(edis_10) == 10 and all(v is None or (0 <= v <= 100) for v in edis_10), code
        assert len(grs_10) == 10 and len(flags_10) == 10, code

print(
    f"{meta['year']} 年版：333 个地级行政区、4 座直辖市、34 个省级图层、"
    f"{len(district_provinces)} 个懒加载地市分片、线级数量、定位字段与南海附图均通过。"
)
