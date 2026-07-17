# -*- coding: utf-8 -*-
"""菜单定义（数据驱动，可热重载）。

入口 MaxSDPlugin.py 只创建顶级 `MaxSDPlugin` 菜单并调用本模块的 `build_menu`。
所有菜单项（版本号、关于、重载、各功能分类）都在这里定义，
所以新增/修改菜单项只动这个文件，Unload→Load 即生效，无需重启 SD。
"""

try:
    from PySide6 import QtGui
except Exception:
    try:
        from PySide2 import QtGui  # 旧版 SD 回退
    except Exception:
        QtGui = None

from . import sdcompat


def _add_category(parent_menu, main_win, ctx, title, import_path, attr, fail_title):
    """通用：在 parent_menu 下建一个子菜单，延迟导入功能模块；失败时做成可点击错误项。"""
    QtWidgets = ctx["QtWidgets"]
    QAction = sdcompat.get_qaction()
    submenu = parent_menu.addMenu(title)
    try:
        import importlib
        mod = importlib.import_module(import_path, ctx["package"])
        show = getattr(mod, attr)
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"[MaxSDPlugin] 加载 {fail_title} 失败: {e}\n{err}")
        act = QAction(f"{fail_title}（加载失败，点击查看原因）", main_win)
        act.triggered.connect(lambda: QtWidgets.QMessageBox.critical(
            main_win, f"MaxSDPlugin · {fail_title} 加载失败", err))
        submenu.addAction(act)
        ctx["keep"].append(act)
        return
    act = QAction(fail_title, main_win)
    act.triggered.connect(lambda: show(main_win))
    submenu.addAction(act)
    ctx["keep"].extend([submenu, act])


def build_menu(menu, main_win, ctx):
    """填充 MaxSDPlugin 顶级菜单。ctx 提供入口注入的工具与回调。

    ctx: {QtWidgets, package, get_version, show_about, reload_plugin, keep(list)}
    返回需保活的对象列表（防 GC）。
    """
    keep = ctx["keep"]
    QAction = sdcompat.get_qaction()
    if QtGui is None or QAction is None:
        return keep

    # 顶部高亮版本号
    ver = QAction(f"● 版本 v{ctx['get_version']()}", main_win)
    f = ver.font(); f.setBold(True); ver.setFont(f)
    ver.triggered.connect(ctx["show_about"])
    menu.addAction(ver)
    try:
        menu.setDefaultAction(ver)
        menu.setStyleSheet("QMenu::item:default { color: #4caf50; font-weight: bold; }")
        no_role = getattr(QAction, "NoRole", None)
        if no_role is None and hasattr(QAction, "MenuRole"):
            no_role = QAction.MenuRole.NoRole
        if no_role is not None:
            ver.setMenuRole(no_role)
    except Exception:
        pass
    keep.append(ver)
    menu.addSeparator()

    about = QAction("关于 / 版本信息", main_win)
    about.triggered.connect(ctx["show_about"])
    menu.addAction(about)
    keep.append(about)

    reload_act = QAction("重载插件（Unload→Load）", main_win)
    reload_act.triggered.connect(ctx["reload_plugin"])
    menu.addAction(reload_act)
    keep.append(reload_act)
    menu.addSeparator()

    # 功能分类：新增分类只在此追加一行
    _add_category(menu, main_win, ctx, "Output", ".output", "show_window", "曝光参数")
    _add_category(menu, main_win, ctx, "Edit", ".frame_color_modify", "show_window", "FrameColorModify")
    _add_category(menu, main_win, ctx, "File", ".save_with_resource", "show_window", "SaveWithResrouce")
    _add_category(menu, main_win, ctx, "Debug", ".debug", "show_window", "Publish Checker")
    _add_category(menu, main_win, ctx, "Analysis", ".sbs_file_reporter", "show_window", "SBSFileRepoter")
    _add_category(menu, main_win, ctx, "OutputTools", ".output_tools", "show_window", "输出脚本")
    return keep
