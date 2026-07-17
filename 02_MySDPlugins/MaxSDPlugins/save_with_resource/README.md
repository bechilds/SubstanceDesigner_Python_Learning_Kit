# 带外部资源保存 (SaveWithResrouce)

保存当前 SBS 副本，并递归收集非官方、非团队 Library 的本地依赖与 Resource。
菜单位置：`MaxSDPlugin/File/SaveWithResrouce`。

---

## 功能概览
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
| `_copy_name()` | 为同名文件生成稳定的哈希后缀，避免覆盖 |

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
- 当前源 SBS 由保存副本 API 处理，不会再次复制进依赖目录。