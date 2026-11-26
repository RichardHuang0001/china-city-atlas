# 中国城市分级地图 · 2025

有本地地图资源时，双击 `site/index.html` 即可离线使用。页面里的来源链接由访客主动打开。

公开仓库保存页面源码、城市记录和底图构建脚本。生成的 `site/assets/map-data.js` 不随仓库分发。新克隆需先按下文从指定来源构建本地地图资源，确认符合源数据的使用条件。

经确认可公开展示后，可将 **`site/` 里的内容**部署到静态托管根目录或任意子路径。请保留 `assets/` 目录结构。可用 `python3 -m http.server 8000 --directory site` 在本机预览。公开发布前请核对天地图源数据条款及专题地图的审图要求。

## 目录

- `site/index.html` 页面结构及来源说明。
- `site/assets/style.css` 响应式样式与地图颜色图例。
- `site/assets/app.js` 原生浏览器交互。
- `site/assets/map-labels.js` 随缩放调整的城市标签与避让。
- `tools/mobile-preview.html` 开发者本地手机预览，位于部署目录之外。
- `site/assets/data.js` 经核对的 297 条城市记录。
- `site/assets/map-data.js` 预投影的省级与地级边界、南海附图和点击区域。
- `site/licenses/map-source.txt` 上游开源仓库的 MIT 声明。
- `scripts/verify_data.py` 离线核对总数、唯一性、线级及地图图层。
- `scripts/build_map.py` 从固定版本的 GeoJSON 重建矢量资产。只在维护底图时需要。
- `docs/sources.md` 数据出处、字段和适用范围。

## 本地核对

运行 `python3 scripts/verify_data.py`。使用浏览器打开页面后，可从“四川省”测试地图放大与 18 座地级市，从“林芝市”测试搜索与五线标记，从“海南省 → 三沙”测试南海诸岛附图。用地图右上角的加减按钮缩放，放大后按住鼠标拖动。“全览”恢复当前范围。桌面默认优先显示一线和新一线名称，放大一档后优先显示当前视野内的二线及以上名称，之后逐档增加。手机端默认显示一线、新一线和二线标记，标签间距更宽松。点击名称可查看城市详情。双击项目内的 `tools/mobile-preview.html`，可切换 360、390、430 像素视口。正式页面没有预览入口，只需部署 `site/`。地图标记支持多选或全部隐藏，城市名录有独立的线级筛选。返回全国会保留筛选条件，重置会恢复当前设备的默认线级。

本期数据按第一财经 2025 年榜单。全榜分数和正式总名次未纳入项目。

重建底图时，按数据说明获取固定版本的两个源文件。安装 Shapely 2.1 或更新版及 PyProj 后，运行 `python3 scripts/build_map.py /path/to/chn/global`。正常打开页面或部署无需执行这一步。
