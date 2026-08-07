# 02 · 我的插件开发项目（MaxSDPlugins）

我自己计划开发的 Substance Designer 插件，以及配套的工具脚本和学习笔记。
这是本工程的**核心实践区**，用于把教程和官方案例中学到的知识落地为真正可用的插件。

## 📂 目录结构

```
02_MySDPlugins/
├── AGENTS.md            # AI 协作者指南（开发本插件前必读）
├── MaxSDPlugins/        # 插件开发主目录
│   ├── __init__.py      # 插件包入口（转发 initialize/uninitialize）
│   ├── MaxSDPlugin.py   # 插件入口逻辑：MaxSDPlugin 菜单 + 版本信息 + Output / Debug 分类
│   ├── output/          # Output 功能分类（曝光参数等）
│   │   ├── __init__.py
│   │   ├── exposed_parameters_window.py  # 曝光参数对话框 UI
│   │   ├── output_data.py                # 枚举参数 + OutputData 读写
│   │   └── README.md
│   ├── batch_merge_tex_channel/ # Output/BatchMergeTexChannel（批量合并贴图通道）
│   │   ├── __init__.py
│   │   ├── logic.py              # 文件匹配、SBS 接口校验、计算与保存
│   │   ├── window.py             # 配置、预览与批处理 UI
│   │   └── README.md
│   ├── BatchMergeTexChannel.sbs  # 通道合并处理资源
│   ├── debug/           # Debug 功能分类（依赖/发布警告检查）
│   │   ├── __init__.py
│   │   ├── check_dependencies.py         # 发布警告扫描 + UI
│   │   └── README.md
│   ├── frame_color_modify/ # Edit/FrameColorModify（批量修改 Frame RGBA）
│   │   ├── __init__.py
│   │   ├── frame_color_modify.py
│   │   └── README.md
│   ├── auto_add_expose_comment/ # Edit/AutoAddExposeCommitToNode（曝光参数描述）
│   │   ├── __init__.py
│   │   ├── auto_add_expose_comment.py
│   │   └── README.md
│   ├── expose_param_sorting/ # 曝光参数面板的分组排序子功能（仅排序 INPUT PARAMETERS）
│   │   ├── __init__.py
│   │   ├── sorting_logic.py
│   │   ├── sorting_window.py
│   │   └── README.md
│   ├── save_with_resource/ # File/SaveWithResrouce（保存副本并收集外部文件）
│   │   ├── __init__.py
│   │   ├── save_with_resource.py
│   │   └── README.md
│   ├── sbs_file_reporter/ # Analysis 功能分类（SBS 静态复杂度审计）
│   │   ├── __init__.py
│   │   ├── reporter_logic.py              # 可达节点遍历 + 复杂度评分
│   │   ├── reporter_window.py             # 报告、定位与发布 UI
│   │   └── README.md
│   └── ReleaseNote.md      # 插件功能计划清单
├── utilities/           # 自己积累的工具脚本（可复用函数）
└── docs/                # 基础概念备注 / 官方文档摘录 / 开发日志
    ├── 官方文档          # 官方文档相关记录
    ├── 报错查看方法,md     # 报错排查方法笔记
    └── 日志              # 开发日志
```

> 🤖 **给 AI 助手**：开发本插件前请先读 [AGENTS.md](AGENTS.md)，其中规定了文件布局、插件入口/菜单注册、SD Python 代码质量基线与防回归规则。

## 🧭 当前菜单结构

```
MaxSDPlugin
├─ 关于 / 版本信息
├─ Output
│  ├─ 曝光参数        # 枚举已暴露参数 / 勾选 / 缓存·导出·加载 OutputData（删除重置为 TODO）
│  │                    # 内含参数分组排序、空参数标记和画布损坏节点检查
│  └─ BatchMergeTexChannel # 按关键字分组并批量合并贴图通道
├─ Edit
│  ├─ FrameColorModify # 统一修改当前画布全部 Frame 的颜色和透明度
│  ├─ AutoAddExposeCommitToNode # 给使用曝光参数的节点创建或更新 Comment
├─ File
│  └─ SaveWithResrouce # 保存 SBS 副本并收集外部依赖与 Resource
└─ Debug
│  └─ Publish Checker    # 扫描发布 sbsar 可能警告的节点（损坏函数/缺失资源/未连接输出/悬挂）
└─ Analysis
  └─ SBSFileRepoter     # 静态复杂度评分、潜在分支、高成本节点定位与发布预警
```

## 📝 插件功能计划（MaxSDPlugin）

详见 [MaxSDPlugins/ReleaseNote.md](MaxSDPlugins/ReleaseNote.md)，主要规划包括：

- 显示插件版本 / 软件版本 / PySide 版本
- SD 窗口布局重置、清理无效依赖
- LGSD 节点库自动更新
- 查错功能（默认分辨率、三面映射输入、输出通道校验等）
- 曝光参数与开关按钮的关联设定
- 3D 预览窗口摄像机参数设置
- 批量修改 Frame 的 A 值
- 保存 SBS 副本并收集非官方、非 Library 外部依赖与 Resource
- 校验输出的 Identifier 与 Usage 是否一致

## ▶️ 运行方式

### 方式一：快速试一段代码（Python Editor）

在 Substance Designer 从 **`Windows > Python Editor`** 打开 Python 编辑器，粘贴代码后按 **Run / `F5`** 运行。适合一次性试验。

### 方式二：让 SD 直接加载本插件（推荐，调试更快）

把本目录加入 SD 的「插件搜索路径」，SD 启动时就会发现 `MaxSDPlugins` 包并自动调用 `initializeSDPlugin()`，
之后改完代码用 Plugin Manager 重载即可，**无需重启 SD**。

**第一步：添加搜索路径（任选其一）**

- **A. 偏好设置（持久）**：`Edit > Preferences…` → 左侧 `Projects` → 选中要编辑的 Project File → `Python` 选项卡 → 点 `+` →
  添加本目录 `02_MySDPlugins/` 的绝对路径（即包含 `MaxSDPlugins` 文件夹的那一层）→ `OK`。
- **B. 环境变量（适合脚本化 / 多机一致）**：把 `02_MySDPlugins/` 的绝对路径加入环境变量 `SBS_DESIGNER_PYTHON_PATH`，再启动 SD。

> 注意：搜索路径要指向**包含 `MaxSDPlugins` 的上一层目录**（即 `02_MySDPlugins/`），SD 会把 `MaxSDPlugins` 当作一个插件包加载。

**第二步：验证已加载**

启动 SD 后，菜单栏应出现顶级菜单 **`MaxSDPlugin`**；点 `关于 / 版本信息` 会在 Python 控制台打印插件 / SD / PySide 版本。

**第三步：改完代码热重载（不重启）**

`Tools > Plugin Manager…` → 选中 `MaxSDPlugins` → 先 **Unload** 再 **Load**（或用 `Browse` 选中 `MaxSDPlugins/__init__.py` 重新加载，`Refresh` 刷新列表）。这样即可看到最新改动。

> 也可用 `Browse` 直接选 `MaxSDPlugins/__init__.py` 临时加载一次，不必先配搜索路径。

## 📌 说明

- `utilities/`：沉淀通用的、可被插件复用的工具函数。
- `docs/`：记录基础概念、报错排查方法与开发日志，供开发时查阅。
