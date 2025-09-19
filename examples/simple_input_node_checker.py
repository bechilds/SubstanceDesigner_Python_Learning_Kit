"""
简化版输入节点参数检查工具 - Simple Input Node Parameter Checker
================================================================

这是一个简化版本的脚本，用于检查 Substance Designer 中可能导致 
"one or more graphs have input nodes with parameters relative to input" 
警告的问题。

使用方法：
1. 在 Substance Designer 中打开有警告的 .sbs 文件
2. 在脚本编辑器中运行此脚本
3. 查看输出的分析结果和建议
"""

import sd

def main():
    """主函数 - 检查输入节点参数问题"""
    print("🔧 简化版输入节点参数检查工具")
    print("=" * 45)
    
    try:
        # 连接到 Substance Designer
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        
        # 获取当前包
        packages = package_mgr.getUserPackages()
        if not packages:
            print("❌ 未找到已加载的包，请先打开一个 .sbs 文件")
            return
        
        current_package = packages[0]
        print(f"📦 当前包: {current_package.getFilePath()}")
        
        # 获取当前图形
        try:
            # 尝试不同的方法获取图形
            graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        except:
            try:
                # 备用方法
                graphs = current_package.getGraphs()
            except:
                try:
                    # 另一种备用方法
                    all_definitions = current_package.getChildrenOfType(sd.api.sddefinition.SDDefinition)
                    graphs = [d for d in all_definitions if hasattr(d, 'getNodes')]
                except:
                    print("❌ 无法获取图形，尝试使用包管理器的其他方法")
                    graphs = []
        
        if not graphs:
            print("❌ 未找到图形")
            return
        
        current_graph = graphs[0]
        print(f"📊 分析图形: {current_graph.getIdentifier()}")
        print()
        
        # 获取所有节点
        nodes = current_graph.getNodes()
        print(f"🔍 找到 {len(nodes)} 个节点")
        
        # 查找可能有问题的输入节点
        problem_found = False
        input_node_types = ['uniform', 'gradient', 'input', 'bitmap']
        
        for node in nodes:
            node_id = node.getIdentifier()
            node_type = node.getDefinition().getId().lower()
            
            # 检查是否为输入类型节点
            is_input_node = any(keyword in node_type for keyword in input_node_types)
            
            if is_input_node:
                print(f"\n🔧 检查输入节点: {node_id}")
                print(f"   类型: {node.getDefinition().getId()}")
                
                # 检查是否有可能的相对参数问题
                has_issues = False
                
                try:
                    # 检查节点的输入属性
                    input_props = node.getProperties(sd.api.sdproperty.SDPropertyCategory.Input)
                    
                    for prop in input_props:
                        prop_id = prop.getId()
                        prop_label = prop.getLabel()
                        
                        # 检查暴露参数
                        if hasattr(prop, 'isConnectedToExposedParameter') and prop.isConnectedToExposedParameter():
                            print(f"   ⚠️  参数 '{prop_label}' ({prop_id}) 连接到暴露参数")
                            has_issues = True
                            problem_found = True
                        
                        # 检查节点连接
                        if hasattr(prop, 'getConnections'):
                            connections = prop.getConnections()
                            if connections and len(connections) > 0:
                                print(f"   ⚠️  参数 '{prop_label}' ({prop_id}) 有输入连接")
                                has_issues = True
                                problem_found = True
                
                except Exception as e:
                    print(f"   ❓ 检查参数时出错: {e}")
                
                if not has_issues:
                    print(f"   ✅ 未发现问题")
        
        # 检查暴露参数
        print(f"\n📋 检查暴露参数...")
        exposed_params = current_graph.getExposedParameters()
        print(f"找到 {len(exposed_params)} 个暴露参数")
        
        for param in exposed_params:
            param_id = param.getId()
            param_label = param.getLabel()
            param_group = param.getGroup()
            
            # 检查连接的属性
            try:
                connected_props = param.getConnectedProperties()
                for prop in connected_props:
                    node = prop.getNode()
                    node_type = node.getDefinition().getId().lower()
                    
                    # 检查是否连接到输入节点
                    if any(keyword in node_type for keyword in input_node_types):
                        print(f"   ⚠️  暴露参数 '{param_label}' 连接到输入节点 {node.getIdentifier()}")
                        problem_found = True
            
            except Exception as e:
                print(f"   ❓ 检查暴露参数连接时出错: {e}")
        
        # 提供建议
        print(f"\n💡 分析结果:")
        if problem_found:
            print(f"   ❌ 发现可能导致警告的问题!")
            print(f"\n🛠️  修复建议:")
            print(f"   1. 取消不必要的参数暴露:")
            print(f"      - 右键点击参数 → 选择 'Unexpose Parameter'")
            print(f"      - 为参数设置固定的默认值")
            print(f"   2. 断开输入节点的动态连接:")
            print(f"      - 断开连接线")
            print(f"      - 直接在节点上设置具体数值")
            print(f"   3. 使用绝对值而非相对值:")
            print(f"      - 避免参数间的相互依赖")
            print(f"      - 设置明确的数值（如颜色 RGB、位置坐标等）")
        else:
            print(f"   ✅ 未发现明显的相对参数问题")
            print(f"   💡 如果仍有警告，可能是其他类型的相对设置")
        
        print(f"\n📖 关于警告的说明:")
        print(f"   'one or more graphs have input nodes with parameters relative to input'")
        print(f"   表示输入节点使用了相对参数设置，可能在不同应用中表现不一致。")
        print(f"   虽然不会阻止导出，但建议修复以确保材质稳定性。")
        
        print(f"\n✅ 检查完成!")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print(f"\n💡 故障排除提示:")
        print(f"   - 确保 Substance Designer 正在运行")
        print(f"   - 在运行脚本前打开一个 .sbs 文件")
        print(f"   - 检查文件是否不是只读状态")

if __name__ == "__main__":
    main()