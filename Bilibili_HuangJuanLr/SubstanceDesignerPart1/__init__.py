import sd  # designer sdk
import os  # 导入os模块


#按需导入功能模块
from sd.api.sdproperty import SDPropertyCategory # 属性类

context = sd.getContext()  # 获取上下文，SD 插件入口
app = context.getSDApplication()  # 获取应用对象

pkg_mgr = app.getPackageMgr()  # 获取包管理器
ui_mgr = app.getQtForPythonUIMgr() ## 获取 Qt UI 管理器


# 获取所有包
all_packages = pkg_mgr.getPackages()

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


#方法4：获取当前节点的属性
graph = ui_mgr.getCurrentGraph()    # 获取当前图形
all_nodes = graph.getNodes() #获取所有节点
selected_node = ui_mgr.getCurrentGraphSelectedNodes()#获取当前选中的节点

for node in selected_node: #遍历所有节点
    print(node.getDefinition()) #获取节点定义
    print(node.getIdentifier()) #获取节点标识符
    print(node.getDefinition().getId()) #获取节点定义的ID



# 插件初始化函数 SD 会自动调用 必须存在 才能被识别
def initializeSDPlugin(): 
    pass

def uninitializeSDPlugin():
    pass