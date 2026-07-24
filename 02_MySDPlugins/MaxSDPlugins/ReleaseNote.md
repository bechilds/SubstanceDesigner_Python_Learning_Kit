我的插件功能计划
插件名称：MaxSDPlugin

## 更新记录（格式：日期 · vX.Y.Z · 改动 · 影响范围 · 是否需重启 SD）
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
曝光参数添加开关按钮的设定关联
设置3D预览窗口的摄像机参数
统一修改frame类的A值
检查输出的Identifier 和 Usage 是否一致
提示输出3个通道，避免unity 索引错误