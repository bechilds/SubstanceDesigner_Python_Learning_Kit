我的插件功能计划
插件名称：MaxSDPlugin

## 更新记录（格式：日期 · vX.Y.Z · 改动 · 影响范围 · 是否需重启 SD）
- 2026-08-13 · v0.23.0 · 曝光参数“参数分组排序”新增组内参数排序、受约束的树内拖拽、Ctrl+上/下快捷移动及“更改分组”：分组只能在顶层排序，参数可在组内拖动或拖入其他组；应用时同步 SBS 的直接 Group 与 metadata Group，并继续保持 INPUTS 原槽位不变 · expose_param_sorting/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-11 · v0.22.0 · OutputTools 新增“输出到 MG”：可选择任意 MaxSD 根目录，按分类生成 `LG_MaxSD_*` 模块并写入共享兼容层；自动改写相对 import、处理同名模块冲突并提示未勾选依赖，同时补齐当前功能分类扫描 · output_tools/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-11 · v0.21.1 · 曝光参数“删除勾选项”在重置依赖节点函数前缓存曝光参数当前 SDValue，重置后将该值写成节点常量，取消曝光不再回到旧默认值 · output/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-11 · v0.21.0 · SBSFileRepoter 的 Potential Maximum 改为逐个 Switch 选择最高成本分支，全部分支总量独立展示；文件健康与性能复杂度拆分，等级阈值调整为 150/400/800；新增报告主体 PNG 截图保存 · sbs_file_reporter/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.20.0 · 预设效果找回参数列表新增导入总数、已匹配数（自动/手动）、未匹配数和逐行匹配状态，并显示目标参数 Editor，手动切换目标时实时刷新；Preset 写入转换结合目标底层类型与 Editor，支持 Toggle/Bool、Dropdown/Enum、ColorRGB(A)、Position、Angle/Slider，非法值在修改 Graph 前中止 · preset_recovery/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.19.5 · 开关管理参数树支持双击编辑 Boolean/Float/Int/String 标量当前值并批量应用，复杂类型与 XML-only INPUTS 保持只读；新增“清除 Visible If”，可把勾选参数或整组的 Visible If 批量删除，两类操作均使用 UndoGroup · switch_manager/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.19.4 · 曝光参数“已暴露参数”列表在引用状态前新增 Editor 类型列，读取并显示 `editor` 注解（如 Slider、Color、Angle），无注解时留空 · output/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.19.3 · 开关管理创建 Boolean 参数时新增 True/False 初始值选择并按所选值写入；当前参数树在 Visible If 后新增“当前数值”列，Graph API 参数显示格式化后的运行时值，XML-only INPUTS 显示 SBS 保存的默认值 · switch_manager/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.19.2 · 修复开关管理刷新后仍显示旧 Group：手动刷新现会先保存当前 Package，再从 SBS 重建 Group 列表；仅当原选中 Group 仍存在时保留，否则自动切换到最新的 Boolean 开关组，已删除或改名的旧 Group 不再被重新写回可编辑框 · switch_manager/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.19.1 · 修复 SD13 Graph API 只返回 INPUT PARAMETERS、完全遗漏属性面板 INPUTS 的问题：参数列表现合并当前已保存 SBS 的 `<paraminputs>`，按 `<isConnectable>` 补入 Input Color/Input Value，并从直接 `<group>` / `<visibleIf>` 读取真实设置；开关 Group 改为可编辑下拉框，可选择现有 Group 或输入新 Group，Group/Visible If 写入不再依赖 API 设置 ID 枚举 · switch_manager/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.19.0 · 按最终需求重做预设效果找回的写入目标：导入 `.sbsprs` 后按当前 Identifier 重映射并通过 SDSBSCompGraph Preset API 写入 `INPUT PARAMETERS > Presets`；目标名称不存在时新建，存在时明确确认后删除重建同名 Preset；全部值先按当前参数类型转换，失败不修改 Graph，导入文件保持只读 · preset_recovery/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.18.1 · 修复开关管理参数树遗漏 Input Color/Input Value 等连接型 INPUTS：改为逐字段容错读取，单个默认值不可读不再跳过整项；创建开关新增 Group 设置，可用开关由下拉框改为单选列表，并严格限定为当前开关 Group 内的 Boolean 参数，应用时再次校验 Group · switch_manager/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.18.0 · 新增 Edit/开关管理工具：可在 INPUT PARAMETERS 创建默认开启的 Boolean 参数，按 INPUT PARAMETERS/INPUTS 与 Group 展示参数当前 Visible If，并把 `input["开关ID"]` 批量写入勾选参数或整组；创建与应用均可单步撤销 · switch_manager/+menu+版本+文档 · 功能、菜单和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.17.2 · 预设效果找回新增来源与目标确认区：并列显示当前 SBS/Graph、导入源文件、源预设序号及原目标，避免单预设时无法判断匹配对象；底部改为明确的执行/取消按钮，执行前汇总源预设、匹配 Graph、替换数量和输出路径，已有输出文件需再次确认覆盖，源预设路径始终禁止覆盖 · preset_recovery/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.17.1 · 纠正预设效果找回的输出目标：不再把旧预设值写入当前 Graph，改为复制源 `.sbsprs`，将匹配参数名称替换为当前 Identifier 对应的新 Label 后另存为新预设；参数类型和值原样保留，源预设与当前 SBS 均不修改 · preset_recovery/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-10 · v0.17.0 · 新增 Output/预设效果找回：导入旧 `.sbsprs` 后按预设参数名与当前 Graph Identifier 自动重映射，Label 改名不再阻断标量参数恢复；未匹配项标红并可手动选择写入目标，整批操作可撤销 · preset_recovery/+menu+版本+文档 · 功能、菜单和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-04 · v0.16.0 · ExposeParameterAutoSorting 合并到 Output/曝光参数面板并移除独立 Edit 菜单项；已暴露参数与画布损坏节点改为独立分组和可调分隔区；参数树新增引用状态并标记未被节点引用的空参数；损坏 Get Variable 对应属性已取得非空输入值（含 0/False）时不再报告或重置“参数输入丢失” · output/+expose_param_sorting/+menu+版本+文档 · 功能、菜单和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-03 · v0.15.5 · AutoAddExposeCommitToNode 读取曝光参数的 Group 注解并写入 Comment，有分组时使用 `分组|-参数`（如 `Base|-Color`），无分组时保留 `-参数`；扫描表格和搜索同步支持分组 · auto_add_expose_comment/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-03 · v0.15.4 · 修复 ExposeParameterAutoSorting 仍将 `<paraminputs>` 中未显示的连接型 INPUTS 误判为错误：Designer 会把 INPUT PARAMETERS 与 INPUTS 同时序列化到 `<paraminputs>`；XML 算法改为目标槽位替换，只在 UI 选中的 INPUT PARAMETERS 原索引之间重排完整节点，未选中的 INPUTS 等节点保持原索引和内容不变 · expose_param_sorting/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-03 · v0.15.3 · 修复 ExposeParameterAutoSorting 扫描范围错误：`getProperties(Input)` 同时包含 INPUT PARAMETERS 与连接型 INPUTS，现按 `isConnectable()` 在数据入口严格过滤，只展示和排序非连接型 INPUT PARAMETERS；INPUTS 与 OUTPUTS 均不读取、不参与 XML 校验或修改，避免图像输入被误报为 SBS 缺失参数 · expose_param_sorting/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-03 · v0.15.2 · 收紧 ExposeParameterAutoSorting 执行范围：仅处理当前活动 Graph 所属的一个已加载 User Package 和该 Graph 对应的唯一 XML 节点，不遍历 Explorer 中其他 Package/Graph；扫描时记录 SBS 路径、Package UID 和 Graph ID，执行前二次比对活动范围，切换文件或 Graph 后自动中止；状态栏和确认框显示唯一目标范围 · expose_param_sorting/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-03 · v0.15.1 · 修复 ExposeParameterAutoSorting 将运行时可见但未序列化到当前 SBS `<paraminputs>` 的继承/动态输入误判为参数列表不一致：XML 排序现在只处理真实存在的 `<paraminput>`，安全跳过并汇总 UI 独有参数；若 SBS 存在 UI 未显示参数仍中止，避免破坏隐藏顺序 · expose_param_sorting/+版本+文档 · 功能和热重载版本无需重启，入口回退版本生效需重启
- 2026-08-03 · v0.15.0 · 新增 Edit/ExposeParameterAutoSorting：扫描当前 Graph 的曝光参数并按 Group 树状展示，支持刷新、全部展开/收起及调整顶级分组顺序；应用时保存当前 Package、创建时间戳备份并卸载，通过原子重排 SBS XML 中完整 `<paraminput>` 节点保持 UID、类型、值、注解和引用不变，失败自动恢复备份并重新加载 · expose_param_sorting/+menu+版本+文档 · 功能、菜单和热重载版本无需重启，入口回退版本生效需重启
- 2026-07-24 · v0.14.1 · 修复 BatchMergeTexChannel 在部分 Designer 版本中将完整 SBS 误报为“缺少贴图输入/输出”：契约检查不再依赖版本差异较大的 getProperties 集合枚举，改为按 5 个贴图输入、32 个开关和 output 的 Identifier 逐项调用 getPropertyFromId，并在 API 查询异常时显示真实原因；误禁用的 RGBA 来源选择会在检查通过后自动恢复 · batch_merge_tex_channel/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.14.0 · BatchMergeTexChannel 适配最终 SBS 接口：按最终输出 Channel R/G/B/A 建立 4 个来源组，每组在 ColorMap RGBA 与 GrayMap01-04 共 8 个来源中严格单选，处理时只将所选开关设为 True、同组其余保持 False；新增顶部“工具功能正常/异常”状态，只有 SBS 的 5 个贴图输入、32 个开关和 output 完整一致时才开放扫描与处理 · batch_merge_tex_channel/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.13.0 · 曝光参数主树的分类/Group 节点新增三态勾选，可整组选择或取消；批量替换弹窗新增 Group 勾选项和逐行选择列，关键字预览及应用只处理勾选参数。新增“去除 Copy”，批量清理勾选参数 Label/ID 中独立的 Copy token；ID 通过创建新参数、迁移所有 Get Variable 引用并删除旧参数实现，失败时恢复引用并清理新参数，整批可单步撤销 · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.12.2 · 修复批量复制预览正确但创建后仍是旧参数：不再复制源 identifier/id/label 身份字段，避免覆盖 graph.newProperty 使用的新 ID；非身份 metadata 继续继承，新 Label 改由目标 property metadata 写入。批量替换新增多个“排除 Group 关键字”，支持逗号/分号/换行分隔，命中类别的整行跳过并显示排除数 · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.12.1 · 修复批量复制执行时 SDApiError.ItemNotFound 穿透回调：Adobe APIException 继承 BaseException，现用专用异常元组捕获；注解复制改为只写源/新参数共同支持的注解，不支持项进入警告汇总。同步检查并加固批量替换，Label、Group、当前值逐字段独立写入，单字段 API 错误只汇总跳过、不再中断窗口 · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.12.0 · “复制当前参数”扩展为“复制勾选参数”：支持一次选择多个 INPUT PARAMETERS，在创建前弹窗预览源 ID/Label 与新 ID/Label，可按关键字批量替换新 ID、新 Label 或两者并手动调整；确认后在一个 UndoGroup 内逐项调用 graph.newProperty 创建真实副本并复制类型、注解和原生当前值，失败项单独汇总 · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.11.2 · 曝光参数复制的来源由不稳定的高亮项改为“唯一勾选项”，随后继续使用与参数面板 + 对应的 graph.newProperty 创建新参数并复制设置；批量替换窗口新增作用字段、查找关键字、替换文本、区分大小写和预览命中数，可对 Label、Group、当前值执行预览后统一应用 · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.11.1 · 纠正曝光参数复制/批量替换语义：“复制当前参数”现在用 graph.newProperty 在 INPUT PARAMETERS 中创建真实副本并复制类型、注解和原生当前值；“批量替换参数设置”改为独立逐行编辑窗口，可统一修改勾选参数的 Label、Group 和受支持的标量当前值，复杂类型值保持只读 · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.11.0 · 曝光参数新增“复制当前参数”和“批量替换参数设置”，可将来源参数的 SD 原生当前值一次应用到勾选的同类型目标并整体撤销；节点列表改为只显示曝光参数输入已丢失并触发 Empty variable 画布警告的节点，正常曝光绑定及资源/连线类问题不再误报，列名同步改为“有曝光参数的节点 / 对应的损坏节点属性 / 警告类型” · output/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.10.0 · 新增 Output/BatchMergeTexChannel：递归扫描输入目录，按 5 组自定义关键字匹配并预览文件组，通过临时 SBS 副本设置 5 个贴图输入与可用通道开关、计算 output 并批量导出；支持缺失/重复/输出冲突检查、逐组日志、取消和显式覆盖。当前随附 SBS 实际仅提供 Color RGBA 与 Gray01 开关，UI 会禁用缺失的 Gray02-04 开关并显示契约诊断 · batch_merge_tex_channel/+BatchMergeTexChannel.sbs+menu+版本+文档 · 功能、菜单和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.9.4 · 修复 AutoAddExposeCommitToNode 创建的 Comment 严重错位：sNewAsChild(node) 生成的是节点子对象，旧代码错误写入节点 Graph 绝对坐标导致父坐标重复叠加；现改为子对象相对坐标 (0, 75)，重新覆盖应用可同步修正已有错位 Comment · auto_add_expose_comment/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.9.3 · AutoAddExposeCommitToNode 预览列表新增名称/ID 实时搜索，覆盖 Graph、节点名称与 ID、节点属性、曝光参数 ID 和显示名称；支持空格多关键词、匹配数量显示、Enter 选中首项，便于在大量扫描结果中快速找到节点 · auto_add_expose_comment/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.9.2 · AutoAddExposeCommitToNode 扫描预览新增“查找节点”按钮和表格双击定位，复用 sdcompat.focus_node 跨 SD13/14/16 居中或回显节点 ID/坐标，便于逐项核对扫描结果且不修改 Graph · auto_add_expose_comment/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-24 · v0.9.1 · AutoAddExposeCommitToNode 改为严格两阶段：先只读扫描并展示可勾选计划、最终拟写内容和逐层诊断，用户点击应用并再次确认后才写 Comment；Get Variable 字符串优先走 SDValueString.get()，保留序列化回退以改善零匹配问题 · auto_add_expose_comment/+版本+文档 · 功能和版本可热重载，入口回退版本生效需重启
- 2026-07-22 · v0.9.0 · 新增 Edit/AutoAddExposeCommitToNode：扫描当前 SBS 文件全部 Graph，将节点实际引用的曝光参数名称写入节点下方 75 像素的 Comment；已有 Comment 支持覆盖或追加，操作可单步撤销 · auto_add_expose_comment/+menu+output_tools+版本+文档 · 功能、菜单和版本可热重载，入口回退版本生效需重启
- 2026-07-16 · v0.8.0 · 新增 Edit/FrameColorModify：汇总当前画布全部 Frame，统一设置 RGB 与全局透明度，支持单步撤销；新增 File/SaveWithResrouce：递归收集非官方/非 D:\LG_SDNodes 依赖与 Resource，保存 SBS 副本、分类复制外部文件并生成 JSON 清单；OutputTools 纳入两个新分类，同时修复 SD16 下 menu.sdcompat 导入缩进 · frame_color_modify/+save_with_resource/+menu+output_tools+文档 · 入口版本回退值生效需重启，功能与菜单可热重载
- 2026-07-16 · v0.7.4 · 修复 Designer 自带节点依赖被计入文件风险：从当前 sd.__file__ 动态反推安装目录 resources/packages 并设为可信根，兼容不同盘符、Adobe/Allegorithmic 路径及 SD13/16；正常官方依赖不再 +15，文件确实丢失时仍保留丢失风险 · sbs_file_reporter/+版本+文档 · 功能模块可热重载
- 2026-07-16 · v0.7.3 · SBSFileRepoter 评分结果首行显示当前 .sbs 文件名；主要成本列表上方新增跨 Qt5/Qt6 自绘直方图，按 0-0.5/0.5-1/1-3/3-8/8+ 固定区间展示节点最终权重与节点数量，刷新失败时清空旧图表 · sbs_file_reporter/+版本+文档 · 功能模块可热重载
- 2026-07-16 · v0.7.2 · SBSFileRepoter 评分按 Low 白/Medium 绿/High 红/Very High 紫显示；新增文件风险分：丢失节点/Ghost/依赖 +60、Resource 丢失 +40、D:\LG_SDNodes 外本地依赖 +15/Resource +10，并在结构警告列出加分来源；复杂度分与文件风险分拆开显示后汇总 · sbs_file_reporter/+版本+文档 · 功能模块可热重载
- 2026-07-16 · v0.7.1 · 修复 SBSFileRepoter 将 SDValueInt2 类型名数字误读为 4x4、将公共 sbscompgraph 定义前缀误判为 Graph Instance；尺寸改按 SDPropertyInheritanceMethod 明确计算，动态值按 1K 标记估算；参数修正改为 Identifier 精确匹配；顶部只保留规则与突出评分，成本列表改为基础权重+可解释计分依据 · sbs_file_reporter/+版本+文档 · 功能模块可热重载
- 2026-07-16 · v0.7.0 · 新增 Analysis/SBSFileRepoter：从 Published Output 反向遍历，输出 Current/Potential 静态复杂度、分辨率/参数修正、热点和结构警告，支持跨 SD13/16 定位与确认后发布；菜单/入口/现有窗口统一补齐 QAction、exec/exec_、当前图和主窗口兼容调用 · sbs_file_reporter/+menu+sdcompat 调用方+文档 · 首次安装或入口版本回退值生效需重启，功能与菜单可热重载
- 2026-07-01 · v0.6.8 · 【SD13 Goto 转正】给 focus_node 增加策略3：SD13 等无 focusGraphNode 的版本，改走纯 Qt 层——用 SDNode.getPosition()（图坐标与 QGraphicsScene 坐标 1:1，已 SD13.0.0 实测）在存活可见的 QGraphicsView 上 fitInView 缩放居中，效果接近 F 键（既居中又放大）。视图枚举用 QApplication.allWidgets()+shiboken.isValid() 判活，规避 findChildren 返回已删除视图的 'already deleted'；优先用 scene.itemAt 命中的节点图元精确框住，命中不到用固定窗口。清理实验期冗余日志 · sdcompat/ · 热重载
- 2026-07-01 · v0.6.7 · 【纠偏】上一版误判：本开发机的 SD 安装其实是 13.0.0（非 16），我把它的 API stub 当成 SD16 读，错误得出“SD16 也没有 focusGraphNode”。事实更正：SD16/SD14 有 focusGraphNode，Goto 正常；仅 SD13 缺定位/选中接口。focus_node 恢复正确分层（SD16/14 居中；SD13 降级），SD13 降级增强：回显 <label>(id:) @ (x,y) 坐标 + 复制 id 到剪贴板（坐标经 SD13 实测 SDNode.getPosition() 可用）；查找表/memory 同步更正 · sdcompat/+docs/+utilities/ · 热重载
- 2026-07-01 · v0.6.6 · 存入 SD13 实测 UI 管理器接口清单到查找表（sd_api_compat.json/SD_API_Compatibility.md）；确认 SD13 只有 getXxxSelection 只读接口、无 focusGraphNode/set 写入接口 → 无法程序化定位/选中；focus_node 降级提示改为回显节点 `<label> (id:<id>)` 便于手动查找 · sdcompat/+docs/ · 热重载
- 2026-07-01 · v0.6.5 · 新增集中式跨版本兼容层 sdcompat.py（能力探测+多策略降级+永不抛异常）；goto_node 改为转发 sdcompat.focus_node，SD13 缺 focusGraphNode 时自动降级为选中高亮；导出物内置 sdcompat（root_sdcompat）最先 exec+qt_patch，废除内联 _RUNTIME_COMPAT_SHIM；查找表/AGENTS 同步 · sdcompat/+output/+debug/+output_tools/+docs/+AGENTS · 热重载
- 2026-07-01 · v0.6.4 · 导出物新增自动弹窗尾巴：直接在 SD Python Editor 运行时（__name__=='__main__'）自动 maxsd_show_all() 弹出所有功能窗口，解决“运行后没反应”（之前只定义不调用）；新增 _maxsd_main_window()/maxsd_show_all()；宿主 import 集成不受影响 · output_tools/ · output_tools 热重载
- 2026-06-30 · v0.6.3 · 修复导出工具跨版本兼容：导出物改为双版本通用（废除 PySide6->PySide2 静态替换，改为运行时补丁 _maxsd_qt_compat 抹平 QAction 位置与 exec/exec_ 差异）；新增 docs/SD_API_Compatibility.md + sd_api_compat.json 查找表；AGENTS §1.7 跨版本规则 · output_tools/+docs/+AGENTS · output_tools 热重载
- 2026-06-30 · v0.6.2 · goto_node 加跨版本守卫：SD13 等旧版 SDUIMgr 无 getGraphViewIDCount/focusGraphNode 时不再报错，提示不支持定位 · output/+debug/ · 热重载
- 2026-06-30 · v0.6.1 · 修复 OutputTools 导出脚本集成后无法激活：改为每模块独立合成子包 _maxsd_bundle.* 保留相对 import，避免同名符号互覆盖；提供 maxsd_activate()/maxsd_show_windows 激活入口 · output_tools/ · output_tools 热重载
- 2026-06-30 · v0.6.0 · 热重载改为动态清整包下所有子模块（保留包根+入口），以后新增功能子包无需再改入口 feature_prefixes · 入口+AGENTS · 本次需重启 SD 一次，此后均热重载
- 2026-06-29 · v0.5.2 · OutputTools 选 SD13 导出时做 Qt5 兼容改写（QAction→QtWidgets、枚举、exec_），生成可在 SD13 跑的插件 · output_tools/ · output_tools 热重载
- 2026-06-29 · v0.5.1 · OutputTools 导出加 _maxsd_ 命名空间前缀防撞名；新增目标 SD 版本选择（16.0/PySide6、13.0/PySide2，导出时自动改写导入） · output_tools/ · output_tools 热重载
- 2026-06-29 · v0.5.0 · 新增 OutputTools（输出脚本）：展示所有功能/分支，勾选打包导出为独立 .py · output_tools/+menu+入口 · 首装需重启 SD（feature_prefixes 为入口改动），之后热重载
- 2026-06-29 · v0.4.8 · Publish Checker 新增勾选列+全选/全不选/删除选中节点+右键删除；新增「清理当前图形」(Clean graph(s)) · debug/ · debug 热重载
- 2026-06-29 · v0.4.7 · Publish Checker 扫描完成后提示：状态栏加「扫描完成」，手动重扫弹框提示警告数 · debug/ · debug 热重载
- 2026-06-29 · v0.4.6 · 「缺失依赖包」来源节点识别放宽：res 为 None 的 instance/bitmap/svg 都列为引用来源，可 Goto/删除 · debug/ · debug 热重载
- 2026-06-29 · v0.4.5 · 「缺失依赖包」能定位到引用该依赖的 Ghost 子图实例节点（可 Goto/删除），不再只显示路径 · debug/ · debug 热重载
- 2026-06-29 · v0.4.4 · Check Dependencies 改名 Publish Checker；新增「缺失依赖包」（package.getDependencies 中 .sbs 找不到）与「可清理(未使用)」（同 Clean graph(s) 判定）两类检查 · debug/ · debug 热重载
- 2026-06-29 · v0.4.3 · 去掉 Ghost 检测的 did 前缀限制，子图丢失、定义无法解析（did 为空）的 Ghost Instance 也能被扫出 · output/ · output 热重载
- 2026-06-29 · v0.4.2 · 损坏节点新增「缺失子图(Ghost)」检测，抓出子图丢失的 Ghost Instance（Cooker: Can't find subgraph）· output/ · output 热重载
- 2026-06-29 · v0.4.1 · 损坏节点检测覆盖 bitmap/svg 引用资源丢失（Referenced resource not found，含 pkg:/// 依赖）· output/ · output 热重载
- 2026-06-29 · v0.4.0 · TodoList 改名 ReleaseNote；画布损坏节点列表不再只列 Empty variable，新增「警告类型」列（Empty variable/缺失资源/未连接输出/悬挂节点）；新增「删除当前节点」按钮+右键项 · output/ + 文档 · output 热重载
- 2026-06-29 · v0.3.7 · 菜单重构为数据驱动：入口只建骨架并调 menu.build_menu，版本号/关于/重载/各分类都移到可热重载的 menu.py。以后改菜单不再动入口、无需重启 · MaxSDPlugin.py + menu.py · 本次需重启，之后改菜单热重载
- 2026-06-29 · v0.3.6 · 重载插件仅在入口文件真改动时提示重启；修复重置函数不生效（_reset_broken_node_functions 加传 valid_ids 识别悬空 Get）；“修复损坏函数”改名为“重置函数” · MaxSDPlugin.py + output/ · 入口需重启，output 热重载
- 2026-06-29 · v0.3.5 · 新增「重载插件（Unload→Load）」菜单项（热重载功能模块，未找到主窗口有提示）；修复画布损坏节点右键 Goto 失效（右键先选中该行）· MaxSDPlugin.py + output/exposed_parameters_window.py · 入口需重启，output 热重载
- 2026-06-29 · v0.3.4 · 菜单版本号高亮（粗体+绿色默认项）；损坏节点扫描加入悬空 Get 变量检测（变量名非空但不在图输入/局部 Set）· MaxSDPlugin.py + output/output_data.py · 入口需重启，output 热重载
- 2026-06-29 · v0.3.3 · 版本号移到独立 _version.py 并登记热重载，菜单版本号改为动态读取；Unload→Load 即可刷新版本（本次入口改动需先重启一次） · MaxSDPlugin.py + _version.py · 本次需重启，之后改版本号热重载
- 2026-06-29 · v0.3.2 · 重新梳理曝光参数面板两个列表功能：曝光参数（刷新/全选/全不选/删除勾选/缓存/导出/加载历史）；画布损坏节点（刷新/全选/全不选/勾选修复，未勾选则修全图）· output/ · 功能模块改动 Unload→Load
- 2026-06-29 · v0.3.1 · MaxSDPlugin 菜单顶部直接显示版本号 · 入口 MaxSDPlugin.py · 需重启 SD
- 2026-06-29 · v0.3.0 · 曝光参数面板新增「画布损坏节点（Empty variable）」列表 + 双击/右键 Goto 定位 · output/ · 功能模块改动 Unload→Load
- 2026-06-29 · v0.2.0 · 新增 Debug/Check Dependencies（发布警告扫描+类别筛选+右键Goto）；曝光参数「修复损坏函数」扫描扩展到 Input/Output/Annotation · output/ + debug/ + 入口菜单 · 入口改动需重启 SD，功能模块改动 Unload→Load

[已完成] Output/曝光参数：按 INPUT PARAMETERS / INPUTS 分组枚举（排除 $ 基础参数）+ 勾选 + OutputData 缓存/导出 + 删除（取消暴露：先 deletePropertyGraph 把依赖节点参数重置回常量，再 deleteProperty；UndoGroup 可撤销 + 删前自动备份）+ 加载历史并应用值。待扩展：复杂类型(向量/颜色/枚举)的值还原、已删除参数的重新暴露。

[已完成] Debug/Check Dependencies：发布 sbsar 前扫描当前图，列出可能产生警告的节点（损坏 Get 函数/缺失资源/未连接输出/悬挂节点）+ 可试发布到临时 .sbsar 核对 SD 日志。

显示插件版本
显示软件版本
显示pyside版本

SD的窗口重制
清理无效的依赖
LGSD节点库自动更新
查错功能（设置了默认的分辨率，三面映射的输入设置，）
[已完成] 曝光参数添加开关按钮的设定关联：创建 Boolean 参数，查看 INPUT PARAMETERS / INPUTS 当前 Visible If，并按参数或 Group 批量写入开关表达式。
设置3D预览窗口的摄像机参数
统一修改frame类的A值
检查输出的Identifier 和 Usage 是否一致
提示输出3个通道，避免unity 索引错误