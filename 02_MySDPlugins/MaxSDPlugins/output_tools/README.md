# 输出脚本 (output_tools)

将选定的 MaxSDPlugins 功能导出为独立脚本，或按 MG 工具包约定写入自定义 MaxSD 目录。
菜单位置：`MaxSDPlugin/OutputTools/输出脚本`。

---

## 功能概览

- 扫描当前插件的功能分类与 Python 模块，按树形列表勾选导出内容。
- “导出为独立脚本”生成带隔离命名空间和 `sdcompat` 的单个 Python 文件。
- “输出到 MG...”生成 `LG_MaxSD_*.py`，保留分类目录并允许自定义 MaxSD 根目录。
- MG 输出自动改写相对 import、处理同名模块冲突，并提示本次未勾选的依赖。

---

## 代码结构

| 文件 / 函数 | 职责 |
|---|---|
| `output_tools.py` | 功能扫描、两种导出逻辑与对话框 UI |
| `collect_features()` | 收集可导出的功能模块 |
| `export_modules()` | 打包独立、自包含脚本 |
| `export_modules_to_mg()` | 输出 MG 分类目录、模块和兼容层 |
| `_rewrite_mg_source()` | 将插件相对 import 改写为 `LG_MaxSD_*` 绝对 import |
| `show_window()` | 菜单入口，打开 OutputTools 对话框 |

---

## 用到的 SD API

- 本模块不直接修改 Graph 或 Package。
- `sdcompat.py` 会随两种导出方式一并写出，供生成模块适配 SD13/PySide2 与 SD16/PySide6。
- UI 使用 PySide 的 `QTreeWidget`、`QFileDialog` 与 `QMessageBox`。

---

## 扩展指南

1. 新增可导出功能时，将包目录名与显示标题加入 `_CATEGORY_TITLES`。
2. 功能存在 logic/window 依赖时，导出到 MG 前同时勾选相关模块。
3. MG 的启动脚本通过 `LG_MaxSD_loader.py` 加载生成文件，再调用模块公开的 `show_window()`。
4. 在 `LG_Tool.py` 中按团队菜单结构注册对应 `*_Start.py`；OutputTools 不自动修改宿主文件。

---

## 已知约束

- MG 输出目录应选择 MaxSD 根目录；工具会在其中创建各功能分类子目录。
- 同名 `LG_MaxSD_*.py` 会在确认后覆盖，现有 `*_Start.py` 与 `LG_Tool.py` 不会被修改。
- 未勾选的相对依赖不会自动补选，完成后会在结果消息中列出。
- 依赖 `.sbs`、图片或其他外部资源的功能仍需手工复制资源并维护路径。
