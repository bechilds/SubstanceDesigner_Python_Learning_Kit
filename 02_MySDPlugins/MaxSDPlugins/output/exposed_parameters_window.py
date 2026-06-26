# -*- coding: utf-8 -*-
"""曝光参数功能的 UI 层：按分组列出当前图的已暴露参数，可勾选、缓存/导出/加载/删除。

菜单位置：`MaxSDPlugin/Output/曝光参数`。

列表只包含「INPUT PARAMETERS」与「INPUTS」两类（排除 $outputsize 等内置基础参数），
并按 SD 中的分组（group 注解）保留层级显示。

功能：
- 缓存 / 导出 OutputData（已暴露参数快照，JSON）。
- 删除勾选项：取消暴露这些参数（graph.deleteProperty），操作可在 SD 中 Ctrl+Z 撤销；
  删除前自动备份一份 OutputData 到 .sbs 同目录，便于回滚。
- 加载历史：读取 OutputData，把其中记录的值应用回当前图中仍存在的同名参数。
"""

# --- PySide 导入：SD 16.0.1 = PySide6；保留 PySide2 回退以兼容旧版 ---
try:
    from PySide6 import QtWidgets, QtCore
except Exception:
    try:
        from PySide2 import QtWidgets, QtCore  # 旧版 SD 回退
    except Exception as _e:
        QtWidgets = None
        QtCore = None
        print(f"[MaxSDPlugin/output] PySide 导入失败，UI 不可用: {_e}")

from . import output_data as od

_LOG = "[MaxSDPlugin/output]"

# 模块级保存窗口引用，防止被 Python 垃圾回收导致窗口一闪而过
_dialog_ref = None


if QtWidgets is not None:

    class ExposedParametersDialog(QtWidgets.QDialog):
        """已暴露参数管理对话框（分组树 + 勾选 + 缓存/导出/加载/删除）。"""

        # 自定义角色：把参数 id 存到 tree item 上
        _ID_ROLE = (QtCore.Qt.UserRole if QtCore is not None else 32)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("曝光参数 - MaxSDPlugin")
            self.resize(600, 520)
            self._build_ui()
            self._refresh()

        # ---------------- UI 搭建 ----------------
        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            self._info_label = QtWidgets.QLabel(self)
            self._info_label.setWordWrap(True)
            layout.addWidget(self._info_label)

            # 分组树：分类 → 分组 → 参数（参数为可勾选叶子）
            self._tree = QtWidgets.QTreeWidget(self)
            self._tree.setHeaderLabels(["参数", "ID", "当前值"])
            self._tree.setColumnWidth(0, 240)
            self._tree.setColumnWidth(1, 160)
            layout.addWidget(self._tree, 1)

            # 选择相关按钮
            sel_row = QtWidgets.QHBoxLayout()
            self._btn_refresh = QtWidgets.QPushButton("刷新", self)
            self._btn_check_all = QtWidgets.QPushButton("全选", self)
            self._btn_uncheck_all = QtWidgets.QPushButton("全不选", self)
            self._btn_refresh.clicked.connect(self._refresh)
            self._btn_check_all.clicked.connect(lambda: self._set_all_checked(True))
            self._btn_uncheck_all.clicked.connect(lambda: self._set_all_checked(False))
            for b in (self._btn_refresh, self._btn_check_all, self._btn_uncheck_all):
                sel_row.addWidget(b)
            sel_row.addStretch(1)
            layout.addLayout(sel_row)

            # OutputData 相关按钮
            data_row = QtWidgets.QHBoxLayout()
            self._btn_cache = QtWidgets.QPushButton("缓存到当前目录", self)
            self._btn_export = QtWidgets.QPushButton("导出 OutputData…", self)
            self._btn_load = QtWidgets.QPushButton("加载历史…", self)
            self._btn_cache.clicked.connect(self._cache)
            self._btn_export.clicked.connect(self._export)
            self._btn_load.clicked.connect(self._load_history)
            for b in (self._btn_cache, self._btn_export, self._btn_load):
                data_row.addWidget(b)
            data_row.addStretch(1)
            layout.addLayout(data_row)

            # 操作 / 关闭按钮
            act_row = QtWidgets.QHBoxLayout()
            self._btn_delete = QtWidgets.QPushButton("删除勾选项（取消暴露）", self)
            self._btn_delete.clicked.connect(self._delete_checked)
            self._btn_repair = QtWidgets.QPushButton("修复损坏函数", self)
            self._btn_repair.setToolTip(
                "扫描当前图，把之前删除暴露参数后残留的、变量名为空的 Get 函数重置回常量值。"
            )
            self._btn_repair.clicked.connect(self._repair_broken)
            self._btn_close = QtWidgets.QPushButton("关闭", self)
            self._btn_close.clicked.connect(self.close)
            act_row.addWidget(self._btn_delete)
            act_row.addWidget(self._btn_repair)
            act_row.addStretch(1)
            act_row.addWidget(self._btn_close)
            layout.addLayout(act_row)

        # ---------------- 数据填充 ----------------
        def _refresh(self):
            """从当前图重新读取已暴露参数，按分组填充树。"""
            self._tree.clear()
            graph = od.get_current_graph()
            if graph is None:
                self._info_label.setText("未找到当前图。请在 SD 中打开一个图后再点“刷新”。")
                return
            params = od.collect_exposed_parameters(graph)
            grouped = od.group_parameters(params)
            pkg_path = od.get_package_file_path(graph) or "（package 尚未保存到磁盘）"
            self._info_label.setText(
                f"已暴露参数（INPUT PARAMETERS / INPUTS）：{len(params)} 个\nPackage：{pkg_path}"
            )
            self._fill_tree(grouped)
            self._tree.expandAll()

        def _fill_tree(self, grouped):
            """grouped: [(category_label, [(group_name, [param,...]), ...]), ...]。"""
            for cat_label, groups in grouped:
                cat_item = QtWidgets.QTreeWidgetItem(self._tree, [cat_label])
                cat_item.setFlags(QtCore.Qt.ItemIsEnabled)  # 分类节点不可勾选
                for group_name, plist in groups:
                    parent = cat_item
                    if group_name:
                        grp_item = QtWidgets.QTreeWidgetItem(cat_item, [group_name])
                        grp_item.setFlags(QtCore.Qt.ItemIsEnabled)
                        parent = grp_item
                    for p in plist:
                        leaf = QtWidgets.QTreeWidgetItem(
                            parent,
                            [p.get("label") or p.get("id"), p.get("id"), str(p.get("value"))],
                        )
                        leaf.setFlags(
                            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
                        )
                        leaf.setCheckState(0, QtCore.Qt.Unchecked)
                        leaf.setData(0, self._ID_ROLE, p.get("id"))

        def _iter_leaves(self):
            """遍历所有「参数叶子」节点（带 id 的可勾选项）。"""
            stack = [
                self._tree.topLevelItem(i)
                for i in range(self._tree.topLevelItemCount())
            ]
            while stack:
                item = stack.pop()
                if item is None:
                    continue
                if item.data(0, self._ID_ROLE) is not None:
                    yield item
                for c in range(item.childCount()):
                    stack.append(item.child(c))

        def _set_all_checked(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for leaf in self._iter_leaves():
                leaf.setCheckState(0, state)

        def _checked_ids(self):
            return [
                leaf.data(0, self._ID_ROLE)
                for leaf in self._iter_leaves()
                if leaf.checkState(0) == QtCore.Qt.Checked
            ]

        # ---------------- OutputData ----------------
        def _cache(self):
            """把当前 OutputData 缓存到当前 .sbs 同目录的 OutputData.json。"""
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            path = od.get_default_output_data_path(graph)
            if not path:
                self._warn("当前 package 尚未保存到磁盘，无法定位缓存目录。请先保存 .sbs。")
                return
            try:
                data = od.build_output_data(graph, self._checked_ids())
                od.save_output_data(data, path)
                self._info(f"已缓存 OutputData：\n{path}")
            except Exception as e:
                print(f"{_LOG} 缓存失败: {e}")
                self._warn(f"缓存失败：{e}")

        def _export(self):
            """导出当前 OutputData 到用户选择的位置。"""
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            default_dir = od.get_default_output_data_path(graph) or od.OUTPUT_DATA_FILENAME
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "导出 OutputData", default_dir, "JSON (*.json)"
            )
            if not path:
                return
            try:
                data = od.build_output_data(graph, self._checked_ids())
                od.save_output_data(data, path)
                self._info(f"已导出 OutputData：\n{path}")
            except Exception as e:
                print(f"{_LOG} 导出失败: {e}")
                self._warn(f"导出失败：{e}")

        def _load_history(self):
            """加载历史 OutputData，并把其中记录的值应用回当前图仍存在的同名参数。"""
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。请先在 SD 中打开要应用的图。")
                return
            start_dir = od.get_default_output_data_path(graph) or ""
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "加载历史 OutputData", start_dir, "JSON (*.json)"
            )
            if not path:
                return
            try:
                data = od.load_output_data(path)
            except Exception as e:
                print(f"{_LOG} 加载失败: {e}")
                self._warn(f"加载失败：{e}")
                return

            summary = od.apply_output_data(graph, data)
            self._refresh()

            lines = [
                f"来源：{path}",
                f"已还原值：{len(summary['restored'])} 个",
            ]
            if summary["missing"]:
                lines.append(
                    f"当前图已不存在、无法还原：{len(summary['missing'])} 个\n  "
                    + ", ".join(summary["missing"][:20])
                    + ("…" if len(summary["missing"]) > 20 else "")
                )
            if summary["skipped"]:
                lines.append(
                    f"类型不支持自动还原 / 失败：{len(summary['skipped'])} 个\n  "
                    + ", ".join(pid for pid, _ in summary["skipped"][:20])
                    + ("…" if len(summary["skipped"]) > 20 else "")
                )
            lines.append("\n注：本功能只还原“仍然暴露的参数的值”；无法重新创建已删除的暴露参数。")
            self._info("\n".join(lines))

        # ---------------- 删除（取消暴露） ----------------
        def _delete_checked(self):
            """删除（取消暴露）勾选的参数。删除前自动备份，操作可在 SD 中 Ctrl+Z 撤销。"""
            ids = self._checked_ids()
            if not ids:
                self._warn("请先勾选要删除的参数。")
                return

            confirm = QtWidgets.QMessageBox.question(
                self,
                "确认删除（取消暴露）",
                f"将取消暴露以下 {len(ids)} 个参数：\n\n"
                + "\n".join(f"· {pid}" for pid in ids[:20])
                + ("\n…" if len(ids) > 20 else "")
                + "\n\n删除前会自动备份一份 OutputData 到 .sbs 同目录；"
                "误删可在 SD 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return

            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return

            # 删除前自动备份（不阻断删除：备份失败只提示）
            backup_path = od.get_default_output_data_path(graph)
            if backup_path:
                try:
                    od.save_output_data(od.build_output_data(graph, ids), backup_path)
                except Exception as e:
                    print(f"{_LOG} 删除前备份失败: {e}")

            deleted, failed, reset = od.delete_exposed_parameters(graph, ids)
            self._refresh()

            msg = [f"已取消暴露：{len(deleted)} 个"]
            msg.append(f"已重置节点参数（恢复常量）：{reset} 个")
            if backup_path:
                msg.append(f"已备份到：{backup_path}")
            if failed:
                msg.append(
                    f"失败：{len(failed)} 个\n  "
                    + "\n  ".join(f"{pid}: {reason}" for pid, reason in failed[:20])
                )
            msg.append("\n如需撤销，请在 SD 中按 Ctrl+Z。")
            self._info("\n".join(msg))

        def _repair_broken(self):
            """扫描当前图，重置之前删除暴露参数后残留的、变量名为空的损坏 Get 函数。"""
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            confirm = QtWidgets.QMessageBox.question(
                self,
                "修复损坏函数",
                "将扫描当前图，把变量名为空的 Get 函数重置回常量值"
                "（即修复之前删除暴露参数后残留的悬空引用）。\n\n"
                "操作可在 SD 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            reset = od.repair_broken_node_functions(graph)
            self._refresh()
            if reset:
                self._info(f"已重置 {reset} 个损坏的节点参数（恢复常量）。\n\n如需撤销，请在 SD 中按 Ctrl+Z。")
            else:
                self._info("未发现需要修复的损坏 Get 函数。")

        # ---------------- 小工具 ----------------
        def _info(self, msg):
            QtWidgets.QMessageBox.information(self, "MaxSDPlugin", msg)

        def _warn(self, msg):
            QtWidgets.QMessageBox.warning(self, "MaxSDPlugin", msg)


def show_window(main_win=None):
    """功能入口：弹出曝光参数对话框。由 MaxSDPlugin.py 的菜单动作调用。"""
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return
    try:
        _dialog_ref = ExposedParametersDialog(parent=main_win)
        _dialog_ref.show()
        _dialog_ref.raise_()
        _dialog_ref.activateWindow()
    except Exception as e:
        print(f"{_LOG} 打开窗口失败: {e}")
