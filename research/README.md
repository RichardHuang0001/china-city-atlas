# 项目研究资料与数据源归档（Research & Sources Archive）

本目录用于集中存档支撑「中国城市分级地图 · 2025」项目的原始权威数据源、官方统计公报、行业报告图表及地图合规规范，不参与前端站点构建与部署。

## 目录结构

### 1. `yicai-2025/` — 第一财经·新一线城市研究所《2025新一线城市魅力排行榜》
- [yicai-2025-news-102638963.html](yicai-2025/yicai-2025-news-102638963.html)：2025-05-28 官方发布正文（含指标体系解读与 19 座一线/新一线榜单）。
- [2025-city-tiers-full-337.jpg](yicai-2025/2025-city-tiers-full-337.jpg)：2025 年城市分级完整名单原图（包含中国内地全部 **337 个**地级及以上行政区：一线 4、新一线 15、二线 30、三线 70、四线 90、五线 128）。
- [2025-new-tier1-ranking.jpg](yicai-2025/2025-new-tier1-ranking.jpg)：一线及新一线 19 城「城市魅力指数」综合得分与一级维度权重图。
- [2025-methodology-indicators.jpg](yicai-2025/2025-methodology-indicators.jpg)：五大一级维度（商业资源集聚度 0.23、城市枢纽性 0.17、城市人活跃度 0.22、新经济竞争力 0.22、未来可塑性 0.16）及二级子维度权重、19 城分维度得分。
- [2016-2025-rank-trend.gif](yicai-2025/2016-2025-rank-trend.gif)：2016–2025 年十年城市分级变迁趋势图。

### 2. `yicai-2026/` — 第一财经城市研究所《2026新一线城市魅力指数报告》（2026-05-28）
- [yicai-2026-news-103204902.html](yicai-2026/yicai-2026-news-103204902.html) & [yicai-2026-topic-103198991.html](yicai-2026/yicai-2026-topic-103198991.html)：2026-05-28 官方发布正文与专题页。
- **重要口径变化**：2026 年报告明确宣布「**不再发布 337 座地级及以上城市的新一线城市魅力指数总分、排名和分级结果**」，改为通过五大维度洞察（五大趋势配图 `2026-trend-1~5.jpg`、`2026-methodology-revision.jpg`）与知城小程序单城三级维度数据开放（`2026-zhicheng-miniapp.jpg`）。因此 **2025 年版是最近一期完整官方城市分级名单**。

### 3. `mca-areacodes/` — 民政部官方统计口径与区划代码
- [mca-2024-statistical-bulletin.pdf](mca-areacodes/mca-2024-statistical-bulletin.pdf)：民政部《2024年民政事业发展统计公报》（第 3 页表 1 明确截至 2024 年底全国共有省级 34 个、地级行政区 333 个，其中地级市 293 个、自治州 30 个、地区 7 个、盟 3 个）。
- [areacodes-README.md](mca-areacodes/areacodes-README.md) & [areacodes-result.csv](mca-areacodes/areacodes-result.csv)：`yescallop/areacodes`（CC0）行政区划代码存档，实测当前在用「地级」单位共 **333 个**，与第一财经 337 城减去 4 直辖市完全一致。

### 4. `geodata-specs/` — 地图数据与制图规范参考
- [public-map-content-spec-2023.pdf](geodata-specs/public-map-content-spec-2023.pdf)：自然资源部《公开地图内容表示规范》（2023 年公布）。
- [geodata-README.md](geodata-specs/geodata-README.md)、[geodata-chn-global-README.md](geodata-specs/geodata-chn-global-README.md) & [geodata-LICENSE](geodata-specs/geodata-LICENSE)：底图上游仓库 `chinese-global-compliant-geodata`（固定 commit `3cf3485789876c37be6193bf2848cf9aaa40f758`）的来源与 MIT 许可说明。
