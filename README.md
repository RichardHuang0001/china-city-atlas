# 中国城市分级地图 · 2025

[在线页面](https://citiescn.hiww.top/) · [源码仓库](https://github.com/RichardHuang0001/china-city-atlas) · [接手指南](AGENTS.md) · [数据来源与口径](docs/sources.md)

用全国及省级地图、线级筛选和城市名录浏览第一财经 2025 年城市魅力榜。完整收录内地 **333 个地级行政区**（含 293 座地级市及 40 个自治州、地区、盟），**4 座直辖市**单列参考，合计与原榜 337 席一致。名录显示榜单原图的线内图序，未纳入综合分数和全国总名次。

## 本地使用

本机已有 `site/assets/map-data.js` 时，双击 `site/index.html` 即可离线打开。桌面端默认显示全部线级，手机端默认显示一线、新一线和二线。地图用「＋／−」缩放，放大后可拖动，点击「全览」恢复当前范围。城市名随缩放逐级出现，地图标记和名录线级可独立筛选。

开发时可双击 `tools/mobile-preview.html`，在 360、390、430 px 三种宽度下操作同一个页面。该入口在 `site/` 之外。也可在项目根目录运行 `python3 -m http.server 8000 --directory site`，打开 `http://localhost:8000/`。

## 技术结构

| 路径 | 职责 |
| --- | --- |
| `site/index.html`、`site/assets/style.css` | 页面结构、响应式布局和样式 |
| `site/assets/app.js` | 视图状态、SVG 地图绘制、地图与表格联动 |
| `site/assets/map-labels.js` | 根据屏幕尺寸和缩放级别安排城市名、避让和引线 |
| `site/assets/data.js` | 城市记录、省级字典与城市投影坐标 |
| `site/assets/map-data.js` | 生成的省级与地级 SVG 路径、南海附图和视图范围 |
| `scripts/build_map.py`、`scripts/verify_data.py` | 底图重建与数据校验 |
| `docs/sources.md`、`site/licenses/map-source.txt` | 数据来源、限制和上游打包仓库的 MIT 许可声明 |

前端使用原生 HTML、CSS、JavaScript 和 SVG。资源均为相对路径，无框架、后端、地图服务密钥或 CDN 运行依赖。Python 只用于维护数据，Node.js 及 pnpm 只用于发布流程。

## 从公开仓库重建底图

公开仓库不包含生成的 `site/assets/map-data.js`。新克隆时，从[固定版本的上游目录](https://github.com/JayMuShui/chinese-global-compliant-geodata/tree/3cf3485789876c37be6193bf2848cf9aaa40f758/src/geojson/countries/as/chn/global)取得 `chn-level-1.json` 和 `chn-level-2.json`，放入同一目录。从项目根目录运行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'shapely>=2.1,<3' pyproj
.venv/bin/python scripts/build_map.py /path/to/chn/global
python3 scripts/verify_data.py
```

构建器校验源文件 SHA-256，写入底图资源，并重新计算 `data.js` 内的城市图面坐标。此步骤无需联网读取源文件。底图资源保留在本地并参与站点构建，受 Git 忽略规则保护。

## 发布与验证

线上站点使用 Cloudflare Workers Static Assets。发布配置维护在同级工作区 `hiww-web/apps/citiescn/`。在 `hiww-web` 根目录运行：

```sh
pnpm --filter @hiww/citiescn typecheck
pnpm --filter @hiww/citiescn build
pnpm --filter @hiww/citiescn deploy:dry
pnpm --filter @hiww/citiescn exec wrangler deploy
```

前三条用于检查、构建及试运行，最后一条才发布。构建脚本只复制正式站点资源，`tools/` 不会部署。发布后验证 HTTPS、桌面与手机布局、地图搜索和缩放，并确认 `/tools/mobile-preview.html` 返回 404。当前专题图未单独送审，不能借用上游数据或原标准地图的审图号，详见[数据来源与口径](docs/sources.md)。
