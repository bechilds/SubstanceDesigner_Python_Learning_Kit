# -*- coding: utf-8 -*-
"""保存当前 SBS 副本，并收集非官方、非团队库的依赖与 Resource。"""

import hashlib
import json
import ntpath
import os
import shutil

from .. import sdcompat

QtWidgets = sdcompat.QtWidgets
QtCore = sdcompat.QtCore

_LOG = "[MaxSDPlugin/SaveWithResrouce]"
_dialog_ref = None
_APPROVED_LIBRARY_ROOT = ntpath.normcase(ntpath.normpath(r"D:\LG_SDNodes"))


def _as_list(value):
    try:
        return list(value)
    except Exception:
        result = []
        try:
            for index in range(len(value)):
                result.append(value[index])
        except Exception:
            pass
        return result


def _file_path(owner):
    try:
        return str(owner.getFilePath() or "")
    except Exception:
        return ""


def _local_path(path):
    if not path:
        return ""
    text = str(path).strip()
    if text.lower().startswith(("sbs://", "pkg://")):
        return ""
    return ntpath.normcase(ntpath.normpath(text))


def _official_package_roots():
    roots = []
    try:
        import sd
        sd_file = getattr(sd, "__file__", "") or ""
        normalized = _local_path(sd_file)
        marker = ntpath.normcase(ntpath.normpath(r"resources\python\sd"))
        marker_index = normalized.rfind(marker)
        if marker_index >= 0:
            install_root = normalized[:marker_index]
            roots.append(ntpath.normcase(ntpath.normpath(
                ntpath.join(install_root, "resources", "packages"))))
    except Exception:
        pass
    return roots


def _is_under_root(path, root):
    try:
        return ntpath.commonpath([path, root]) == root
    except Exception:
        return False


def _is_approved_path(path):
    normalized = _local_path(path)
    if not normalized:
        return True
    roots = [_APPROVED_LIBRARY_ROOT] + _official_package_roots()
    return any(_is_under_root(normalized, root) for root in roots)


def _is_collectable(path):
    """仅收集可信库之外的本地路径。"""
    if not _local_path(path):
        return False
    return not _is_approved_path(path)


def collect_external_files(package):
    """递归收集 Package 的外部依赖与 Resource，按源路径去重。"""
    collected = {}
    if package is None:
        return []
    root_package_path = _local_path(_file_path(package))
    visited_packages = set()

    def _package_key(current_package):
        path = _local_path(_file_path(current_package))
        if path:
            return path
        try:
            return str(current_package.getUID() or id(current_package))
        except Exception:
            return str(id(current_package))

    def _scan(current_package):
        key = _package_key(current_package)
        if key in visited_packages:
            return
        visited_packages.add(key)
        package_path = _local_path(_file_path(current_package))

        try:
            resources = _as_list(current_package.getChildrenResources(True))
        except Exception:
            resources = []
        for resource in resources:
            path = _file_path(resource)
            normalized = _local_path(path)
            if normalized == package_path:
                continue
            if _is_collectable(path):
                collected.setdefault(normalized, {"source": path, "kinds": set()})["kinds"].add("resource")

        try:
            dependencies = _as_list(current_package.getDependencies())
        except Exception:
            dependencies = []
        for dependency in dependencies:
            path = _file_path(dependency)
            if not _is_collectable(path):
                continue
            normalized = _local_path(path)
            if normalized == root_package_path:
                continue
            collected.setdefault(normalized, {"source": path, "kinds": set()})["kinds"].add("dependency")
            try:
                nested_package = dependency.getPackage()
            except Exception:
                nested_package = None
            if nested_package is not None:
                _scan(nested_package)

    _scan(package)

    result = []
    for item in collected.values():
        source = item["source"]
        result.append({
            "source": source,
            "kinds": sorted(item["kinds"]),
            "exists": os.path.isfile(source),
        })
    result.sort(key=lambda item: (not item["exists"], item["source"].lower()))
    return result


def _copy_name(source, used_names):
    """生成不冲突的复制文件名；同名不同路径追加短哈希。"""
    base_name = os.path.basename(source) or "unnamed_resource"
    key = base_name.lower()
    if key not in used_names:
        used_names.add(key)
        return base_name
    stem, extension = os.path.splitext(base_name)
    suffix = hashlib.sha1(source.lower().encode("utf-8")).hexdigest()[:8]
    candidate = f"{stem}_{suffix}{extension}"
    used_names.add(candidate.lower())
    return candidate


def save_package_with_resources(app, package, target_folder, items):
    """保存 SBS 副本、复制文件并生成清单，返回清单字典。"""
    if app is None or package is None:
        raise ValueError("未找到 SDApplication 或当前 Package。")
    os.makedirs(target_folder, exist_ok=True)
    source_package_path = _file_path(package)
    package_name = os.path.basename(source_package_path) if source_package_path else "package_copy.sbs"
    if not package_name.lower().endswith(".sbs"):
        package_name += ".sbs"
    target_package_path = os.path.join(target_folder, package_name)
    app.getPackageMgr().saveCopyOfPackageAs(package, target_package_path)

    used_by_folder = {"dependencies": set(), "resources": set()}
    manifest_items = []
    for item in items:
        kinds = item.get("kinds", [])
        folder_name = "dependencies" if "dependency" in kinds else "resources"
        destination_folder = os.path.join(target_folder, folder_name)
        os.makedirs(destination_folder, exist_ok=True)
        entry = {
            "source": item.get("source", ""),
            "kinds": list(kinds),
            "exists": bool(item.get("exists")),
            "copied_to": "",
            "status": "missing" if not item.get("exists") else "pending",
        }
        if item.get("exists"):
            try:
                destination_name = _copy_name(item["source"], used_by_folder[folder_name])
                destination = os.path.join(destination_folder, destination_name)
                shutil.copy2(item["source"], destination)
                entry["copied_to"] = os.path.relpath(destination, target_folder)
                entry["status"] = "copied"
            except Exception as error:
                entry["status"] = "error"
                entry["error"] = str(error)
        manifest_items.append(entry)

    manifest = {
        "source_package": source_package_path,
        "saved_package": package_name,
        "note": "文件已复制但当前 SBS 内的引用路径未改写。",
        "items": manifest_items,
    }
    manifest_path = os.path.join(target_folder, "resource_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    return manifest


if QtWidgets is not None:

    class SaveWithResrouceDialog(QtWidgets.QDialog):
        """外部文件预览与 Package 副本保存窗口。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("SaveWithResrouce")
            self.resize(780, 520)
            self._app = None
            self._package = None
            self._items = []
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            self._summary = QtWidgets.QLabel(self)
            self._summary.setWordWrap(True)
            layout.addWidget(self._summary)
            self._table = QtWidgets.QTableWidget(0, 3, self)
            self._table.setHorizontalHeaderLabels(["类型", "状态", "原始路径"])
            self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self._table, 1)
            tip = QtWidgets.QLabel(
                "只收集 Substance Designer 官方节点库和 D:\\LG_SDNodes 之外的本地文件。"
                "保存操作不会修改当前 Package，也不会改写副本中的引用路径。", self)
            tip.setWordWrap(True)
            layout.addWidget(tip)
            buttons = QtWidgets.QHBoxLayout()
            refresh_button = QtWidgets.QPushButton("重新搜集", self)
            save_button = QtWidgets.QPushButton("选择文件夹并保存", self)
            close_button = QtWidgets.QPushButton("关闭", self)
            refresh_button.clicked.connect(self._refresh)
            save_button.clicked.connect(self._save)
            close_button.clicked.connect(self.close)
            buttons.addWidget(refresh_button)
            buttons.addStretch(1)
            buttons.addWidget(save_button)
            buttons.addWidget(close_button)
            layout.addLayout(buttons)

        def _refresh(self):
            self._app = sdcompat.get_app()
            graph = sdcompat.get_current_graph(self._app)
            try:
                self._package = graph.getPackage() if graph is not None else None
            except Exception:
                self._package = None
            self._items = collect_external_files(self._package)
            missing_count = sum(1 for item in self._items if not item["exists"])
            package_path = _file_path(self._package) or "<未保存 Package>"
            self._summary.setText(
                f"当前文件：{package_path}\n待收集：{len(self._items)} 个，缺失：{missing_count} 个")
            self._table.setRowCount(len(self._items))
            for row, item in enumerate(self._items):
                values = (
                    " + ".join(item["kinds"]),
                    "存在" if item["exists"] else "缺失",
                    item["source"],
                )
                for column, value in enumerate(values):
                    self._table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            self._table.resizeColumnsToContents()

        def _save(self):
            if self._package is None or self._app is None:
                QtWidgets.QMessageBox.warning(self, "SaveWithResrouce", "未找到当前 Package。")
                return
            target = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存文件夹")
            if not target:
                return
            package_name = os.path.basename(_file_path(self._package)) or "package_copy.sbs"
            package_target = os.path.join(target, package_name)
            if os.path.exists(package_target):
                answer = QtWidgets.QMessageBox.question(
                    self, "覆盖确认", f"目标文件已存在：\n{package_target}\n\n是否覆盖？",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if answer != QtWidgets.QMessageBox.Yes:
                    return
            try:
                manifest = save_package_with_resources(self._app, self._package, target, self._items)
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "SaveWithResrouce", f"保存失败：{error}")
                print(f"{_LOG} 保存失败: {error}")
                return
            copied = sum(1 for item in manifest["items"] if item["status"] == "copied")
            failed = sum(1 for item in manifest["items"] if item["status"] != "copied")
            QtWidgets.QMessageBox.information(
                self, "SaveWithResrouce",
                f"保存完成。\nSBS 副本：{manifest['saved_package']}\n复制文件：{copied}\n缺失/失败：{failed}\n"
                "清单：resource_manifest.json")


def show_window(main_win=None):
    """菜单入口。"""
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return
    try:
        _dialog_ref = SaveWithResrouceDialog(main_win or sdcompat.get_main_window())
        _dialog_ref.show()
        _dialog_ref.raise_()
        _dialog_ref.activateWindow()
    except Exception as error:
        print(f"{_LOG} 打开窗口失败: {error}")