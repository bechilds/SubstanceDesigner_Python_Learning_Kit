### 这是SD插件的基本示例。


 ###官方代码如下，并不能直接被SD加载
# def initializeSDPlugin():
#     print("Plugin initialized")

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.uimgr import SDUIMgr  # 用于操作UI

# 全局变量存储菜单ID，方便卸载时清理
g_menu_id = None

def initializeSDPlugin():
    global g_menu_id
    print("我的插件已加载！")
    
    # 获取UI管理器
    ui_mgr = sd.getContext().getSDApplication().getUIMgr()
    
    # 向主菜单添加一个新菜单"我的工具"
    # 参数：父菜单ID（None表示添加到顶级）、菜单名称、图标（可选）
    g_menu_id = ui_mgr.newMenu(None, "我的工具", "")
    
    # 向"我的工具"菜单添加一个菜单项"创建噪波节点"
    ui_mgr.newMenuItem(
        menuId=g_menu_id,
        name="创建噪波节点",
        callback=create_noise_node,  # 点击后执行的函数
        tooltip="在当前图表创建一个自定义噪波节点"
    )

def create_noise_node():
    """点击菜单项时执行的函数"""
    try:
        # 获取当前图表
        app = sd.getContext().getSDApplication()
        graph = app.getPackageMgr().getCurrentGraph()
        
        if graph and isinstance(graph, SDSBSCompGraph):
            # 创建噪波节点
            noise_node = graph.newNode("sbs::compositing::noise")
            noise_node.setPosition(300, 300)
            noise_node.setDisplayName("插件创建的噪波")
            print("已创建噪波节点！")
        else:
            print("请先打开一个合成图表")
    except Exception as e:
        print(f"操作失败：{e}")

def uninitializeSDPlugin():
    global g_menu_id
    print("我的插件已卸载！")
    
    # 清理：移除自定义菜单
    if g_menu_id:
        ui_mgr = sd.getContext().getSDApplication().getUIMgr()
        ui_mgr.deleteMenu(g_menu_id)
        g_menu_id = None