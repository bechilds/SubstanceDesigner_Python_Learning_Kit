# Publish Checker（发布检查）

> 当前开发工具版本：v0.4.9（`__init__.py/TOOL_VERSION`）；随插件 v0.25.0 升级。此版本号不代表 MG 已发布版本。

发布 `.sbsar` 前，扫描当前图里**可能在 publish/cook 时产生警告**的节点 + package 依赖，列成清单，便于发布前自查。
菜单位置：`MaxSDPlugin/Debug/Publish Checker`。

---

## 功能概览

### 使用流程

<whiteboard type="mermaid">
flowchart TD
    A[打开当前 Graph] --> B[扫描发布警告与依赖]
    B --> C[按类别核对节点列表]
    C --> D{输入与目标确认无误?}
    D -- 否 --> B
    D -- 是 --> E[定位或确认后删除 清理 也可试发布]
    E --> F[检查 Graph 和 SD 日志 保存需要的修改]
</whiteboard>


打开后自动扫描 `getCurrentGraph()` 返回的当前图，列出常见会导致 cook 警告的节点：

| 类别 | 含义 | 对应 SD 日志 |
|---|---|---|
| 损坏函数 | 节点参数被函数图驱动，但 Get 节点变量名为空 | `Empty variable` / `Some Get nodes don't have a variable name` |
| 缺失资源 | bitmap / svg 节点未引用资源，或引用的外部文件不存在 | 资源缺失 / 输出为空 |
| 缺失依赖包 | package 引用的其他 .sbs 找不到（复制别的图常带来） | `Cannot publish package, dependencies cannot be found` |
| 可清理(未使用) | 未连到任何 output，Clean graph(s) 会删除 | 节点被清理 |
| 未连接输出 | 标记为 output 的节点没有输入连线 | 输出空图 |
| 悬挂节点 | 既不是 output、又无任何下游连接的孤立节点 | 节点被忽略 |

- **重新扫描**：再次扫描当前图刷新清单。
- **类别筛选**：顶部每个类别一个复选框，勾掉即在列表中隐藏该类（筛选用缓存结果，不重扫）。
- **Goto 定位**：右键列表行 → 「Goto（在图中定位）」，或双击该行，把图视图居中到该节点（`SDUIMgr.focusGraphNode`）。
- **试发布到临时 .sbsar**：用 `SDSBSARExporter` 把当前 package 导出到系统临时目录，验证能否成功发布；逐节点的详细警告由 C++ cooker 打印在 SD 自带日志面板（Python 无法完整截获）。

---

## 代码结构

```
debug/
├── __init__.py             # 暴露 show_window(main_win)
├── check_dependencies.py   # 数据层(扫描/试发布) + QDialog UI
└── README.md               # 本文件
```

| 函数 / 类 | 职责 |
|---|---|
| `get_current_graph()` | 取当前图 |
| `scan_warnings(graph)` | 扫描全图，返回 [(类别, 节点描述, 说明, 节点id), ...] |
| `goto_node(graph, id)` | 用 `SDUIMgr.focusGraphNode` 把视图居中到该节点 |
| `test_publish(graph)` | 导出临时 .sbsar 试发布，返回 (ok, 信息) |
| `CheckDependenciesDialog` | 对话框 UI：类别筛选 + 警告表 + 右键 Goto + 重新扫描 / 试发布 |
| `show_window(main_win)` | 功能入口，被菜单动作调用 |

---

## 用到的 SD API

- `app.getQtForPythonUIMgr().getCurrentGraph()` — 当前图
- `graph.getNodes() / getOutputNodes()` — 节点与输出节点
- `node.getProperties(SDPropertyCategory.Input/Output)` + `getPropertyConnections(prop)` — 连线判断
- `node.getPropertyGraph(prop)` — 取参数函数图，检测空变量 Get 节点
- `sdcompat.focus_node(graph, node_id)` — Goto 定位居中
- `node.getReferencedResource()` + `res.getFilePath()` — bitmap/svg 资源缺失判断
- `SDSBSARExporter.sNew().exportPackageToSBSAR(pkg, path)` — 试发布 .sbsar

---

## 已知约束

- 仅在有打开的图时可用；无当前图时按钮会提示。
- 试发布的逐节点警告无法在 Python 内完整截获，需配合 SD 日志面板查看。
- 扫描和定位为只读；删除节点与清理 Graph 会修改当前图，执行前需要确认，可尝试 Ctrl+Z 撤销。试发布会覆盖系统临时目录中的固定 `maxsd_check_dependencies.sbsar`。
- 切换 Graph 后请先重新扫描，勿直接使用旧列表执行删除。

## 框架升级说明

本工具公开入口和原有参数保持不变。窗口统一由 `shared.lifecycle` 管理：重复打开复用、关闭释放；插件重载会关闭窗口。未保存的界面配置请先处理。升级包含入口变更，需要重启 Designer 一次。离线回归不替代目标 Designer 中的实际功能和撤销验证。

## 更新日志

- 2026-09-04 · v0.4.9 · 接入统一窗口生命周期；删除/清理增加确认，右键先选中目标行 · 本工具入口与错误处理 · 随插件 v0.25.0 升级需重启 SD
