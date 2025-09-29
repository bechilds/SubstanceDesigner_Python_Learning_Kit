# -*- coding: utf-8 -*-
"""Minimal Substance Designer Qt Menu Plugin (Clean Version)

面向初学者的极简插件示例：

核心目标 / 你将学到：
1. Substance Designer 在启动时会自动调用 `initializeSDPlugin()`，在关闭或卸载插件时调用 `uninitializeSDPlugin()`。
2. 通过 SD 提供的 API 获取 Qt 主窗口（Main Window），再向其菜单栏添加一个自定义顶级菜单。
3. 使用 Qt 的 QAction（菜单项）并连接一个简单的回调函数（这里用 lambda 打印一句话）。
4. 如何在卸载时把自己加的菜单清理干净，避免“越卸载菜单越多”的情况。

本脚本只做一件事：创建一个顶级菜单 MyPlugin，里面有一个动作(菜单项)“Hello”，点击后在 SD 的 Python 输出窗口打印：`菜单加载成功`。
卸载插件时则把整个 `MyPlugin` 菜单移除。

阅读指引：
- 如果你完全没接触过 Qt：把 QMenu 理解成“菜单”，QAction 理解成“菜单里的一个选项”。
- 如果你不确定某段代码做啥，可以先看每一行旁边的中文注释再回到上面的总览。

提示：本例属于“界面扩展”类型，不涉及 .sbs 文件的读写或图节点操作，专注于 UI 菜单的增删。以后你可以按类似方式添加更多动作（比如批量修改图参数、批量导出贴图等）。
"""

import sd  # Substance Designer 提供的 Python 包根命名空间，通过它获取上下文 / 应用对象

try:
    # Substance Designer 版本不同可能内置 PySide2 或 PySide6
    # 优先尝试 PySide2（旧版本常见），失败再尝试 PySide6（较新版本）。
    from PySide2 import QtWidgets  # QtWidgets 包含我们需要的 QMenu / QAction / 主窗口等类
except Exception:
    try:
        from PySide6 import QtWidgets  # 如果 PySide2 不存在再尝试 PySide6
    except Exception as _e:
        # 两个都失败：说明当前环境下无法做 UI 扩展（也许在无界面或命令行模式）。逻辑继续运行但不会创建菜单。
        QtWidgets = None
        print(f"[MyPlugin] PySide 导入失败: {_e}")

_menu_ref = None   # 保存我们创建的 QMenu（顶级菜单）引用，便于重复调用时不再新建 & 卸载时移除
_action_ref = None # 保存菜单项 QAction 引用，防止被 Python 垃圾回收；并可判断是否已经创建


def _create(main_win):
    """内部辅助函数：在主窗口上创建(或复用)我们的菜单与动作。

    为什么要写成单独函数：
    - 初始化时要调用一次；理论上你也可以在别处（比如热重载脚本）再次调用，它会做“幂等”检查（已经存在就复用，不重复添加）。

    参数:
        main_win (QMainWindow): Substance Designer 主窗口对象。
    """
    global _menu_ref, _action_ref

    # 1. 基础防御：如果没有 Qt 环境（无界面）或没有主窗口，就直接返回。
    if QtWidgets is None or main_win is None:
        return

    # 2. 获取主窗口的菜单栏 (QMenuBar)。
    mb = main_win.menuBar()
    if not mb:  # 理论上应该总能拿到，除非界面异常。
        print('[MyPlugin] 未找到菜单栏')
        return

    # 3. 如果我们还没有缓存 _menu_ref，则遍历现有菜单，看是否已经有名为 "MyPlugin" 的菜单。
    #    这样可以避免重复创建（例如脚本被重新加载时）。
    if _menu_ref is None:
        for act in mb.actions():  # 每个 action 可能对应一个下拉菜单
            if act.text() == 'MyPlugin':
                _menu_ref = act.menu()  # 复用之前创建的那个菜单
                break

    # 4. 如果还是没有，说明确实不存在，就新建一个顶级菜单。
    if _menu_ref is None:
        _menu_ref = mb.addMenu('MyPlugin')
        print('[MyPlugin] 顶级菜单创建')

    # 5. 创建一个菜单项 QAction（如果之前没建）。
    if _action_ref is None:
        _action_ref = QtWidgets.QAction('Hello', main_win)
        # 连接点击信号。这里用 lambda，只打印一句话。实际项目里可换成函数，做更多操作。
        _action_ref.triggered.connect(lambda: print('菜单加载成功'))

    # 6. 防止重复添加（比如热重载或再次执行 _create）。
    if _action_ref not in _menu_ref.actions():
        _menu_ref.addAction(_action_ref)


def initializeSDPlugin():
    """Substance Designer 发现并加载插件时自动调用的入口函数。

    典型流程：
    1. 打印加载日志，方便在 Python 控制台确认插件是否被执行。
    2. 检查 Qt 是否可用（无 Qt 就无法做 UI 扩展）。
    3. 通过 sd.getContext() -> getSDApplication() -> getQtForPythonUIMgr() 拿到 UI 管理器，再获取主窗口。
    4. 调用我们自己的 _create() 去创建或复用菜单。

    注意：
    - 如果你要在这里再做别的初始化（比如注册事件回调、预加载资源），可以继续往下写。
    - 若插件 import 失败或函数名写错，Substance Designer 将不会调用成功，需在 Console 查看报错。
    """
    print('[MyPlugin] Plugin loaded')
    if QtWidgets is None:
        print('[MyPlugin] 未检测到 PySide，放弃。')
        return
    try:
        # 获取 SD 应用实例
        app = sd.getContext().getSDApplication()
        # 通过 UI 管理器拿到 Qt 主窗口（包装层，兼容不同 Qt 版本）
        qt_ui = app.getQtForPythonUIMgr()
        main_win = qt_ui.getMainWindow() if qt_ui else None
        if not main_win:
            print('[MyPlugin] 主窗口不可用')
            return
    except Exception as e:
        # 保持插件稳健：即使这里失败也不要崩溃整个环境，打印日志即可。
        print(f'[MyPlugin] 获取主窗口失败: {e}')
        return
    # 真正创建或复用菜单
    _create(main_win)


def uninitializeSDPlugin():
    """Substance Designer 卸载插件或关闭软件时调用，用于清理我们创建的 UI。

    清理原则：撤销我们在 initialize 阶段做的所有“外部可见”修改。
    对本例来说，就是把加到菜单栏里的 `MyPlugin` 菜单删除，避免残留。
    （如果你还注册了事件、线程、定时器，也应该在这里断开或停止。）
    """
    global _menu_ref, _action_ref
    print('[MyPlugin] Plugin unloading')
    if QtWidgets is None:  # 如果当初没创建成功，这里也没事做。
        return
    try:
        if _menu_ref:  # 只有我们确实创建过菜单才尝试移除
            mb = _menu_ref.parentWidget()  # 通常是 QMenuBar
            if mb and hasattr(mb, 'actions'):
                for act in mb.actions():
                    # 找到绑定此菜单的 action，然后将其移除，相当于删除整个顶级菜单
                    if act.menu() is _menu_ref:
                        mb.removeAction(act)
                        print('[MyPlugin] 菜单已移除')
                        break
    except Exception as e:
        # 尽量不要在清理阶段抛未捕获异常，否则可能影响其他插件卸载。
        print(f'[MyPlugin] 卸载清理失败: {e}')
    finally:
        # 无论是否成功，都将引用置空，方便垃圾回收 & 防止悬挂引用。
        _menu_ref = None
        _action_ref = None