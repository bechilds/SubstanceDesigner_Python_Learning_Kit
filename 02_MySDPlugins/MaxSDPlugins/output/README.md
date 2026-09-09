# 曝光参数 (Exposed Parameters)

> 当前开发工具版本：v0.21.2（`__init__.py/TOOL_VERSION`）；随插件 v0.25.0 升级。此版本号不代表 MG 已发布版本。

管理当前图的「已曝露输入参数」：按分组枚举和排序、标记未被节点引用的空参数、复制并创建真实的新参数、批量修改设置、缓存/导出、删除（取消曝露），以及检查画布损坏节点。
菜单位置：`MaxSDPlugin/Output/曝光参数`。

---

## 功能概览

### 使用流程

<whiteboard type="mermaid">
flowchart TD
    A[打开当前 Graph] --> B[刷新曝光参数与损坏节点列表]
    B --> C[勾选并核对参数或节点]
    C --> D{输入与目标确认无误?}
    D -- 否 --> B
    D -- 是 --> E[执行参数操作 或缓存 导出 加载]
    E --> F[核对 Graph 与结果文件 按需保存 SBS]
</whiteboard>


- **按分组列出**当前图（`getCurrentGraph()`）的已曝露参数，**只含「INPUT PARAMETERS」与「INPUTS」两类**（排除 `$outputsize` 等以 `$` 开头的内置基础参数），并按 SD 的分组（`group` 注解）保留层级。分类与 Group 节点支持三态勾选，选择或取消组会同步组内全部参数；也支持全选 / 全不选。
  - `prop.isConnectable()` 为 `True` → 归入 **INPUTS**（图像输入）；为 `False` → 归入 **INPUT PARAMETERS**（数值型参数）。
- **显示 Editor 类型**：在“引用状态”前显示参数的 `editor` 注解，例如 `Slider`、`Color`、`Angle`；没有该注解时留空。
- **标记空参数**：扫描当前 Graph 全部节点属性函数中的 Get Variable；没有被任何节点引用的已暴露参数在“引用状态”列标记为“未被节点引用”。
- **参数分组排序**：曝光参数区域内直接打开 ExposeParameterAutoSorting，按 Group 调整 INPUT PARAMETERS 顺序；排序包原公开入口继续保留供兼容调用。
- **缓存到当前目录**：把当前已曝露参数快照写到 `.sbs` 同目录的 `OutputData.json`。
- **导出 OutputData…**：把快照导出到用户选择的位置（JSON）。
- **复制勾选参数**：支持同时勾选一个或多个 INPUT PARAMETERS 参数。弹窗按行预览 `源 ID / 源 Label / 新 ID / 新 Label`，可逐行编辑，也可设置关键字批量替换新 ID、新 Label 或两者；确认后通过与 Designer 参数面板 `+` 对应的 `graph.newProperty()` 创建真实的新参数，再复制每个来源参数的类型、全部可读注解和 SD 原生当前值。整批创建放在一个 UndoGroup 中，可按 **Ctrl+Z** 一次撤销。图像 INPUTS 因属性类型本身可连接，不能强制复制到 INPUT PARAMETERS，失败项会单独汇总。
  - 注解复制会先读取新参数实际支持的注解，只复制源/目标交集；`min`、`max`、`editor` 等目标类型不支持的注解会进入警告汇总，不会因 `SDApiError.ItemNotFound` 中断整批创建。
  - `identifier / id / label` 属于副本自身的身份设置，不从源参数复制，避免在 `newProperty(new_id, ...)` 后又把新 ID 覆盖回旧 ID。其它 property metadata 会继承，新 Label 最后通过目标参数 metadata 写入。
- **批量替换参数设置**：勾选多个参数后打开独立表格窗口。表格提供逐行选择列，并为每个 Group 提供三态勾选项；选择或取消 Group 会同步组内全部参数，关键字预览和最终应用只处理当前勾选行。既可逐行修改，也可设置「作用字段 / 查找关键字 / 替换为 / 是否区分大小写」，点击“预览替换”先更新表格并显示命中数，确认后再统一应用。作用字段支持 `Label / Group / 当前值 / Label + Group`；标量值可编辑，向量、颜色和图像等复杂类型的当前值只读。整批操作包在一个 UndoGroup 中。
  - 可填写多个“排除 Group 关键字”（逗号、分号或换行分隔）；Group 命中任一关键字的参数整行不参与本次预览替换，结果栏显示排除行数。
  - Label、Group 和当前值逐字段独立写入；目标不支持某注解或 SD API 返回错误时只跳过该字段并汇总原因，其余字段和参数继续处理。
- **去除 Copy**：批量去除勾选参数 Label 和 ID 中独立的 `Copy`（不区分大小写，不会误伤 `Copyright` 等单词），并清理遗留空格、下划线和连字符。Label 可直接通过 metadata 修改；SDProperty ID 不可原地重命名，因此 ID 变化时会创建继承原设置/当前值的新参数、迁移全图 Get Variable 引用，再删除旧参数。目标 ID 冲突会跳过；迁移失败会恢复引用并清理新参数。整批操作包在一个 UndoGroup 中。
- **删除勾选项（取消曝露）**：对勾选参数取消曝露。
  - **先重置依赖该变量的节点参数**：曝露参数时 SD 会把节点参数变成「Get <变量名>」函数；删除前先缓存曝光参数的当前 `SDValue`，用 `SDNode.deletePropertyGraph(prop)` 移除函数，再通过 `SDNode.setPropertyValue(prop, value)` 把当前曝光值写成节点常量，避免节点回到旧默认值或留下悬空变量（否则会出现大量 `[WRN][Cooker]Empty variable` / `Some Get nodes don't have a variable name`）。变量名读自 Get 节点的 `__constant__` 属性。
  - 再调用 `graph.deleteProperty()` 删除图层级的输入属性。
  - 删除后再扫描全图一次，兜底重置仍残留的、变量名已变空的损坏 Get 函数。
  - 整个删除（重置 + 删除）包在同一个 `SDHistoryUtils.UndoGroup` 里，可在 SD 中按 **Ctrl+Z** 一次性撤销。
  - 删除前**自动备份**一份 OutputData 到 `.sbs` 同目录，便于回滚。
  - 操作前有二次确认对话框。
- **重置损坏函数**：勾选下方列表后只重置勾选项；**未勾选则处理全图**——把丢失曝光参数输入并出现 Empty variable 警告的 Get 函数重置回常量值。同样包 UndoGroup 可撤销。
- **画布损坏节点列表**：与已暴露参数区域使用独立标题和可拖动分隔器。只列出曝光参数输入已丢失、且对应节点属性没有非空输入值的节点；已经正确取得输入值（包括 `0` 和 `False`）时不再报告“参数输入丢失”，与 Designer 的警告逻辑保持一致。列表支持勾选、Goto 和删除。
- **加载历史…**：读取一个历史 `OutputData.json`，把其中记录的值**应用回当前图中仍然存在的同名参数**（`graph.setPropertyValue()`，同样包 UndoGroup 可撤销）。完成后弹窗汇总「已还原 / 已不存在无法还原 / 类型不支持」三类计数。

---

## 代码结构

```
output/
├── __init__.py                    # 暴露 show_window(main_win)
├── exposed_parameters_window.py   # QDialog UI：列表 + 勾选 + 各按钮
├── output_data.py                 # 数据层：枚举/分组/删除/应用 + OutputData 读写
└── README.md                      # 本文件
```

| 文件 / 函数 | 职责 |
|---|---|
| `output_data.get_current_graph()` | 取当前图 |
| `output_data.collect_exposed_parameters(graph)` | 枚举已暴露参数（排除基础参数）→ list[dict]，带 `category`/`group`/`editor`/`referenced` |
| `output_data.group_parameters(params)` | 组织成「分类 → 分组 → 参数」结构供 UI 渲染 |
| `output_data.duplicate_exposed_parameter(graph, source_id, new_id, new_label)` | 用 `newProperty` 创建真实副本，复制类型、注解和 SD 原生当前值 |
| `output_data.duplicate_exposed_parameters(graph, copies)` | 在一个 UndoGroup 中批量创建真实参数副本，返回成功/失败/注解警告汇总 |
| `output_data.update_exposed_parameter_settings(graph, updates)` | 批量写入 Label、Group 和受支持的标量当前值；包 UndoGroup |
| `output_data.remove_copy_from_parameters(graph, ids)` | 清理 Label/ID 的独立 Copy；ID 变化时迁移 Get Variable 引用并删除旧参数，失败时回滚 |
| `output_data.delete_exposed_parameters(graph, ids)` | 缓存曝光参数当前值，先 `deletePropertyGraph` 重置依赖节点参数并用 `setPropertyValue` 写回当前值，再 `deleteProperty` 取消暴露，删后再扫一遍兜底；包 UndoGroup，返回 (deleted, failed, reset) |
| `output_data.repair_broken_node_functions(graph)` | 扫描全图重置变量名已空的损坏 Get 函数，返回重置个数；包 UndoGroup |
| `output_data.collect_broken_nodes(graph)` | 只读列出 Get Variable 损坏且节点属性没有非空输入值的节点 |
| `output_data.goto_node(graph, id)` | 用 `SDUIMgr.focusGraphNode` 把视图居中到该节点 |
| `output_data.apply_output_data(graph, data)` | 把 OutputData 的值应用回现存参数，返回 {restored, missing, skipped} |
| `output_data.get_default_output_data_path(graph)` | 推算 `.sbs` 同目录的 `OutputData.json` 路径 |
| `output_data.build_output_data(graph, selected_ids)` | 构建 OutputData 快照字典 |
| `output_data.save_output_data / load_output_data` | OutputData JSON 读写 |
| `exposed_parameters_window.ExposedParametersDialog` | 对话框 UI 与交互（分组树） |
| `exposed_parameters_window.show_window(main_win)` | 功能入口，被菜单动作调用 |

OutputData JSON 结构：

```json
{
  "schema_version": "0.1.0",
  "exported_at": "2026-06-26T10:00:00",
  "package": "D:/.../Foo.sbs",
  "graph": "<graph identifier>",
  "exposed_parameters": [
    {
      "id": "...", "label": "...", "type": "...",
      "default": "...", "value": "...",
      "connectable": false, "category": "parameters", "group": "...", "editor": "Slider",
      "referenced": true, "selected": false
    }
  ]
}
```

---

## 用到的 SD API

- `sd.getContext().getSDApplication()` — 获取 SD 应用
- `app.getQtForPythonUIMgr().getCurrentGraph()` — 当前图
- `graph.getProperties(SDPropertyCategory.Input)` — 输入属性列表
- `prop.getId() / getLabel() / getType() / getDefaultValue() / isConnectable()` — 参数信息与「输入 vs 参数」判定
- `graph.getPropertyAnnotationValueFromId(prop, 'group' / 'editor')` — 读取分组和 Editor 类型
- `graph.getPropertyFromId(id, SDPropertyCategory.Input)` — 按 id 取属性
- `graph.newProperty(id, type, SDPropertyCategory.Input)` — 创建真实的新 INPUT PARAMETERS 参数
- `graph.getPropertyAnnotations()` / `setPropertyAnnotationValueFromId()` — 复制或修改 Label、Group、范围等参数注解
- `graph.getPropertyMetadataDictFromId()` / `SDMetadataDict.setPropertyValueFromId()` — 复制参数 metadata，并可靠写入新 Label / Group
- `graph.deleteProperty(prop)` — 取消曝露（删除输入属性）
- `node.getPropertyGraph(prop)` — 取控制某属性的函数图（无则 None），用于判断该参数是否被函数驱动
- `node.deletePropertyGraph(prop)` — 删除属性函数图并**恢复之前的常量值**（删除暴露参数前的重置手段）
- `node.getPropertyValue(prop)` — 读节点属性值（用于匹配 Get 节点引用的变量名）
- `graph.setPropertyValue(prop, value)` — 写回参数值（加载应用）
- `graph.getPropertyValue(prop)` — 读取来源参数的 SD 原生值（批量复制设置）
- `SDHistoryUtils.UndoGroup(name)` — 把破坏性操作包成可撤销事务
- `SDValueSerializer.sToString(value)` — 值转字符串（保存快照用）
- `app.getUIMgr().focusGraphNode(viewID, node)` — Goto 定位损坏节点（配合 getGraphViewIDCount/At）
- `graph.getPackage().getFilePath()` — 定位 `.sbs` 磁盘路径

---

## 扩展指南

1. **扩大可还原类型**：`output_data._build_sdvalue()` 目前只还原 `float / int / bool / string`。如需还原向量 / 颜色 / 枚举，在此按 `type` 构造对应的 `SDValue*`（注意 SD 无 `SDValueSerializer.sFromString`，需逐类型 `sNew`）。
2. **重新曝露已删除参数**：当前「加载」只还原仍存在参数的值，无法重建已删除的曝露参数（需重建节点函数绑定，公共 API 不直接支持）。若官方提供相应 API，可在 `apply_output_data()` 里补 missing 项的重建。
3. 新增 Output 下的其它功能时，复用 `output/` 包并在 `MaxSDPlugin.py` 的 `_create_output_category()` 里追加菜单动作。

---

## 已知约束

- 仅在有打开的图时可用；无当前图时按钮会提示。
- 列表**不含**内置基础参数（`$outputsize`/`$format`/`$pixelsize`/`$pixelratio`/`$tiling`/`$randomseed` 等）。
- “缓存到当前目录 / 删除前自动备份”要求 package 已保存到磁盘（能取到 `.sbs` 路径），否则提示先保存。
- **删除是破坏性操作**，但已包 UndoGroup（Ctrl+Z 可撤销）+ 删除前自动备份 + 二次确认。
- **加载只还原值**，不会重建已删除的曝露参数；复杂类型（向量/颜色/枚举）暂不自动还原，会在汇总里列为“跳过”。
- Adobe `APIException` 直接继承 `BaseException`；本模块使用专用异常元组捕获 SD API 错误，避免 `ItemNotFound` 穿透到 Designer Python 回调。

## 框架升级说明

本工具公开入口和原有参数保持不变。窗口统一由 `shared.lifecycle` 管理：重复打开复用、关闭释放；插件重载会关闭窗口。未保存的界面配置请先处理。升级包含入口变更，需要重启 Designer 一次。离线回归不替代目标 Designer 中的实际功能和撤销验证。

## 更新日志

- 2026-09-04 · v0.21.2 · 接入统一窗口生命周期 · 本工具入口与错误处理 · 随插件 v0.25.0 升级需重启 SD
