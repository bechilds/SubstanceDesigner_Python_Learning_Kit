# -*- coding: utf-8 -*-
"""MaxSDPlugin 插件入口（唯一注册点）。

职责（见同目录 AGENTS.md §1.3）：
- 提供 SD 启动/卸载时自动调用的 `initializeSDPlugin()` / `uninitializeSDPlugin()`。
- 在主窗口菜单栏创建唯一顶级菜单 `MaxSDPlugin`（幂等，不重复添加）。
- 卸载时把本插件加的菜单 / 动作清理干净，并把模块级引用置 None。

当前只内置一个演示动作「关于 / 版本信息」，用于验证插件已被 SD 正确加载，
同时对应 TodoList 第 1 项（显示插件版本 / 软件版本 / PySide 版本）。
后续功能请按 AGENTS.md §2 的流程，在功能子文件夹里实现，再由本文件注册成菜单项。
"""

import sd  # SD 提供的 Python 包；只在 SD 进程内可用

# --- PySide 导入：SD 16.0.1 内置 PySide6（Qt 6.8.x），保留 PySide2 回退以兼容旧版 ---
_PYSIDE_NAME = None
try:
    from PySide6 import QtWidgets, QtGui
    from PySide6.QtCore import qVersion
    _PYSIDE_NAME = "PySide6"
except Exception:
    try:
        from PySide2 import QtWidgets, QtGui  # 旧版 SD 回退
        from PySide2.QtCore import qVersion
        _PYSIDE_NAME = "PySide2"
    except Exception as _e:
        QtWidgets = None
        QtGui = None
        qVersion = None
        print(f"[MaxSDPlugin] PySide 导入失败，UI 功能不可用: {_e}")

__version__ = "0.1.0"

# 模块级引用：防止被 Python 垃圾回收导致菜单 / 回调失效
_menu_ref = None
_action_about_ref = None
_output_menu_ref = None
_action_exposed_params_ref = None


def _get_main_window():
    """获取 SD 的 Qt 主窗口；无界面或失败时返回 None。"""
    try:
        app = sd.getContext().getSDApplication()
        qt_ui = app.getQtForPythonUIMgr()
        return qt_ui.getMainWindow() if qt_ui else None
    except Exception as e:
        print(f"[MaxSDPlugin] 获取主窗口失败: {e}")
        return None


def _show_about(main_win=None):
    """显示插件 / SD / PySide 版本信息（UI 弹窗）。"""
    sd_version = "未知"
    try:
        app = sd.getContext().getSDApplication()
        # 不同版本 API 名可能不同，逐个尝试，全失败则保持「未知」
        for getter in ("getVersion", "getEditorVersion"):
            if hasattr(app, getter):
                sd_version = getattr(app, getter)()
                break
    except Exception as e:
        print(f"[MaxSDPlugin] 读取 SD 版本失败: {e}")

    qt_ver = qVersion() if qVersion else "未知"
    msg = (
        f"插件版本：{__version__}\n"
        f"SD 版本：{sd_version}\n"
        f"PySide 绑定：{_PYSIDE_NAME}（Qt {qt_ver}）"
    )
    if QtWidgets is not None:
        QtWidgets.QMessageBox.information(main_win, "MaxSDPlugin · 版本信息", msg)
    else:
        print(msg)


def _create_menu(main_win):
    """创建 `MaxSDPlugin` 顶级菜单。幂等：每次加载先按名移除旧菜单再重建。"""
    global _menu_ref, _action_about_ref

    if QtWidgets is None or main_win is None:
        return

    menu_bar = main_win.menuBar()
    if not menu_bar:
        print("[MaxSDPlugin] 未找到菜单栏")
        return

    # 幂等关键：按文字移除所有旧的 MaxSDPlugin 菜单（含历史重复 / 重载残留），再新建一个干净的
    for act in list(menu_bar.actions()):
        if act.text() == "MaxSDPlugin":
            menu_bar.removeAction(act)
    _menu_ref = menu_bar.addMenu("MaxSDPlugin")

    _action_about_ref = QtGui.QAction("关于 / 版本信息", main_win)
    _action_about_ref.triggered.connect(lambda: _show_about(main_win))
    _menu_ref.addAction(_action_about_ref)

    _create_output_category(main_win)


def _create_output_category(main_win):
    """在 MaxSDPlugin 菜单下创建 Output 分类子菜单及其功能项。随菜单一起重建。"""
    global _output_menu_ref, _action_exposed_params_ref

    if _menu_ref is None:
        return

    _output_menu_ref = _menu_ref.addMenu("Output")

    # 曝光参数功能：延迟导入；失败时不连累插件，并把错误做成可点击菜单项便于排查
    try:
        from .output import show_window as _show_exposed_params
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"[MaxSDPlugin] 加载 Output/曝光参数 功能失败: {e}\n{err}")
        _action_exposed_params_ref = QtGui.QAction("曝光参数（加载失败，点击查看原因）", main_win)
        _action_exposed_params_ref.triggered.connect(
            lambda: QtWidgets.QMessageBox.critical(
                main_win, "MaxSDPlugin · 曝光参数加载失败", err)
        )
        _output_menu_ref.addAction(_action_exposed_params_ref)
        return

    _action_exposed_params_ref = QtGui.QAction("曝光参数", main_win)
    _action_exposed_params_ref.triggered.connect(lambda: _show_exposed_params(main_win))
    _output_menu_ref.addAction(_action_exposed_params_ref)


def _remove_menu(main_win):
    """卸载时按文字移除本插件创建的 MaxSDPlugin 菜单（连同 Output 子菜单），并清空引用。"""
    global _menu_ref, _action_about_ref, _output_menu_ref, _action_exposed_params_ref
    try:
        if main_win:
            menu_bar = main_win.menuBar()
            if menu_bar:
                for act in list(menu_bar.actions()):
                    if act.text() == "MaxSDPlugin":
                        menu_bar.removeAction(act)
    except Exception as e:
        print(f"[MaxSDPlugin] 菜单清理失败: {e}")
    finally:
        _menu_ref = None
        _action_about_ref = None
        _output_menu_ref = None
        _action_exposed_params_ref = None


def _reload_feature_modules():
    """在「加载时」清掉功能子模块（output/ 等）的 import 缓存，
    使下一次延迟 import 能从磁盘重新读取最新代码，实现子模块热重载。

    注意：
    - 只清「功能子模块」，绝不清包本身（MaxSDPlugins）和入口模块（MaxSDPlugin），
      否则相对导入 `from .output import …` 会因父包缺失而出错。
    - 入口文件 MaxSDPlugin.py / __init__.py 的改动无法热重载，必须重启 SD，
      因为 SD 攥着它们的旧模块对象，不会重新 import。
    """
    import sys
    pkg = __package__ or "MaxSDPlugins"
    # 要重载的功能子包前缀（新功能在此登记即可）；故意不含包本身与入口模块
    feature_prefixes = (pkg + ".output",)
    for name in list(sys.modules):
        if any(name == p or name.startswith(p + ".") for p in feature_prefixes):
            try:
                del sys.modules[name]
            except Exception:
                pass


def initializeSDPlugin():
    """SD 加载插件时自动调用。"""
    print("[MaxSDPlugin] Plugin loaded")
    if QtWidgets is None:
        print("[MaxSDPlugin] 未检测到 PySide，跳过 UI 注册。")
        return
    # 先清功能子模块缓存，使本次 Load 能读到 output/ 下的最新代码（无需重启）
    _reload_feature_modules()
    main_win = _get_main_window()
    if not main_win:
        print("[MaxSDPlugin] 主窗口不可用（可能为命令行模式），跳过 UI 注册。")
        return
    _create_menu(main_win)


def uninitializeSDPlugin():
    """SD 卸载插件 / 关闭软件时自动调用。"""
    print("[MaxSDPlugin] Plugin unloaded")
    if QtWidgets is not None:
        _remove_menu(_get_main_window())
