#这个文件是教程作者拆分出来的一个子文件，主要用于定义一个窗口类window。

from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools
# 导入 PySide2 模块 用于界面操作,pyside2 是qt的python接口,QtWidgets用于创建和操作GUI元素，QtCore包含核心非GUI功能，QtGui用于图形相关功能，QtUiTools用于加载.ui文件


#教程作者发现拆除多个文件后，在substance designer中调试时，需要重启SD才能更新插件，很不方便。所以后续将这部分功能合并到一个文件中，方便调试。
#但是教程后续没有再拆解除这个文件了。所以这个文件实际上没有被使用到。

#构建window类，继承自QtWidgets.QDialog
class window(QtWidgets.QDialog):

    # 子类window的初始化函数，构建了传入父窗口的参数parent，包管理器pkg_mgr，UI管理器ui_mgr
    def __init__(self,parent,pkg_mgr,ui_mgr): 
        
        #super()是用来调用父类的方法的，语法是 super(子类名, self).方法名()，通过super()就可以访问父类的方法__init__().
        #__init__() 是父类构造函数，在子类初始化的时候，必须调用父类的构造函数，否则，子类实例将没有父类的属性和方法。
        # 这里调用父类的__init__()方法，按照参数位置传入子类window的parent参数（也可以叫其他参数名），确保子类window正确继承父类QtWidgets.QDialog的属性和行为。

        super(window, self).__init__(parent)

        
        
        # pkg_mgr 是传入 __init__ 函数的临时参数。
        # self.pkg_mgr = pkg_mgr 是在 __init__ 执行期间，把这个临时参数的值，赋值给类实例的一个永久属性（也叫 pkg_mgr）。
        # 这行代码是为了把外部传入的工具，保存到类实例身上，方便类的其他方法（不仅仅是 __init__ 内部）在未来随时调用
        self.pkg_mgr = pkg_mgr 
        self.ui_mgr = ui_mgr


        #self.window ，！！！AI对这句有疑问，认为冗余。后面再测试理解！！！
        self.window = QtWidgets.QDialog(parent=parent) #创建一个对话框窗口，parent是父窗口

        # 设置窗口标题,进行测试
        layout = QtWidgets.QVBoxLayout() #创建一个垂直布局管理器，用于管理窗口中的控件布局
        self.testLineEdit = QtWidgets.QLineEdit("Test") #创建一个单行文本编辑框
        layout.addWidget(self.testLineEdit) #把文本编辑框添加到布局管理器中
        self.window.setLayout(layout) #把布局管理器设置为窗口的布局


    def show(self):
        self.window.show()