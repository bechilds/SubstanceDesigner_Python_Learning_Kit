# SD16 / SD13 Python API 兼容查找表

> 本表是 **本地标准查找表**。涉及导出工具 / 跨版本兼容的改动前**先查这里**，不要凭记忆猜 SD13 接口名。
> 机器可读版本：[sd_api_compat.json](sd_api_compat.json)。新增差异时两份都要同步，并更新 `output_tools.py` 的 `_RUNTIME_COMPAT_SHIM`。
>
> 最后更新：2026-07-22

## 版本对照

| 标识 | 应用 | Python | PySide | Qt |
|---|---|---|---|---|
| SD16 | Adobe Substance 3D Designer 16.0.1 | 3.13.x | PySide6 | 6.8.x |
| SD14–15 | Substance 3D Designer 14.0–15.x | — | PySide6 | 6.5.x |
| SD13 | Substance Designer 13.x | — | PySide2 | 5.15.x |

> 注：SD14 起即为 PySide6/Qt6；SD13 及更早才是 PySide2/Qt5。

## 差异清单

| # | 主题 | SD16 / PySide6 | SD13 / PySide2 | 处理策略 |
|---|---|---|---|---|
| 1 | Qt 绑定 / 导入 | `from PySide6 import ...` | `from PySide2 import ...` | **运行时回退**：模块 `try PySide6 except PySide2`；导出物**不做静态替换** |
| 2 | `QAction` 所在模块 | `QtGui.QAction` | `QtWidgets.QAction` | **运行时补丁**：双向补全 |
| 3 | 对话框/菜单模态执行 | `dialog.exec()` / `menu.exec(pos)` | `dialog.exec_()` / `menu.exec_(pos)` | **运行时补丁**：`exec` 与 `exec_` 互为别名 |
| 4 | 枚举作用域 | `Qt.UserRole`（非作用域可用） | `Qt.UserRole` | **代码约定**：统一非作用域写法，两版通用 |
| 5 | 图视图定位（`SDUIMgr`） | `getGraphViewIDCount` / `getGraphViewIDAt` / `getGraphFromGraphViewID` / `focusGraphNode` | 无这些方法；改走 Qt 层 `SDNode.getPosition()` + `QGraphicsView.fitInView` | **`sdcompat.focus_node` 多策略探测**：SD16/14 用 focusGraphNode；SD13 用 Qt 层缩放居中 |
| 6 | 创建 Comment 图对象 | `SDGraphObjectComment.sNew()` / `sNewAsChild()` | 本机 SD13.0.0 Python 绑定无 `SDGraphObjectComment` | **导入守卫**：功能明确提示 API 不可用，不修改 Graph |

## SD13 实测 UI 管理器接口清单（2026-07-01）

在 SD13 Python Editor 里 `dir(app.getX())` 实测结果（去掉 `__` 前缀）：

- **`app.getSDUIMgr()`**：SD13 **不存在**此方法。
- **`app.getQtForPythonUIMgr()`** → `QtForPythonUIMgrWrapper`：
  `getCurrentGraph`、`getCurrentGraphSelectedNodes`、`getCurrentGraphSelectedObjects`、
  `getCurrentGraphSelection`、`getCurrentGraphSelectionFromGraphViewID`、`getGraphFromGraphViewID`、
  `getGraphSelectedNodesFromGraphViewID`、`getGraphSelectedObjectsFromGraphViewID`、`getMainWindow`、
  `newMenu`、`newDockWidget`、`add*Toolbar*`、`register*Callback` 等。
- **`app.getUIMgr()`** → `SDUIMgr`：与上面基本相同，但主窗口是 `getMainWindowPtr`（非 `getMainWindow`），另有 `getClassName`/`release`。

**关键结论**：
- ✅ `getCurrentGraph()` 可用 → `get_current_graph` 在 SD13 正常。
- ✅ `QtForPythonUIMgr.getMainWindow()` 可用 → `get_main_window` 在 SD13 正常。
- ❌ **没有** `focusGraphNode` / `getGraphViewIDCount` / `getGraphViewIDAt` / `setCurrentGraphSelection` / `selectNode(s)`。SD13 的选择相关接口**全是 getter（只读）**，没有 set/focus 写入接口。
- ✅ **但 `SDNode.getPosition()` 可用**，且节点图坐标与 `QGraphicsScene` 坐标**1:1 对应**（SD13.0.0 实测）→ `focus_node` 策略3 用 `QApplication.allWidgets()` 枚举存活可见 `QGraphicsView` + `fitInView` 缩放居中，**SD13 的 Goto 已可用**，效果接近 F 键（既居中又放大）。视图枚举必须配 `shiboken.isValid()` 判活，否则 `findChildren` 会返回已删除视图导致 `already deleted`。
- ✅ **SD16 / SD14 有 `focusGraphNode`** → Goto 在这两个版本走策略1 居中。只有 SD13 缺这个接口、改走策略3。
- ⚠ **排错教训（2026-07-01）**：本开发机的 SD 安装其实是 **13.0.0**（不是 16）。曾误把它当 SD16、读它的 `resources/python/sd/api` stub，错误得出“SD16 也没有 focusGraphNode”。**核对某版本接口必须在该版本 SD 里 `dir()` introspect，不能读别的版本的 stub。** 已更正。

## 兼容机制（唯一真源：`MaxSDPlugins/sdcompat.py`）

**原则**：所有版本脆弱的 SD/Qt 接口**只走 `sdcompat.py`**，功能模块不再硬编码。`sdcompat` 提供三层保障：

1. **能力探测**：`hasattr` + 遍历多个候选 UI 管理器（`getQtForPythonUIMgr` / `getUIMgr` / `getSDUIMgr`）与多个候选方法名；
2. **多策略降级**：如 `focus_node` 先试 `focusGraphNode` 居中（SD16/14），再试 `setCurrentGraphSelection` / `selectNodes` 选中高亮（旧版兜底），SD13 走 Qt 层 `getPosition()`+`fitInView` 缩放居中，都不行才给友好提示；
3. **永不抛异常 + 精确日志**：缺接口时打印缺失的方法名，返回安全默认值，不冒泡到 SD 主进程。

**接入方式**：
- 功能模块：`from .. import sdcompat`，然后调 `sdcompat.get_current_graph()` / `sdcompat.focus_node(...)` / `sdcompat.get_main_window()` 等，`goto_node` 只做转发。
- 导出物：OutputTools **始终把 `sdcompat.py` 打包**为 `_maxsd_bundle.root_sdcompat`，加载时**最先 exec 并调 `qt_patch()`**，随后其余模块的 `from .. import sdcompat` 被自动改写到它。

**扩展**：新发现跨版本差异 → 在 `sdcompat.py` 加一个候选方法名/策略即可，**一处维护**，功能模块与导出物都自动受益。

### 处理策略说明

- **运行时回退（runtime-fallback）**：源码保留 `try PySide6 → except PySide2`，加载时自动选可用绑定。**禁止**把 `PySide6` 整体替换成 `PySide2`（会写死单版本，在另一版本上崩溃）。
- **运行时补丁（runtime-patch）**：由导出物顶部的 `_maxsd_qt_compat()` 抹平（见 [output_tools.py](../MaxSDPlugins/output_tools/output_tools.py) 的 `_RUNTIME_COMPAT_SHIM`）。覆盖 #2 `QAction` 位置与 #3 `exec/exec_`。
- **代码约定（code-convention）**：写代码时直接采用两版通用写法（如非作用域枚举 `Qt.UserRole`）。
- **`hasattr` 守卫（hasattr-guard）**：SD 专有接口（`SDUIMgr` 等）无法运行时补丁，必须在调用处 `hasattr` 检查后降级。例：

  ```python
  ui = app.getUIMgr()
  if not (hasattr(ui, "getGraphViewIDCount") and hasattr(ui, "focusGraphNode")):
      return False, "当前 SD 版本不支持 Goto 定位（缺少 focusGraphNode 接口）。"
  ```

  涉及文件：`MaxSDPlugins/output/output_data.py`、`MaxSDPlugins/debug/check_dependencies.py`（均为 `goto_node`）。

## 导出模块实际用到的 Qt API（决定补丁覆盖范围）

- 导入：仅 `QtWidgets`、`QtCore`（**不**用 `QtGui.QAction`）。
- `exec`：`QMenu.exec(pos)`（→ 运行时补丁覆盖）。
- 静态对话框：`QFileDialog.getSaveFileName` / `getOpenFileName`、`QMessageBox.information/warning`（两版一致）。
- 枚举：`Qt.UserRole` / `Qt.Checked` / `Qt.Unchecked` / `Qt.ItemIsUserCheckable` / `Qt.ItemIsAutoTristate` / `Qt.CustomContextMenu`（非作用域，两版通用）。

## 维护规则

新发现一处版本差异时，**三处同步**：

1. 本表 + [sd_api_compat.json](sd_api_compat.json) 加一行；
2. 若可运行时抹平 → 更新 `output_tools.py` 的 `_RUNTIME_COMPAT_SHIM`；
3. 若是 SD 专有接口 → 在调用处加 `hasattr` 守卫。
