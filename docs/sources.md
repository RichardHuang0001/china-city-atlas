# 数据说明

## 榜单与行政区划

- 第一财经 2025-05-28 [发布原文](https://www.yicai.com/news/102638963.html)与[完整分级图](https://imgcdn.yicai.com/uppics/images/2025/05/64daefdf154d5b39e23c5a345cadd7df.jpg)。以原图左到右、上到下转录并复核，同一线级保留原图序号。第一财经正文独立确认了最前两档的次序。其余线级只显示图序；不把该序号外推为分数或全榜总名次。
- [民政部国家地名信息库](https://dmfw.mca.gov.cn/XzqhVersionPublish.html)、[2024 年民政事业发展统计公报](https://www.mca.gov.cn/gdnps/n2445/n2451/n2458/n2681/c1662004999980006189/attr/400985.pdf)与[2024/2025 年区划代码 CC0 存档](https://github.com/yescallop/areacodes)。两个年份的地级行政区及直辖市代码、名称一致。完整收录 333 个地级行政区（293 座地级市 + 30 个自治州 + 7 个地区 + 3 个盟）及 4 座直辖市，与原榜 337 席一一匹配。
- 西藏 7 个地级行政区为拉萨、日喀则、昌都、林芝、山南、那曲和阿里。

| 范围 | 一线 | 新一线 | 二线 | 三线 | 四线 | 五线 | 合计 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 原榜 | 4 | 15 | 30 | 70 | 90 | 128 | 337 |
| 地级行政区 | 2 | 13 | 30 | 70 | 90 | 128 | 333 |
| 直辖市参考 | 2 | 2 | 0 | 0 | 0 | 0 | 4 |

## 地图与位置

- 矢量底图使用开源仓库 [chinese-global-compliant-geodata](https://github.com/JayMuShui/chinese-global-compliant-geodata/tree/3cf3485789876c37be6193bf2848cf9aaa40f758/src/geojson/countries/as/chn/global) 的 `chn-level-1.json` 和 `chn-level-2.json`。仓库注明源数据为 2024 年 5 月的[天地图行政区划数据](https://cloudcenter.tianditu.gov.cn/administrativeDivision/)，并按 MIT 发布其整理版。项目附该仓库的许可证，第三方源数据使用与公开展示仍应遵循原来源条件。
- 项目从文件声明的 CGCS2000（EPSG:4490）投影到 Albers 等面积坐标。城市点使用 WGS 84 近似经纬度，与 CGCS2000 的差异在本图比例尺下忽略。按源几何绘制 34 个省级要素，保留台湾、香港、澳门、所含离岸岛屿和南海断续线。省视图叠加源文件的地级图层，其区划快照与榜单年份有时间差。
- 屏幕上的中国地图是网页根据矢量数据绘制的专题图，未单独送审，也没有沿用原 JPG 底图的审图号。发布前参照[公开地图内容表示规范](https://www.fmprc.gov.cn/web/wjb_673085/zzjg_673183/bjhysws_674671/bhflfg/dtdmxgfl/202303/P020230313585504979937.pdf)及[天地图版权声明](https://www.tianditu.gov.cn/about/copyright)。
- [GaoHR 2020 年 WGS 84 驻地坐标](https://gaohr.win/site/blogs/2022/2022-03-29-location-of-gov.html)与[当时的民政部区划定位存档](https://github.com/sotex/XingZhengQuHuaShuJu)及 [DataV 城市定位数据](https://datav.aliyun.com/portal/school/atlas/area_selector)交叉比对。发现较大偏移时改用可追溯的城区参考点，共 35 座。城区点统一到 WGS 84 近似值。2020 年资料和城市参考点没有逐一核实到市政府现址。地图配准用于展示分布，用于计算或导航须另选数据源。
- 三沙标记按永兴岛附近的公开坐标落在南海诸岛附图中。附图使用独立的投影参数。选择三沙名录会自动切换到附图。

## 数据字段

一条城市记录依次保存简称、六位行政区划代码、省级代码、线级索引（从 0 开始）、原图线内序号（从 1 开始）、是否为直辖市、WGS 84 经度和纬度、图面坐标、是否为城区参考点。
