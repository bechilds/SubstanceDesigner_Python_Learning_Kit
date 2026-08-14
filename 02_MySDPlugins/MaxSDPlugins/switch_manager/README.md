# 开关管理工具 (Switch Manager)

创建 Boolean 输入参数，并将它批量设为参数或 Group 的显示开关。
菜单位置：`MaxSDPlugin/Edit/开关管理工具`。

---

## 功能概览
- 在当前 Graph 的 INPUT PARAMETERS 中创建 Boolean 参数，可选择初始值为 True 或 False，并将新参数放入指定的开关 Group。
- Group 控件与 Designer 的 Group 栏一致：可从当前 Graph 的现有 Group 中选择，也可直接输入新名称；新名称会在创建参数并归组后成为实际 Group。
- 点击“刷新”或“按 Group 刷新开关列表”时，工具先保存当前 Package，再从 SBS 重建 Group 选项；已删除或改名的旧 Group 不会残留在输入框中。
- 按 INPUT PARAMETERS / INPUTS 和 Group 展示参数。因部分 Designer 版本的 Graph API 不枚举 Input Color、Input Value 等连接型 INPUTS，工具会把当前已保存 SBS 的 `<paraminputs>` 合并到 API 结果中，并读取直接 `<group>` / `<visibleIf>` 字段。
- 参数树在 Visible If 后显示“当前数值”：Graph API 可枚举的参数显示运行时当前值，XML-only INPUTS 显示 SBS 中保存的默认值。
- Boolean、Float、Int、String 等标量参数可双击“当前数值”单元格编辑，再点击“应用数值修改”批量写回；Color、Vector、图像和 XML-only INPUTS 保持只读。
- 可用开关使用单选列表展示，只包含指定开关 Group 中的 Boolean 参数；其他 Group 的 Boolean 不会被当作开关。
- 勾选单个参数、整个 Group 或分类后，批量写入 `input["开关参数ID"]`；操作可用 Ctrl+Z 撤销。
- “清除 Visible If”可批量删除所有勾选参数当前的 Visible If，操作同样可用 Ctrl+Z 撤销。

---

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