# 曝光参数自动排序 (ExposeParameterAutoSorting)

按分组调整当前活动 Graph 的 INPUT PARAMETERS 顺序，并通过安全重排 SBS XML 保存结果。
入口位置：`MaxSDPlugin/Output/曝光参数/参数分组排序` 按钮。

---

## 功能概览
- 只扫描 `isConnectable() == False` 的 INPUT PARAMETERS，并按 Group 树状展示。
- 支持拖拽顶级分组调整组顺序，以及拖拽参数调整组内顺序或移入其他组。
- 支持按钮和 `Ctrl+↑` / `Ctrl+↓` 快速移动选中的分组或组内参数，并可通过“更改分组…”把参数移到已有组。
- 应用前保存当前 SBS 并创建时间戳备份，只在目标 INPUT PARAMETERS 的原 XML 槽位之间重排完整 `<paraminput>` 节点；改组参数会同步直接 `<group>` 与 metadata Group。
- INPUTS、OUTPUTS、其他 Graph 和 Explorer 中其他 Package 均不读取、不修改。
- 扫描后切换 Graph 或 SBS 会触发范围校验并中止操作。

---

## 代码结构

| 文件 / 函数 | 职责 |
|---|---|
| `__init__.py / show_window()` | 兼容入口，由曝光参数面板的排序按钮调用 |
| `sorting_window.py / ExposeParamSortingDialog` | 参数树、受约束拖拽、组内排序、参数改组、范围提示和应用确认 |
| `sorting_logic.py / collect_groups()` | 获取当前 Graph 的非连接型 INPUT PARAMETERS |
| `sorting_logic.py / get_graph_scope()` | 记录当前 SBS 路径、Package UID 和 Graph ID |
| `sorting_logic.py / _stage_reordered_xml()` | 在临时 SBS 中同步参数 Group、重排目标 Graph 的 `<paraminput>` 节点并验证 XML |
| `sorting_logic.py / apply_group_order()` | 保存、备份、卸载、原子替换、重新加载及失败恢复 |

---

## 用到的 SD API
- `QtForPythonUIMgr.getCurrentGraph()` — 通过 `sdcompat.get_current_graph()` 获取当前活动 Graph。
- `SDResource.getProperties(SDPropertyCategory.Input)` — 枚举输入类别属性。
- `SDProperty.isConnectable()` — 区分 INPUT PARAMETERS 与连接型 INPUTS。
- `SDResource.getPackage()` — 获取当前 Graph 所属 Package。
- `SDPackageMgr.getUserPackageFromFilePath()` — 校验目标 SBS 是当前已加载 User Package。
- `SDPackageMgr.savePackage()` — XML 修改前保存当前 Package。
- `SDPackageMgr.unloadUserPackage()` / `loadUserPackage()` — 文件替换前卸载并在完成后重新加载。

---

## 扩展指南
1. 新增参数筛选规则时，应在 `collect_param_snapshot()` 入口处理，不要让 INPUTS 进入 UI 或 XML 校验。
2. 新增 XML 操作时，只修改唯一匹配当前 Graph ID 的节点，并保留完整 `<paraminput>` 子树。
3. 修改 Package 生命周期时，必须保留临时文件验证、时间戳备份、原子替换和失败恢复。

---

## 已知约束
- 当前 Package 必须已经保存为 `.sbs` 文件。
- 排序会卸载并重新加载当前 Package，完成后需要在 Explorer 中重新打开原 Graph。
- XML 排序不支持 Ctrl+Z；操作前会自动创建备份。
- 运行时可见但未序列化到 `<paraminputs>` 的继承或动态参数会安全跳过。
