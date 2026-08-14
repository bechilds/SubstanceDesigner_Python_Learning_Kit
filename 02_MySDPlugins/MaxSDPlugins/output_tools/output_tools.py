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
数据层与 UI 层放在同一文件（SD 专有 API 极少，全部包 try/except）。
"""

import os
import datetime
import re

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
    """把所选模块打包成一个独立、可激活的 .py。返回 (ok, 信息)。

    导出物为「双版本通用」：源码不做 PySide 静态改写（各模块本就 try PySide6
    except PySide2）。跨版本 SD/Qt 接口差异统一由**兼容层 sdcompat.py** 抹平——它被
    始终打包为 `_maxsd_bundle.root_sdcompat`，加载时先 exec、再调 `qt_patch()`，功能
    模块通过 `from .. import sdcompat` 使用它（导出时自动改写到 root_sdcompat）。

    每个模块被装进独立的合成子包 `_maxsd_bundle.<模块名>`，保留各自的相对 import，
    避免平铺拼接导致的同名符号互相覆盖（show_window/_dialog_ref/_LOG）与
    `from . import output_data` 失效问题。导出物提供 `maxsd_show_windows` 字典与
    `maxsd_activate()`，供宿主工具调用激活。
    """
    if not module_paths:
        return False, "未选择任何功能。"

    # 收集每个模块：合成子包名（用「分类_文件名」防重名）与源码（base64 安全内嵌）
    import base64
    entries = []  # (bundle_name, rel, b64src)

    # 始终把兼容层 sdcompat.py 打包进去，作为 _maxsd_bundle.root_sdcompat（放最前，最先 exec）
    _sdc_path = os.path.join(_plugin_root(), "sdcompat.py")
    try:
        with open(_sdc_path, "r", encoding="utf-8") as f:
            _sdc_src = f.read()
        entries.append((
            "root_sdcompat",
            os.path.relpath(_sdc_path, _plugin_root()).replace(os.sep, "/"),
            base64.b64encode(_sdc_src.encode("utf-8")).decode("ascii"),
        ))
    except Exception as e:
        return False, f"读取兼容层 sdcompat.py 失败: {e}"

    for p in module_paths:
        rel = os.path.relpath(p, _plugin_root()).replace(os.sep, "/")
        cat = os.path.basename(os.path.dirname(p))
        mod = os.path.splitext(os.path.basename(p))[0]
        if mod == "sdcompat":
            continue  # 已作为 root_sdcompat 打包
        bundle_name = f"{cat}_{mod}"
        try:
            with open(p, "r", encoding="utf-8") as f:
                src = f.read()
        except Exception as e:
            return False, f"读取失败 {rel}: {e}"
        # 不做 PySide 静态改写：模块本就 try PySide6 except PySide2，兼容层负责抹平差异。
        # 相对 import 指向同包内其他模块：改写到合成子包内对应名字
        # from . import output_data as od  ->  from _maxsd_bundle import <cat>_output_data as od
        src = _rewrite_relative_imports(src, cat)
        b64 = base64.b64encode(src.encode("utf-8")).decode("ascii")
        entries.append((bundle_name, rel, b64))

    _feature_count = len(entries) - 1  # 扣掉 root_sdcompat
    header = '\n'.join([
        "# -*- coding: utf-8 -*-",
        '"""由 MaxSDPlugin/OutputTools 打包导出的独立脚本（命名空间隔离，前缀 _maxsd_）。',
        f"生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
        "目标 SD 版本：双版本通用（运行时自适应 SD16=PySide6/Qt6 与 SD13=PySide2/Qt5）",
        "跨版本差异由内置兼容层 _maxsd_bundle.root_sdcompat（sdcompat.py）统一抹平。",
        "包含模块：",
        *[f"  - {rel}（-> _maxsd_bundle.{bn}）" for bn, rel, _ in entries],
        "",
        "用法：merge 进你的工具后，调用 maxsd_activate(main_win) 或",
        "maxsd_show_windows['<模块名>'](main_win) 即可弹出对应功能窗口。",
        '"""',
        "",
        "import sys as _sys, types as _types, base64 as _b64",
        "",
        "_maxsd_export_version = 'universal'",
        "_MAXSD_PKG = '_maxsd_bundle'",
        "",
        "# 合成父包，使各模块的相对 import 仍可解析",
        "if _MAXSD_PKG not in _sys.modules:",
        "    _maxsd_p = _types.ModuleType(_MAXSD_PKG)",
        "    _maxsd_p.__path__ = []",
        "    _sys.modules[_MAXSD_PKG] = _maxsd_p",
        "_maxsd_pkg = _sys.modules[_MAXSD_PKG]",
        "",
        "# 各模块源码（base64，避免引号转义问题）",
        "_maxsd_sources = {",
        *[f"    {bn!r}: {b64!r}," for bn, _, b64 in entries],
        "}",
        "",
        "# 先登记空模块对象（让跨模块相对 import 拿到同一对象），再逐个 exec 填充",
        "for _n in _maxsd_sources:",
        "    _full = _MAXSD_PKG + '.' + _n",
        "    if _full not in _sys.modules:",
        "        _m = _types.ModuleType(_full)",
        "        _m.__package__ = _MAXSD_PKG",
        "        _sys.modules[_full] = _m",
        "        setattr(_maxsd_pkg, _n, _m)",
        "",
        "def _maxsd_exec(_n):",
        "    _full = _MAXSD_PKG + '.' + _n",
        "    _src = _b64.b64decode(_maxsd_sources[_n]).decode('utf-8')",
        "    exec(compile(_src, _full, 'exec'), _sys.modules[_full].__dict__)",
        "    return _sys.modules[_full]",
        "",
        "# 兼容层最先 exec 并打补丁，随后其余功能模块才引用它",
        "_maxsd_compat = None",
        "if 'root_sdcompat' in _maxsd_sources:",
        "    _maxsd_compat = _maxsd_exec('root_sdcompat')",
        "    try:",
        "        _maxsd_compat.qt_patch()",
        "    except Exception as _e:",
        "        print('[maxsd-export] qt_patch 失败', _e)",
        "for _n in _maxsd_sources:",
        "    if _n == 'root_sdcompat':",
        "        continue",
        "    _maxsd_exec(_n)",
        "",
        "# 暴露各模块的 show_window，供宿主激活",
        "maxsd_show_windows = {",
        "    _n: getattr(_sys.modules[_MAXSD_PKG + '.' + _n], 'show_window')",
        "    for _n in _maxsd_sources",
        "    if hasattr(_sys.modules[_MAXSD_PKG + '.' + _n], 'show_window')",
        "}",
        "",
        "def maxsd_activate(main_win=None):",
        '    """激活入口：返回 {模块名: show_window}。宿主可据此挂菜单或直接调用。"""',
        "    return maxsd_show_windows",
        "",
        "def _maxsd_main_window():",
        '    """尽力拿到 SD 主窗口作为父窗口；拿不到返回 None。优先走内置兼容层。"""',
        "    if _maxsd_compat is not None and hasattr(_maxsd_compat, 'get_main_window'):",
        "        try:",
        "            return _maxsd_compat.get_main_window()",
        "        except Exception:",
        "            pass",
        "    return None",
        "",
        "def maxsd_show_all(main_win=None):",
        '    """弹出所有含 show_window 的功能窗口。返回成功弹出的模块名列表。"""',
        "    if main_win is None:",
        "        main_win = _maxsd_main_window()",
        "    _shown = []",
        "    for _name, _fn in maxsd_show_windows.items():",
        "        try:",
        "            _fn(main_win)",
        "            _shown.append(_name)",
        "        except Exception as _e:",
        "            print('[maxsd-export] 弹窗失败', _name, _e)",
        "    return _shown",
        "",
        "# 直接在 SD Python Editor 里运行本文件时自动弹窗；被宿主 import 时不触发。",
        "if __name__ == '__main__':",
        "    if not maxsd_show_windows:",
        "        print('[maxsd-export] 未包含任何带 show_window 的功能，无窗口可弹。')",
        "    else:",
        "        print('[maxsd-export] 直接运行：弹出', maxsd_show_all())",
        "",
    ])
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header)
    except Exception as e:
        return False, f"写出失败: {e}"
    return True, (f"已导出 {_feature_count} 个模块（双版本通用，运行时自适应 SD13/SD16，内置兼容层）到:\n{out_path}\n"
                  f"· 直接在 SD Python Editor 运行会自动弹窗；\n"
                  f"· 宿主集成则 import 后调 maxsd_activate(main_win) 或 maxsd_show_all(main_win)。")


def export_modules_to_mg(module_paths, output_root):
    """把所选模块输出为 MG MaxSD loader 可加载的文件。返回 (ok, 信息)。

    输出目录可由用户指定；模块保留原分类子目录，文件名统一加 ``LG_MaxSD_``
    前缀。共享兼容层固定写到根目录 ``LG_MaxSD_sdcompat.py``。同名模块被同时
    选择时自动加分类名，避免 ``logic.py`` / ``window.py`` 互相覆盖。
    """
    if not module_paths:
        return False, "未选择任何功能。"
    if not output_root:
        return False, "未指定 MG 输出目录。"

    output_root = os.path.abspath(output_root)
    entries = _build_mg_entries(module_paths)
    written = []
    warnings = []

    try:
        os.makedirs(output_root, exist_ok=True)
        compat_source = os.path.join(_plugin_root(), "sdcompat.py")
        compat_target = os.path.join(output_root, "LG_MaxSD_sdcompat.py")
        with open(compat_source, "r", encoding="utf-8") as source_file:
            compat_text = source_file.read().replace("[MaxSDPlugin", "[LG_MaxSD")
        _write_text_file(compat_target, compat_text)
        written.append(compat_target)

        for entry in entries:
            with open(entry["source_path"], "r", encoding="utf-8") as source_file:
                source_text = source_file.read()
            output_text, missing = _rewrite_mg_source(source_text, entry, entries)
            category_dir = os.path.join(output_root, entry["category"])
            os.makedirs(category_dir, exist_ok=True)
            target_path = os.path.join(category_dir, entry["module_name"] + ".py")
            _write_text_file(target_path, output_text)
            written.append(target_path)
            warnings.extend(missing)
    except Exception as e:
        return False, f"输出到 MG 失败: {e}"

    message = f"已输出 {len(entries)} 个模块和兼容层到 MG 目录:\n{output_root}"
    if warnings:
        unique_warnings = sorted(set(warnings))
        message += "\n\n注意：以下相对依赖未在本次勾选中，请一并输出：\n· " + "\n· ".join(unique_warnings)
    message += "\n\n模块文件已生成；Start.py 与 LG_Tool.py 菜单仍由 MG 工具包按实际入口注册。"
    return True, message


def _build_mg_entries(module_paths):
    """建立源模块到 MG 模块名的映射，必要时消除同名冲突。"""
    raw_entries = []
    name_counts = {}
    for source_path in module_paths:
        absolute_path = os.path.abspath(source_path)
        category = os.path.basename(os.path.dirname(absolute_path))
        source_name = os.path.splitext(os.path.basename(absolute_path))[0]
        name_counts[source_name] = name_counts.get(source_name, 0) + 1
        raw_entries.append((absolute_path, category, source_name))

    entries = []
    for source_path, category, source_name in raw_entries:
        suffix = source_name
        if name_counts[source_name] > 1:
            suffix = f"{category}_{source_name}"
        entries.append({
            "source_path": source_path,
            "category": category,
            "source_name": source_name,
            "module_name": f"LG_MaxSD_{suffix}",
        })
    return entries


def _rewrite_mg_source(source_text, current_entry, entries):
    """把插件包相对 import 改为 MG loader 使用的唯一绝对模块名。"""
    by_key = {
        (entry["category"], entry["source_name"]): entry["module_name"]
        for entry in entries
    }
    missing = []
    output_lines = []
    category = current_entry["category"]

    for line in source_text.splitlines():
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        match = re.match(r"from \. import ([A-Za-z_]\w*)(?: as ([A-Za-z_]\w*))?\s*$", stripped)
        if match:
            dependency, alias = match.groups()
            target_name = by_key.get((category, dependency))
            if target_name is None:
                target_name = "LG_MaxSD_" + dependency
                missing.append(f"{category}/{dependency}.py")
            line = f"{indent}import {target_name}"
            if alias:
                line += f" as {alias}"
        else:
            match = re.match(r"from \.([A-Za-z_]\w*) import (.+)$", stripped)
            if match:
                dependency, imported_names = match.groups()
                target_name = by_key.get((category, dependency))
                if target_name is None:
                    target_name = "LG_MaxSD_" + dependency
                    missing.append(f"{category}/{dependency}.py")
                line = f"{indent}from {target_name} import {imported_names}"
            elif stripped.startswith("from .. import sdcompat"):
                alias = "sdcompat"
                if " as " in stripped:
                    alias = stripped.rsplit(" as ", 1)[1].strip()
                line = f"{indent}import LG_MaxSD_sdcompat as {alias}"
            elif stripped.startswith("from ..sdcompat import "):
                imported_names = stripped[len("from ..sdcompat import "):]
                line = f"{indent}from LG_MaxSD_sdcompat import {imported_names}"
            else:
                match = re.match(r"from \.\.([A-Za-z_]\w*) import (.+)$", stripped)
                if match:
                    dependency, imported_names = match.groups()
                    imported_module, alias = _split_single_import(imported_names)
                    target_name = by_key.get((dependency, imported_module))
                    if target_name is not None:
                        line = f"{indent}import {target_name}"
                        if alias:
                            line += f" as {alias}"
                    else:
                        target_name = _find_mg_symbol_module(dependency, imported_names, entries)
                        if target_name is None:
                            target_name = "LG_MaxSD_" + dependency
                            missing.append(f"{dependency}/__init__.py")
                        line = f"{indent}from {target_name} import {imported_names}"

        output_lines.append(line.replace("MaxSDPlugin", "LG_MaxSD"))

    return "\n".join(output_lines) + "\n", missing


def _split_single_import(imported_names):
    """解析单个 ``name [as alias]``；多项导入返回不会命中的原文本。"""
    if "," in imported_names:
        return imported_names.strip(), None
    parts = imported_names.strip().split(" as ", 1)
    return parts[0].strip(), parts[1].strip() if len(parts) == 2 else None


def _find_mg_symbol_module(category, imported_names, entries):
    """在已选分类模块中找到定义导入符号的文件，供跨分类 import 使用。"""
    symbol = imported_names.split(",", 1)[0].strip().split(" as ", 1)[0].strip()
    candidates = [entry for entry in entries if entry["category"] == category]
    for entry in candidates:
        try:
            with open(entry["source_path"], "r", encoding="utf-8") as source_file:
                source_text = source_file.read()
        except Exception:
            continue
        pattern = r"^(?:def|class)\s+" + re.escape(symbol) + r"\b"
        if re.search(pattern, source_text, re.MULTILINE):
            return entry["module_name"]
    if len(candidates) == 1:
        return candidates[0]["module_name"]
    return None


def _write_text_file(path, text):
    """先写临时文件再替换目标，避免输出中断留下半个 Python 文件。"""
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(text)
    os.replace(temp_path, path)


def _rewrite_relative_imports(src, cat):
    """把同包相对 import 改写到合成子包，前缀加上分类名以匹配 bundle 命名。

    `from . import output_data as od`      -> `from _maxsd_bundle import <cat>_output_data as od`
    `from .output_data import X`           -> `from _maxsd_bundle.<cat>_output_data import X`
    其他 `from .X` / `from ..X` 退化为指向合成父包，尽量不报错。
    """
    out = []
    for line in src.splitlines():
        s = line.lstrip()
        indent = line[:len(line) - len(s)]
        if s.startswith("from . import "):
            rest = s[len("from . import "):]
            # 可能形如 "output_data as od" 或 "a, b"
            names = []
            for token in rest.split(","):
                token = token.strip()
                if " as " in token:
                    name, alias = token.split(" as ", 1)
                    names.append(f"{cat}_{name.strip()} as {alias.strip()}")
                else:
                    names.append(f"{cat}_{token} as {token}")
            line = f"{indent}from _maxsd_bundle import " + ", ".join(names)
        elif s.startswith("from .") and not s.startswith("from .."):
            # from .modname import ...
            after = s[len("from ."):]
            modname, _, tail = after.partition(" import ")
            modname = modname.strip()
            line = f"{indent}from _maxsd_bundle.{cat}_{modname} import {tail.strip()}"
        elif s.startswith("from .. import sdcompat"):
            # 共享兼容层：from .. import sdcompat [as X] -> _maxsd_bundle.root_sdcompat
            rest = s[len("from .. import "):].strip()
            if " as " in rest:
                _, alias = rest.split(" as ", 1)
                line = f"{indent}from _maxsd_bundle import root_sdcompat as {alias.strip()}"
            else:
                line = f"{indent}from _maxsd_bundle import root_sdcompat as sdcompat"
        elif s.startswith("from ..sdcompat import "):
            tail = s[len("from ..sdcompat import "):]
            line = f"{indent}from _maxsd_bundle.root_sdcompat import {tail.strip()}"
        elif s.startswith("from ..") or s.startswith("import ."):
            # 父级/点 import：导出场景下无法精确还原，注释掉避免报错
            line = f"{indent}# [maxsd-export 移除相对 import] {s}"
        out.append(line)
    return "\n".join(out)


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
            self._info = QtWidgets.QLabel("勾选要打包的功能/分支，导出为一个独立 Python 文件。", self)
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
                "将把所选模块按分类写入以下目录，同名 LG_MaxSD_*.py 会被覆盖：\n\n"
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
    """功能入口：弹出 OutputTools 对话框。由 menu.py 的菜单动作调用。"""
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return
    try:
        _dialog_ref = OutputToolsDialog(parent=main_win)
        _dialog_ref.show()
        _dialog_ref.raise_()
        _dialog_ref.activateWindow()
    except Exception as e:
        print(f"{_LOG} 打开窗口失败: {e}")
