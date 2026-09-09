# 开关管理工具 (Switch Manager)

# 项目概览

> 当前开发工具版本：v0.19.8（`__init__.py/TOOL_VERSION`）；随插件 v0.25.2 升级。此版本号不代表 MG 已发布版本。

创建 Boolean 输入参数，并将它批量设为参数或 Group 的显示开关。
菜单位置：`MaxSDPlugin/Edit/开关管理工具`。

---

# 功能说明与使用流程

## 创建开关与批量控制显示

### 使用流程

<whiteboard type="mermaid">
flowchart TD
    A[打开当前 Graph] --> B[选择开关 Group 并刷新参数树]
    B --> C[配置 Boolean 勾选目标或编辑标量值]
    C --> D{输入与目标确认无误?}
    D -- 否 --> B
    D -- 是 --> G{活动 Graph 与扫描范围一致?}
    G -- 否或无法读取 --> B
    G -- 是 --> E[创建开关 应用数值或写入清除 Visible If]
    E --> F[核对参数面板 按需保存 SBS]
</whiteboard>

- 扫描时记录 Package UID、SBS 路径与 Graph Identifier。创建、补齐控件、应用数值及写入/清除 Visible If 前检查范围；切换 Graph/SBS 或范围不可读时中止，不写参数、不触发后续保存。请刷新后重新勾选；有确认框的操作返回后再次校验。
- 在当前 Graph 的 INPUT PARAMETERS 中创建 Boolean 参数，可选择初始值为 True 或 False，并将新参数放入指定的开关 Group。创建时通过原生 `editor` 注解显式写入 `buttons` 并读回检查，避免发布 SBSAR 时缺少 `togglebutton`。控件写入失败会清理本次新参数并报告错误；清理失败时明确提示撤销或删除该参数。
- Group 控件与 Designer 的 Group 栏一致：可从当前 Graph 的现有 Group 中选择，也可直接输入新名称；新名称会在创建参数并归组后成为实际 Group。
- 点击“刷新”或“按 Group 刷新开关列表”时，工具先保存当前 Package，再从 SBS 重建 Group 选项；已删除或改名的旧 Group 不会残留在输入框中。
- 按 INPUT PARAMETERS / INPUTS 和 Group 展示参数。因部分 Designer 版本的 Graph API 不枚举 Input Color、Input Value 等连接型 INPUTS，工具会把当前已保存 SBS 的 `<paraminputs>` 合并到 API 结果中，并读取直接 `<group>` / `<visibleIf>` 字段。
- 参数树在 Visible If 后显示“当前数值”：Graph API 可枚举的参数显示运行时当前值，XML-only INPUTS 显示 SBS 中保存的默认值。
- Boolean、Float、Int、String 等标量参数可双击“当前数值”单元格编辑，再点击“应用数值修改”批量写回；Color、Vector、图像和 XML-only INPUTS 保持只读。
- 可用开关使用单选列表展示，只包含指定开关 Group 中的 Boolean 参数；其他 Group 的 Boolean 不会被当作开关。
- 勾选单个参数、整个 Group 或分类后，批量写入 `input["开关参数ID"]`；操作可用 Ctrl+Z 撤销。
- “清除 Visible If”可批量删除所有勾选参数当前的 Visible If，操作同样可用 Ctrl+Z 撤销。

---

## 补齐已有开关的按钮控件

入口：`MaxSDPlugin/Edit/开关管理工具` → 选择“开关 Group” → “补齐本组开关控件”。用于修复旧版插件创建的 Boolean 参数缺少按钮控件声明的问题。

<whiteboard type="mermaid">
flowchart TD
    A[打开目标 Graph] --> B[选择开关 Group]
    B --> C[核对 Group 后点击补齐本组开关控件]
    C --> D{组内非连接型 Boolean 的 editor 是否为空?}
    D -- 否 --> E[保留原控件]
    D -- 是 --> F[写入 buttons 并读回验证]
    F --> G{读回是否一致?}
    G -- 否 --> H[报告失败参数]
    G -- 是 --> I[报告补齐参数]
    E --> J[核对结果 保存 SBS 并重新发布 SBSAR]
    I --> J
    H --> J
</whiteboard>

| 参数 | 作用、范围与默认行为 | 输出影响、约束与撤销 |
|---|---|---|
| 开关 Group | 非空组名，使用上方当前选择；按去除首尾空格后的组名精确匹配 | 只处理当前 Graph 的该组；已有 editor、非 Boolean、连接型输入和其他组保持不变；可 Ctrl+Z 撤销 |

输出：显示补齐、保留和失败数量，以及补齐/失败参数 ID。只修改内存中的控件注解，不改变参数值、Identifier、Group、Visible If 或节点连接；不会自动保存或发布，也不直接编辑 SBS XML。完成后手动保存 SBS，再重新发布 SBSAR。批量失败按参数报告，已成功项仍可撤销。

# 安装与使用

使用现有插件安装方式。更新后执行 Plugin Manager 的 Unload → Load，打开开关管理工具；旧参数选择对应 Group 后补齐，新建参数自动写入按钮控件。无需安装额外依赖或复制外部资源。

# 技术与兼容性

目标为 Designer 16.0.1，兼容目标为 SD13；通过两版已有的 `setPropertyAnnotationValueFromId(prop, "editor", SDValueString.sNew("buttons"))` 写入，并读回验证。依据为 Adobe 随安装提供的 `sample_sbs_graph_inputs.py` 和 `test_write_content.py` 中的 editor 用法和 buttons 候选。此修复不添加新版本专属 API。

离线回归覆盖创建、写入失败与静默失败回滚、修复范围、保留既有控件和值及重复执行。使用用户 SBS 的临时副本补齐 buttons 后，经本机 Adobe sbscooker 编译，确认 01–12 均输出 togglebutton；这项检查不替代 Designer 内 API、保存和加载/卸载验证。

## 代码结构

```text
switch_manager/
├── __init__.py
├── logic.py
├── window.py
└── README.md
```

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 功能入口，由菜单动作调用 |
| `logic.collect_parameters()` | 合并 Graph API 与已保存 SBS XML，收集完整参数分类、Group 与 Visible If |
| `logic.collect_group_names()` | 按当前顺序收集现有 Group，供可编辑下拉框选择 |
| `logic.parameter_value_text()` | 格式化 Boolean、数值与 XML 默认值供参数树展示 |
| `logic.update_parameter_values()` | 批量解析并写回受支持的标量当前值 |
| `logic.clear_visible_if()` | 批量清空勾选参数的 Visible If |
| `logic.collect_switches()` | 筛选指定开关 Group 内的 Boolean 参数 |
| `logic.create_boolean_switch()` | 在指定 Group 创建指定 True/False 初始值的 Boolean 输入参数 |
| `logic.assign_switch()` | 批量写入 Visible If 表达式 |
| `SwitchManagerDialog` | 创建开关、选择目标和显示执行结果 |

---

## 用到的 SD API
- `SDGraph.newProperty()` - 在 INPUT PARAMETERS 中创建 Boolean 参数。
- `SDGraph.getProperties()` - 枚举 INPUT PARAMETERS 与 INPUTS。
- `SDGraph.getPropertyAnnotations()` - 探测当前版本支持的 Visible If 注解 ID。
- `SDGraph.setPropertyAnnotationValueFromId()` - 写入 Visible If 表达式。
- `SDGraph.getPropertyMetadataDictFromId()` - 兼容从参数 metadata 读取和写入设置。
- `SDHistoryUtils.UndoGroup` - 将创建或批量设置合并成一次撤销操作。
- `xml.etree.ElementTree` - 只读解析当前已保存 SBS，补齐 API 未枚举的 INPUTS、Group 与 Visible If。

---

## 扩展指南
1. 如需组合已有 Visible If 条件，在 `logic.assign_switch()` 中增加“覆盖 / 与 / 或”模式，并在应用确认框显示最终表达式。
2. 如新 Designer 版本调整设置 ID，在 `_VISIBLE_IF_CANDIDATES` 中添加候选；代码仍会优先探测属性实际提供的 ID。

---

## 已知约束
- 仅操作当前活动 Graph，且目标必须属于 INPUT PARAMETERS 或 INPUTS。
- 开关 Group 不能为空；创建与应用使用同一个 Group 输入，只有该组内的 Boolean 参数可被选择。
- XML 补充列表依赖当前 Package 已保存到磁盘；未保存的新 Graph 只能显示 Graph API 当前可枚举的参数。
- 刷新 Group 会保存当前 Package，以便 Designer 内刚修改的 Group 写入 SBS 后立即可读。
- 当前值文本修改仅支持 Boolean、Float、Int、String 标量；复杂类型不可编辑。
- 批量应用会覆盖目标当前的 Visible If；执行前会确认，执行后可按 Ctrl+Z 撤销。
- SD API 只能在 Substance Designer 进程内完成运行验证。

### 框架升级说明

本工具公开入口和原有参数保持不变。窗口统一由 `shared.lifecycle` 管理：重复打开复用、关闭释放；插件重载会关闭窗口。未保存的界面配置请先处理。升级包含入口变更，需要重启 Designer 一次。离线回归不替代目标 Designer 中的实际功能和撤销验证。

# 发布与更新规则

本次为开发修复，工具 v0.19.8、插件 v0.25.2，未发布 MG。功能模块可热重载；本次入口仅同步回退版本号，其生效需重启 Designer。验收时新建 True/False 开关，补齐旧组，保存后检查 defaultWidget/name=buttons，并验证发布后 inputgui/widget=togglebutton；同时检查已有开关、Ctrl+Z 和加载/卸载。SD13/16 实机验收及 Unity 验证尚未执行。

## 本次修复验证与安装

目标 Designer 16.0.1，兼容目标 SD13；未新增依赖或外部资源。更新插件文件后 Unload→Load 生效；入口回退版本需重启。离线回归已覆盖本次失败场景；仍需在 Designer 验证加载/卸载、对应工具操作及撤销或文件副本，尚未执行实机验收或 MG 发布。

# 更新日志

- 2026-09-09 · v0.19.8 · 阻止扫描后切换 Graph 或 SBS 的写操作，确认弹窗返回后复查范围 · 本工具数据安全边界 · 功能可 Unload→Load，入口回退版本需重启

- 2026-09-08 · v0.19.7 · 新建开关显式设置并验证 buttons；增加本组空控件补齐 · 当前 Graph 的 Boolean 控件注解 · 功能可 Unload→Load，入口回退版本需重启

- 2026-09-04 · v0.19.6 · 接入统一窗口生命周期 · 本工具入口与错误处理 · 随插件 v0.25.0 升级需重启 SD
