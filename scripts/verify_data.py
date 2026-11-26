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
main = [city for city in cities if not city[5]]
references = [city for city in cities if city[5]]

assert len(main) == 293 and len(references) == 4
assert len({city[1] for city in cities}) == len(cities)
assert len({city[0] for city in cities}) == len(cities)
assert len({(city[3], city[4]) for city in cities}) == len(cities)
assert len(data["provinces"]) == 34
assert set(data["provinces"]) == set(atlas_map["bounds"]) == set(atlas_map["provinces"])
assert all(path.startswith("M") for path, _ in atlas_map["provinces"].values())
assert atlas_map["seaBoundary"].count("M") == 10
assert atlas_map["seaLand"].startswith("M")
assert atlas_map["districts"]["51"].startswith("M")
assert Counter(city[3] for city in main) == dict(enumerate([2, 13, 30, 70, 83, 95]))
assert {city[0] for city in references} == {"北京", "上海", "天津", "重庆"}
assert {city[0] for city in main if city[2] == "54"} == {
    "拉萨", "日喀则", "昌都", "林芝", "山南", "那曲",
}
for name, code, province, tier, position, _, coordinates, point, _ in cities:
    assert code[:2] == province and province in data["provinces"], name
    assert 1 <= position <= [4, 15, 30, 70, 90, 128][tier], name
    assert 73 <= coordinates[0] <= 135 and 16 <= coordinates[1] <= 54, name
    frame = atlas_map["seaFrame"] if code == "460300" else atlas_map["frame"]
    assert frame[0] <= point[0] <= frame[2] and frame[1] <= point[1] <= frame[3], name
print("293 座地级市、4 座直辖市、34 个省级图层、线级数量、定位字段与南海附图均通过。")
