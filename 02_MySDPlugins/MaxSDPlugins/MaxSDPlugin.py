# -*- coding: utf-8 -*-
"""MaxSDPlugin 插件入口（唯一注册点）。

职责（见同目录 AGENTS.md §1.3）：
- 提供 SD 启动/卸载时自动调用的 `initializeSDPlugin()` / `uninitializeSDPlugin()`。
- 在主窗口菜单栏创建唯一顶级菜单 `MaxSDPlugin`（幂等，不重复添加）。
- 卸载时把本插件加的菜单 / 动作清理干净，并把模块级引用置 None。

当前只内置一个演示动作「关于 / 版本信息」，用于验证插件已被 SD 正确加载，
同时对应 ReleaseNote 第 1 项（显示插件版本 / 软件版本 / PySide 版本）。
后续功能请按 AGENTS.md §2 的流程，在功能子文件夹里实现，再由本文件注册成菜单项。
"""

import sd  # SD 提供的 Python 包；只在 SD 进程内可用
from . import sdcompat

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

__version__ = "0.16.0"

def _entry_files_mtime():
    """返回入口文件 MaxSDPlugin.py / __init__.py 的最新修改时间（取不到返回 0）。"""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    latest = 0.0
    for name in ("MaxSDPlugin.py", "__init__.py"):
        try:
            latest = max(latest, os.path.getmtime(os.path.join(here, name)))
        except Exception:
            pass
    return latest


# 入口文件加载时的基线时间：reload 不会重新 import 入口，所以此值保持加载时的快照
_ENTRY_MTIME_AT_LOAD = _entry_files_mtime()

def _get_version():
    """读取热重载版本号。版本号实际存于 _version.py（每次 Load 会清缓存重读），
    入口里的 __version__ 仅作回退（入口改动需重启才生效）。"""
    try:
        import importlib
        pkg = __package__ or "MaxSDPlugins"
        mod = importlib.import_module(pkg + "._version")
        return getattr(mod, "VERSION", __version__)
    except Exception:
        return __version__


# 模块级引用：防止被 Python 垃圾回收导致菜单 / 回调失效
_menu_ref = None
_keep_alive = []  # 菜单项/子菜单的保活引用（由 menu.build_menu 填充）


def _get_main_window():
    """获取 SD 的 Qt 主窗口；无界面或失败时返回 None。"""
    return sdcompat.get_main_window()


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
        f"插件版本：{_get_version()}\n"
        f"SD 版本：{sd_version}\n"
        f"PySide 绑定：{_PYSIDE_NAME}（Qt {qt_ver}）"
    )
    if QtWidgets is not None:
        QtWidgets.QMessageBox.information(main_win, "MaxSDPlugin · 版本信息", msg)
    else:
        print(msg)


def _create_menu(main_win):
    """创建 `MaxSDPlugin` 顶级菜单骨架，菜单项由热重载模块 menu.build_menu 填充。

    幂等：每次加载先按名移除旧菜单再重建。入口只管骨架与生命周期；
    具体菜单项（版本号/关于/重载/各分类）全在 menu.py，改菜单不再动入口。
    """
    global _menu_ref, _keep_alive

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
    _keep_alive = []

    ctx = {
        "QtWidgets": QtWidgets,
        "package": __package__ or "MaxSDPlugins",
        "get_version": _get_version,
        "show_about": lambda: _show_about(main_win),
        "reload_plugin": lambda: _reload_plugin(main_win),
        "keep": _keep_alive,
    }
    try:
        import importlib
        menu_mod = importlib.import_module((__package__ or "MaxSDPlugins") + ".menu")
        menu_mod.build_menu(_menu_ref, main_win, ctx)
    except Exception as e:
        import traceback
        print(f"[MaxSDPlugin] 构建菜单失败: {e}\n{traceback.format_exc()}")


def _remove_menu(main_win):
    """卸载时按文字移除本插件创建的 MaxSDPlugin 菜单，并清空保活引用。"""
    global _menu_ref, _keep_alive
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
        _keep_alive = []


def _reload_feature_modules():
    """在「加载时」清掉所有功能子模块的 import 缓存，
    使下一次延迟 import 能从磁盘重新读取最新代码，实现子模块热重载。

    动态策略（新增功能无需改入口）：
    - 清掉本包 `MaxSDPlugins.*` 下的所有子模块，唯独保留包本身与入口模块
      （MaxSDPlugin / __init__），否则相对导入 `from .output import …`
      会因父包缺失而出错。
    - 这样任何新功能子包（如 output_tools）一旦放进包目录即自动纳入热重载，
      不用再维护 feature_prefixes 名单。
    - 入口文件 MaxSDPlugin.py / __init__.py 的改动仍无法热重载，必须重启 SD，
      因为 SD 攥着它们的旧模块对象，不会重新 import。
    """
    import sys
    pkg = __package__ or "MaxSDPlugins"
    # 永不清理：包根 + 入口模块（清了会破坏相对导入与 SD 持有的入口引用）
    keep = {pkg, pkg + ".MaxSDPlugin", pkg + ".__init__"}
    for name in list(sys.modules):
        if name in keep:
            continue
        if name == pkg or name.startswith(pkg + "."):
            try:
                del sys.modules[name]
            except Exception:
                pass


def _reload_plugin(main_win=None):
    """等价于 Plugin Manager 的 Unload→Load：卸载本插件菜单 + 清子模块缓存 + 重建菜单。

    用于热重载功能子模块（output/debug/_version）改动，无需手动去 Plugin Manager。
    未找到主窗口（命令行/未注册）时给出提示。"""
    if QtWidgets is None:
        print("[MaxSDPlugin] 未检测到 PySide，无法重载。")
        return
    win = main_win or _get_main_window()
    if not win:
        QtWidgets.QMessageBox.warning(
            None, "MaxSDPlugin · 重载插件",
            "未找到 MaxSDPlugin / SD 主窗口，无法重载。\n"
            "请确认插件已正确加载，或在 Plugin Manager 中手动 Unload→Load。")
        return
    try:
        uninitializeSDPlugin()
        initializeSDPlugin()
        entry_changed = _entry_files_mtime() > _ENTRY_MTIME_AT_LOAD
        msg = f"已重载功能模块并重建菜单（v{_get_version()}）。"
        if entry_changed:
            msg += "\n\n检测到入口文件 MaxSDPlugin.py / __init__.py 有改动，需重启 SD 才能完全生效。"
        QtWidgets.QMessageBox.information(win, "MaxSDPlugin · 重载插件", msg)
    except Exception as e:
        import traceback
        QtWidgets.QMessageBox.critical(
            win, "MaxSDPlugin · 重载失败", f"{e}\n\n{traceback.format_exc()}")


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
