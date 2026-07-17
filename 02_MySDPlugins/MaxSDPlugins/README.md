# MaxSDPlugins

面向 Substance Designer 13 与 16 的制作辅助插件。所有工具统一挂载在 `MaxSDPlugin` 顶级菜单下。

## 菜单

| 菜单 | 功能 |
|---|---|
| `Output/曝光参数` | 管理当前 Graph 的已暴露参数与损坏节点 |
| `Edit/FrameColorModify` | 汇总当前画布 Frame，并统一修改颜色与透明度 |
| `File/SaveWithResrouce` | 保存 SBS 副本并收集非官方、非团队库的外部文件 |
| `Debug/Publish Checker` | 检查发布依赖、资源、悬挂节点和未连接输出 |
| `Analysis/SBSFileRepoter` | 审计当前 Graph 的静态复杂度、潜在分支和高成本节点 |
| `OutputTools/输出脚本` | 将选定功能打包成可集成的独立 Python 脚本 |

## 目录

```text
MaxSDPlugins/
├── MaxSDPlugin.py
├── menu.py
├── sdcompat.py
├── output/
├── frame_color_modify/
├── save_with_resource/
├── debug/
├── sbs_file_reporter/
└── output_tools/
```

跨版本差异集中在 `sdcompat.py`。功能模块不直接依赖版本特定的 UI 管理器、`QAction` 位置或 `exec/exec_` 名称。