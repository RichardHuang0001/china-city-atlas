"""Verify the data shipped with the static website using Python's standard library."""
from collections import Counter
from pathlib import Path
import json

assets = Path(__file__).resolve().parents[1] / "site" / "assets"
source = (assets / "data.js").read_text(encoding="utf-8").strip()
prefix = "window.atlasData = "
assert source.startswith(prefix) and source.endswith(";")
data = json.loads(source[len(prefix):-1])
map_prefix = "window.atlasMap = "
map_source = (assets / "map-data.js").read_text(encoding="utf-8").strip()
assert map_source.startswith(map_prefix) and map_source.endswith(";")
atlas_map = json.loads(map_source[len(map_prefix):-1])
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
assert set(data["provinces"]) == set(atlas_map["bounds"]) == set(atlas_map["provinces"])
assert all(path.startswith("M") for path, _ in atlas_map["provinces"].values())
assert atlas_map["seaBoundary"].count("M") == 10
assert atlas_map["seaLand"].startswith("M")
assert atlas_map["districts"]["51"]["510100"].startswith("M")
assert atlas_map["seaCities"]["460300"].startswith("M")
for city in main:
    code, province = city[1], city[2]
    if code == "460300":
        continue
    assert atlas_map["districts"][province][code].startswith("M"), code
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
    frame = atlas_map["seaFrame"] if code == "460300" else atlas_map["frame"]
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

print(f"{meta['year']} 年版：333 个地级行政区、4 座直辖市、34 个省级图层、线级数量、定位字段与南海附图均通过。")
