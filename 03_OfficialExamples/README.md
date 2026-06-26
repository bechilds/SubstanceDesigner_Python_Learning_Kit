# 03 · 官方案例

Adobe 官方提供的 Substance Designer Python 案例，作为 API 用法的权威参考。
本分类用于「对照官方写法」，理解规范的插件结构与 API 调用方式。

## 📂 目录结构

```
03_OfficialExamples/
├── OfficialExamples/             # 官方基础脚本案例
│   ├── PluginBasics.py            # 插件基础结构示例
│   ├── Original_PluginBasics.py   # 原始未改动版本
│   └── PrintSDMainMenu.py         # 打印 SD 主菜单示例
└── OfficialSDInsertPlugins/      # SD 内置的插件案例
    └── custom_graph/             # 自定义 Graph 插件示例
        ├── custom_graph.py
        └── data/mdl/custom_graph/custom_graph_nodes.mdl
```

## 🎯 学习目标

- 学习官方推荐的插件入口与注册方式
- 参考官方对 SD 应用上下文、菜单、Graph 的标准操作
- 作为自研插件（02_MySDPlugins）的写法对照

## ▶️ 运行方式

在 Substance Designer 中从 **`Windows > Python Editor`** 打开 Python 编辑器，粘贴代码后按 **Run / `F5`** 运行；
`OfficialSDInsertPlugins/` 下的内置插件案例可放入 SD 插件目录加载，或用 **`Tools > Plugin Manager...`** 管理。

## 🔗 来源

- [Substance Designer Python API 文档](https://substance3d.adobe.com/documentation/sddoc/python-api-184191934.html)
