# Substance Designer Python Scripts

本项目用于学习substance designer的 python脚本开发，通过Vscode 编写代码
借助AI工具 进行代码生成

## 📁 Project Structure

本工程按**三个分类**组织，每个分类目录下都有独立的 `README.md` 说明：

```
01_BilibiliTutorial/            # ① B 站教程项目（黄卷Lr）
├── Bilibili_HuangJuanLr/       #    教程配套代码
└── SDFiles/                    #    教程练习用的 .sbs 文件

02_MySDPlugins/                 # ② 我的插件开发项目（计划开发）
├── MaxSDPlugins/               #    插件主目录（含 TodoList 计划）
├── utilities/                  #    可复用的工具脚本
└── docs/                       #    基础概念备注 / 文档 / 开发日志

03_OfficialExamples/            # ③ 官方案例（API 权威参考）
├── OfficialExamples/           #    官方基础脚本案例
└── OfficialSDInsertPlugins/    #    SD 内置插件案例
```

> 各分类详细说明见：
> [01_BilibiliTutorial/README.md](01_BilibiliTutorial/README.md) ·
> [02_MySDPlugins/README.md](02_MySDPlugins/README.md) ·
> [03_OfficialExamples/README.md](03_OfficialExamples/README.md)

## 🛠 Requirements

- Adobe Substance 3D Designer 16.0.1（本人当前使用版本）
- Python 3.13.x（SD 16.0 内置）—— 代码需在 SD 内置的 Python 解释器中运行
- PySide6 / Qt 6.8.x（SD 16.0 内置的 QtForPython，用于 UI 开发）
- Basic understanding of Substance Designer interface

## 📖 Learning Path

03_OfficialExamples（官方案例）→ 01_BilibiliTutorial（教程实践）→ 02_MySDPlugins（自研插件）


## 🎯 Common Use Cases

- Automating repetitive node setups
- Batch processing multiple substances
- Creating custom material generators
- Exposing/unexposing parameters automatically
- Generating variations of existing materials


## 🔧 Running Scripts

### In Substance Designer (16.0.1):
1. 打开 Substance 3D Designer
2. 从菜单栏 **`Windows > Python Editor`** 打开 Python 编辑器面板
3. 粘贴代码，点 **Run**（或按 `F5`；运行选中部分用 `Ctrl+Enter`），输出显示在控制台

### 作为插件加载：
- 把插件放入 SD 的用户 Python 插件目录，启动时自动调用 `initializeSDPlugin()`；
- 或通过 **`Tools > Plugin Manager...`** 查看 / 管理已加载的插件。

> 注：SD 没有 `Tools > Scripting` 菜单。脚本运行统一走 **Python Editor**（`Windows` 菜单），插件管理走 **Plugin Manager**（`Tools` 菜单）。



## 📚 Resources

- [Substance Designer Python API Documentation](https://substance3d.adobe.com/documentation/sddoc/python-api-184191934.html)
- [Substance Automation Toolkit](https://substance3d.adobe.com/documentation/sddoc/substance-automation-toolkit-187073291.html)

## 🤝 Contributing

Feel free to add your own scripts and improvements to this workspace!

---
Happy scripting! 🎨
