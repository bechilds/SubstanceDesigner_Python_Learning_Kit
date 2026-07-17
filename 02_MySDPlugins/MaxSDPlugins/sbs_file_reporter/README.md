# SBS 复杂度审计器 (SBSFileRepoter)

在发布 SBSAR 前，对当前 Graph 做静态复杂度评分并列出高成本节点与结构风险。
菜单位置：`MaxSDPlugin/Analysis/SBSFileRepoter`。

---

## 功能概览
- 从 Published Output 反向遍历，只统计参与最终输出的节点。
- 同时显示当前 Switch 路径与所有潜在分支的复杂度分数。
- 按节点类型、有效分辨率、关键参数和输出数量估算静态成本。
- 顶部固定展示评分公式、统计范围、分支规则和等级阈值，评分结果单独突出显示。
- 成本列表只展示规则分类、基础权重、实际计分依据与最终得分；估算尺寸会明确标记。
- 列出 4K 节点、Graph Instance、Pixel Processor 和疑似重复昂贵计算。
- 将节点/Ghost、依赖和 Resource 丢失纳入文件风险分；Designer 安装自带的 `resources/packages` 和 `D:\LG_SDNodes` 视为可信目录。
- 评分按 Low 白色、Medium 绿色、High 红色、Very High 紫色显示。
- 评分结果首行显示当前 `.sbs` 文件名；未保存的 Package 明确显示为未保存文件。
- 成本列表上方以固定区间直方图展示节点最终权重分布和各区间节点数量。
- 支持双击或点击按钮定位高成本节点，并可在确认预警后发布 SBSAR。

---

## 代码结构

```text
sbs_file_reporter/
├── __init__.py
├── reporter_logic.py
└── reporter_window.py
```

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 菜单入口，打开并保活报告窗口 |
| `analyze_graph()` | 反向遍历并生成可供 UI 使用的报告字典 |
| `_reachable_nodes()` | 分别计算 Current 与 Potential 可达节点 |
| `_score_node()` | 计算类型、像素、参数和输出数量综合分数 |
| `_score_histogram()` | 按 `0-0.5 / 0.5-1 / 1-3 / 3-8 / 8+` 聚合节点最终得分 |
| `_collect_file_risks()` | 扫描丢失内容与非标准本地路径并累计文件风险分 |

---

## 用到的 SD API
- `QtForPythonUIMgr.getCurrentGraph()` - 通过 `sdcompat.get_current_graph()` 获取当前 Graph。
- `SDGraph.getOutputNodes()` - 获取 Published Output，作为反向遍历起点。
- `SDNode.getPropertyConnections()` - 沿输入连线找到上游节点。
- `SDNode.getPropertyValueFromId()` - 读取输出尺寸和关键参数。
- `SDSBSARExporter.exportPackageToSBSAR()` - 用户确认后发布 SBSAR。

---

## 扩展指南
1. 用团队现有的 20-50 个 Graph 校准 `reporter_logic.py` 中的 `_WEIGHTS` 与等级阈值。
2. 新增节点动态参数时，在 `_PARAMETER_HINTS` 中登记稳定的参数 Identifier 和基准值。
3. 团队标准库迁移时同步修改 `_APPROVED_LIBRARY_ROOT`。
4. 只有确认目标 SD 版本能可靠清缓存并等待计算完成后，才添加整图 wall-clock 测量。

---

## 已知约束
- 分数是项目内部复杂度单位，不代表毫秒；默认权重需要用真实项目数据校准。
- Graph Instance 当前使用固定风险权重，不递归分析依赖 Graph。
- `SDValueInt2` 按 `x/y` 成员读取；只有继承方式明确时才使用计算尺寸，动态或不可读尺寸按 1024 x 1024 基准估算并提示。
- Graph Instance 仅在节点实际引用 Graph 资源时识别，不再依据公共 Definition ID 前缀猜测。
- 文件风险权重：丢失节点/依赖 `+60`，丢失 Resource `+40`，可信目录外依赖 `+15`、Resource `+10`；风险分同时加入 Current 与 Potential 总分。
- 官方节点根目录从当前 `sd.__file__` 动态反推，兼容不同盘符、Adobe/Allegorithmic 安装目录及 SD13/SD16。
- `sbs://`、`pkg://` 属于内置协议，不做本地路径风险检查。
- 不汇总节点 Timing；整图重算耗时目前显示为未测量。