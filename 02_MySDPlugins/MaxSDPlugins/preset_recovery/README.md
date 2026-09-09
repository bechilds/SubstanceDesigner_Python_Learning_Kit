# 预设效果找回 (preset_recovery)

> 当前开发工具版本：v0.20.2（`__init__.py/TOOL_VERSION`）；随插件 v0.25.2 升级。此版本号不代表 MG 已发布版本。

导入旧 `.sbsprs`，按旧参数名与当前 Graph 的 Identifier 重新建立映射，并在 `INPUT PARAMETERS > Presets` 中创建或覆盖预设。
菜单位置：`MaxSDPlugin/Output/预设效果找回`。

---

## 功能概览

### 使用流程

<whiteboard type="mermaid">
flowchart TD
    A[打开当前 Graph 并准备旧 sbsprs] --> B[读取预设并按 Identifier 匹配]
    B --> C[核对自动映射 手动目标与 Preset 名称]
    C --> D{输入与目标确认无误?}
    D -- 否 --> B
    D -- 是 --> E[校验值 确认新建或覆盖 Preset]
    E --> G{创建及参数写入成功?}
    G -- 是 --> F[保存当前 SBS 原 sbsprs 保持不变]
    G -- 否 --> H[清理半成品 覆盖时恢复旧标签和输入]
    H --> I{恢复成功?}
    I -- 是 --> J[报告原始错误 不保存]
    I -- 否 --> K[同时报告写入与恢复错误 检查撤销后再保存]
</whiteboard>

- 读取一个预设文件中的一个或多个预设，并列出其中的参数名称、类型和值。
- 优先按当前参数 Identifier 精确匹配；找不到时标红提示，并允许手动选择目标参数。
- 目标名称不存在时调用 Graph Preset API 新建；存在时明确询问，再删除并重建同名 Preset。
- 写入键始终使用当前目标参数 Identifier；预设名称默认使用源预设名称，也可编辑。
- 全部参数先按当前目标类型转换为原生 SDValue，任何一项失败都不会修改当前 Graph。
- 导入的 `.sbsprs` 文件不会修改；当前 SBS 会产生 Preset 变更，完成后需要保存。
- 参数列表显示导入总数、已匹配数（自动/手动）和未匹配数；每行显示匹配状态与目标 Editor，切换目标时实时更新。
- 写入时结合目标参数底层类型与 Editor 转换：Toggle/Bool、Dropdown/Enum、ColorRGB(A)、Position、Angle/Slider 均转换为对应原生 SDValue。

---

## 代码结构

```text
preset_recovery/
├── __init__.py
├── logic.py
└── window.py
```

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 功能入口，被菜单动作调用 |
| `parse_preset_file()` | 解析 `.sbsprs` 中的预设与参数 |
| `build_mappings()` | 按当前 Identifier 自动建立映射 |
| `collect_target_parameters()` | 读取当前 INPUT PARAMETERS 的 Identifier、底层类型和 Editor |
| `prepare_preset_inputs()` | 按目标参数类型校验并构造原生 SDValue |
| `create_or_replace_preset()` | 在当前 Graph 中新建或完整覆盖同名 Preset |

---

## 用到的 SD API
- `SDGraph.getProperties(SDPropertyCategory.Input)` — 枚举当前 Graph 输入参数。
- `SDGraph.getPropertyAnnotationValueFromId(prop, "editor")` — 读取参数 Editor 表现类型。
- `SDSBSCompGraph.getPresets() / getPreset()` — 枚举并检查当前 Graph 的命名预设。
- `SDSBSCompGraph.newPreset() / deletePreset()` — 新建或完整替换同名预设。
- `SDSBSCompGraphPreset.addInput()` — 用当前参数 Identifier 和原生 SDValue 添加 Preset 输入。
- `SDHistoryUtils.UndoGroup` — 将创建或覆盖操作合并为一次撤销。

---

## 扩展指南
1. 在 `parse_preset_file()` 中增加属性候选，可兼容额外的预设 XML 版本。
2. 在 `_build_sdvalue()` 中增加新类型构造器，可支持资源类 Preset 输入。

---

## 已知约束
- 工具只处理 `.sbsprs` 中带参数名称和值属性的 `presetinput`；未映射项不会写入目标 Preset。
- 自动匹配只依据 Identifier，不根据 Label 猜测；多个旧参数不能映射到同一个目标 Identifier。
- 当前支持 float/int/bool/string 及 2-4 维 float/int 值，并支持 Toggle、Dropdown/Enum、Color、Position、Angle/Slider Editor 转换；图像、字体等资源类型会在执行前提示且不修改 Graph。
- 覆盖同名 Preset 会完整替换其输入集合；执行前必须确认，创建或写入失败时会清理半成品并尽量恢复旧 Preset 的标签和输入；恢复也失败时同时报告两次错误，请检查并尝试撤销，确认恢复前不要保存 SBS。

## 框架升级说明

本工具公开入口和原有参数保持不变。窗口统一由 `shared.lifecycle` 管理：重复打开复用、关闭释放；插件重载会关闭窗口。未保存的界面配置请先处理。升级包含入口变更，需要重启 Designer 一次。离线回归不替代目标 Designer 中的实际功能和撤销验证。

## 本次修复验证与安装

目标 Designer 16.0.1，兼容目标 SD13；未新增依赖或外部资源。更新插件文件后 Unload→Load 生效；入口回退版本需重启。离线回归已覆盖本次失败场景；仍需在 Designer 验证加载/卸载、对应工具操作及撤销或文件副本，尚未执行实机验收或 MG 发布。

## 更新日志

- 2026-09-09 · v0.20.2 · 创建新 Preset 失败时也恢复旧预设，恢复失败保留两次错误 · 本工具数据安全边界 · 功能可 Unload→Load，入口回退版本需重启

- 2026-09-04 · v0.20.1 · 接入统一窗口生命周期 · 本工具入口与错误处理 · 随插件 v0.25.0 升级需重启 SD
