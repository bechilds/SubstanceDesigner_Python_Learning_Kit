# Substance Designer SBSAR 导出警告解决指南

## 🚨 警告信息
```
one or more graphs have input nodes with parameters relative to input
```

## 📖 警告详解

### 含义
这个警告表示您的 Substance 材质图形中存在**输入节点（Input nodes）**，这些节点的参数设置是**相对于输入**的，而不是绝对值。

### 常见情况
1. **Uniform Color 节点**：颜色参数连接到暴露参数
2. **Gradient 节点**：渐变参数通过表达式或连接设置
3. **Input 节点**：位置、缩放、旋转等参数相对于其他输入

### 为什么会产生警告
- Substance Designer 在导出 .sbsar 时检测到相对参数
- 这些相对参数可能在不同应用程序中表现不一致
- 可能影响材质在游戏引擎或其他软件中的显示效果

## 🔍 问题识别

### 手动检查方法
1. **查看暴露参数**
   - 打开 Properties 面板
   - 检查哪些参数被暴露（Exposed）
   - 特别注意输入节点的参数

2. **检查节点连接**
   - 查看输入节点（如 Uniform Color、Gradient）
   - 看是否有参数通过连线从其他节点获取值
   - 检查是否使用了函数或表达式

3. **常见问题节点类型**
   - `sbs::compositing::uniform` (Uniform Color)
   - `sbs::compositing::gradient` (Gradient)
   - `sbs::compositing::input` (Input)
   - 任何自定义输入节点

### 使用脚本检查
运行我提供的 `fix_input_node_parameters.py` 脚本：
1. 在 Substance Designer 中打开有警告的 .sbs 文件
2. 打开 Script Editor
3. 运行脚本查看详细分析

## 🛠️ 解决方法

### 方法 1：取消暴露参数（推荐）
```
对于不需要外部控制的参数：
1. 右键点击有问题的参数
2. 选择 "Unexpose Parameter"
3. 设置一个固定的默认值
```

### 方法 2：断开节点连接
```
对于通过连接获取值的参数：
1. 断开输入连接线
2. 手动设置具体数值
3. 确保值是绝对的，不依赖其他输入
```

### 方法 3：使用 Switch 节点
```
如果需要保持动态性：
1. 使用 Switch 节点控制参数选择
2. 为每个选项设置固定值
3. 通过暴露的整数参数控制切换
```

### 方法 4：烘焙参数值
```
将动态参数转换为静态值：
1. 记录当前参数的具体数值
2. 断开所有连接和暴露
3. 直接输入记录的数值
```

## 📋 具体操作步骤

### 修复 Uniform Color 节点
```
1. 选择有问题的 Uniform Color 节点
2. 在 Properties 面板中查看 Output Color 参数
3. 如果连接到暴露参数：
   - 记录当前颜色值 (如 R:0.5, G:0.3, B:0.8)
   - 右键 → Unexpose Parameter
   - 直接在节点上设置颜色值
```

### 修复 Gradient 节点
```
1. 检查 Gradient 节点的 Position 和 Gradient 参数
2. 如果使用了动态控制：
   - 记录当前渐变设置
   - 断开动态连接
   - 在节点上直接编辑渐变
```

### 修复位置/缩放参数
```
1. 查看节点的 Offset、Tiling、Rotation 参数
2. 如果连接到其他节点：
   - 记录当前的 X、Y 值
   - 断开连接
   - 直接输入数值（如 Offset X: 0.0, Y: 0.0）
```

## ⚠️ 注意事项

### 保留的相对参数
以下情况可能需要保留相对参数：
- 材质需要在不同尺寸下自适应
- 参数需要根据用户输入动态调整
- 材质用于程序化生成变体

### 测试建议
1. **导出测试**：修复后重新导出 .sbsar 检查警告是否消失
2. **功能测试**：确保材质在目标应用中正常显示
3. **参数测试**：验证暴露的参数仍能正常工作

### 备份建议
- 修改前保存文件副本
- 记录原始参数设置
- 可以使用版本控制跟踪修改

## 🎯 最佳实践

### 设计时预防
1. **尽量使用绝对值**：在输入节点中直接设置具体数值
2. **减少不必要的暴露参数**：只暴露真正需要外部控制的参数
3. **避免复杂的参数链**：减少参数间的相互依赖
4. **使用固定的基础值**：为动态参数设置合理的默认值

### 导出前检查
1. 运行检查脚本分析潜在问题
2. 验证所有暴露参数的必要性
3. 测试材质在目标平台的表现
4. 确认警告信息已消除

## 📚 相关文档

- [Substance Designer Python API](https://substance3d.adobe.com/documentation/sddoc/python-api-184191934.html)
- [SBSAR 格式说明](https://substance3d.adobe.com/documentation/sddoc/sbsar-format-184257730.html)
- [参数暴露最佳实践](https://substance3d.adobe.com/documentation/sddoc/exposing-parameters-184257724.html)

---

*使用提供的 Python 脚本可以自动检测和分析这些问题，帮助您快速定位需要修复的节点和参数。*