# 带外部资源保存 (SaveWithResrouce)

> 当前开发工具版本：v0.8.2（`__init__.py/TOOL_VERSION`）；随插件 v0.25.2 升级。此版本号不代表 MG 已发布版本。

保存当前 SBS 副本，并递归收集非官方、非团队 Library 的本地依赖与 Resource。
菜单位置：`MaxSDPlugin/File/SaveWithResrouce`。

---

## 功能概览

### 使用流程

<whiteboard type="mermaid">
flowchart TD
    A[打开并保存目标 SBS] --> B[选择副本输出位置]
    B --> C[确认资源收集范围与目标路径]
    C --> D{输入与目标确认无误?}
    D -- 否 --> B
    D -- 是 --> E[保存副本并收集符合规则的外部文件]
    E --> G{本次复制名称已占用?}
    G -- 否 --> H[复制文件]
    G -- 是 --> I[追加哈希 冲突时继续追加编号]
    I --> G
    H --> F[生成副本 文件目录与 JSON 清单]
</whiteboard>

- 递归扫描当前 Package 及外部 Package 的依赖和 Resource，并防止循环引用。
- 排除 Designer 安装自带的 `resources/packages`、`D:\LG_SDNodes`、`sbs://` 和 `pkg://`。
- 将依赖复制到 `dependencies/`，其他 Resource 复制到 `resources/`。
- 使用 `saveCopyOfPackageAs()` 保存 SBS 副本，不改变当前打开文件的路径。
- 生成 `resource_manifest.json`，记录原始路径、复制位置、缺失和失败状态。

---

## 代码结构

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 菜单入口，打开资源预览窗口 |
| `collect_external_files()` | 递归收集并去重外部依赖和 Resource |
| `save_package_with_resources()` | 保存 SBS 副本、复制文件并生成 JSON 清单 |
| `_copy_name()` | 同名追加哈希，仍冲突则追加 _2、_3 等编号，直至本批次唯一 |

---

## 用到的 SD API
- `SDPackage.getDependencies()` - 读取 Package 依赖。
- `SDPackage.getChildrenResources(True)` - 递归枚举 Package Resource。
- `SDPackageDependency.getPackage()` - 继续扫描可解析的外部 Package。
- `SDPackageMgr.saveCopyOfPackageAs()` - 非破坏性保存当前 SBS 副本。

---

## 扩展指南
1. 修改 `_APPROVED_LIBRARY_ROOT` 可切换团队 Library 根目录。
2. 如需重建可迁移 Package，可在确认 SD API 支持后增加引用路径重写流程。

---

## 已知约束
- 工具复制文件但不改写 SBS 副本中的引用路径；原路径映射保存在 JSON 清单中。
- 缺失文件只写入清单，无法复制。
- 本次收集的不同资源按大小写不敏感名称去重：原名 → 短哈希后缀 → 数字后缀；资源名改变会反映在 JSON 清单中。本修复不改变已有目标目录同名文件的覆盖行为；复制和覆盖不支持 Ctrl+Z。
- 当前源 SBS 由保存副本 API 处理，不会再次复制进依赖目录。

## 框架升级说明

本工具公开入口和原有参数保持不变。窗口统一由 `shared.lifecycle` 管理：重复打开复用、关闭释放；插件重载会关闭窗口。未保存的界面配置请先处理。升级包含入口变更，需要重启 Designer 一次。离线回归不替代目标 Designer 中的实际功能和撤销验证。

## 本次修复验证与安装

目标 Designer 16.0.1，兼容目标 SD13；未新增依赖或外部资源。更新插件文件后 Unload→Load 生效；入口回退版本需重启。离线回归已覆盖本次失败场景；仍需在 Designer 验证加载/卸载、对应工具操作及撤销或文件副本，尚未执行实机验收或 MG 发布。

## 更新日志

- 2026-09-09 · v0.8.2 · 资源哈希名称冲突时继续追加编号，按大小写不敏感规则避让 · 本工具数据安全边界 · 功能可 Unload→Load，入口回退版本需重启

- 2026-09-04 · v0.8.1 · 接入统一窗口生命周期 · 本工具入口与错误处理 · 随插件 v0.25.0 升级需重启 SD
