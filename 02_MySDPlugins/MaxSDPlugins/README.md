# MaxSDPlugins

面向 Substance Designer 13 与 16 的制作辅助插件。所有工具统一挂载在 `MaxSDPlugin` 顶级菜单下。

## 菜单

| 菜单 | 功能 |
|---|---|
| `Output/曝光参数` | 管理、排序当前 Graph 的已暴露参数，标记未被节点引用的空参数，并修复真正丢失输入的节点 |
| `Output/预设效果找回` | 导入旧 `.sbsprs`，按当前 Identifier 重映射，并在当前 Graph 的 Presets 中新建或覆盖预设 |
| `Output/BatchMergeTexChannel` | 按文件名关键字分组贴图，通过处理 SBS 批量合并通道并导出 |
| `Edit/FrameColorModify` | 汇总当前画布 Frame，并统一修改颜色与透明度 |
| `Edit/AutoAddExposeCommitToNode` | 为当前 SBS 文件中使用曝光参数的节点创建或更新描述 Comment，并按 `分组|-参数` 写入参数名称 |
| `Edit/开关管理工具` | 在指定开关 Group 创建 Boolean 参数，通过组内开关列表批量设置参数或 Group 的 Visible If |
| `File/SaveWithResrouce` | 保存 SBS 副本并收集非官方、非团队库的外部文件 |
| `Debug/Publish Checker` | 检查发布依赖、资源、悬挂节点和未连接输出 |
| `Analysis/SBSFileRepoter` | 审计当前 Graph 的静态复杂度、最坏分支和文件健康，并保存报告截图 |
| `OutputTools/输出脚本` | 将选定功能打包成独立脚本，或按 `LG_MaxSD_*` 约定输出到自定义 MG MaxSD 目录 |

## BatchMergeTexChannel 工作流

1. 选择输入目录、输出目录和处理 SBS，设置五类贴图的文件名关键字。
2. 分别为最终输出的 Channel R/G/B/A 选择一个来源；每组可选择 ColorMap R/G/B/A 或 GrayMap01-04。
3. 在列表中核对文件组、缺失或重复输入、输出路径，只勾选确认无误的组。
4. 点击“开始批处理”，工具使用临时 SBS 副本逐组计算并导出，不修改源贴图和插件处理资源。

窗口顶部会显示“工具功能正常/异常”。只有随附 SBS 的 5 个贴图输入、4 组共 32 个互斥通道开关和 `output` 完整一致时，才会开放扫描和批处理；完整接口和命名示例见 [batch_merge_tex_channel/README.md](batch_merge_tex_channel/README.md)。

## 曝光参数分组排序工作流

1. 打开 `Output/曝光参数`，点击“参数分组排序”；排序树只收集非连接型 INPUT PARAMETERS。
2. 拖拽顶级 Group 调整分组顺序；拖拽参数调整组内顺序，或把参数拖入其他 Group。选中项目后也可使用按钮或 `Ctrl+↑` / `Ctrl+↓` 快速移动。
3. 选中参数后可点击“更改分组…”选择已有目标 Group，并在确认框核对唯一目标 SBS 路径和 Graph ID。
4. 应用后工具保存并备份当前 SBS，按树中顺序重排目标 Graph 的 `<paraminputs>`，同步参数 Group，再重新加载 Package。

INPUTS、OUTPUTS、同一 SBS 的其他 Graph，以及 Explorer 中其他 Package 均不参与处理。完整安全约束见 [expose_param_sorting/README.md](expose_param_sorting/README.md)。

## 开关管理工作流

1. 打开 `Edit/开关管理工具`，从可编辑 Group 下拉框选择现有组或输入新组，再输入参数 ID、Label 并选择 True/False 初始值，创建归入该组的 Boolean 参数。
2. 工具以列表展示当前开关 Group 内的 Boolean 参数；其他 Group 的 Boolean 不会进入开关列表。
3. 在 INPUT PARAMETERS / INPUTS 分组树中查看每项当前的 Visible If 与当前数值；双击受支持的标量当前值可编辑，再点击“应用数值修改”批量写回。工具会合并当前已保存 SBS 的 `<paraminputs>`，因此 Graph API 未枚举的 Input Color、Input Value 等连接型 INPUTS 也会列出。
4. 勾选单个参数或整个 Group 后，可从开关列表选择一项并写入 `input["开关参数ID"]`，也可点击“清除 Visible If”批量删除现有条件。

创建和批量设置均在 UndoGroup 中执行，可在 Designer 中按 Ctrl+Z 撤销。完整说明见 [switch_manager/README.md](switch_manager/README.md)。

## 预设效果找回工作流

1. 打开需要恢复效果的 Graph，再进入 `Output/预设效果找回` 并导入旧 `.sbsprs`。
2. 核对当前 SBS/Graph、源预设和参数映射；工具用旧预设参数名匹配当前参数 Identifier，不依赖已经变化的 Label。
3. 参数列表会实时显示导入总数、自动/手动匹配数、未匹配数，以及每项的目标 Editor；可为未匹配项手动选择目标。
4. 输入目标 Preset 名称并执行：名称不存在时新建，存在时确认后完整覆盖；完成后保存当前 SBS。

工具不会修改导入的 `.sbsprs`。参数值会结合当前目标的底层类型与 Editor（Toggle、Dropdown、Color、Position、Angle/Slider）转换后，通过 Designer Graph Preset API 写入 `INPUT PARAMETERS > Presets`。完整说明见 [preset_recovery/README.md](preset_recovery/README.md)。

## 目录

```text
MaxSDPlugins/
├── MaxSDPlugin.py
├── menu.py
├── sdcompat.py
├── output/
├── preset_recovery/
├── batch_merge_tex_channel/
├── BatchMergeTexChannel.sbs
├── frame_color_modify/
├── auto_add_expose_comment/
├── switch_manager/
├── expose_param_sorting/
├── save_with_resource/
├── debug/
├── sbs_file_reporter/
└── output_tools/
```

跨版本差异集中在 `sdcompat.py`。功能模块不直接依赖版本特定的 UI 管理器、`QAction` 位置或 `exec/exec_` 名称。

## OutputTools 输出到 MG

1. 在功能树勾选要集成的模块；有关联的 logic/window 模块应一起勾选。
2. 点击“输出到 MG...”，选择任意 MaxSD 根目录。若环境变量 `LGPublicMGEnv` 可用，会默认定位到团队工具包的 `Scriptlibrary/substance/sdesigner/MaxSD`。
3. 工具将 `LG_MaxSD_sdcompat.py` 写到所选根目录，并把 `LG_MaxSD_*.py` 写入对应分类子目录；同名模块会自动加分类前缀。
4. 根据实际功能入口编写或更新 `*_Start.py`，并在 MG 的 `LG_Tool.py` 中注册菜单。OutputTools 不自动修改宿主菜单文件。