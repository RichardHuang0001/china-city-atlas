# 纯前端性能与渐进式加载架构规范

本文档记录「中国城市分级地图 · 2026」在**无后端服务器、纯静态资源、同时兼容本地 `file://` 与 Cloudflare Workers Assets 托管**前提下的首屏加载优化方案与后续开发约束。

## 1. 问题诊断（优化前基准）

优化前，`site/index.html` 通过五个串联 `<script defer>` 在首屏一次性阻塞加载全部静态脚本（合计 **3,848.2 KB 原始 / 1,275.5 KB gzip**）：

- `map-data.js` 占总传输体积的 **93.5%**（3,592.7 KB 原始 / 1,193.0 KB gzip），其中 **`districts`（全国 333 个地级界线）就占 2,431.5 KB 原始 / 801.0 KB gzip**，但全国默认视图根本不渲染地市界线；
- `city-profiles.js`（141.2 KB 原始 / 46.6 KB gzip）仅在点击具体城市查看详情卡时才用到，却参与了 `<head>` 首屏串联阻塞；
- 默认响应头为 `cache-control: public, max-age=0, must-revalidate`，二次访问仍需发条件请求协商。

## 2. 工程架构与四层优化

### (1) 静态资产分层与按需分片（Critical Core + Lazy Shards）

- **首屏关键路径（`<head>` 同步必备）**：
  - `assets/style.css` + `assets/data.js` + `assets/map-base.js` + `assets/map-labels.js` + `assets/app.js`
  - [split_map_assets.py](../scripts/split_map_assets.py) 从 `map-data.js` 生成 `site/assets/map-base.js` 与 `site/assets/districts/<prov>.js`：
    - `map-base.js` 仅保留首屏必须的省级多边形、包络框、国界/南海附图及 `districtProvinces` 索引列表，并对全国视图边界坐标实施确定性 `0.1` SVG 单位舍入与连续重复点去重（相邻省界共享顶点完全同值、零接缝缺口，全国画布下误差 < 0.1 px），`map-base.js` 体积由 1,193 KB gzip 降至 **~272 KB gzip**。
    - 全量 27 个省份的地市界线保留原始高精度，拆分为 `site/assets/districts/<prov>.js`（单省均值 **~30 KB gzip**）。
- **城市语料与详情数据（`assets/city-profiles.js`）**：
  - 不在 `<head>` 中阻塞声明。首屏地图完成第一帧 `render()` 后，通过浏览器空闲回调（`requestIdleCallback` / `setTimeout`）静默预加载。
  - 若用户在预加载完成前提前点击某城市，面板先渲染名称、线级与坐标骨架，并显示轻量加载提示；脚本就绪后自动原地刷新补全简介、经济与交通信息。

### (2) `file://` 与静态托管双兼容的动态 `<script>` 加载器

为保证本地 `file://` 双击打开时不触发浏览器的 `fetch()` CORS 拦截，所有懒加载统一使用 [app.js](../site/assets/app.js) 中的 `loadScriptOnce(key, src)`：

- 动态向 `<head>` 注入带 `async = true` 的 `<script>`，由分片脚本挂载 `window.atlasProfiles` 或 `window.atlasDistricts[prov]`；
- 按资源 key 对 Promise 去重并在失败时清理缓存以便重试；
- **地市界线按三类精准时机触发**：
  1. 鼠标悬停在某城市标记/标签上时，静默加载该市所属省份分片；
  2. 点击进入某省或选中某城市时，加载该省分片并刷新虚线边界；
  3. 全国视图按第 3 次「＋」（`zoomSteps[3] = 2.35×`）及更大倍率时，通过 `visibleDistrictProvinces()` **仅按当前可视 `viewBox` 交集加载视口内省份**，拖拽期间不发请求，松手后按新视口按需补齐。

### (3) 消除首屏空白与预加载优先级

- `<head>` 使用 `<link rel="preload" as="script">` 提前并行调度首屏核心 4 个 JS；
- `#map-stage` 内置 `.map-loading`（“正在绘制全国底图…”）与预设 `aspect-ratio: 1.32` 容器，避免慢网下出现空白塌陷或布局抖动（CLS），首帧 `render()` 后立即隐藏。

### (4) 版本化指纹与边缘长效强缓存

在部署构建脚本 [build.mjs](../../hiww-web/apps/citiescn/build.mjs) 中：

- 对 `assets/` 下全部构建文件计算统一内容指纹 `assetVersion`（8 位 SHA-256 摘要）；
- 构建产物 `dist/index.html` 注入 `<meta name="asset-version" content="...">` 并为首屏静态 `<link>` / `<script>` 追加 `?v=<hash>`；[app.js](../site/assets/app.js) 动态加载懒分片时自动读取该 `meta` 并附加 `?v=<hash>`（本地 `file://` 无该 `meta` 时退化为无参数相对路径）；
- 自动生成 Cloudflare Workers Assets 的 `dist/_headers`：`/assets/*` 启用 `Cache-Control: public, max-age=31536000, immutable`，`/` 与 `/index.html` 保持 `Cache-Control: public, max-age=0, must-revalidate`，实现更新即时生效且二次打开 **0 ms 静态缓存直出**。

## 3. 后续功能扩展准则（必须遵守）

今后新增任何中大型数据维度（如自定义权重评分指标、历史年份序列、多维对比面板、城市专题图层等），须遵循以下工程纪律：

1. **严控首屏预算**：首屏阻塞下载的 JS/CSS 总 gzip 体积控制在 **≤ 350 KB**，禁止向 `<head>` 直接塞入百 KB 级以上非首屏必需数据集。
2. **数据与几何分离、按需下发**：超过 ~30 KB gzip 且仅在点击、筛选特定维度或放大后才展示的数据，必须独立成模块脚本并在交互触发或 `requestIdleCallback` 阶段通过 `loadScriptOnce` 懒加载，不得回退到 `fetch()` 破坏 `file://` 可用性。
3. **保留兼容兜底与渐进水合**：组件渲染函数须能处理“分片尚未到达”的瞬间状态（渲染骨架/提示并在 Promise `onload` 后幂等重绘），避免竞态空指针。
4. **同步维护构建与校验链路**：
   - 更新地理数据后运行 `python3 scripts/build_map.py ...` 或 `python3 scripts/split_map_assets.py`；
   - 新增分片或资产文件时同步更新 [scripts/verify_data.py](../scripts/verify_data.py) 与 [hiww-web/apps/citiescn/build.mjs](../../hiww-web/apps/citiescn/build.mjs)；
   - 衍生地理边界文件（`map-data.js`、`map-base.js`、`districts/`）继续保持 `.gitignore` 忽略，不提交大体积几何产物至公开源码仓库。
