# 教程：从零实现一个 Substance Designer 顶层菜单插件（LGNode）

> 目标：在 Substance Designer 主菜单栏中添加一个名为 **LGNode** 的新菜单，并包含一个可点击的测试动作。
>
> 难度：入门
>
> 适合：刚开始学习 Substance Designer Python 的你。

---
## 你将学到什么
- 了解 Designer 的 **用户插件目录** 在哪里
- 明白 **plugin.txt** 的作用和正确格式
- 区分两种插件风格：`SDPluginLibrary` vs `SDPlugin`
- 编写最小可运行插件并逐步扩展
- 创建一个顶层菜单并添加 QAction 按钮
- 添加日志与调试技巧

---
## 目录
1. 环境与目录认识  
2. 最小插件结构  
3. 编写 `plugin.txt`  
4. 编写最小版本 `mini.py`  
5. 验证加载  
6. 添加菜单  
7. 添加测试动作  
8. 增加防重复逻辑  
9. 加入日志与帮助文本  
10. 最终版本结构整理  
11. 常见报错与排查  
12. 下一步扩展方向  

---
## 1. 环境与目录认识
Substance Designer 启动时会扫描你的用户插件目录：
```
%USERPROFILE%\Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins\
```
在这里的每一个子文件夹都可能是一个插件。如：
```
...\sduserplugins\lgnode\
```
插件加载流程核心概念：
1. 读取该目录下 `plugin.txt`
2. 解析映射：`模块名=类名`
3. `import 模块名`（模块名 = 子目录名）
4. 找到类并实例化
5. 调用 `initializeSDPlugin()` 获取插件信息
6. UI 完成后调用 `onInitializeSDUIMgr()` → 你在这里加菜单

---
## 2. 最小插件结构
创建目录：
```
%USERPROFILE%/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/lgnode/
```
最小三件套（初始阶段只要两个也可以）：
```
plugin.txt
__init__.py      (可选：导出 factory)
mini.py          (你的实现文件)
```

---
## 3. 编写 plugin.txt
内容必须严格两行，无多余缩进/空格：
```
SUBSTANCE_DESIGNER_PLUGINS
lgnode=LGNodeMini
```
解释：
- 第一行固定关键字
- 第二行左边 `lgnode` = 目录名（模块名）
- 右边 `LGNodeMini` = 你稍后定义的类名

---
## 4. 编写最小版本 mini.py
先不加菜单，只让它“被识别”。使用 **Library 风格**：
```python
from sd.api.sdplugin import SDPluginLibrary, SDPluginInfo

class LGNodeMini(SDPluginLibrary):
    def __init__(self):
        self._menu = None  # 预留

    def initializeSDPlugin(self):
        # 返回 SDPluginInfo（核心！不是 True/False）
        return SDPluginInfo(
            "LGNodeMini",                # 插件名称
            "Minimal test plugin",      # 描述
            "You",                      # 作者
            "0.0.1",                    # 版本
            "2025",                     # 年份
            SDPluginInfo.LibraryType.Python
        )

    def onInitializeSDUIMgr(self, uiMgr):
        # 暂时什么都不做
        print("LGNodeMini onInitializeSDUIMgr called")
        return True

    def onDeinitializeSDPlugin(self):
        return True
```
可选：`__init__.py`（让某些加载器或工具能找到工厂函数）
```python
from .mini import LGNodeMini  # 仅导出类即可
```
> 先重启 Designer，确认没有红色 “not a Designer plugin” 警告。如果有，检查：类名、plugin.txt、返回值。

---
## 5. 验证加载
启动 Substance Designer：
- 打开 Console（或查看启动日志）
- 搜 `LGNodeMini` 或 `mini` 的打印
如果看到 `LGNodeMini onInitializeSDUIMgr called`，说明生命周期调用成功。

常见错误：
| 日志提示 | 可能原因 | 对策 |
|----------|----------|------|
| not a Designer plugin | 类名不匹配 / 返回不是 SDPluginInfo | 检查 plugin.txt & 返回值 |
| ImportError | `plugin.txt` 指向的类不存在 | 检查文件/命名 | 

---
## 6. 添加菜单（升级）
修改 `onInitializeSDUIMgr`：
```python
from PySide2 import QtWidgets

    def onInitializeSDUIMgr(self, uiMgr):
        mainwindow = uiMgr.getMainWindow()
        menubar = mainwindow.menuBar()

        # 防止重复
        for act in menubar.actions():
            if act.text() == "LGNode":
                self._menu = act.menu()
                return True

        self._menu = QtWidgets.QMenu("LGNode", menubar)
        menubar.addMenu(self._menu)
        print("LGNode menu added")
        return True
```
重启查看菜单栏是否出现 **LGNode**。

---
## 7. 添加测试动作
```python
        self._menu = QtWidgets.QMenu("LGNode", menubar)
        test_action = QtWidgets.QAction("Test Action", self._menu)

        def _on_test():
            from sd import getContext
            ctx = getContext()
            app = ctx.getSDApplication()
            mw = app.getQtForPythonUIMgr().getMainWindow()
            QtWidgets.QMessageBox.information(mw, "LGNode", "It works!")

        test_action.triggered.connect(_on_test)
        self._menu.addAction(test_action)
        menubar.addMenu(self._menu)
```

---
## 8. 防重复逻辑（热加载友好）
核心就是在添加菜单前遍历：
```python
for act in menubar.actions():
    if act.text() == "LGNode":
        self._menu = act.menu()
        return True
```

---
## 9. 添加日志（用于调试）
```python
import os, time
LOG_PATH = os.path.join(os.path.expanduser('~'), 'lgnode_plugin.log')

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[LGNode][{ts}] {msg}"
    print(line)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
```
在关键函数开头加：`_log('onInitializeSDUIMgr')` / `_log('menu added')`

---
## 10. 最终版本结构（参考）
```
lgnode/
  plugin.txt
  mini.py          (可以改名 core.py)
  __init__.py
  lgnode_plugin.log (运行后生成)
```
最终类：`LGNodeLibrary`（你可以把 mini 改名更正式）

---
## 11. 常见报错与排查表
| 报错 | 根因 | 解决 |
|------|------|------|
| The Python module is not a Designer plugin | initialize 返回值不对 / 类继承错 | 用 `SDPluginLibrary + SDPluginInfo` 验证版 |
| cannot import name XXX | plugin.txt 指向的类没定义 | 检查拼写、文件是否存在 |
| 菜单不出现 | UI钩子没调或异常 | 在 `onInitializeSDUIMgr` 加 print/日志 |
| QMessageBox 崩溃 | 获取主窗口方式不对 | 使用 `ctx -> app -> getQtForPythonUIMgr()` 链 |
| 旧代码被加载 | 目录残留旧 .py | 清理后重启 |

---
## 12. 下一步扩展方向
| 功能 | 建议实现思路 |
|------|----------------|
| 批量重命名选中节点 | 获取 Graph + Selection API |
| 快速创建模板节点组 | 预置一组节点然后连接 |
| 导出当前 Graph 信息 | 遍历节点输出 JSON |
| 快捷键绑定 | QAction 设置 shortcut / 或 Qt 事件过滤 |
| 子菜单分类 | `submenu = self._menu.addMenu('Utilities')` |

---
## 附：完整示例（整合版）
```python
from sd.api.sdplugin import SDPluginLibrary, SDPluginInfo
from PySide2 import QtWidgets
import sd, time, os

LOG_PATH = os.path.join(os.path.expanduser('~'), 'lgnode_plugin.log')

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[LGNode][{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

class LGNodeLibrary(SDPluginLibrary):
    def __init__(self):
        self._menu = None
        _log('__init__')

    def initializeSDPlugin(self):
        _log('initializeSDPlugin')
        return SDPluginInfo(
            'LGNode',
            'Adds a custom LGNode menu',
            'You', '1.0.0', '2025',
            SDPluginInfo.LibraryType.Python
        )

    def onInitializeSDUIMgr(self, uiMgr):
        _log('onInitializeSDUIMgr')
        try:
            mw = uiMgr.getMainWindow()
            bar = mw.menuBar()
            for act in bar.actions():
                if act.text() == 'LGNode':
                    _log('Menu exists')
                    self._menu = act.menu()
                    return True
            self._menu = QtWidgets.QMenu('LGNode', bar)
            act = QtWidgets.QAction('Test Action', self._menu)
            act.triggered.connect(self._on_test)  # type: ignore
            self._menu.addAction(act)
            bar.addMenu(self._menu)
            _log('Menu added')
            return True
        except Exception as e:
            _log('UI init failed: ' + str(e))
            return False

    def onDeinitializeSDPlugin(self):
        _log('onDeinitializeSDPlugin')
        if self._menu:
            self._menu.deleteLater()
        return True

    def _on_test(self):
        _log('Test clicked')
        try:
            ctx = sd.getContext()
            app = ctx.getSDApplication()
            mw = app.getQtForPythonUIMgr().getMainWindow()
            QtWidgets.QMessageBox.information(mw, 'LGNode', 'It works!')
        except Exception as e:
            _log('Test failed: ' + str(e))

    def getHelp(self):
        return 'LGNode Plugin: Adds a custom menu.'
```
`plugin.txt`：
```
SUBSTANCE_DESIGNER_PLUGINS
lgnode=LGNodeLibrary
```

---
## 恭喜！🎉
做到这里你已经掌握了：
- 插件目录结构的本质
- plugin.txt 的语法和作用
- 生命周期关键钩子
- 菜单与 QAction 的基本用法
- 如何排查“不是插件”类型错误

如果你希望下一步我帮你：
- 做一个“节点统计”动作
- 做一个“批量替换 Uniform Color 节点颜色”的脚本
- 增加子菜单和图标

直接告诉我你的下一个学习目标。

继续吗？告诉我你最想加的第一个真实功能，我给你第二篇进阶教程。 :)
