"""
修复输入节点相对参数警告 - Fix Input Node Parameters Warning
=========================================================

这个脚本用于检查和修复 Substance Designer 中导致 "one or more graphs have input nodes 
with parameters relative to input" 警告的问题。

警告含义：
- 材质图形中的输入节点有相对于输入的参数设置
- 这可能导致导出的 .sbsar 文件在不同环境中表现不一致

使用方法：
1. 在 Substance Designer 中打开有警告的 .sbs 文件
2. 在脚本编辑器中运行此脚本
3. 按照提示检查和修复相对参数问题
"""

import sd
from sd.api.sdproperty import *
from sd.api.sdvaluearray import *
from sd.api.sdvaluecolorrgba import *
from sd.api.sdvaluefloat import *
from sd.api.sdvalueint import *

class InputNodeChecker:
    """检查和修复输入节点参数的工具类"""
    
    def __init__(self):
        self.context = sd.getContext()
        self.app = self.context.getSDApplication()
        self.package_mgr = self.app.getPackageMgr()
    
    def get_current_graph(self):
        """获取当前活动的图形"""
        packages = self.package_mgr.getUserPackages()
        if not packages:
            raise Exception("未找到已加载的包，请先打开一个 .sbs 文件")
        
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if not graphs:
            raise Exception("当前包中未找到图形")
        
        return graphs[0]
    
    def find_input_nodes(self, graph):
        """查找图形中的所有输入节点"""
        nodes = graph.getNodes()
        input_nodes = []
        
        for node in nodes:
            node_def = node.getDefinition()
            node_id = node_def.getId().lower()
            
            # 检查是否为输入类型节点
            if any(keyword in node_id for keyword in ['input', 'uniform', 'gradient']):
                input_nodes.append(node)
        
        return input_nodes
    
    def check_relative_parameters(self, node):
        """检查节点是否有相对参数设置"""
        relative_params = []
        
        try:
            # 获取节点的输入属性
            input_props = node.getProperties(sd.api.sdproperty.SDPropertyCategory.Input)
            
            for prop in input_props:
                prop_id = prop.getId()
                prop_label = prop.getLabel()
                
                # 检查是否连接到暴露参数（这可能导致相对性）
                if prop.isConnectedToExposedParameter():
                    relative_params.append({
                        'property': prop,
                        'id': prop_id,
                        'label': prop_label,
                        'type': 'exposed_parameter'
                    })
                
                # 检查是否有连接（可能来自其他节点）
                elif prop.getConnections():
                    relative_params.append({
                        'property': prop,
                        'id': prop_id,
                        'label': prop_label,
                        'type': 'node_connection'
                    })
        
        except Exception as e:
            print(f"检查节点 {node.getIdentifier()} 时出错: {e}")
        
        return relative_params
    
    def get_parameter_value_info(self, prop):
        """获取参数值的详细信息"""
        try:
            value = prop.getValue()
            value_type = type(value).__name__
            
            # 尝试获取更多详细信息
            if hasattr(value, 'get'):
                if value_type == 'SDValueFloat':
                    return f"Float: {value.get()}"
                elif value_type == 'SDValueInt':
                    return f"Int: {value.get()}"
                elif value_type == 'SDValueColorRGBA':
                    rgba = value.get()
                    return f"Color: R={rgba.r:.3f}, G={rgba.g:.3f}, B={rgba.b:.3f}, A={rgba.a:.3f}"
                elif 'Vector2' in value_type:
                    try:
                        vec = value.get()
                        return f"Vector2: X={vec.x:.3f}, Y={vec.y:.3f}"
                    except:
                        return f"Vector2: {str(value)}"
                elif 'Vector3' in value_type:
                    try:
                        vec = value.get()
                        return f"Vector3: X={vec.x:.3f}, Y={vec.y:.3f}, Z={vec.z:.3f}"
                    except:
                        return f"Vector3: {str(value)}"
            
            return f"{value_type}: {str(value)}"
            
        except Exception as e:
            return f"无法获取值: {e}"
    
    def analyze_graph(self, graph):
        """分析图形中的输入节点问题"""
        print(f"🔍 分析图形: {graph.getIdentifier()}")
        print("=" * 50)
        
        input_nodes = self.find_input_nodes(graph)
        print(f"📊 找到 {len(input_nodes)} 个可能的输入节点")
        
        problematic_nodes = []
        
        for i, node in enumerate(input_nodes):
            node_id = node.getIdentifier()
            node_type = node.getDefinition().getId()
            
            print(f"\n🔧 检查节点 {i+1}: {node_id}")
            print(f"   类型: {node_type}")
            
            relative_params = self.check_relative_parameters(node)
            
            if relative_params:
                problematic_nodes.append({
                    'node': node,
                    'relative_params': relative_params
                })
                
                print(f"   ⚠️  发现 {len(relative_params)} 个相对参数:")
                
                for param in relative_params:
                    prop = param['property']
                    value_info = self.get_parameter_value_info(prop)
                    
                    print(f"      - {param['label']} ({param['id']})")
                    print(f"        类型: {param['type']}")
                    print(f"        值: {value_info}")
                    
                    if param['type'] == 'exposed_parameter':
                        exposed_param = prop.getExposedParameter()
                        if exposed_param:
                            print(f"        暴露参数: {exposed_param.getLabel()}")
                    
                    elif param['type'] == 'node_connection':
                        connections = prop.getConnections()
                        for conn in connections:
                            source_node = conn.getInputProperty().getNode()
                            print(f"        连接来源: {source_node.getIdentifier()}")
            else:
                print(f"   ✅ 未发现相对参数问题")
        
        return problematic_nodes
    
    def suggest_fixes(self, problematic_nodes):
        """建议修复方案"""
        if not problematic_nodes:
            print("\n🎉 未发现需要修复的问题！")
            return
        
        print(f"\n🛠️  修复建议:")
        print("=" * 30)
        
        for i, node_info in enumerate(problematic_nodes):
            node = node_info['node']
            relative_params = node_info['relative_params']
            
            print(f"\n{i+1}. 节点: {node.getIdentifier()}")
            
            for param in relative_params:
                print(f"   参数: {param['label']}")
                
                if param['type'] == 'exposed_parameter':
                    print(f"      💡 建议: 考虑取消暴露此参数，使用固定值")
                    print(f"      操作: 在图形中右键点击参数 → 取消暴露")
                
                elif param['type'] == 'node_connection':
                    print(f"      💡 建议: 考虑断开连接，使用直接设置的值")
                    print(f"      操作: 断开输入连接，手动设置参数值")
        
        print(f"\n📋 通用建议:")
        print(f"   1. 对于位置、缩放、旋转等参数，尽量使用绝对值")
        print(f"   2. 避免在输入节点上使用过多的动态参数")
        print(f"   3. 如果必须使用相对参数，确保在目标平台上测试")
        print(f"   4. 考虑在导出前将动态参数'烘焙'为固定值")

def main():
    """主函数"""
    print("🔧 输入节点相对参数检查工具")
    print("=" * 40)
    
    try:
        checker = InputNodeChecker()
        graph = checker.get_current_graph()
        
        # 分析图形
        problematic_nodes = checker.analyze_graph(graph)
        
        # 提供修复建议
        checker.suggest_fixes(problematic_nodes)
        
        if problematic_nodes:
            print(f"\n📖 关于警告 'one or more graphs have input nodes with parameters relative to input':")
            print(f"   这个警告表示您的材质中有输入节点使用了相对参数设置。")
            print(f"   虽然不会阻止导出，但可能在其他应用中产生不一致的结果。")
            print(f"   建议按照上述建议进行调整，以确保材质的稳定性。")
        
        print(f"\n✅ 检查完成!")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print(f"\n💡 故障排除提示:")
        print(f"   - 确保 Substance Designer 正在运行")
        print(f"   - 在运行脚本前打开一个 .sbs 文件")
        print(f"   - 检查文件是否不是只读状态")

if __name__ == "__main__":
    main()