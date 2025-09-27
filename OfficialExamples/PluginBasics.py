# -*- coding: utf-8 -*-
"""Minimal Substance Designer Qt Menu Plugin (Clean Version)
只做一件事：创建一个顶级菜单 MyPlugin，里面有一个动作 Hello，点击打印“菜单加载成功”。
卸载时移除该菜单。
"""

import sd

try:
    from PySide2 import QtWidgets
except Exception:
    try:
        from PySide6 import QtWidgets
    except Exception as _e:
        QtWidgets = None
        print(f"[MyPlugin] PySide 导入失败: {_e}")

_menu_ref = None  # QMenu 引用
_action_ref = None  # QAction 引用


def _create(main_win):
    """创建菜单与动作（若尚未存在）。"""
    global _menu_ref, _action_ref
    if QtWidgets is None or main_win is None:
        return
    mb = main_win.menuBar()
    if not mb:
        print('[MyPlugin] 未找到菜单栏')
        return
    # 查找是否已经存在同名菜单
    if _menu_ref is None:
        for act in mb.actions():
            if act.text() == 'MyPlugin':
                _menu_ref = act.menu()
                break
    if _menu_ref is None:
        _menu_ref = mb.addMenu('MyPlugin')
        print('[MyPlugin] 顶级菜单创建')
    if _action_ref is None:
        _action_ref = QtWidgets.QAction('Hello', main_win)
        _action_ref.triggered.connect(lambda: print('菜单加载成功'))
    if _action_ref not in _menu_ref.actions():
        _menu_ref.addAction(_action_ref)


def initializeSDPlugin():
    print('[MyPlugin] Plugin loaded')
    if QtWidgets is None:
        print('[MyPlugin] 未检测到 PySide，放弃。')
        return
    try:
        app = sd.getContext().getSDApplication()
        qt_ui = app.getQtForPythonUIMgr()
        main_win = qt_ui.getMainWindow() if qt_ui else None
        if not main_win:
            print('[MyPlugin] 主窗口不可用')
            return
    except Exception as e:
        print(f'[MyPlugin] 获取主窗口失败: {e}')
        return
    _create(main_win)


def uninitializeSDPlugin():
    global _menu_ref, _action_ref
    print('[MyPlugin] Plugin unloading')
    if QtWidgets is None:
        return
    try:
        if _menu_ref:
            mb = _menu_ref.parentWidget()
            if mb and hasattr(mb, 'actions'):
                for act in mb.actions():
                    if act.menu() is _menu_ref:
                        mb.removeAction(act)
                        print('[MyPlugin] 菜单已移除')
                        break
    except Exception as e:
        print(f'[MyPlugin] 卸载清理失败: {e}')
    finally:
        _menu_ref = None
        _action_ref = None