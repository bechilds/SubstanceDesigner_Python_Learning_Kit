# 曝光参数 (Exposed Parameters)

管理当前图的「已曝露输入参数」：按分组枚举、勾选、把快照缓存/导出为 `OutputData.json`、删除（取消曝露），以及加载历史 OutputData 把值应用回当前图。
菜单位置：`MaxSDPlugin/Output/曝光参数`。

---

## 功能概览

- **按分组列出**当前图（`getCurrentGraph()`）的已曝露参数，**只含「INPUT PARAMETERS」与「INPUTS」两类**（排除 `$outputsize` 等以 `$` 开头的内置基础参数），并按 SD 的分组（`group` 注解）保留层级。支持勾选 / 全选 / 全不选。
  - `prop.isConnectable()` 为 `True` → 归入 **INPUTS**（图像输入）；为 `False` → 归入 **INPUT PARAMETERS**（数值型参数）。
- **缓存到当前目录**：把当前已曝露参数快照写到 `.sbs` 同目录的 `OutputData.json`。
- **导出 OutputData…**：把快照导出到用户选择的位置（JSON）。
- **删除勾选项（取消曝露）**：对勾选参数取消曝露。
  - **先重置依赖该变量的节点参数**：曝露参数时 SD 会把节点参数变成「Get <变量名>」函数；删除前先用 `SDNode.deletePropertyGraph(prop)` 把这些节点参数恢复成常量值，避免删除后留下悬空变量（否则会出现大量 `[WRN][Cooker]Empty variable` / `Some Get nodes don't have a variable name`）。变量名读自 Get 节点的 `__constant__` 属性。
  - 再调用 `graph.deleteProperty()` 删除图层级的输入属性。
  - 删除后再扫描全图一次，兜底重置仍残留的、变量名已变空的损坏 Get 函数。
  - 整个删除（重置 + 删除）包在同一个 `SDHistoryUtils.UndoGroup` 里，可在 SD 中按 **Ctrl+Z** 一次性撤销。
  - 删除前**自动备份**一份 OutputData 到 `.sbs` 同目录，便于回滚。
  - 操作前有二次确认对话框。
- **修复损坏函数**：扫描当前图，把之前删除暴露参数时残留的、变量名为空的 Get 函数重置回常量值（修复已经损坏的图，无需再次删除）。同样包 UndoGroup 可撤销。
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
| `output_data.collect_exposed_parameters(graph)` | 枚举已暴露参数（排除基础参数）→ list[dict]，带 `category`/`group` |
| `output_data.group_parameters(params)` | 组织成「分类 → 分组 → 参数」结构供 UI 渲染 |
| `output_data.delete_exposed_parameters(graph, ids)` | 先 `deletePropertyGraph` 重置依赖节点参数，再 `deleteProperty` 取消暴露，删后再扫一遍兜底；包 UndoGroup，返回 (deleted, failed, reset) |
| `output_data.repair_broken_node_functions(graph)` | 扫描全图重置变量名已空的损坏 Get 函数，返回重置个数；包 UndoGroup |
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
      "connectable": false, "category": "parameters", "group": "...",
      "selected": false
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
- `graph.getPropertyAnnotationValueFromId(prop, 'group')` — 读取分组
- `graph.getPropertyFromId(id, SDPropertyCategory.Input)` — 按 id 取属性
- `graph.deleteProperty(prop)` — 取消曝露（删除输入属性）
- `node.getPropertyGraph(prop)` — 取控制某属性的函数图（无则 None），用于判断该参数是否被函数驱动
- `node.deletePropertyGraph(prop)` — 删除属性函数图并**恢复之前的常量值**（删除暴露参数前的重置手段）
- `node.getPropertyValue(prop)` — 读节点属性值（用于匹配 Get 节点引用的变量名）
- `graph.setPropertyValue(prop, value)` — 写回参数值（加载应用）
- `SDHistoryUtils.UndoGroup(name)` — 把破坏性操作包成可撤销事务
- `SDValueSerializer.sToString(value)` — 值转字符串（保存快照用）
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
