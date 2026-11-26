"""Build unified 337-city public transport dataset (2025-2026).

Covers the 4 major public transport modes across all 337 prefecture-level units:
1. Civil airports (CAAC 2025 full-year + 2026-11-26 openings/relocations + Wikipedia grades/IATA/ICAO)
2. High-speed & EMU rail (2026-11-24 China Railway GTFS 7-day average + lines.json corridors + Yicai 2025 baseline)
3. Metro / Light Rail (MOT 2025 full-year & 2026-10 snapshots + Wikipedia/2026-11 system split)
4. Urban / Suburban Rail (Non-metro urban rail: suburban rapid transit, monorail, maglev, tram, skybus/APM + CR S/C intercity rail)

Outputs written to research/transport-2025-2026/.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"

GTFS_ZIP = Path("/tmp/gtfs_20261124/output_gtfs.zip")
GTFS_LINES = Path("/tmp/gtfs_20261124/lines.json")

# Verified MOT 2025 full-year (54 cities) — exact sums verified:
# lines=343 (excl 6 cross-city), km=11710.2 (official 11710.3), stations=6680 (exact),
# pax=332.44亿 (official 332.4), entries=197.96亿 (official 198.0), pkm=2780.85亿 (official 2780.8).
# Format: (mot_city, lines_2025, km_2025, stations_2025, pax_2025_wan, entries_2025_wan, pkm_2025_wan)
MOT_2025_ANNUAL = [
    ("北京", 30, 909.0, 423, 357356.8, 196819.1, 3418305.8),
    ("上海", 22, 881.5, 461, 370021.8, 206238.3, 3388406.4),
    ("广州", 22, 772.6, 332, 332108.5, 178978.8, 2739137.8),
    ("成都", 17, 719.5, 387, 224448.2, 125796.8, 1946468.1),
    ("深圳", 18, 634.5, 364, 328508.6, 185434.9, 2555957.9),
    ("武汉", 15, 561.2, 332, 144383.6, 91561.5, 1183804.3),
    ("南京", 15, 524.4, 255, 112995.9, 66844.0, 1795787.6),
    ("杭州", 12, 516.0, 259, 150149.7, 90785.8, 1264396.5),
    ("重庆", 11, 501.5, 258, 149866.8, 88506.1, 1176127.0),
    ("西安", 12, 404.1, 239, 152411.6, 95277.8, 1144185.0),
    ("郑州", 12, 382.7, 209, 82332.8, 48533.2, 628988.5),
    ("青岛", 9, 360.9, 184, 53577.1, 36638.1, 538842.5),
    ("苏州", 11, 355.4, 239, 65995.3, 39173.0, 430106.1),
    ("天津", 10, 349.2, 225, 66857.8, 41108.7, 480041.4),
    ("沈阳", 12, 301.0, 201, 70010.6, 44963.2, 457469.0),
    ("宁波", 8, 261.4, 142, 40265.4, 22820.8, 243422.4),
    ("合肥", 7, 259.0, 183, 56931.8, 33900.9, 361748.5),
    ("大连", 6, 237.1, 100, 26125.7, 19262.7, 256979.9),
    ("长沙", 7, 219.0, 135, 101244.4, 55179.4, 605692.7),
    ("济南", 7, 217.9, 113, 13375.7, 9523.1, 141949.5),
    ("昆明", 6, 165.9, 103, 29857.3, 21489.7, 267577.3),
    ("南昌", 4, 160.2, 113, 43167.2, 25925.9, 258227.1),
    ("长春", 6, 151.4, 117, 28127.9, 19674.1, 185010.8),
    ("佛山", 6, 150.2, 93, 19105.6, 13853.0, 179954.6),
    ("贵阳", 4, 146.5, 93, 28665.6, 20017.6, 211321.6),
    ("福州", 5, 143.9, 93, 31496.3, 22854.0, 234886.8),
    ("南宁", 5, 132.5, 95, 37564.7, 23548.3, 211017.0),
    ("无锡", 4, 110.8, 80, 22804.8, 15122.1, 134767.9),
    ("厦门", 3, 98.4, 70, 27590.4, 21194.3, 208772.8),
    ("东莞", 2, 95.3, 39, 5528.8, 5416.6, 67587.9),
    ("徐州", 4, 95.1, 70, 11912.9, 8368.4, 73645.9),
    ("哈尔滨", 3, 91.6, 73, 41628.1, 26875.1, 245912.2),
    ("石家庄", 3, 74.3, 60, 18934.3, 13055.5, 109476.9),
    ("绍兴", 3, 64.5, 40, 4514.5, 2644.9, 44748.1),
    ("南通", 2, 58.8, 43, 4878.2, 4270.9, 33595.7),
    ("常州", 2, 54.0, 43, 7408.5, 6027.0, 51515.1),
    ("温州", 1, 52.5, 18, 2106.2, 1787.5, 38856.7),
    ("太原", 2, 51.7, 46, 10128.1, 8849.3, 68252.2),
    ("呼和浩特", 2, 49.0, 43, 8173.7, 6635.5, 46367.9),
    ("海宁", 1, 46.4, 12, 1407.6, 1086.5, 30057.4),
    ("芜湖", 2, 46.2, 35, 3746.1, 3152.2, 25753.7),
    ("洛阳", 2, 43.5, 33, 6744.8, 5090.2, 40844.9),
    ("昆山", 2, 43.0, 29, 5579.6, 4079.0, 48696.6),
    ("兰州", 2, 33.5, 27, 14368.9, 12339.1, 101637.8),
    ("天水", 1, 32.4, 29, 363.3, 363.3, 2870.2),
    ("乌鲁木齐", 1, 26.8, 21, 4440.6, 4440.6, 37606.2),
    ("黄石", 1, 26.8, 30, 455.8, 455.8, 6125.4),
    ("淮安", 1, 20.1, 23, 881.3, 881.3, 8813.1),
    ("句容", 1, 17.3, 5, 763.6, 439.2, 12973.6),
    ("嘉兴", 1, 13.8, 16, 300.2, 300.2, 2071.4),
    ("文山", 1, 13.4, 10, 46.6, 44.9, 448.4),
    ("红河", 1, 13.4, 15, 0.0, 0.0, 0.0),
    ("咸阳", 1, 10.7, 7, 2586.6, 1840.4, 60702.6),
    ("三亚", 1, 8.4, 15, 147.4, 147.4, 547.8),
]

# Verified MOT 2026-10 (54 cities) — exact sums verified:
# lines=350 (excl 6 cross-city), km=11992.4 (official 11992.5), pax=29.43亿 (official 29.4), entries=17.46亿 (official 17.5).
MOT_2026_10 = [
    ("北京", 30, 909.0, 28978.3, 16160.8, 1.03),
    ("上海", 22, 881.5, 30332.1, 17028.1, 1.11),
    ("广州", 22, 772.6, 29249.6, 15803.2, 1.22),
    ("成都", 17, 719.5, 19953.6, 10884.4, 0.89),
    ("深圳", 18, 653.7, 29383.8, 16730.1, 1.45),
    ("武汉", 16, 624.0, 12637.9, 8134.3, 0.68),
    ("南京", 16, 556.8, 11371.3, 6098.7, 0.66),
    ("杭州", 12, 516.0, 13052.6, 7920.3, 0.82),
    ("重庆", 11, 512.3, 12395.9, 7291.7, 0.78),
    ("西安", 12, 404.1, 12726.3, 7980.0, 1.02),
    ("郑州", 12, 382.7, 7114.8, 4153.9, 0.60),
    ("青岛", 9, 374.0, 4691.7, 3229.8, 0.40),
    ("天津", 11, 370.8, 5989.4, 3692.4, 0.52),
    ("苏州", 11, 355.4, 5659.7, 3253.7, 0.51),
    ("沈阳", 12, 314.2, 6424.9, 4034.3, 0.87),
    ("宁波", 9, 296.8, 3827.1, 2079.6, 0.42),
    ("合肥", 8, 275.5, 6456.9, 4022.4, 0.76),
    ("大连", 6, 237.1, 2219.8, 1649.9, 0.30),
    ("长沙", 7, 230.6, 8732.6, 4824.2, 1.22),
    ("济南", 7, 217.9, 3633.4, 2261.4, 0.54),
    ("长春", 8, 194.1, 3245.5, 2121.0, 0.54),
    ("昆明", 6, 165.9, 2332.9, 1689.0, 0.45),
    ("南昌", 4, 160.2, 3855.6, 2343.3, 0.78),
    ("佛山", 6, 153.1, 1878.0, 1323.2, 0.41),
    ("贵阳", 4, 146.5, 2325.9, 1604.2, 0.51),
    ("福州", 5, 143.9, 3410.5, 2169.9, 0.76),
    ("南宁", 5, 132.5, 3226.7, 1990.0, 0.79),
    ("无锡", 4, 110.8, 2280.6, 1524.3, 0.66),
    ("厦门", 3, 98.4, 2849.9, 1949.5, 0.93),
    ("东莞", 2, 95.3, 988.2, 849.0, 0.33),
    ("徐州", 4, 95.1, 1053.1, 735.9, 0.36),
    ("哈尔滨", 3, 91.6, 3492.1, 2282.2, 1.23),
    ("石家庄", 3, 74.3, 1421.5, 983.5, 0.62),
    ("绍兴", 3, 64.5, 437.4, 261.6, 0.22),
    ("南通", 2, 58.8, 401.3, 324.7, 0.22),
    ("常州", 2, 54.0, 714.9, 586.5, 0.43),
    ("温州", 1, 52.5, 198.9, 167.7, 0.12),
    ("太原", 2, 51.7, 950.4, 805.6, 0.59),
    ("呼和浩特", 2, 49.0, 718.4, 589.5, 0.47),
    ("海宁", 1, 46.4, 135.8, 105.7, 0.09),
    ("芜湖", 2, 46.2, 327.4, 277.1, 0.23),
    ("洛阳", 2, 43.5, 605.7, 458.7, 0.45),
    ("昆山", 2, 43.0, 513.9, 384.3, 0.39),
    ("兰州", 2, 33.5, 1171.7, 1010.4, 1.13),
    ("天水", 1, 32.4, 48.3, 48.3, 0.05),
    ("乌鲁木齐", 1, 26.8, 398.6, 398.6, 0.48),
    ("黄石", 1, 26.8, 34.5, 34.5, 0.04),
    ("淮安", 1, 20.1, 78.5, 78.5, 0.13),
    ("句容", 1, 17.3, 80.0, 56.4, 0.15),
    ("嘉兴", 1, 13.8, 31.0, 31.0, 0.07),
    ("文山", 1, 13.4, 3.2, 3.1, 0.01),
    ("红河", 1, 13.4, None, None, None),
    ("咸阳", 1, 10.7, 223.5, 157.7, 0.67),
    ("三亚", 1, 8.4, 9.1, 9.1, 0.04),
]

# MOT city name -> 337 city code
MOT_TO_CODE = {
    "海宁": "330400",  # 嘉兴 (杭海城际)
    "昆山": "320500",  # 苏州 (上海11号线昆山段+苏州11号线)
    "句容": "321100",  # 镇江 (南京S6宁句线句容段)
}

# Airport prefix -> 337 city code (or NON_337 for provincial county-level/XPCC units)
AIRPORT_PREFIX_TO_CODE = {
    "义乌": "330700",       # 金华
    "库尔勒": "652800",     # 巴音郭楞
    "库车": "652900",       # 阿克苏
    "兴义": "522300",       # 黔西南
    "延吉": "222400",       # 延边
    "敦煌": "620900",       # 酒泉
    "锡林浩特": "152500",   # 锡林郭勒
    "乌兰浩特": "152200",   # 兴安
    "西昌": "513400",       # 凉山
    "万州": "500000",       # 重庆
    "琼海": "NON_337",      # 海南省直辖县级市 (469002)
    "腾冲": "530500",       # 保山
    "石河子": "NON_337",    # 新疆兵团八师 (659001)
    "博乐": "652700",       # 博尔塔拉
    "莎车": "653100",       # 喀什
    "阿拉尔": "NON_337",    # 新疆兵团一师 (659002)
    "图木舒克": "NON_337",  # 新疆兵团三师 (659003)
    "格尔木": "632800",     # 海西
    "满洲里": "150700",     # 呼伦贝尔
    "二连浩特": "152500",   # 锡林郭勒
    "武夷山": "350700",     # 南平
    "奇台": "652300",       # 昌吉
    "漠河": "232700",       # 大兴安岭
    "阆中": "511300",       # 南充
    "于田": "653200",       # 和田
    "扎兰屯": "150700",     # 呼伦贝尔
    "霍林郭勒": "150500",   # 通辽
    "沧源": "530900",       # 临沧
    "昭苏": "654000",       # 伊犁
    "若羌": "652800",       # 巴音郭楞
    "澜沧": "530800",       # 普洱
    "阿拉善左旗": "152900", # 阿拉善
    "且末": "652800",       # 巴音郭楞
    "黔江": "500000",       # 重庆
    "富蕴": "654300",       # 阿勒泰
    "稻城": "513300",       # 甘孜
    "抚远": "230800",       # 佳木斯
    "建三江": "230800",     # 佳木斯
    "阿尔山": "152200",     # 兴安
    "巴里坤": "650500",     # 哈密
    "绥芬河": "231000",     # 牡丹江
    "新源": "654000",       # 伊犁
    "五大连池": "231100",   # 黑河
    "布尔津": "654300",     # 阿勒泰
    "九寨": "513200",       # 阿坝
    "塔什库尔干": "653100", # 喀什
    "凯里": "522600",       # 黔东南
    "宁蒗": "530700",       # 丽江
    "神农架": "NON_337",    # 湖北省直辖林区 (429021)
    "额济纳旗": "152900",   # 阿拉善
    "阿拉善右旗": "152900", # 阿拉善
    "长海": "210200",       # 大连
    "和静": "652800",       # 巴音郭楞
    "连城": "350800",       # 龙岩
}

# Verified GTFS fallback-coordinate station overrides (10 stations on 2026 new lines / enclaves)
GTFS_STATION_CITY_OVERRIDE = {
    "APY": "610900",  # 安康西 -> 安康市
    "NGY": "611000",  # 牛背梁 -> 商洛市
    "ZCY": "611000",  # 柞水西 -> 商洛市
    "ZTY": "611000",  # 镇安西 -> 商洛市
    "SGB": "231200",  # 绥化南 -> 绥化市
    "QHR": "130500",  # 清河西 -> 邢台市 (check exact code below)
    "SZD": "131100",  # 深州东 -> 衡水市
    "ZQI": "131100",  # 枣强南 -> 衡水市
    "TQD": "410900",  # 台前东 -> 濮阳市
    "JEJ": "620700",  # 山丹马场 -> 张掖市
}

# Non-metro urban rail & cross-city metro/suburban rail metadata (verified from MOT + Wikipedia + 2026 news)
# Maps city_code -> dict with metro/other_urban_rail distinctions
EXTRA_URBAN_RAIL_2026 = {
    # Pure non-metro in MOT 54
    "340200": {"modes": ["跨座式单轨"], "other_lines": 2, "other_km": 46.2, "metro_own": False, "note": "芜湖轨道交通1/2号线为跨座式单轨"},
    "330300": {"modes": ["市域快轨"], "other_lines": 1, "other_km": 52.5, "metro_own": False, "note": "温州轨道交通S1/S2线为市域铁路(注:Wiki计2条116.4km,MOT口径52.5km)"},
    "620500": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 32.4, "metro_own": False, "note": "天水有轨电车"},
    "420200": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 26.8, "metro_own": False, "note": "黄石有轨电车"},
    "320800": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 20.1, "metro_own": False, "note": "淮安有轨电车"},
    "532600": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 13.4, "metro_own": False, "note": "文山有轨电车"},
    "532500": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 13.4, "metro_own": False, "note": "红河有轨电车(2025-2026暂停运营)"},
    "460200": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 8.4, "metro_own": False, "note": "三亚有轨电车"},
    "330400": {"modes": ["市域快轨", "有轨电车"], "other_lines": 2, "other_km": 60.2, "metro_own": False, "note": "含海宁杭海城际(46.4km)+嘉兴有轨电车(13.8km)"},
    # Cross-city metro / suburban rail extensions (not standalone in MOT 54 except 咸阳/句容/佛山)
    "610400": {"modes": ["跨市地铁"], "other_lines": 0, "other_km": 0.0, "metro_own": False, "cross_metro_from": "西安", "note": "西安地铁1号线三期等延伸至咸阳"},
    "321100": {"modes": ["跨市市域快轨"], "other_lines": 1, "other_km": 17.3, "metro_own": False, "cross_metro_from": "南京", "note": "南京地铁S6宁句线句容段"},
    "420700": {"modes": ["跨市地铁"], "other_lines": 0, "other_km": 0.0, "metro_own": False, "cross_metro_from": "武汉", "note": "武汉地铁11号线葛店段延伸至鄂州"},
    "411000": {"modes": ["跨市市域快轨"], "other_lines": 1, "other_km": 0.0, "metro_own": False, "cross_metro_from": "郑州", "note": "郑州地铁郑许线(市域快轨)延伸至许昌"},
    "430300": {"modes": ["跨市地铁"], "other_lines": 0, "other_km": 0.0, "metro_own": False, "cross_metro_from": "长沙", "note": "长沙地铁3号线南延(长株潭西环线)延伸至湘潭"},
    "512000": {"modes": ["跨市市域快轨"], "other_lines": 1, "other_km": 38.7, "metro_own": False, "cross_metro_from": "成都", "note": "成都轨道交通S3资阳线(2024-09开通)"},
    "341100": {"modes": ["跨市市域快轨"], "other_lines": 1, "other_km": 0.0, "metro_own": False, "cross_metro_from": "南京", "note": "南京地铁S4宁滁城际滁州段(CAMET口径)"},
    "340500": {"modes": ["跨市市域快轨"], "other_lines": 1, "other_km": 27.0, "metro_own": False, "cross_metro_from": "南京", "note": "宁马城际/南京S2线2026-04-22开通(马鞍山段8站)"},
    # Standalone CAMET/Wiki systems outside MOT 54
    "330700": {"modes": ["市域快轨"], "other_lines": 2, "other_km": 107.2, "metro_own": False, "note": "金华轨道交通金义东线(CAMET口径,2025-04累计破1亿人次)"},
    "331000": {"modes": ["市域快轨"], "other_lines": 1, "other_km": 52.4, "metro_own": False, "note": "台州市域铁路S1线(CAMET口径,至2025-09累计3237万人次)"},
    "350700": {"modes": ["有轨电车"], "other_lines": 1, "other_km": 26.2, "metro_own": False, "note": "南平武夷有轨电车"},
    "530700": {"modes": ["有轨电车/旅游轨道"], "other_lines": 1, "other_km": 20.7, "metro_own": False, "note": "丽江雪山观光火车(2025-02开通,2026初曾阶段性停运)"},
    "433100": {"modes": ["磁浮"], "other_lines": 1, "other_km": 9.1, "metro_own": False, "note": "湘西凤凰磁浮观光快线"},
    "441800": {"modes": ["磁浮"], "other_lines": 1, "other_km": 8.0, "metro_own": False, "note": "清远磁浮旅游专线(2024开通)"},
    "520200": {"modes": ["旅游单轨"], "other_lines": 1, "other_km": 11.0, "metro_own": False, "note": "六盘水野玉海旅游单轨"},
    "640100": {"modes": ["旅游单轨(云轨)"], "other_lines": 1, "other_km": 5.7, "metro_own": False, "note": "银川花博园云轨"},
}

# Cities with BOTH metro and non-metro urban rail modes (from Wiki/MOT footnote 2)
MIXED_UR_MODES = {
    "110000": ["地铁", "磁浮", "有轨电车", "市郊线"],
    "310000": ["地铁", "磁浮", "市域线", "胶轮APM", "有轨电车"],
    "440100": ["地铁", "APM", "有轨电车"],
    "510100": ["地铁", "市域快轨", "有轨电车"],
    "440300": ["地铁", "云巴", "有轨电车"],
    "420100": ["地铁", "有轨电车", "光谷空轨(旅游)"],
    "320100": ["地铁", "市域快轨(S线)", "有轨电车"],
    "500000": ["地铁", "跨座式单轨", "胶轮云巴"],
    "320500": ["地铁", "有轨电车"],
    "370200": ["地铁", "有轨电车"],
    "210100": ["地铁", "有轨电车"],
    "440600": ["地铁", "有轨电车"],
    "430100": ["地铁", "磁浮", "云巴"],
    "370100": ["地铁", "有轨电车", "云巴"],
    "610100": ["地铁", "云巴"],
    "220100": ["地铁", "轻轨", "有轨电车"],
    "210200": ["地铁", "快轨", "有轨电车"],
    "120000": ["地铁", "轻轨"],
    "330200": ["地铁", "市域线"],
    "340100": ["地铁", "市域快轨(S1)"],
}


def load_cities():
    txt = (ROOT / "site" / "assets" / "data.js").read_text()
    atlas = json.loads(txt.strip().removeprefix("window.atlasData = ").removesuffix(";"))
    tiers = [t["name"] for t in atlas["meta"]["tiers"]]
    cities = {}
    for row in atlas["cities"]:
        short, code, prov, tidx, trank, is_muni, lonlat, xy, _ = row
        cities[code] = {
            "place_id": code,
            "short_name": short,
            "province_code": prov,
            "tier_2026_idx": tidx,
            "tier_2026": tiers[tidx],
            "tier_rank_2026": trank,
            "is_municipality": bool(is_muni),
        }
    # Enrich canonical_name, province, rank_2026 from charm_2026_scores_wide.csv
    with open(ROOT / "research/datayicai-mcp/charm-2026/city_charm_2026_scores_wide.csv") as f:
        for r in csv.DictReader(f):
            pid = r["\ufeffplace_id"]
            if pid in cities:
                cities[pid]["canonical_name"] = r["canonical_name"]
                cities[pid]["province"] = r["province"]
                cities[pid]["rank_2026"] = int(r["rank_2026"])
    # Enrich Yicai 2025 baseline stats
    with open(ROOT / "research/datayicai-mcp/city-stats/statistics_latest_337_wide.csv") as f:
        rdr = csv.DictReader(f)
        hsr_col = [c for c in rdr.fieldnames if "高铁站数量" in c][0]
        air_col = [c for c in rdr.fieldnames if "机场数量" in c][0]
        for r in rdr:
            pid = r["\ufeffplace_id"]
            if pid in cities:
                cities[pid]["yicai_hsr_stations_2025"] = int(float(r[hsr_col] or 0))
                cities[pid]["yicai_airports_2024"] = int(float(r[air_col])) if r[air_col] else 0
    return cities


def parse_wiki_airports():
    rows = json.loads((RAW / "wiki_airports_extracted.json").read_text())
    info = {}
    for cols in rows:
        name_raw, icao, iata, open_date, grade, nature = cols[:6]
        info[iata] = {
            "wiki_name": name_raw,
            "icao": icao,
            "iata": iata,
            "open_date": open_date,
            "grade": grade,
            "nature": nature,
        }
    return info


def build_airports(cities):
    short_to_code = {v["short_name"]: k for k, v in cities.items()}
    wiki_by_iata = parse_wiki_airports()
    # Also build wiki lookup by airport Chinese short token
    wiki_by_name = []
    for iata, w in wiki_by_iata.items():
        cn_part = w["wiki_name"].split()[0]
        wiki_by_name.append((cn_part, w))

    caac_data = json.loads((RAW / "caac_2025_extracted.json").read_text())
    hub_intl = {}
    for r in caac_data["file2"]:
        if r[0] and r[0] != "枢纽机场合计":
            nm = str(r[0]).strip()
            hkmotw = r[3] or 0
            intl = r[4] or 0
            hub_intl[nm] = (int(hkmotw + intl), int(intl))

    airports = []
    for r in caac_data["file1"]:
        if not r[0] or str(r[0]).startswith("注："):
            continue
        raw_name = str(r[0]).strip()
        prefix = raw_name.split("/")[0]
        suffix = raw_name.split("/")[1] if "/" in raw_name else ""
        city_code = short_to_code.get(prefix) or AIRPORT_PREFIX_TO_CODE[prefix]
        pax = int(r[2]) if r[2] is not None else 0
        cargo = float(r[6]) if r[6] is not None else 0.0
        mv = int(r[10]) if r[10] is not None else 0
        ext_pax, intl_pax = hub_intl.get(raw_name, (0, 0))

        # Match wiki grade & IATA
        matched_w = None
        for cn, w in wiki_by_name:
            if (prefix in cn and (not suffix or suffix in cn)) or (suffix and suffix in cn and len(suffix) >= 2):
                matched_w = w
                break
        if raw_name == "呼和浩特/白塔":
            matched_w = {"icao": "ZBHH", "iata": "HET", "grade": "4F(2026-11-26迁建盛乐)", "open_date": "1958->2026-11-26迁建盛乐"}

        status = "2025在营"
        if raw_name == "连城/冠豸山":
            status = "2024-08停航改造，2026-03-29复航"
        elif raw_name == "黔东南/黎平":
            status = "2025无定期客运吞吐(仅有通航/训练起降)"
        elif raw_name == "呼和浩特/白塔":
            status = "2026-11-26已由呼和浩特盛乐国际机场(4F)整体转场替代"

        airports.append({
            "airport_caac_name": raw_name,
            "city_code": city_code,
            "city_name": cities[city_code]["short_name"] if city_code in cities else prefix,
            "iata": matched_w["iata"] if matched_w else "",
            "icao": matched_w["icao"] if matched_w else "",
            "flight_grade": matched_w["grade"] if matched_w else "",
            "pax_2025": pax,
            "intl_hkmotw_pax_2025": ext_pax,
            "intl_pax_2025": intl_pax,
            "cargo_tons_2025": round(cargo, 3),
            "movements_2025": mv,
            "status_2026_11": status,
        })

    # Add 2026-01..2026-11-26 newly opened civil transport airports
    new_2026 = [
        ("蚌埠/滕湖", "340300", "蚌埠", "BFY", "ZSBA", "4C", "2026-04-29首航通航"),
        ("铜仁/德江", "520600", "铜仁", "DEJ", "ZUDJ", "4C", "2026-05-18首航通航"),
        ("巴音郭楞/轮台", "652800", "巴音郭楞", "LTJ", "ZWLT", "4C", "2026-06-18试运行通航"),
    ]
    for nm, cc, cname, iata, icao, grade, st in new_2026:
        airports.append({
            "airport_caac_name": nm,
            "city_code": cc,
            "city_name": cname,
            "iata": iata,
            "icao": icao,
            "flight_grade": grade,
            "pax_2025": 0,
            "intl_hkmotw_pax_2025": 0,
            "intl_pax_2025": 0,
            "cargo_tons_2025": 0.0,
            "movements_2025": 0,
            "status_2026_11": st,
        })

    # Write airports CSV
    ap_csv = OUT / "airports_2025_2026_by_airport.csv"
    with open(ap_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(airports[0].keys()))
        w.writeheader()
        w.writerows(airports)

    # Roll up per 337 city
    grade_rank = {"4F": 4, "4E": 3, "4D": 2, "4C": 1}
    city_ap = defaultdict(lambda: {
        "airport_count_2026": 0,
        "airport_pax_2025": 0,
        "airport_intl_hkmotw_pax_2025": 0,
        "airport_cargo_tons_2025": 0.0,
        "airport_movements_2025": 0,
        "airport_names": [],
        "airport_max_grade": "",
        "_gmax": 0,
    })
    for a in airports:
        cc = a["city_code"]
        if cc not in cities:
            continue
        # Note 黔东南/黎平 had 0 passenger flights in 2025; still listed in CAAC 2025 certificate table
        d = city_ap[cc]
        d["airport_count_2026"] += 1
        d["airport_pax_2025"] += a["pax_2025"]
        d["airport_intl_hkmotw_pax_2025"] += a["intl_hkmotw_pax_2025"]
        d["airport_cargo_tons_2025"] = round(d["airport_cargo_tons_2025"] + a["cargo_tons_2025"], 3)
        d["airport_movements_2025"] += a["movements_2025"]
        g_clean = a["flight_grade"][:2] if a["flight_grade"][:2] in grade_rank else ""
        disp = a["airport_caac_name"] + (f"({g_clean})" if g_clean else "")
        d["airport_names"].append(disp)
        if g_clean and grade_rank[g_clean] > d["_gmax"]:
            d["_gmax"] = grade_rank[g_clean]
            d["airport_max_grade"] = g_clean
    return city_ap, len(airports)


def build_hsr(cities):
    # Load map polygons
    map_data = json.loads((ROOT / "site/assets/map-data.js").read_text().strip().removeprefix("window.atlasMap = ").removesuffix(";"))

    def svg_to_polys(path_str):
        polys = []
        for sub in path_str.split("Z"):
            sub = sub.strip()
            if not sub:
                continue
            if sub.startswith("M"):
                sub = sub[1:]
            pts = [tuple(map(float, tok.split(","))) for tok in sub.split() if "," in tok]
            if len(pts) >= 3:
                polys.append(Polygon(pts))
        return polys

    geoms, geom_codes, code_area = [], [], defaultdict(float)
    for mcode in ["110000", "120000", "310000", "500000"]:
        for poly in svg_to_polys(map_data["provinces"][mcode[:2]][0]):
            geoms.append(poly)
            geom_codes.append(mcode)
            code_area[mcode] += poly.area
    for prov, dmap in map_data["districts"].items():
        for code, pstr in dmap.items():
            for poly in svg_to_polys(pstr):
                geoms.append(poly)
                geom_codes.append(code)
                code_area[code] += poly.area

    tree = STRtree(geoms)
    proj = Transformer.from_crs(4490, "+proj=aea +lon_0=105 +lat_0=36 +lat_1=25 +lat_2=47 +ellps=GRS80 +units=m", always_xy=True)

    with zipfile.ZipFile(GTFS_ZIP) as z:
        stops = list(csv.DictReader(io.TextIOWrapper(z.open("stops.txt"), "utf-8")))
        trips = list(csv.DictReader(io.TextIOWrapper(z.open("trips.txt"), "utf-8")))
        cals = list(csv.DictReader(io.TextIOWrapper(z.open("calendar_dates.txt"), "utf-8")))
        stop_times = list(csv.DictReader(io.TextIOWrapper(z.open("stop_times.txt"), "utf-8")))

    # Verify stop_id for 清河西
    qhx = [s["stop_id"] for s in stops if s["stop_name"] == "清河西"]
    for sid in qhx:
        GTFS_STATION_CITY_OVERRIDE[sid] = "130500"

    stop_city = {}
    for st in stops:
        sid = st["stop_id"]
        if sid in GTFS_STATION_CITY_OVERRIDE:
            stop_city[sid] = (GTFS_STATION_CITY_OVERRIDE[sid], st["stop_name"])
            continue
        e, n = proj.transform(float(st["stop_lon"]), float(st["stop_lat"]))
        pt = Point(e / 4000, -n / 4000)
        hits = [geom_codes[idx] for idx in tree.query(pt) if geoms[idx].contains(pt)]
        if hits:
            found = min(hits, key=lambda c: code_area[c])
        else:
            best_d, found = min((geoms[i].distance(pt), geom_codes[i]) for i in range(len(geoms)))
            if best_d >= 5.0:
                continue
        if found in cities:
            stop_city[sid] = (found, st["stop_name"])

    # 7-day average: 2026-11-27 .. 2026-12-03
    week_dates = {"20261127", "20261128", "20261129", "20261130", "20261201", "20261202", "20261203"}
    svc_days = defaultdict(int)
    for c in cals:
        if c["date"] in week_dates:
            svc_days[c["service_id"]] += 1

    trip_weight = {t["trip_id"]: svc_days.get(t["service_id"], 0) / 7.0 for t in trips}
    tmap = {t["trip_id"]: t for t in trips}

    trip_stops = defaultdict(list)
    for st in stop_times:
        tid = st["trip_id"]
        if trip_weight.get(tid, 0) > 0:
            trip_stops[tid].append((int(st["stop_sequence"]), st["stop_id"]))

    city_gdc_w = defaultdict(float)
    city_gd_w = defaultdict(float)
    city_gdc_ot_w = defaultdict(float)
    city_cs_w = defaultdict(float)
    city_gdc_stns = defaultdict(set)
    city_gd_stns = defaultdict(set)
    city_cs_stns = defaultdict(set)
    city_reach = defaultdict(set)

    for tid, seq_stops in trip_stops.items():
        seq_stops.sort()
        w = trip_weight[tid]
        code = tmap[tid]["trip_short_name"]
        pfx = code[:1]
        if pfx not in ("G", "D", "C", "S"):
            continue
        touched_gdc, touched_gd, touched_cs, ot_gdc = set(), set(), set(), set()
        for idx, (_, sid) in enumerate(seq_stops):
            if sid not in stop_city:
                continue
            cc, sname = stop_city[sid]
            if pfx in ("G", "D", "C"):
                city_gdc_stns[cc].add(sname)
                touched_gdc.add(cc)
                if idx == 0 or idx == len(seq_stops) - 1:
                    ot_gdc.add(cc)
            if pfx in ("G", "D"):
                city_gd_stns[cc].add(sname)
                touched_gd.add(cc)
            if pfx in ("C", "S"):
                city_cs_stns[cc].add(sname)
                touched_cs.add(cc)
        for cc in touched_gdc:
            city_gdc_w[cc] += w
            city_reach[cc].update(touched_gdc)
        for cc in touched_gd:
            city_gd_w[cc] += w
        for cc in ot_gdc:
            city_gdc_ot_w[cc] += w
        for cc in touched_cs:
            city_cs_w[cc] += w

    for cc in city_reach:
        city_reach[cc].discard(cc)

    # Extract HSR/intercity corridor lines per city from lines.json
    lines_json = json.loads(GTFS_LINES.read_text())
    # Map station_name (or telecode) -> city_code using stops.txt
    sname_to_city = {}
    tele_to_city = {}
    for st in stops:
        if st["stop_id"] in stop_city:
            cc = stop_city[st["stop_id"]][0]
            tele_to_city[st["stop_id"]] = cc
            sname_to_city[st["stop_name"]] = cc

    city_corridors = defaultdict(set)
    for lname, st_list in lines_json.items():
        if not any(k in lname for k in ("高速", "客专", "城际", "高铁")):
            continue
        for item in st_list:
            if len(item) < 4:
                continue
            st_nm = item[1]
            tele = item[3].lstrip("-")
            cc = tele_to_city.get(tele) or sname_to_city.get(st_nm)
            if cc:
                city_corridors[cc].add(lname)

    hsr_rows = []
    hsr_by_city = {}
    for cc, info in sorted(cities.items(), key=lambda x: x[1]["rank_2026"]):
        gdc_stns = sorted(city_gdc_stns[cc])
        gd_stns = sorted(city_gd_stns[cc])
        cs_stns = sorted(city_cs_stns[cc])
        corr = sorted(city_corridors[cc])
        rec = {
            "place_id": cc,
            "short_name": info["short_name"],
            "tier_2026": info["tier_2026"],
            "rank_2026": info["rank_2026"],
            "has_hsr_gdc": 1 if gdc_stns else 0,
            "has_hsr_gd": 1 if gd_stns else 0,
            "hsr_stations_gdc_2026": len(gdc_stns),
            "hsr_stations_gd_2026": len(gd_stns),
            "yicai_hsr_stations_2025": info["yicai_hsr_stations_2025"],
            "hsr_daily_trains_gdc": round(city_gdc_w[cc], 1),
            "hsr_daily_trains_gd": round(city_gd_w[cc], 1),
            "hsr_daily_origin_term_gdc": round(city_gdc_ot_w[cc], 1),
            "hsr_direct_cities_gdc": len(city_reach[cc]),
            "hsr_corridor_count": len(corr),
            "hsr_corridor_names": ";".join(corr),
            "hsr_station_names_gdc": ";".join(gdc_stns),
            "cr_cs_stations": len(cs_stns),
            "cr_cs_daily_trains": round(city_cs_w[cc], 1),
        }
        hsr_rows.append(rec)
        hsr_by_city[cc] = rec

    with open(OUT / "hsr_2026_11_by_city.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hsr_rows[0].keys()))
        w.writeheader()
        w.writerows(hsr_rows)

    return hsr_by_city


def build_urban_rail(cities):
    short_to_code = {v["short_name"]: k for k, v in cities.items()}
    m25_map = {r[0]: r for r in MOT_2025_ANNUAL}
    m26_map = {r[0]: r for r in MOT_2026_10}

    # Roll up MOT 54 rows into 337 cities (combining 海宁->嘉兴, 昆山->苏州, 句容->镇江)
    ur_city = defaultdict(lambda: {
        "in_mot_54": 0,
        "ur_lines_2025": 0,
        "ur_km_2025": 0.0,
        "ur_stations_2025": 0,
        "ur_pax_2025_wan": 0.0,
        "ur_entries_2025_wan": 0.0,
        "ur_pkm_2025_wan": 0.0,
        "ur_lines_2026_10": 0,
        "ur_km_2026_10": 0.0,
        "ur_pax_2026_10_wan": 0.0,
        "ur_entries_2026_10_wan": 0.0,
        "ur_intensity_2026_10": None,
        "mot_sub_entries": [],
    })

    for mot_nm, l25, km25, st25, pax25, ent25, pkm25 in MOT_2025_ANNUAL:
        cc = MOT_TO_CODE.get(mot_nm) or short_to_code[mot_nm]
        _, l26, km26, pax26, ent26, int26 = m26_map[mot_nm]
        d = ur_city[cc]
        d["in_mot_54"] = 1
        d["ur_lines_2025"] += l25
        d["ur_km_2025"] = round(d["ur_km_2025"] + km25, 1)
        d["ur_stations_2025"] += st25
        d["ur_pax_2025_wan"] = round(d["ur_pax_2025_wan"] + pax25, 1)
        d["ur_entries_2025_wan"] = round(d["ur_entries_2025_wan"] + ent25, 1)
        d["ur_pkm_2025_wan"] = round(d["ur_pkm_2025_wan"] + pkm25, 1)
        d["ur_lines_2026_10"] += l26
        d["ur_km_2026_10"] = round(d["ur_km_2026_10"] + km26, 1)
        if pax26 is not None:
            d["ur_pax_2026_10_wan"] = round(d["ur_pax_2026_10_wan"] + pax26, 1)
        if ent26 is not None:
            d["ur_entries_2026_10_wan"] = round(d["ur_entries_2026_10_wan"] + ent26, 1)
        if mot_nm not in MOT_TO_CODE and int26 is not None:
            d["ur_intensity_2026_10"] = int26
        d["mot_sub_entries"].append(mot_nm)

    # Adjust 2026-11 Hefei S1 opening (opened 2026-11-19, +1 line, ~18.7 km initial section)
    ur_city["340100"]["ur_lines_2026_10"] = 9  # 8 as of Oct + S1 in Nov

    ur_rows = []
    ur_by_city = {}
    all_ur_codes = sorted(set(ur_city.keys()) | set(EXTRA_URBAN_RAIL_2026.keys()), key=lambda c: cities[c]["rank_2026"])
    for cc in all_ur_codes:
        info = cities[cc]
        d = ur_city[cc]
        extra = EXTRA_URBAN_RAIL_2026.get(cc)
        if extra:
            has_metro = 0
            has_cross_metro = 1 if "cross_metro_from" in extra else 0
            has_other_ur = 1 if extra["other_lines"] > 0 or not has_cross_metro else 0
            modes = extra["modes"]
            note = extra["note"]
            ur_km_latest = d["ur_km_2026_10"] if d["in_mot_54"] else extra["other_km"]
            ur_lines_latest = d["ur_lines_2026_10"] if d["in_mot_54"] else extra["other_lines"]
        else:
            has_metro = 1
            has_cross_metro = 0
            modes = MIXED_UR_MODES.get(cc, ["地铁"])
            has_other_ur = 1 if any(m != "地铁" for m in modes) else 0
            note = "MOT 54城主城区独立轨道交通网" + ("(含苏州/昆山合并)" if cc == "320500" else "")
            if cc == "340100":
                note += "；2026-11-19新开新桥机场S1线"
            ur_km_latest = d["ur_km_2026_10"]
            ur_lines_latest = d["ur_lines_2026_10"]

        rec = {
            "place_id": cc,
            "short_name": info["short_name"],
            "tier_2026": info["tier_2026"],
            "rank_2026": info["rank_2026"],
            "in_mot_54": d["in_mot_54"],
            "has_metro": has_metro,
            "has_cross_city_metro_ext": has_cross_metro,
            "has_other_urban_rail": has_other_ur,
            "urban_rail_modes": ";".join(modes),
            "ur_lines_latest": ur_lines_latest,
            "ur_km_latest": ur_km_latest,
            "ur_stations_2025": d["ur_stations_2025"] if d["in_mot_54"] else None,
            "ur_pax_2025_wan": d["ur_pax_2025_wan"] if d["in_mot_54"] else None,
            "ur_entries_2025_wan": d["ur_entries_2025_wan"] if d["in_mot_54"] else None,
            "ur_pax_2026_10_wan": d["ur_pax_2026_10_wan"] if (d["in_mot_54"] and d["ur_pax_2026_10_wan"] > 0) else None,
            "ur_intensity_2026_10": d["ur_intensity_2026_10"],
            "note": note,
        }
        ur_rows.append(rec)
        ur_by_city[cc] = rec

    with open(OUT / "urban_rail_2025_2026_by_city.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ur_rows[0].keys()))
        w.writeheader()
        w.writerows(ur_rows)

    return ur_by_city


def main():
    cities = load_cities()
    city_ap, ap_total = build_airports(cities)
    hsr_by_city = build_hsr(cities)
    ur_by_city = build_urban_rail(cities)

    master_rows = []
    for cc, info in sorted(cities.items(), key=lambda x: x[1]["rank_2026"]):
        ap = city_ap[cc]
        hsr = hsr_by_city[cc]
        ur = ur_by_city.get(cc)

        has_metro = ur["has_metro"] if ur else 0
        has_cross_metro = ur["has_cross_city_metro_ext"] if ur else 0
        has_other_ur = ur["has_other_urban_rail"] if ur else 0
        has_cr_intercity = 1 if hsr["cr_cs_stations"] > 0 else 0

        row = {
            "place_id": cc,
            "short_name": info["short_name"],
            "canonical_name": info["canonical_name"],
            "province": info["province"],
            "tier_2026": info["tier_2026"],
            "rank_2026": info["rank_2026"],
            # 1. Airport
            "has_airport": 1 if ap["airport_count_2026"] > 0 else 0,
            "airport_count_2026": ap["airport_count_2026"],
            "airport_max_grade": ap["airport_max_grade"],
            "airport_pax_2025": ap["airport_pax_2025"],
            "airport_intl_hkmotw_pax_2025": ap["airport_intl_hkmotw_pax_2025"],
            "airport_cargo_tons_2025": ap["airport_cargo_tons_2025"],
            "airport_movements_2025": ap["airport_movements_2025"],
            "airport_names": ";".join(ap["airport_names"]),
            # 2. High-speed Rail
            "has_hsr_gdc": hsr["has_hsr_gdc"],
            "has_hsr_gd": hsr["has_hsr_gd"],
            "hsr_stations_gdc_2026": hsr["hsr_stations_gdc_2026"],
            "hsr_stations_gd_2026": hsr["hsr_stations_gd_2026"],
            "hsr_daily_trains_gdc": hsr["hsr_daily_trains_gdc"],
            "hsr_daily_trains_gd": hsr["hsr_daily_trains_gd"],
            "hsr_daily_origin_term_gdc": hsr["hsr_daily_origin_term_gdc"],
            "hsr_direct_cities_gdc": hsr["hsr_direct_cities_gdc"],
            "hsr_corridor_count": hsr["hsr_corridor_count"],
            # 3. Metro
            "has_metro": has_metro,
            "has_cross_city_metro_ext": has_cross_metro,
            # 4. Urban / Suburban Rail (MOT/CAMET + CR S/C)
            "has_other_urban_rail": has_other_ur,
            "has_cr_intercity_sc": has_cr_intercity,
            "urban_rail_modes": ur["urban_rail_modes"] if ur else "",
            "ur_lines_latest": ur["ur_lines_latest"] if ur else 0,
            "ur_km_latest": ur["ur_km_latest"] if ur else 0.0,
            "ur_stations_2025": ur["ur_stations_2025"] if ur else None,
            "ur_pax_2025_wan": ur["ur_pax_2025_wan"] if ur else None,
            "ur_entries_2025_wan": ur["ur_entries_2025_wan"] if ur else None,
            "ur_pax_2026_10_wan": ur["ur_pax_2026_10_wan"] if ur else None,
            "ur_intensity_2026_10": ur["ur_intensity_2026_10"] if ur else None,
            "cr_cs_stations": hsr["cr_cs_stations"],
            "cr_cs_daily_trains": hsr["cr_cs_daily_trains"],
            "urban_rail_note": ur["note"] if ur else "",
        }
        master_rows.append(row)

    with open(OUT / "city_transport_337_2025_2026.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(master_rows[0].keys()))
        w.writeheader()
        w.writerows(master_rows)

    with open(OUT / "city_transport_337_2025_2026.json", "w", encoding="utf-8") as f:
        json.dump(master_rows, f, ensure_ascii=False, indent=2)

    # Print summary statistics by tier
    print(f"Built master dataset: {len(master_rows)} cities, {ap_total} airports total")
    for tier in ["一线", "新一线", "二线", "三线", "四线", "五线"]:
        sub = [r for r in master_rows if r["tier_2026"] == tier]
        n = len(sub)
        ap_n = sum(r["has_airport"] for r in sub)
        hsr_n = sum(r["has_hsr_gdc"] for r in sub)
        gd_n = sum(r["has_hsr_gd"] for r in sub)
        met_n = sum(r["has_metro"] for r in sub)
        xmet_n = sum(r["has_cross_city_metro_ext"] for r in sub)
        our_n = sum(r["has_other_urban_rail"] for r in sub)
        sc_n = sum(r["has_cr_intercity_sc"] for r in sub)
        print(f"  {tier:4s} (n={n:3d}): airport={ap_n:3d}, hsr_gdc={hsr_n:3d} (gd={gd_n:3d}), metro={met_n:2d} (+{xmet_n} ext), other_ur={our_n:2d}, cr_sc={sc_n:3d}")


if __name__ == "__main__":
    main()
