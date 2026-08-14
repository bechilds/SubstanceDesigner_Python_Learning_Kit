# 预设效果找回 (preset_recovery)

导入旧 `.sbsprs`，按旧参数名与当前 Graph 的 Identifier 重新建立映射，并在 `INPUT PARAMETERS > Presets` 中创建或覆盖预设。
菜单位置：`MaxSDPlugin/Output/预设效果找回`。

---

## 功能概览
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
- 覆盖同名 Preset 会完整替换其输入集合；执行前必须确认，失败时会尽量恢复旧 Preset。
