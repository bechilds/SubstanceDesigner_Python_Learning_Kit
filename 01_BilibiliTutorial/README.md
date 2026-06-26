# 01 · Bilibili 教程项目

跟随 B 站 UP 主 **黄卷Lr** 的 Substance Designer Python 开发教程整理的学习代码。
本分类用于「跟教程练手」，理解 SD Python API 的基础用法与插件结构。

## 📂 目录结构

```
01_BilibiliTutorial/
├── Bilibili_HuangJuanLr/         # 教程配套代码
│   ├── SubstanceDesignerPart1/   # 第一部分：基础脚本
│   │   ├── CheckPyside.py         # 检查 PySide 版本
│   │   ├── ResetViewLayout.py     # 重置视图布局
│   │   └── ShowViewLayoutList.py  # 显示视图布局列表
│   └── SubstanceDesignerPart2/   # 第二部分：UI 窗口开发
│       └── mylib/window.py        # 自定义窗口示例
└── SDFiles/                      # 教程练习用的 .sbs 测试文件
    └── Bilibili_HuangJuanLr/
        ├── BatchMergeGraphSample.sbs
        └── DefultSimpleGraph.sbs
```

## 🎯 学习目标

- 熟悉 SD Python API 的基础调用方式
- 了解 PySide/Qt 在 SD 中构建界面的方法
- 掌握视图布局、图（Graph）操作等常见任务

## ▶️ 运行方式

在 Substance Designer 中：从 **`Windows > Python Editor`** 打开 Python 编辑器，粘贴脚本后按 **Run / `F5`** 运行。
`SDFiles/` 下的 `.sbs` 文件可在 SD 中打开，作为脚本操作的练习素材。

## 🔗 来源

- UP 主：黄卷Lr（Bilibili）
