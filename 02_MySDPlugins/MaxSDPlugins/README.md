# MaxSDPlugins

面向 Substance Designer 13 与 16 的制作辅助插件。所有工具统一挂载在 `MaxSDPlugin` 顶级菜单下。

## 菜单

| 菜单 | 功能 |
|---|---|
| `Output/曝光参数` | 管理当前 Graph 的已暴露参数，批量创建并按关键字命名参数副本，通过独立窗口批量修改设置，修复丢失输入的参数节点 |
| `Output/BatchMergeTexChannel` | 按文件名关键字分组贴图，通过处理 SBS 批量合并通道并导出 |
| `Edit/FrameColorModify` | 汇总当前画布 Frame，并统一修改颜色与透明度 |
| `Edit/AutoAddExposeCommitToNode` | 为当前 SBS 文件中使用曝光参数的节点创建或更新描述 Comment |
| `File/SaveWithResrouce` | 保存 SBS 副本并收集非官方、非团队库的外部文件 |
| `Debug/Publish Checker` | 检查发布依赖、资源、悬挂节点和未连接输出 |
| `Analysis/SBSFileRepoter` | 审计当前 Graph 的静态复杂度、潜在分支和高成本节点 |
| `OutputTools/输出脚本` | 将选定功能打包成可集成的独立 Python 脚本 |

## BatchMergeTexChannel 工作流

1. 选择输入目录、输出目录和处理 SBS，设置五类贴图的文件名关键字。
2. 分别为最终输出的 Channel R/G/B/A 选择一个来源；每组可选择 ColorMap R/G/B/A 或 GrayMap01-04。
3. 在列表中核对文件组、缺失或重复输入、输出路径，只勾选确认无误的组。
4. 点击“开始批处理”，工具使用临时 SBS 副本逐组计算并导出，不修改源贴图和插件处理资源。

窗口顶部会显示“工具功能正常/异常”。只有随附 SBS 的 5 个贴图输入、4 组共 32 个互斥通道开关和 `output` 完整一致时，才会开放扫描和批处理；完整接口和命名示例见 [batch_merge_tex_channel/README.md](batch_merge_tex_channel/README.md)。

## 目录

```text
MaxSDPlugins/
├── MaxSDPlugin.py
├── menu.py
├── sdcompat.py
├── output/
├── batch_merge_tex_channel/
├── BatchMergeTexChannel.sbs
├── frame_color_modify/
├── auto_add_expose_comment/
├── save_with_resource/
├── debug/
├── sbs_file_reporter/
└── output_tools/
```

跨版本差异集中在 `sdcompat.py`。功能模块不直接依赖版本特定的 UI 管理器、`QAction` 位置或 `exec/exec_` 名称。