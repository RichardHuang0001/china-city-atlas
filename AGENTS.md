# AGENTS.md

## 先了解项目

这是 **中国城市分级地图 · 2026**。源码在本目录，公开仓库为 `RichardHuang0001/china-city-atlas`，线上站点为 `https://citiescn.hiww.top/`。开发入口是 `site/index.html`。浏览器直接加载同目录资源，使用原生 HTML、CSS、JavaScript 和 SVG。不要引入框架、后端、CDN、在线瓦片、字体下载或 API Key 来实现常规功能。

- `site/index.html` 定义地图、筛选、城市名录和来源说明。`<head>` 仅通过 `<link rel="preload">` + `defer` 加载首屏关键脚本：`data.js → map-base.js → map-labels.js → app.js`；其余体量较大的详情数据（`city-profiles.js`）、按省分片的地市边界（`districts/<prov>.js`）以及 4 座直辖市与深圳的区级边界/区名分片（`subdistricts/<city>.js`）由 `app.js` 在首帧绘制后通过动态 `<script>` 按需/空闲懒加载（不用 `fetch()`，保持本地 `file://` 与静态托管子路径均可用）。
- `site/assets/app.js` 是交互入口。筛选状态和相机状态分开维护。完整 `render()` 同步地图和表格，`paintCamera()` 更新 SVG 的 `viewBox` 并按当前可视区域与缩放状态按需加载并更新地市界线。拖动期间沿用现有标签且不发起分片请求，松手后重新避让与补全边界。
- **性能与渐进加载规范（长期准则）**：详见 [docs/performance-architecture.md](docs/performance-architecture.md)。后续扩展功能时，首屏关键 JS/CSS 总传输预算控制在 **≤ 350 KB gzip**；新增大型数据或专题图层须拆为懒加载脚本，由 `loadScriptOnce` 挂载全局变量并在 UI 层支持骨架占位与就绪后原地刷新。
- `site/assets/map-labels.js` 根据当前画布像素、视野、缩放步进和城市线级决定名称与微调避让。标签和标记用同一个六位行政区划代码关联，通过 `data-city` 与 `data-leader-for` 联动悬停高亮。
- `tools/mobile-preview.html` 是开发者入口。通过嵌入正式页面验证 360／390／430 px。禁止在正式页面加入预览按钮或把 `tools/` 放进部署包。
- `research/` 存放支撑项目的原始报告、官方统计公报、区划代码与地图规范，仅用于溯源与研究，不参与构建和部署。

## 产品设计与交互偏好（维护必读）

多轮迭代沉淀下来的核心设计理念如下，后续改动需保持一致：

1. **视觉克制与信息主次**：坚持低饱和暖纸配色。地名优先就近 8 向贴靠放置，**宁可保留轻微的文字/光晕叠压，也尽量避免满屏“标点—连线—文字”式的引线网**；发生轻微叠压时，必须保证高线级（及选中城市）文字在 SVG DOM 层级压在上方。
2. **直观辨识、零重复徽标**：六个线级采用互不重复的轮廓与内嵌数字（一线八角星 `1`、新一线立菱 `1+`、二线盾牌 `2`、三线圆角方 `3`、四线六边形 `4`、五线正圆 `5`），并辅以克制的体积阶梯（109% → 85%）。
3. **真正的渐进式披露与单调性**：全国默认画面保持疏朗，随「＋」缩放逐级解锁各档城市名；第 3 次放大（`2.35×`）及更大视野时才渲染全国地市界线，且地市界线采用更轻的虚线以与实线省界清晰区分。**勾选低线级（如五线）时绝不允许反过来挤掉已显示的高线级地名**。
4. **移动端一等体验与操作可达**：放大后必须支持单指拖拽（未放大时放行整页滚动），不拦截滚轮或双指缩放页面；「返回全国」放在缩放按钮旁以免在省级视图被忽略；内嵌表格滚动区（名录、省统计表）需用明显边框、限制高度与独立滚动条和整页滚动做视觉区隔。
5. **数据诚实与全量对齐**：完整收录第一财经知城数据库 2026 版全部 337 席（333 个地级行政区 + 4 座直辖市），诚实说明 2026 年 5 月公开报告不再发总榜与分级、当前线级与线内序来自官方知城数据库归档（`city_charm.2026` / `city-tier-2026-*`），不借用上游底图审图号充当成品凭据。

## 交互与布局约定

- 桌面全国默认勾选六档。窄屏（视口不超过 720 px）或粗指针设备（不超过 960 px）默认只勾选一线、新一线、二线。用户主动修改后，调整窗口尺寸应保留选择。「重置」恢复当前设备默认。
- 地图勾选只改变地图标记和名称。名录线级筛选独立。城市搜索和省份选择作用于两边。返回全国时保留筛选，重置会清除筛选并恢复全国。
- 地图用「＋／−」按固定级别缩放，放大后桌面与手机单指均可拖动，「全览」复位当前范围。不拦截滚轮或触控手势来缩放地图；滚轮要能正常滚动页面。拖动不能误触城市或省份点击。
- 宽画布（至少 650 px）的全国视图默认优先放置全部一线与新一线名称；第一次按「＋」用 1.23 倍取景，优先放置视野内所有二线及以上名称；第 3 次按「＋」（`zoomSteps[3]` = `2.35×`）起渲染全国地市界线。
- 省级视图显示省内地级界线并在缩放工具旁展示「返回全国」；在省级视图中直接拖动地图时，无缝退回全国视图并保留当前视觉缩放比例，方便拖看并点选邻近省份。海南视图可切换南海诸岛附图，选择三沙时自动切换。
- 4 座直辖市（`110000`、`120000`、`310000`、`500000`）及深圳（`440300`）支持区级边界（`#subdistrict-lines`）与区名（`#subdistrict-labels`）：区界线采用比地市界更浅更细的虚线以清晰区分层级；放大至局部视图（或选中/点击直辖市与深圳并放大）时懒加载对应 `subdistricts/<city>.js` 并展示区名，且在标签避让时优先让位给城市名和点位徽标。

## 数据与底图构建

- `site/assets/data.js` 暴露 `window.atlasData`（含自描述的 `meta` 版次与线级配置、`cities`、`provinces`），可通过 `scripts/build_data.py` 从 `research/datayicai-mcp/charm-2026/city_charm_2026_scores_wide.csv` 重新生成。333 个地级行政区（293 座地级市及 40 个自治州、地区、盟）与 4 座直辖市分开统计，合计覆盖 337 席。城市名录的数字是 **知城 2026 版线内序**。六档地级行政区数量依次为 `2、13、30、70、90、128`。西藏有 7 条地级记录（6 座地级市 + 阿里地区）。
- 城市记录为 `[简称, 六位代码, 省级代码, 线级索引, 线内图序, 是否直辖市, [经度, 纬度], [图面 x, y], 是否城区参考点]`。坐标是近似位置，不应称为现时精确驻地或用于导航。
- `scripts/build_map.py` 从[固定版本上游目录](https://github.com/JayMuShui/chinese-global-compliant-geodata/tree/3cf3485789876c37be6193bf2848cf9aaa40f758/src/geojson/countries/as/chn/global)的 `chn-level-1.json` 和 `chn-level-2.json` 生成 `window.atlasMap`，校验源文件 SHA-256 并重算投影坐标：
  ```sh
  python3 -m venv .venv
  .venv/bin/python -m pip install 'shapely>=2.1,<3' pyproj
  .venv/bin/python scripts/build_map.py /path/to/chn/global
  python3 scripts/verify_data.py
  ```
- `site/assets/map-data.js`、`site/assets/map-base.js`、`site/assets/districts/` 和 `site/assets/subdistricts/` 是本地生成文件，保持 Git 忽略；公开仓库不分发，运行和部署均需要。改动 `map-data.js` 后可用 `python3 scripts/split_map_assets.py` 重新生成核心底图与分片；直辖市与深圳的区级分片由 `scripts/build_subdistricts.py /path/to/chn/global` 从同一上游版本的 `chn-level-3.json` 生成。数据出处和限制见 `docs/sources.md`。

## 检查与部署

1. 施工前确认工作区干净；改动后在项目根目录执行 `python3 scripts/verify_data.py`，并对改动的 JS 运行 `node --check`。
2. 在桌面宽度（如 1440 px）和手机宽度（如 360 / 390 px）打开正式页面实测：
   - 桌面应有 337 个标记，手机默认 49 个，两端名录仍有 333 条；
   - 核验四川 21 个地级行政区（18 市 + 3 州）、第 3 次「＋」放大后全国虚线地市界线渲染、省级视图缩放区旁「返回全国」、放大后桌面/单指拖动、名录独立框滚动及五线切换单调性。
3. 部署维护在同级 `hiww-web/apps/citiescn/`，Worker 名为 `hiww-citiescn`。新增运行时文件时同步更新 `build.mjs` 的复制清单。在 `hiww-web` 根目录执行：
   ```sh
   pnpm --filter @hiww/citiescn typecheck
   pnpm --filter @hiww/citiescn build
   pnpm --filter @hiww/citiescn deploy:dry
   pnpm --filter @hiww/citiescn exec wrangler deploy
   ```
   发布后验证 `https://citiescn.hiww.top/` 返回 200、桌面与手机布局正常、`/tools/mobile-preview.html` 返回 404。
4. 不要把 Cloudflare 凭据或私人站点配置复制到本仓库。不改动 `hiww.top`、`home.hiww.top` 的路由或邮件 DNS。不要使用腾讯云代替既有部署。若需在远程服务器运行耗时任务，尽量使用 tmux。
