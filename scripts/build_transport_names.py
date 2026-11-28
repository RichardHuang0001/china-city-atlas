"""Build the lazy-loaded transport names from the archived transport dataset.

Run: python3 scripts/build_transport_names.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'research/transport-2025-2026'
DESTINATION = ROOT / 'site/assets/city-transport-names.js'


def main():
    cities = json.loads((SOURCE / 'city_transport_337_2025_2026.json').read_text(encoding='utf-8'))
    with (SOURCE / 'hsr_2026_11_by_city.csv').open(encoding='utf-8', newline='') as stream:
        rail = {row['place_id']: row for row in csv.DictReader(stream)}
    assert len(cities) == len(rail) == 337
    result = {}
    for city in cities:
        code = city['place_id']
        # CAAC's city/airport shorthand is retained, with the category added;
        # avoid inventing formal names where the source gives only shorthand.
        airports = [re.sub(r'\([^()]*\)$', '', name) + '机场'
                    for name in city['airport_names'].split(';') if name]
        stations = [name for name in rail[code]['hsr_station_names_gdc'].split(';') if name]
        assert len(airports) == city['airport_count_2026'], (code, airports)
        assert len(stations) == city['hsr_stations_gdc_2026'], (code, stations)
        assert len(set(airports)) == len(airports) and len(set(stations)) == len(stations), code
        result[code] = {'airports': airports, 'stations': stations}
    DESTINATION.write_text('window.atlasTransportNames = ' + json.dumps(result, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    print(f'Wrote {DESTINATION}: {len(result)} cities')


if __name__ == '__main__':
    main()
