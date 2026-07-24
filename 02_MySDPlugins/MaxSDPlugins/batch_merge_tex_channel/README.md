# 批量合并贴图通道 (BatchMergeTexChannel)

按文件名关键字自动分组贴图，并通过指定的 Substance Graph 批量计算和导出合并结果。
菜单位置：`MaxSDPlugin/Output/BatchMergeTexChannel`。

---

## 功能概览
- 递归扫描输入目录，按 Color、Gray01、Gray02、Gray03、Gray04 五个自定义关键字匹配贴图。
- 先展示文件组、缺失输入、重复匹配、输出冲突和计划输出路径，不会在扫描阶段计算或写文件。
- 最终输出的 Channel R/G/B/A 各有一个独立来源组，每组可从 ColorMap R/G/B/A 和 GrayMap01-04 中选择一个来源。
- 每个输出通道组严格八选一：选中的 SBS 开关为 `True`，同组其余七个开关均为 `False`。
- 顶部状态显示“工具功能正常/异常”；只有处理 SBS 的 5 个贴图输入、32 个通道开关和 `output` 完整一致时才允许扫描和处理。
- 使用临时 SBS 副本执行计算，不修改插件自带的 `BatchMergeTexChannel.sbs`。
- 支持 PNG、TGA、TIF、EXR 输出、命名模板、显式覆盖、进度显示、取消和逐组错误日志。

文件名示例：

```text
Hero_ColorMap.png
Hero_GrayMap01.png
Hero_GrayMap02.tga
```

使用默认关键字扫描后，以上文件会组成 `Hero` 文件组。命名模板 `{group}_Merged` 会生成 `Hero_Merged.png`。

---

## 代码结构

```text
batch_merge_tex_channel/
├── __init__.py
├── logic.py
├── window.py
└── README.md
```

| 文件 / 函数 | 职责 |
|---|---|
| `show_window()` | 菜单入口，创建并保活批处理窗口 |
| `scan_texture_groups()` | 按最长关键字优先匹配文件并建立文件组 |
| `validate_channel_assignments()` | 检查最终 RGBA 是否都选择了一个合法来源 |
| `validate_group()` | 检查通道来源所需输入和重复文件 |
| `load_processor()` | 复制并加载临时 SBS，按 Identifier 逐项查询并校验 Graph 输入、开关与输出接口 |
| `process_group()` | 设置输入贴图和开关、计算 Graph、保存输出纹理 |
| `cleanup_processor()` | 卸载临时 Package 并删除临时目录 |

---

## 用到的 SD API
- `SDPackageMgr.loadUserPackage()` / `unloadUserPackage()` — 加载和卸载临时处理 Package。
- `SDTexture.sFromFile()` — 从磁盘加载输入贴图。
- `SDValueTexture.sNew()` — 将贴图包装为 Graph 输入值。
- `SDValueBool.sNew()` — 设置通道开关值。
- `SDResource.setInputPropertyValueFromId()` — 写入处理 Graph 的输入属性。
- `SDSBSCompGraph.compute()` — 计算处理 Graph。
- `SDResource.getPropertyValue()` — 读取 `output` 属性值。
- `SDTexture.save()` — 保存合并后的贴图。

---

## 扩展指南
1. 在 `logic.py` 的 `IMAGE_EXTENSIONS` 中增加需要扫描的图片扩展名。
2. 修改 SBS 接口时，同步更新 `INPUTS`、`OUTPUT_CHANNELS`、`CHANNEL_SOURCES`、`GRAPH_ID` 或 `OUTPUT_ID`。
3. 开关 Identifier 由输出通道前缀和来源后缀生成，例如 `ChannelR_ColorMapR_On`。
4. 在 Designer 中先点击“检查 SBS 接口”，确认能力诊断后再扫描和处理。

---

## 已知约束
- 必须在 Substance Designer 内运行；普通 Python 只能验证文件扫描和语法，不能执行 Graph 计算。
- 处理 SBS 必须完整提供 `InputColorMap`、`InputGrayMap01-04`、32 个 `ChannelR/G/B/A_*_On` 开关和 `output`；缺少任一项都会停用工具。
- ColorMap R/G/B/A 四种来源都读取 `InputColorMap`，GrayMap01-04 分别读取对应灰度输入。
- 同一文件组同一输入槽匹配到多个文件时，必须整理文件或修改关键字后重新扫描，工具不会猜测应使用哪一个。
- 处理在 Designer UI 线程逐组执行。当前组计算期间点击取消，会在该组完成后停止后续组。
- 本功能依赖外部 `.sbs` 资源，因此没有加入 OutputTools 的单文件脚本导出列表。
