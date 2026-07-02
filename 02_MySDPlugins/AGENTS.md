# AGENTS.md — AI 协作者指南（02_MySDPlugins）

> 本文件是给 **AI 编码助手**（Copilot / Claude / Cursor 等）读的操作手册。
> 人类开发者请先看本目录 [README.md](README.md) 与插件计划 [MaxSDPlugins/ReleaseNote.md](MaxSDPlugins/ReleaseNote.md)。
>
> **当你（AI）接到"给 MaxSDPlugin 添加新功能"类指令时，必须先完整读完本文件，再动手。**

---

## 0. 必读背景

- 本目录是 **我的 Substance Designer（SD）Python 插件开发区**，对应工程三大分类中的「② 我的插件开发项目」。
- 代码运行在 **Substance Designer 内置的 Python 解释器**里，不是普通命令行 Python。很多 API（`sd`、`PySide`）只有在 SD 进程内才存在。
- **目标版本：SD 16.0.1**。该版本内置 **Python 3.13.x** 与 **PySide6（Qt 6.8.x）**。因此本项目代码以 **PySide6** 为准（而非旧版的 PySide2 / Qt5）。
  > 注：SD 14.0–15.x 为 Qt 6.5.x，12.x 及以前才是 PySide2/Qt5。官方示例里的“try PySide2 再 try PySide6”只是为了跨版本兼容；在 16.0.1 上实际走的是 PySide6 分支。
- 插件主体在 [MaxSDPlugins/](MaxSDPlugins/)，所有功能通过唯一顶级菜单 **`MaxSDPlugin`** 暴露给用户。
- 学习写法时优先对照官方案例：[../03_OfficialExamples/OfficialExamples/PluginBasics.py](../03_OfficialExamples/OfficialExamples/PluginBasics.py)。
- 本工程定位是**初学者友好**：代码必须注释清晰、有中文说明、有防御性错误处理（见根 [README.md](../README.md) 的 Copilot 指南）。

### 本目录职责划分

| 子目录 | 职责 | 动它的注意点 |
|---|---|---|
| `MaxSDPlugins/` | 插件主体（入口 + 各功能模块） | 新功能加在这里 |
| `utilities/` | 可被插件复用的通用工具函数 | 跨功能共用逻辑沉淀到这里，不要在功能里复制粘贴 |
| `docs/` | 基础概念备注 / 报错排查 / 开发日志 | 踩坑后把结论补进去 |

---

## 1. 硬性约定（违反即视为错误）

### 1.1 文件布局

```
MaxSDPlugins/
├─ MaxSDPlugin.py                  ← 唯一插件入口：initializeSDPlugin/uninitializeSDPlugin + 菜单骨架/重载机制
├─ menu.py                         ← 数据驱动菜单：build_menu 定义所有菜单项（可热重载）
├─ _version.py                     ← 版本号单一来源（可热重载）
├─ sdcompat.py                     ← 跨版本(SD16/SD13) SD+Qt 接口兼容层（唯一真源，无相对 import，可被导出打包）
├─ README.md / ReleaseNote.md       ← 文档与功能计划
│
├─ <feature_name>/                 ← 每个功能一个文件夹（snake_case）
│  ├─ __init__.py                  ← 暴露功能入口函数（如 run / show_window）
│  ├─ <feature_name>.py            ← 小工具：单文件即可
│  ├─ <feature_name>_window.py     ← 大模块（>300 行）按职责拆分
│  ├─ <feature_name>_logic.py
│  └─ README.md                    ← **必须存在**，结构见 §3
│
└─ shared/                         ← 跨功能共用的工具（与 ../utilities 的区别见下）
   └─ __init__.py
```

- **根目录（MaxSDPlugins/）只放入口文件、菜单/版本等框架文件与文档**，业务功能放各功能文件夹，不在根目录放独立业务 `.py`。
- 每个功能文件夹必须有 `__init__.py`，让它成为可 import 的包。
- `shared/`：仅插件内部、跨功能共用的小工具；`../utilities/`：更通用、可能脱离本插件复用的工具。拿不准放 `shared/`。

### 1.2 命名约定

| 情况 | 规则 |
|---|---|
| 功能文件夹 / 模块文件 | `snake_case`（如 `reset_view_layout/`） |
| 类名 | `PascalCase`（如 `ResetViewLayoutWindow`） |
| 函数 / 变量 | `snake_case` |
| 模块级缓存引用（菜单/动作） | 前缀下划线（如 `_menu_ref`、`_action_ref`） |
| 日志前缀 | 统一 `[MaxSDPlugin]`，子功能可用 `[MaxSDPlugin/<feature>]` |
| 文件编码 | 含中文的文件首行必须有 `# -*- coding: utf-8 -*-` |

### 1.3 插件入口与菜单注册（**唯一注册点**）

- SD 在启动时自动调用 `initializeSDPlugin()`，卸载/关闭时调用 `uninitializeSDPlugin()`。这两个函数**只能存在于** [MaxSDPlugins/MaxSDPlugin.py](MaxSDPlugins/MaxSDPlugin.py)。
- **不允许**在功能模块里直接往菜单栏加菜单。功能模块只暴露入口函数（如 `run(app)` / `show_window(main_win)`），由入口文件统一注册成一个 `QAction` 挂到 `MaxSDPlugin` 菜单下。
- 标准获取主窗口链路（参考官方案例）：
  ```python
  app = sd.getContext().getSDApplication()
  qt_ui = app.getQtForPythonUIMgr()
  main_win = qt_ui.getMainWindow() if qt_ui else None
  ```
- **菜单创建必须幂等**：先遍历已存在的菜单项判断有没有同名 `MaxSDPlugin`，有就复用，避免"越加载菜单越多"。
- **`uninitializeSDPlugin()` 必须把本插件加的菜单/动作/事件/定时器全部清理干净**，并把模块级引用置 `None`。
- **菜单数据驱动（避免每次改菜单都动入口）**：入口只创建顶级 `MaxSDPlugin` 菜单骨架，再调用可热重载的 `MaxSDPlugins/menu.py` 的 `build_menu(menu, main_win, ctx)` 填充所有菜单项（版本号、关于、重载、各功能分类）。
  - 新增/修改菜单项**只改 `menu.py`**，随 Unload→Load 热重载，**不需重启 SD、不动入口**。新增功能分类在 `menu.py` 用 `_add_category(...)` 加一行即可。
  - 入口通过 `ctx` 注入回调（`get_version` / `show_about` / `reload_plugin` / `keep`）。版本号存于热重载的 `_version.py`，入口 `__version__` 仅作回退。
  - 只有改入口 `MaxSDPlugin.py` / `__init__.py` 才需重启 SD；其余（menu/output/debug/_version）走「重载插件（Unload→Load）」菜单即可。

### 1.4 SD / PySide 环境约定

- **以 PySide6 为准（SD 16.0.1 = Qt 6.8.x）**：新代码直接 `from PySide6 import QtWidgets, QtCore, QtGui` 即可。若希望兼容旧版 SD，可保留“try PySide2 → except try PySide6”的双兼容写法（参考 [PluginBasics.py](../03_OfficialExamples/OfficialExamples/PluginBasics.py) 顶部），但两者都失败时都要优雅降级（`QtWidgets = None` 并打印日志，不崩溃）。
- **模块级保存 QMenu / QAction 引用**，否则会被 Python 垃圾回收导致菜单/回调失效。
- 所有 `sd` / Qt API 调用包 `try/except`，失败时打印 `[MaxSDPlugin]` 前缀日志，**不要让异常冒泡到 SD 主进程**。
- 代码可能跑在无界面（命令行）模式下：拿不到 `main_win` 时要能优雅返回。

### 1.5 不要做的事

- ❌ 不要在根目录（MaxSDPlugins/）下新建业务 `.py`
- ❌ 不要在功能模块里写 `initializeSDPlugin` / 直接操作菜单栏
- ❌ 不要删除或重命名任何对外入口（`initializeSDPlugin` / `uninitializeSDPlugin` / 功能的 `run` / `show_window`）——会破坏插件加载或菜单
- ❌ 不要静默变更被其它文件 import 的函数/类签名（函数名、参数个数、默认值）——详见 §5
- ❌ 不要在改 A 功能时顺手"清理"看起来多余的 B 功能调用点 / 参数，除非任务明确要求
- ❌ 不要省略 `uninitializeSDPlugin()` 里的清理逻辑（会残留菜单 / 悬挂引用）
- ❌ 不要把只在 SD 内才有的 `import sd` 放到模块顶层做"裸调用"——import 可以，但取上下文要在函数里、包 try/except
- ❌ 不要新增功能 / 重命名文件夹但不同步更新 [MaxSDPlugins/README.md](MaxSDPlugins/README.md) 与本目录 [README.md](README.md) 的目录结构与功能说明
- ❌ 不要新增 "QUICKSTART / INDEX" 之类与 README 重复的文档

> **未覆盖场景的默认原则**：遇到本文档没明确规定的情况，默认取**保守**做法 —— 先 `grep_search` / 读代码搞清现状，不确定就向用户确认，不猜、不静默扩大改动范围。

### 1.6 插件热重载边界（Plugin Manager 的 Unload/Load）

**原理**：SD 的 Plugin Manager「Unload → Load」**不会从磁盘重读源码**。SD 启动时 `import` 出插件模块并攥着这个**模块对象**；Load 只是在旧对象上再次调用 `initializeSDPlugin()`。叠加 Python 的 `sys.modules` 缓存（已 import 的模块再 `import` 直接返回缓存、不重新执行文件），导致磁盘上的改动进不了内存。

**因此区分两类改动**：

| 改动位置 | 能否热重载 | 操作 |
|---|---|---|
| 入口文件 `MaxSDPlugin.py` / `__init__.py` | ❌ 不能 | **必须重启 SD**（SD 攥着旧模块对象，运行时无法替换入口自身） |
| 功能子模块（`<feature>/` 下的文件） | ✅ 能 | Plugin Manager **Unload → Load** 即可，无需重启 |

**实现机制（已落地，勿破坏）**：[MaxSDPlugins/MaxSDPlugin.py](MaxSDPlugins/MaxSDPlugin.py) 的 `_reload_feature_modules()` 在**加载时**（`initializeSDPlugin()` 开头）把功能子模块从 `sys.modules` 删除，使随后的延迟 `import` 从磁盘重新读取。**采用动态策略**：清掉本包 `MaxSDPlugins.*` 下所有子模块，唯独保留包根与入口模块（MaxSDPlugin / __init__）。因此**新增功能子包无需再登记任何名单**。

**硬性约定**：

- **只在「加载时」清缓存，绝不在「卸载时」清**——卸载时 SD 不会重新 import，清了也无效，还可能破坏相对导入。
- **只清功能子模块，绝不清包本身（`MaxSDPlugins`）和入口模块（`MaxSDPlugin`）**——否则 `from .<feature> import …` 会因父包缺失而出错。
- **新增功能子包无需动入口**：`_reload_feature_modules()` 动态清本包下所有子模块，放进包目录即自动热重载（只需在 `menu.py` 用 `_add_category` 挂菜单）。
- **保持入口文件极薄、稳定**：只做菜单注册 + 子模块加载，真正逻辑全放进功能子模块，最大化可热重载范围、最小化重启次数。

---

### 1.7 跨版本（SD16 / SD13）兼容与导出工具规则

OutputTools 的「输出脚本」会把功能模块打包成**一个独立 .py** 给宿主工具集成。该产物需在 **SD16（PySide6/Qt6）与 SD13（PySide2/Qt5）两个版本上都能直接运行**，因此有以下硬性约定：

- **版本脆弱的 SD/Qt 接口，只走集中式兼容层 [sdcompat.py](MaxSDPlugins/sdcompat.py)。** 功能模块**禁止**再硬编码 `app.getQtForPythonUIMgr()` / `app.getUIMgr()` / `focusGraphNode(...)` 等；改为 `from .. import sdcompat` 后调 `sdcompat.get_current_graph()` / `sdcompat.focus_node()` / `sdcompat.get_main_window()`。`goto_node` 等只做转发。
- **`sdcompat` 三层保障**：能力探测（`hasattr` + 遍历多候选管理器/方法名）→ 多策略降级（定位不了就选中高亮，再不行给提示）→ 永不抛异常 + 精确日志。**新差异只在 `sdcompat.py` 加候选，一处维护。**
- **导出物必须「双版本通用」，不做 PySide 静态字符串替换。** 历史上的 `PySide6 -> PySide2` 整体替换会把模块里的 `try PySide6 except PySide2` 回退写死成单版本，**已废弃，禁止再用**。
- **导出时 `sdcompat.py` 始终被打包**为 `_maxsd_bundle.root_sdcompat`，**最先 exec 并调 `qt_patch()`**（抹平 `QAction` 位置、`exec/exec_`），随后功能模块的 `from .. import sdcompat` 自动改写到它。见 [output_tools.py](MaxSDPlugins/output_tools/output_tools.py) 的 `export_modules`。
- **写兼容前先查本地查找表**：差异清单见 [docs/SD_API_Compatibility.md](docs/SD_API_Compatibility.md) 与 [docs/sd_api_compat.json](docs/sd_api_compat.json)。**优先查这份本地备份**，不要凭记忆猜 SD13 接口名。
- **新发现一处差异，三处同步**：(1) `sdcompat.py` 加候选/策略；(2) 查找表 md+json；(3) 若 `sdcompat` 无法覆盖的极端情况才在调用处 `hasattr` 守卫。

已知差异速查（完整见查找表）：

| 主题 | SD16 / PySide6 | SD13 / PySide2 | 处理方式 |
|---|---|---|---|
| Qt 绑定 | PySide6 / Qt6.8 | PySide2 / Qt5 | 模块 `try PySide6 except PySide2`；导出物不静态替换 |
| `QAction` 所在模块 | `QtGui.QAction` | `QtWidgets.QAction` | `sdcompat.qt_patch()` 双向补全 |
| 模态执行 | `dialog.exec()` | `dialog.exec_()` | `sdcompat.qt_patch()` 互为别名 |
| 枚举作用域 | `Qt.UserRole`（非作用域仍可用） | `Qt.UserRole` | 用非作用域写法，两版通用 |
| 图视图定位 | `SDUIMgr.getGraphViewIDCount/focusGraphNode` | **不存在** | `sdcompat.focus_node` 多策略探测降级 |

---

## 2. 添加新功能的标准流程

按顺序执行：

### 步骤 1：判断规模

| 预估代码量 | 做法 |
|---|---|
| < 300 行 | 单文件 `<feature_name>/<feature_name>.py` + `__init__.py` |
| ≥ 300 行 | 按职责拆分（window / logic / utils），参考官方内置插件 [../03_OfficialExamples/OfficialSDInsertPlugins/custom_graph/](../03_OfficialExamples/OfficialSDInsertPlugins/custom_graph/) |

### 步骤 2：创建功能文件夹 + 代码

功能模块最小骨架（`<feature_name>/__init__.py` 或主文件）：

```python
# -*- coding: utf-8 -*-
"""<功能中文名>：<一句话描述>。"""

import sd


def run(app=None):
    """功能入口。由 MaxSDPlugin.py 的菜单动作调用。

    参数:
        app: SDApplication，可选；不传时自行从 sd.getContext() 获取。
    """
    try:
        if app is None:
            app = sd.getContext().getSDApplication()
        # —— 在这里写功能逻辑 ——
        print('[MaxSDPlugin/<feature>] 执行成功')
    except Exception as e:
        # 保持插件稳健：失败只打印日志，不抛到 SD 主进程。
        print(f'[MaxSDPlugin/<feature>] 执行失败: {e}')
```

> 带 UI 的功能改为暴露 `show_window(main_win)`，窗口类参考 [../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart2/mylib/window.py](../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart2/mylib/window.py)。

### 步骤 3：在入口文件注册菜单项

编辑 [MaxSDPlugins/MaxSDPlugin.py](MaxSDPlugins/MaxSDPlugin.py)，在创建菜单的辅助函数里追加一个动作（**唯一注册点**）：

```python
from <feature_name> import run as run_<feature>

action = QtWidgets.QAction('<中文功能名>', main_win)
action.triggered.connect(lambda: run_<feature>())
menu.addAction(action)
# 记得把 action 存进模块级列表，卸载时统一移除
```

确保该动作在 `uninitializeSDPlugin()` 的清理范围内。

> **若新建了功能子包**：无需再动入口。`_reload_feature_modules()` 会动态清本包下所有子模块，放进包目录并在 `menu.py` 挂上菜单即可热重载（见 §1.6）。

### 步骤 4：编写模块 README

**必须创建** `<feature_name>/README.md`，严格按 §3 模板填写。

### 步骤 5：更新目录级文档

同时更新：

1. **[MaxSDPlugins/README.md](MaxSDPlugins/README.md)**：菜单项列表 + 功能说明小节 + 目录结构。
2. **本目录 [README.md](README.md)**：若文件夹结构有变，同步目录树。
3. **[MaxSDPlugins/ReleaseNote.md](MaxSDPlugins/ReleaseNote.md)**：把对应计划项标记为已完成（如划掉或加 ✅）。
4. **升版本 + 写更新记录（强制）**：每次功能变更必须升 [MaxSDPlugins/MaxSDPlugin.py](MaxSDPlugins/MaxSDPlugin.py) 顶部的 `__version__`（语义化：修 bug 升 patch、加功能升 minor、破坏兼容升 major），并在 [MaxSDPlugins/ReleaseNote.md](MaxSDPlugins/ReleaseNote.md) 顶部「更新记录」区追加**一行**：`日期 · vX.Y.Z · 改动 · 影响范围 · 是否需重启 SD`。

### 步骤 6：编译 / 加载验证

SD 插件没有独立 CLI 构建，验证分两层：

1. **语法编译**：运行工作区任务 `Python Lint Check`（`py_compile`），或对新文件调用 `get_errors`。**任何语法/导入错误必须本轮修复**。
   > 注意：`import sd` / `import PySide` 在工作区 lint 里可能找不到（它们只在 SD 内存在），这类"缺失模块"告警可接受；但**语法错误、缩进错误、未定义名**必须修。
2. **运行验证（说明给用户）**：快速试脚本在 SD `Windows > Python Editor` 面板粘贴运行（Run / `F5`）；插件则放入 SD 插件目录加载（或 `Tools > Plugin Manager...` 管理），确认菜单出现、点击可用、卸载后菜单消失。
   > SD 没有 `Tools > Scripting` 菜单；脚本运行走 **Python Editor**（`Windows` 菜单），插件管理走 **Plugin Manager**（`Tools` 菜单）。
   > **热重载边界（见 §1.6）**：改**功能子模块**用 Plugin Manager `Unload → Load` 即可生效；改**入口文件**（`MaxSDPlugin.py` / `__init__.py`）必须**重启 SD**。给用户的验证说明里要按改动位置说清用哪种。

---

## 3. 模块 README 模板（必须遵循）

所有 `<feature_name>/README.md` 使用此结构，章节顺序不要改：

```markdown
# <功能中文名> (<english_name>)

<一句话描述功能目的>。
菜单位置：`MaxSDPlugin/<中文功能名>`。

---

## 功能概览
- 具体要点 1
- 具体要点 2

---

## 代码结构

<单文件给成员职责表；多文件给文件树 + 职责表>

| 文件 / 函数 | 职责 |
|---|---|
| `run()` | 功能入口，被菜单动作调用 |
| ... | ... |

---

## 用到的 SD API
- `sd.getContext().getSDApplication()` — ...
- ...

---

## 扩展指南
1. 步骤 1
2. 步骤 2

---

## 已知约束
- 约束 1（如：仅在有打开的 package 时可用）
```

---

## 4. 代码质量基线（SD Python 踩坑总结）

写新代码时 **必须** 遵守：

| 问题 | 正确做法 |
|---|---|
| 导入 Qt 未做防护 | SD 16.0.1 用 `from PySide6 import ...`；需跨版本时 try PySide2 → except try PySide6 → 都失败则 `QtWidgets = None` 并打印日志 |
| QMenu / QAction 建完不保存引用 | 存到模块级变量/列表，防止被垃圾回收导致菜单失效 |
| `uninitializeSDPlugin()` 不清理 | 移除本插件加的菜单 + 断开信号 + 停止定时器/线程，最后引用置 `None` |
| 重复加载导致菜单重复 | 创建前遍历已有菜单做幂等判断 |
| `sd` / Qt API 裸调用 | 包 `try/except`，失败打印 `[MaxSDPlugin]` 日志，不让异常冒泡 |
| 拿 `main_win` 不判空 | `main_win = qt_ui.getMainWindow() if qt_ui else None`，为空优雅返回 |
| 操作 package / graph 不判空 | 取到的 `SDPackage` / `SDGraph` 先判 `None` 再用 |
| 路径硬编码 `"/"` / `"\\"` | 用 `os.path.join` / `pathlib.Path` |
| 含中文文件无编码声明 | 首行加 `# -*- coding: utf-8 -*-` |
| 在 UI 线程跑长任务卡死界面 | 大批处理给进度反馈 / 分批；必要时提示用户耗时 |
| 改了 .sbs 不保存/刷新 | 修改后按需调用保存（`SDPackage` 写回）并刷新视图 |
| `print` 调试信息无前缀 | 统一 `[MaxSDPlugin]` / `[MaxSDPlugin/<feature>]` 前缀，便于在 Console 过滤 |

---

## 5. 防回归：改动不得影响现有功能

> AI 在动任何文件前，**必须**先按下面检查一遍。

### 5.1 动各类符号前的必走检查

| 符号 / 类型 | 动它之前必验 | 工具 |
|---|---|---|
| 函数签名变动（加删参数 / 默认值 / 返回值） | 全工程搜调用点 | `grep_search` 函数名 / `vscode_listCodeUsages` |
| 对外入口 `initializeSDPlugin` / `uninitializeSDPlugin` / `run` / `show_window` | 全工程搜引用 + 确认菜单仍能挂上 | `grep_search` |
| 菜单字面量（`'MaxSDPlugin'` / 各动作中文名） | 查重复、查 README 是否同步 | `grep_search` |
| 模块级缓存引用（`_menu_ref` 等） | 确认 init / uninit 两端都改 | `grep_search` |
| 功能文件夹 / 模块名（新增、重命名、删除） | grep 全工程 import 与 README 引用 | `grep_search` |

### 5.2 几条硬线

- **不能"看起来多余"就删**：一个参数 / 一个 `if` / 一个菜单动作看不出用途，也要先全工程搜过才能动。
- **函数签名只能"添加可选参数"，不能"减参 / 去默认值"**；必须减参时同步改所有调用点并在说明里罗列。
- **不能随意重命名 / 移动公开函数与类**；不可避免时用 `vscode_renameSymbol` 走语义重命名，不走文本替换。
- **只改"你负责的那个文件"**；没要求就别顺手改其它文件的错别字 / 重排 import。
- **改完要在脑中走一遍**：「SD 加载插件 → 菜单出现 → 点动作 → 功能执行 → 卸载插件 → 菜单消失」。`get_errors` 0 错只证明能编译，不证明能点开。

### 5.3 安全演进模式（推荐默认用）

修改被多处引用的入口时优先**增量演进**：加新可选参数 / 新重载函数，旧入口保留并内部转调 → 调用点逐个迁移 → 确认无引用后再删旧的。

---

## 6. AI 自检清单（提交前对照）

声明"完成"之前必须确认：

- [ ] 新功能位于独立文件夹 `<feature_name>/`，含 `__init__.py`，根目录未新增业务 `.py`
- [ ] `initializeSDPlugin` / `uninitializeSDPlugin` 仅存在于 `MaxSDPlugin.py`，菜单注册唯一
- [ ] 新功能暴露了 `run()` / `show_window()` 等对外入口，并被入口文件挂到 `MaxSDPlugin` 菜单
- [ ] `uninitializeSDPlugin()` 已清理新加的菜单动作 / 信号 / 引用
- [ ] 新增功能子包无需动入口（`_reload_feature_modules()` 动态热重载全包，见 §1.6），只需在 `menu.py` 挂菜单
- [ ] 使用 PySide6（或保留双兼容写法）；菜单创建幂等；模块级保存了 QMenu/QAction 引用
- [ ] 所有 `sd` / Qt 调用包 `try/except`，日志带 `[MaxSDPlugin]` 前缀
- [ ] 含中文文件有 `# -*- coding: utf-8 -*-`
- [ ] 改过的任何对外函数/类都走了 §5.1 的「动它之前必验」
- [ ] `<feature_name>/README.md` 已按 §3 模板创建
- [ ] [MaxSDPlugins/README.md](MaxSDPlugins/README.md) 的菜单/功能/目录结构已同步
- [ ] 本目录 [README.md](README.md) 目录树（如有变动）已同步
- [ ] [MaxSDPlugins/ReleaseNote.md](MaxSDPlugins/ReleaseNote.md) 对应计划项已标记完成
- [ ] 已升 `__version__`（语义化）并在 ReleaseNote 顶部「更新记录」追加一行（日期+改动+影响范围+是否需重启 SD）
- [ ] 代码符合 §4 全部质量基线
- [ ] `Python Lint Check` 任务 / `get_errors` 无语法错误（`import sd` 等环境缺失告警可接受）
- [ ] 交付前 `grep_search` 验证「新功能中文名 / 新文件夹名 / 新菜单项」各至少在 README 命中一次

任一项未达成，视为未完成。

---

## 7. 参考实现对照表

需要模仿某种结构时，按类型对照最近的样板：

| 类型 | 参考文件 |
|---|---|
| 菜单插件入口 + 幂等创建 + 卸载清理（标杆） | [../03_OfficialExamples/OfficialExamples/PluginBasics.py](../03_OfficialExamples/OfficialExamples/PluginBasics.py) |
| 遍历 / 打印 SD 主菜单 | [../03_OfficialExamples/OfficialExamples/PrintSDMainMenu.py](../03_OfficialExamples/OfficialExamples/PrintSDMainMenu.py) |
| 多文件 / 带数据资源的内置插件结构 | [../03_OfficialExamples/OfficialSDInsertPlugins/custom_graph/](../03_OfficialExamples/OfficialSDInsertPlugins/custom_graph/) |
| PySide UI 窗口类 | [../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart2/mylib/window.py](../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart2/mylib/window.py) |
| 环境/版本检查（PySide 是否加载） | [../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart1/CheckPyside.py](../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart1/CheckPyside.py) |
| 视图布局操作 | [../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart1/ResetViewLayout.py](../01_BilibiliTutorial/Bilibili_HuangJuanLr/SubstanceDesignerPart1/ResetViewLayout.py) |
