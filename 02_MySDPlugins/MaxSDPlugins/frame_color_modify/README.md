# Frame 颜色批量修改 (FrameColorModify)

> 当前开发工具版本：v0.8.1（`__init__.py/TOOL_VERSION`）；随插件 v0.25.0 升级。此版本号不代表 MG 已发布版本。

搜集当前画布的全部 Frame，并统一修改颜色与透明度。
菜单位置：`MaxSDPlugin/Edit/FrameColorModify`。

---

## 功能概览

### 使用流程

<whiteboard type="mermaid">
flowchart TD
    A[打开目标 Graph] --> B[读取画布 Frame]
    B --> C[配置 RGB 与透明度并核对目标数量]
    C --> D{输入与目标确认无误?}
    D -- 否 --> B
    D -- 是 --> E[在撤销组内应用颜色]
    E --> F[检查画布并保存 SBS]
</whiteboard>

- 列出当前 Graph 中所有 Frame 的标题、位置、尺寸、颜色、透明度和描述。
- “修改颜色”开启时使用颜色选择器统一设置 RGB；关闭时保留每个 Frame 的原颜色。
- 通过 0-100% 全局参数统一设置透明度。
- 批量修改进入一个 Undo Group，可在 SD 中按 `Ctrl+Z` 一次撤销。

---

## 代码结构

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 菜单入口，打开并保活窗口 |
| `collect_frames()` | 枚举当前 Graph 的 Frame 对象 |
| `frame_info()` | 读取 Frame 标题和 RGBA |
| `frame_details()` | 汇总 Frame 位置、尺寸和描述等只读信息 |
| `apply_frame_color()` | 批量写入透明度，并按选项统一或保留 RGB |

---

## 用到的 SD API
- `SDGraph.getGraphObjects()` - 枚举当前画布的 Graph Object。
- `SDGraphObjectFrame.getColor()` - 读取 Frame 当前 RGBA。
- `SDGraphObjectFrame.setColor()` - 写入 Frame 新 RGBA。
- `SDHistoryUtils.UndoGroup` - 将批量修改合并为一次撤销操作。

---

## 扩展指南
1. 如需按名称筛选，可在 `collect_frames()` 的结果上增加勾选状态。
2. 如需预设色板，可在窗口中增加常用 `QColor` 按钮。

---

## 已知约束
- 仅处理当前图视图打开的 Graph，不会修改同一 Package 内的其他 Graph。
- 开启“修改颜色”时，颜色统一应用到全部 Frame，不保留各 Frame 之间的颜色差异。

## 框架升级说明

本工具公开入口和原有参数保持不变。窗口统一由 `shared.lifecycle` 管理：重复打开复用、关闭释放；插件重载会关闭窗口。未保存的界面配置请先处理。升级包含入口变更，需要重启 Designer 一次。离线回归不替代目标 Designer 中的实际功能和撤销验证。

## 更新日志

- 2026-09-04 · v0.8.1 · 接入统一窗口生命周期 · 本工具入口与错误处理 · 随插件 v0.25.0 升级需重启 SD
