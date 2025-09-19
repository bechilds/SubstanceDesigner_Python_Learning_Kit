"""
超简化版输入节点参数检查工具 - Ultra Simple Input Node Parameter Checker
=======================================================================

这是一个超简化版本的脚本，用于检查 Substance Designer 中可能导致 
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
    print("🔧 超简化版输入节点参数检查工具")
    print("=" * 50)
    
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
        
        # 尝试获取图形 - 使用最简单的方法
        print(f"🔍 尝试获取图形信息...")
        
        try:
            # 方法1：直接从包获取定义
            definitions = []
            for i in range(current_package.getChildCount()):
                child = current_package.getChildAt(i)
                definitions.append(child)
            
            print(f"📊 找到 {len(definitions)} 个定义")
            
            # 查找图形定义
            graphs = []
            for definition in definitions:
                try:
                    # 检查是否有getNodes方法（表示这是一个图形）
                    if hasattr(definition, 'getNodes'):
                        graphs.append(definition)
                        print(f"   📈 图形: {definition.getIdentifier()}")
                except:
                    continue
            
            if not graphs:
                print("❌ 未找到可用的图形定义")
                print("💡 这可能意味着:")
                print("   - 文件没有完全加载")
                print("   - 文件格式不兼容")
                print("   - 需要在Substance Designer中完全打开文件")
                return
            
            # 分析第一个图形
            current_graph = graphs[0]
            print(f"\n📊 分析图形: {current_graph.getIdentifier()}")
            
            # 获取所有节点
            nodes = current_graph.getNodes()
            print(f"🔍 找到 {len(nodes)} 个节点")
            
            # 检查暴露参数
            print(f"\n📋 检查暴露参数...")
            exposed_params = current_graph.getExposedParameters()
            print(f"找到 {len(exposed_params)} 个暴露参数")
            
            problem_found = False
            
            if len(exposed_params) > 0:
                print(f"\n暴露参数列表:")
                for i, param in enumerate(exposed_params):
                    param_id = param.getId()
                    param_label = param.getLabel()
                    param_group = param.getGroup()
                    print(f"   {i+1}. {param_label} ({param_id}) - 组: {param_group}")
                    
                    # 简单检查：如果有很多暴露参数，可能就是问题所在
                    if i < 10:  # 只检查前10个避免输出过多
                        try:
                            connected_props = param.getConnectedProperties()
                            if connected_props:
                                for prop in connected_props:
                                    node = prop.getNode()
                                    node_type = node.getDefinition().getId()
                                    print(f"      → 连接到节点: {node.getIdentifier()} ({node_type})")
                                    
                                    # 检查是否连接到常见的输入节点类型
                                    if any(keyword in node_type.lower() for keyword in ['uniform', 'gradient', 'input']):
                                        print(f"      ⚠️  这是一个输入节点连接！")
                                        problem_found = True
                        except Exception as e:
                            print(f"      ❓ 检查连接时出错: {e}")
            
            # 简单的节点类型统计
            print(f"\n🔧 节点类型分析:")
            node_types = {}
            input_nodes = []
            
            for node in nodes:
                try:
                    node_type = node.getDefinition().getId()
                    simple_type = node_type.split('::')[-1] if '::' in node_type else node_type
                    node_types[simple_type] = node_types.get(simple_type, 0) + 1
                    
                    # 检查输入节点
                    if any(keyword in node_type.lower() for keyword in ['uniform', 'gradient', 'input', 'bitmap']):
                        input_nodes.append(node)
                except:
                    continue
            
            # 显示节点类型统计（前10个最常见的）
            sorted_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)[:10]
            for node_type, count in sorted_types:
                print(f"   {node_type}: {count}")
            
            print(f"\n🎯 输入节点分析:")
            print(f"找到 {len(input_nodes)} 个输入类型节点")
            
            for node in input_nodes[:5]:  # 只显示前5个
                print(f"   🔧 {node.getIdentifier()} - {node.getDefinition().getId()}")
            
            if len(input_nodes) > 5:
                print(f"   ... 还有 {len(input_nodes) - 5} 个输入节点")
            
            # 分析结果
            print(f"\n💡 分析结果:")
            
            if len(exposed_params) > 10:
                print(f"   ⚠️  暴露参数较多 ({len(exposed_params)} 个) - 这可能是警告的原因")
                problem_found = True
            
            if len(input_nodes) > 0 and len(exposed_params) > 0:
                print(f"   ⚠️  存在输入节点和暴露参数 - 可能存在相对参数问题")
                problem_found = True
            
            if problem_found:
                print(f"\n🛠️  修复建议:")
                print(f"   1. 减少暴露参数数量:")
                print(f"      - 只保留真正需要外部控制的参数")
                print(f"      - 取消不必要的参数暴露")
                print(f"   2. 检查输入节点:")
                print(f"      - 确保Uniform Color、Gradient等节点使用固定值")
                print(f"      - 避免这些节点的参数被暴露或连接")
                print(f"   3. 使用绝对值:")
                print(f"      - 为颜色、位置等参数设置具体数值")
                print(f"      - 避免参数间的动态依赖关系")
            else:
                print(f"   ✅ 未发现明显的相对参数问题")
                print(f"   💡 警告可能来自其他更复杂的参数设置")
            
        except Exception as e:
            print(f"❌ 分析图形时出错: {e}")
            print(f"💡 可能的原因:")
            print(f"   - 文件格式问题")
            print(f"   - Substance Designer版本兼容性")
            print(f"   - 文件没有完全加载")
        
        print(f"\n📖 关于警告的说明:")
        print(f"   'one or more graphs have input nodes with parameters relative to input'")
        print(f"   这个警告表示材质中的输入节点参数设置是相对的，不是绝对值。")
        print(f"   常见原因：暴露的Uniform Color、Gradient参数，或节点间的动态连接。")
        
        print(f"\n✅ 检查完成!")
        
    except Exception as e:
        print(f"❌ 主要错误: {str(e)}")
        print(f"\n💡 故障排除提示:")
        print(f"   - 确保 Substance Designer 正在运行")
        print(f"   - 确保 .sbs 文件已完全加载")
        print(f"   - 尝试关闭并重新打开文件")
        print(f"   - 检查Substance Designer版本是否支持Python脚本")

if __name__ == "__main__":
    main()