# -*- coding: utf-8 -*-
"""OutputTools（输出脚本）：展示当前插件的所有功能（分类）及其分支（子模块）。

支持导出独立、自包含的 .py 文件，或按 MG MaxSD loader 约定输出到自定义目录。

菜单位置：`MaxSDPlugin/OutputTools/输出脚本`。

功能分类 -> 分支（子模块）由扫描插件包目录得到：
  - Output      -> output/ 下各 .py
  - Debug       -> debug/ 下各 .py
    - Edit        -> frame_color_modify/ 下各 .py
    - File        -> save_with_resource/ 下各 .py
    - Analysis    -> sbs_file_reporter/ 下各 .py
    - OutputTools -> 本包各 .py
独立脚本：把所选模块封装到隔离命名空间，附带跨版本兼容层。
MG 输出：保留分类目录，生成 LG_MaxSD_*.py 并改写模块 import。
UI 与扫描保留在本文件；依赖解析和文件写出集中在 exporter.py。
"""

import os

# --- PySide：SD 16.0.1 = PySide6；保留 PySide2 回退 ---
try:
    from PySide6 import QtWidgets, QtCore
except Exception:
    try:
        from PySide2 import QtWidgets, QtCore
    except Exception as _e:
        QtWidgets = None
        QtCore = None
        print(f"[MaxSDPlugin/output_tools] PySide 导入失败，UI 不可用: {_e}")

_LOG = "[MaxSDPlugin/output_tools]"
_dialog_ref = None  # 防 GC

# 分类显示名：包目录名 -> 中文标题
_CATEGORY_TITLES = {
    "output": "Output（曝光参数）",
    "preset_recovery": "Output（预设效果找回）",
    "batch_merge_tex_channel": "Output（BatchMergeTexChannel）",
    "debug": "Debug（Publish Checker）",
    "frame_color_modify": "Edit（FrameColorModify）",
    "auto_add_expose_comment": "Edit（AutoAddExposeCommitToNode）",
    "switch_manager": "Edit（开关管理工具）",
    "expose_param_sorting": "Output（曝光参数分组排序）",
    "save_with_resource": "File（SaveWithResrouce）",
    "sbs_file_reporter": "Analysis（SBSFileRepoter）",
    "output_tools": "OutputTools（输出脚本）",
}


# --------------------------------------------------------------------------- #
# 数据层：扫描功能与分支
# --------------------------------------------------------------------------- #
def _plugin_root():
    """插件包根目录（本文件位于 output_tools/，上一级即包根）。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect_features():
    """扫描插件包，返回 [(分类名, 标题, [模块文件绝对路径...]), ...]。"""
    root = _plugin_root()
    features = []
    for cat in _CATEGORY_TITLES:
        cat_dir = os.path.join(root, cat)
        if not os.path.isdir(cat_dir):
            continue
        mods = []
        for name in sorted(os.listdir(cat_dir)):
            if name.endswith(".py") and name != "__init__.py":
                mods.append(os.path.join(cat_dir, name))
        if mods:
            features.append((cat, _CATEGORY_TITLES.get(cat, cat), mods))
    return features


def export_modules(module_paths, out_path, sd_version="auto"):
    """兼容公开入口；依赖解析和写出由独立 exporter 数据层实现。"""
    from .exporter import export_modules as export
    return export(module_paths, out_path, sd_version)


def export_modules_to_mg(module_paths, output_root):
    """兼容公开入口；自动补齐依赖和外部资源。"""
    from .exporter import export_modules_to_mg as export
    return export(module_paths, output_root)


# --------------------------------------------------------------------------- #
# UI 层
# --------------------------------------------------------------------------- #
if QtWidgets is not None:

    class OutputToolsDialog(QtWidgets.QDialog):
        """展示功能/分支，勾选后导出为独立 .py。"""

        _PATH_ROLE = (QtCore.Qt.UserRole if QtCore is not None else 32)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("OutputTools - MaxSDPlugin")
            self.resize(700, 500)
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            self._info = QtWidgets.QLabel("勾选功能/分支；导出时自动补齐 Python 依赖与处理 SBS 资源。", self)
            self._info.setWordWrap(True)
            layout.addWidget(self._info)

            self._tree = QtWidgets.QTreeWidget(self)
            self._tree.setHeaderLabels(["功能 / 分支"])
            layout.addWidget(self._tree, 1)

            tip = QtWidgets.QLabel(
                "导出物为双版本通用：运行时自动适配 SD16(PySide6) 与 SD13(PySide2)，无需选版本。", self)
            tip.setWordWrap(True)
            layout.addWidget(tip)

            row = QtWidgets.QHBoxLayout()
            self._btn_refresh = QtWidgets.QPushButton("刷新", self)
            self._btn_all = QtWidgets.QPushButton("全选", self)
            self._btn_none = QtWidgets.QPushButton("全不选", self)
            self._btn_export = QtWidgets.QPushButton("导出为独立脚本", self)
            self._btn_export_mg = QtWidgets.QPushButton("输出到 MG...", self)
            self._btn_close = QtWidgets.QPushButton("关闭", self)
            self._btn_refresh.clicked.connect(self._refresh)
            self._btn_all.clicked.connect(lambda: self._set_all(True))
            self._btn_none.clicked.connect(lambda: self._set_all(False))
            self._btn_export.clicked.connect(self._export)
            self._btn_export_mg.clicked.connect(self._export_to_mg)
            self._btn_close.clicked.connect(self.close)
            for b in (self._btn_refresh, self._btn_all, self._btn_none,
                      self._btn_export, self._btn_export_mg):
                row.addWidget(b)
            row.addStretch(1)
            row.addWidget(self._btn_close)
            layout.addLayout(row)

        def _refresh(self):
            self._tree.clear()
            for cat, title, mods in collect_features():
                top = QtWidgets.QTreeWidgetItem(self._tree, [title])
                top.setFlags(top.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsAutoTristate)
                top.setCheckState(0, QtCore.Qt.Unchecked)
                for path in mods:
                    child = QtWidgets.QTreeWidgetItem(top, [os.path.basename(path)])
                    child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                    child.setCheckState(0, QtCore.Qt.Unchecked)
                    child.setData(0, self._PATH_ROLE, path)
            self._tree.expandAll()

        def _set_all(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for i in range(self._tree.topLevelItemCount()):
                self._tree.topLevelItem(i).setCheckState(0, state)

        def _checked_paths(self):
            paths = []
            for i in range(self._tree.topLevelItemCount()):
                top = self._tree.topLevelItem(i)
                for j in range(top.childCount()):
                    c = top.child(j)
                    if c.checkState(0) == QtCore.Qt.Checked:
                        paths.append(c.data(0, self._PATH_ROLE))
            return paths

        def _export(self):
            paths = self._checked_paths()
            if not paths:
                QtWidgets.QMessageBox.information(self, "MaxSDPlugin", "请先勾选要导出的功能/分支。")
                return
            out, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "导出为独立脚本", "_maxsd_export.py", "Python (*.py)")
            if not out:
                return
            ok, msg = export_modules(paths, out)
            box = QtWidgets.QMessageBox.information if ok else QtWidgets.QMessageBox.warning
            box(self, "MaxSDPlugin · OutputTools", msg)

        def _export_to_mg(self):
            paths = self._checked_paths()
            if not paths:
                QtWidgets.QMessageBox.information(self, "MaxSDPlugin", "请先勾选要输出到 MG 的功能/分支。")
                return

            default_root = ""
            public_root = os.environ.get("LGPublicMGEnv", "")
            if public_root:
                candidate = os.path.join(
                    public_root, "Scriptlibrary", "substance", "sdesigner", "MaxSD")
                if os.path.isdir(candidate):
                    default_root = candidate
            output_root = QtWidgets.QFileDialog.getExistingDirectory(
                self, "选择 MG MaxSD 输出目录", default_root)
            if not output_root:
                return

            answer = QtWidgets.QMessageBox.question(
                self,
                "确认输出到 MG",
                "将写入所选模块、自动补齐的依赖、SBS 资源和清单。\n"
                "以下目录中的同名生成文件会被覆盖，Start.py / LG_Tool.py 不修改：\n\n"
                + output_root,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return

            ok, msg = export_modules_to_mg(paths, output_root)
            box = QtWidgets.QMessageBox.information if ok else QtWidgets.QMessageBox.warning
            box(self, "MaxSDPlugin · 输出到 MG", msg)


def show_window(main_win=None):
    """公开入口：统一单实例、关闭释放；兼容旧调用签名。"""
    from ..shared.lifecycle import show_dialog
    from .. import sdcompat
    if QtWidgets is None:
        print('[MaxSDPlugin] Qt 不可用，无法显示窗口。')
        return None
    try:
        return show_dialog(__name__, lambda: OutputToolsDialog(parent=main_win or sdcompat.get_main_window()), globals())
    except sdcompat.SD_API_ERRORS as error:
        QtWidgets.QMessageBox.critical(main_win, "MaxSDPlugin", sdcompat.error_text(error))
        return None
