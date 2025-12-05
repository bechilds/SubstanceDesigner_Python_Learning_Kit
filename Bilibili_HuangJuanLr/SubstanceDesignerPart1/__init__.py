import sd  # designer sdk
import os  # 导入os模块


#按需导入功能模块
from sd.api.sdproperty import SDPropertyCategory # 导入参数类型枚举，用于调用 getProperties() 方法
from sd.api.sdbasetypes import float2 , float4 # 导入基础类型模块 ,getPosition() 方法返回 float2 类型,python没有内置的二维向量类型，需要导入 float2 类型来表示二维向量，这里的sd.api.sdbasetypes.float2 就是SD提供的二维向量类型
#导入 float4 类型模块，用于表示四维向量，在sdvaluefloat4 中
from sd.api.sdvaluefloat4 import SDValueFloat4 # 导入 float4 类型模块，用于设置颜色值,sbs::compositing::uniform 节点的颜色属性是一个四维向量，表示 RGBA 颜色值，因此需要使用 SDValueFloat4 类型来设置该属性的值,这个类中内置一个Static静态函数 SNew() 创建一个 SDValueFloat4 对象，这个对象需要sd.api.sdbasetypes.float4 类型的参数.
#静态方法 sNew 是在 SDValueFloat4 类上调用的，所以它的作用是创建一个 SDValueFloat4 的新实例，而不是 sdbasetypes.float4。它的函数原型应该是这样的（概念上的）：
# static sNew(value: sdbasetypes.float4) -> SDValueFloat4
# 输入: 它接收一个基础数据类型的对象，也就是一个 “现金” (sdbasetypes.float4) 。
# 输出: 它返回一个封装好的值对象，也就是一个 “钱包” (SDValueFloat4) 。
# 所以，这个方法确实实现了我们之前讨论的“反向”过程：
# sdbasetypes.float4 --- (通过 SDValueFloat4.sNew() 方法) ---> SDValueFloat4
from sd.api.sdvaluefloat import SDValueFloat # 导入 float 类型模块，用于设置数值属性,sbs::compositing::hue节点的Hue属性是一个浮点数值，因此需要使用 SDValueFloat 类型来设置该属性的值，这个类中内置一个Static静态函数 SNew() 创建一个 SDValueFloat 对象，这个对象需要float类型的参数.

from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools # 导入 PySide2 模块 用于界面操作,pyside2 是qt的python接口,QtWidgets用于创建和操作GUI元素，QtCore包含核心非GUI功能，QtGui用于图形相关功能，QtUiTools用于加载.ui文件




context = sd.getContext()  # 获取上下文，SD 插件入口
app = context.getSDApplication()  # 获取应用对象

pkg_mgr = app.getPackageMgr()  # 获取包管理器
ui_mgr = app.getQtForPythonUIMgr() ## 获取 Qt UI 管理器

all_packages = pkg_mgr.getPackages() # 获取所有包列表


#方法1：获取package 路径
# for package in all_packages:
#     print(package.getFilePath())



#方法2：通过路径 加载 .sbsar 包
# --- 加载 .sbsar 包 ---
# sbsar_path = os.path.join("E:/ProjcetFiles/SubstanceDesigner_Python_Learning_Kit/importsbsfiles", "Importtest.sbsar")

# # loadUserPackage 返回一个 Package 对象
# loaded_package = pkg_mgr.loadUserPackage(sbsar_path)

# if loaded_package is not None:
#     package_file_path = loaded_package.getFilePath()  # ✅ 在卸载前获取路径
#     print(f"成功加载包: {package_file_path}")
# else:
#     print(f"加载包失败: {sbsar_path}")
#     loaded_package = None

# # --- 卸载 .sbsar 包 ---
# if loaded_package is not None:
#     try:
#         pkg_mgr.unloadUserPackage(loaded_package)
#         # ✅ 使用之前保存的路径字符串，而不是调用已卸载对象的方法
#         print(f"成功卸载包: {package_file_path}")
#     except Exception as e: # 捕获异常并将错误信息赋值到变量 e
#         print(f"卸载包时出错: {e}")
# else:
    # print("未加载有效的包，跳过卸载步骤。")


#方法3：通过graph加载 .sbsar 包
# graph = ui_mgr.getCurrentGraph()    # 获取当前图形
# cur_pkg = graph.getPackage()           #获取当前包
# cur_pkg_path = os.path.dirname(cur_pkg.getFilePath())            #获取包的目录路径
# sbsar_dir = os.path.join(cur_pkg_path,"importsbsfiles","Importtest.sbsar")  #拼接资源路径
# pkg = pkg_mgr.loadUserPackage(sbsar_dir)#加载包


# res = pkg.findResourceFromUrl("Substance_graph")#通过资源URL查找资源
# graph.newInstanceNode(res) #新增实例节点，需要依赖包

# pkg_mgr.unloadUserPackage(pkg)#卸载包

# graph.newNode("sbs::compositing::blend") #新增节点，SD内置的节点


#方法4：通过图形获取当前节点，使用节点的方法获取节点相关参数属性
graph = ui_mgr.getCurrentGraph()    # 获取当前图形
# all_nodes = graph.getNodes() #获取所有节点
# selected_node = ui_mgr.getCurrentGraphSelectedNodes()#获取当前选中的节点,返回一个列表


# for node in selected_node: #遍历所有节点
#     print(node.getDefinition()) #获取节点定义
#     print(node.getIdentifier()) #获取节点标识符
#     print(node.getDefinition().getId()) #获取节点定义的ID


#方法5：通过getProperties()方法获取节点的属性
#Annotation 备注 节点的描述信息，Attribute 属性 节点的属性
#input   输入 BASE PARAMETER 输入值
#output  输出  当前图表的输出
# selected_props = selected_node[0].getProperties(SDPropertyCategory.Annotation)
#使用getProperties()方法获取节点的属性,需要导入SDPropertyCategory模块
# for prop in selected_props: #遍历所有属性
#     print(prop.getType()) #获取属性类型 
#     print(prop.getCategory()) #获取属性类别  SDPropertyType annotation input output parameter
#     print(prop.getId()) #获取属性ID


#方法6：创建节点，并将其链接到当前选择的节点上
# selected_props = selected_node[0].getProperties(SDPropertyCategory.Output) #Prop 是 property 的缩写形式，为了方便，业内人员通常把 theatrical property（舞台道具）简称为 prop

# uniform_color_node = graph.newNode("sbs::compositing::uniform")#新增节点
# uniform_color_node.newPropertyConnectionFromId("unique_filter_output",selected_node[0],"basecolor") #newPropertyConnectionFromId(目标属性ID,源节点,源属性ID),选择节点的属性连接


# #方法7，获取选择节点的位置，并设置新增节点位置

# processor_pos = selected_node[0].getPosition() #获取选择节点位置,导入sdbasetypes模块的float2类型
# uniform_color_node.setPosition(float2(processor_pos.x-200,processor_pos.y)) #设置新增节点位置

# #方法8：设置uniform节点输出颜色
# #output_color = uniform_color_node.getPropertyValueFromId("outputcolor") #getPropertyValueFromId(属性ID)是获取属性值的方法，应该先获取属性对象，再获取属性值
# output_color = uniform_color_node.getPropertyFromId("outputcolor",SDPropertyCategory.Input) #获取属性对象，getPropertyFromId(属性ID,属性类别)
# uniform_color_node.setPropertyValue(output_color, SDValueFloat4.sNew(float4(1.0, 0.0, 0.0, 1.0)))#SetPropertyValue(属性对象,属性值),设置属性值的方法，需要导入sdvaluefloat4模块的SDValueFloat4类型和sdbasetypes模块的float4类型



#方法9：获取当前选择节点的Hue,Saturation,Lightness属性
# hue = selected_node[0].getPropertyFromId("hue",SDPropertyCategory.Input)  # 在当前课程节点的proceesor中，Identifier hue,Label 为Hue.getPropertyFromId("hue",SDPropertyCategory.Input), 获取的应该是Identifier hue。
# Saturation = selected_node[0].getPropertyFromId("saturation",SDPropertyCategory.Input)#在当前课程节点的proceesor中，Identifier saturation,Label 为Saturation.getPropertyFromId("saturation",SDPropertyCategory.Input), 获取的应该是Identifier saturation。
# Lightness = selected_node[0].getPropertyFromId("luminosity",SDPropertyCategory.Input) #在当前课程节点的proceesor中，Identifier luminosity,Label 为Lightness.getPropertyFromId("luminosity",SDPropertyCategory.Input), 获取的应该是Identifier luminosity。


# selected_node[0].setPropertyValue(hue, SDValueFloat.sNew(0.5)) #设置Hue属性值
# selected_node[0].setPropertyValue(Saturation, SDValueFloat.sNew(0.8)) #设置Saturation属性值
# selected_node[0].setPropertyValue(Lightness, SDValueFloat.sNew(0.2)) #设置Lightness属性值



#方法10：创建substance 的Dialog对话窗口
main_window = ui_mgr.getMainWindow() #获取主窗口对象

menu_id = "TestDialogMenu" + "#123"  # 创建菜单ID，确保唯一性，+ #123 是为了确保唯一性


dialog = QtWidgets.QDialog(parent=main_window) #创建对话窗口，指定主窗口为父窗口
# dialog.show() #显示对话窗口


def test_function():
    # print("测试窗口创建成功")
    dialog.show() #显示对话窗口

menu_bar = main_window.menuBar() #获取主窗口的菜单栏

menu = ui_mgr.findMenuFromObjectName(menu_id) #通过菜单ID查找菜单对象
if menu is not None:
    ui_mgr.deleteMenu(menu_id) #删除已存在的菜单，避免重复创建


menu = QtWidgets.QMenu("TEST",menu_bar)#创建菜单对象

menu.setObjectName(menu_id)

menu_bar.addMenu(menu) #将菜单添加到菜单栏
action = QtWidgets.QAction("Open Test Dialog",menu) #创建菜单项对象,QAction再pyside6中移到了QtGui模块下(菜单项名称,父对象)
action.triggered.connect(test_function) #将菜单项的触发信号连接到对话窗口的显示槽函数
menu.addAction(action) #将菜单项添加到菜单

# 插件初始化函数 SD 会自动调用 必须存在 才能被识别
def initializeSDPlugin():
    pass

def uninitializeSDPlugin():
    pass