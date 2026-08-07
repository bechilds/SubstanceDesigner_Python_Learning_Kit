# 自动添加曝光参数描述 (AutoAddExposeCommitToNode)

扫描当前 SBS 文件的所有 Graph，在使用曝光参数的节点下方 75 像素处创建或更新 Comment。
菜单位置：`MaxSDPlugin/Edit/AutoAddExposeCommitToNode`。

---

## 功能概览
- 遍历当前 Package 的全部 Graph 和节点属性函数，定位真正引用曝光参数的节点。
- “扫描预览”阶段严格只读，先列出 Graph、节点、节点属性、参数 ID/Label、已有 Comment、目标位置和拟执行操作。
- 选中计划项时显示最终拟写文本；只有勾选并点击“应用选中项”、再次确认后才修改 Graph。
- 列表上方可按节点名称、节点 ID、节点属性、曝光参数 ID、分组或显示名称实时搜索；空格分隔的多个关键词需要同时匹配。
- 选择扫描结果后可点击“查找节点”或双击表格行，在画布中定位对应节点；定位仅操作视图，不修改 Graph。
- 显示 Graph、参数、节点、Property Graph、Get Variable 和匹配引用的逐层统计，并保留 API 读取错误和未匹配变量诊断。
- Comment 内容使用曝光参数的分组和显示名称，每个参数单独一行；有分组时格式为 `分组|-参数`（如 `Base|-Color`），无分组时保留 `-参数`。
- 已有绑定到节点的 Comment 时，可选择覆盖原内容或追加新内容。
- Comment 通过 `sNewAsChild(node)` 绑定到节点，并使用相对坐标 `(0, 75)`，避免重复叠加节点的 Graph 绝对坐标而错位。
- 所有修改进入一个 Undo Group，可在 SD 中按 `Ctrl+Z` 一次撤销。

---

## 代码结构

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 菜单入口，显示覆盖/追加选项 |
| `collect_package_graphs()` | 枚举当前 SBS Package 中的全部 Graph |
| `collect_node_exposed_parameters()` | 反查节点属性函数引用的曝光参数名称 |
| `scan_package()` | 只读生成计划项、逐层统计和诊断，不调用任何写 API |
| `apply_comment_plans()` | 只应用用户勾选并确认的计划项 |
| `apply_comments()` | 兼容旧调用的入口；新 UI 不再使用 |

---

## 用到的 SD API
- `SDPackage.getChildrenResources(True)` - 枚举当前文件中的全部资源。
- `SDGraph.getPropertyAnnotationValueFromId()` - 读取曝光参数的 `group` 注解。
- `SDNode.getPropertyGraph()` - 获取节点属性上的函数图。
- `sdcompat.focus_node()` - 跨 SD13/14/16 在图视图中查找并定位扫描结果节点。
- `SDGraphObjectComment.sNewAsChild()` - 创建绑定到节点的 Comment。
- `SDGraphObject.setDescription()` / `setPosition()` - 写入描述与位置。
- `SDHistoryUtils.UndoGroup` - 将批量修改合并为一次撤销操作。

---

## 扩展指南
1. 如需改变垂直距离，可修改 `_COMMENT_OFFSET_Y`。
2. 如需改变 Comment 文本格式，可修改 `_comment_text()`。

---

## 已知约束
- 必须先打开当前 SBS 文件中的一个 Graph，插件据此确定要扫描的 Package。
- 仅处理节点属性函数中的 Get Variable 引用，不把未被节点使用的图输入参数写入 Comment。
- 参数没有 Group 或 Group 注解读取失败时，仅输出 `-参数`，不会添加空的分组前缀。
- SD13 的公开 Python 绑定没有 `SDGraphObjectComment`，因此创建 Comment 需要 SD14 或更高版本。
- 修复旧版本生成的错位 Comment 时，重新扫描后选择“覆盖原 Comment 内容”并应用，可修正位置且避免重复追加文本。
