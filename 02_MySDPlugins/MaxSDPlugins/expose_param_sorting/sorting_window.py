# -*- coding: utf-8 -*-
"""曝光参数自动排序 —— Qt 对话框。

树状展示：
  ├── [分组名]  (3 个参数)       ← 顶级节点，可上/下移
  │     ├── label_A  [id_A]  float1
  │     ├── label_B  [id_B]  bool
  │     └── label_C  [id_C]  float3
  └── （未分组）  (1 个参数)
        └── label_D  [id_D]  string

只扫描并排序 INPUT PARAMETERS；连接型 INPUTS 和 OUTPUTS 不读取、不修改。

操作：
  - [刷新]      重新从当前 Graph 读取参数树。
  - [↑ 上移分组] 将选中分组在树中上移一位。
  - [↓ 下移分组] 将选中分组在树中下移一位。
    - [应用排序]   保存并重载 Package，通过 XML 调整参数顺序。
  - [关闭]      关闭窗口。
"""

from .. import sdcompat

QtWidgets = sdcompat.QtWidgets
QtCore = sdcompat.QtCore
QtGui = sdcompat.QtGui

_LOG = "[MaxSDPlugin/ExposeParamSorting]"
_dialog_ref = None  # 保活引用，防止 GC

# ── 树节点数据角色 ──────────────────────────────────────────────────────────
_ROLE_IS_GROUP = (QtCore.Qt.UserRole if QtCore is not None else 32)
_ROLE_SNAPSHOT = (QtCore.Qt.UserRole + 1 if QtCore is not None else 33)


if QtWidgets is not None:

    class _ParamTreeWidget(QtWidgets.QTreeWidget):
        """仅响应单击选中分组，屏蔽双击展开/折叠（防止误操作）。"""

        def mouseDoubleClickEvent(self, event):
            # 双击只切换展开/折叠，不做其他操作
            super().mouseDoubleClickEvent(event)

    # ─────────────────────────────────────────────────────────────────────── #

    class ExposeParamSortingDialog(QtWidgets.QDialog):
        """曝光参数自动排序主窗口。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("曝光参数自动排序 — ExposeParameterAutoSorting")
            self.resize(640, 520)
            self._graph = None
            self._scope = None
            self._build_ui()
            self._refresh()

        # ── UI 构建 ─────────────────────────────────────────────────────── #

        def _build_ui(self):
            root_layout = QtWidgets.QVBoxLayout(self)

            # 顶部说明栏
            info = QtWidgets.QLabel(
                "树状展示当前 Graph 的 INPUT PARAMETERS 与分组。选中分组后可上/下移动，"
                "调整完毕后点击「应用排序」保存、关闭并重新加载 Package。\n"
                "INPUTS 和 OUTPUTS 不读取、不修改。工具会先创建 SBS 备份；此操作不支持 Ctrl+Z。",
                self,
            )
            info.setWordWrap(True)
            root_layout.addWidget(info)

            # 中部：树 + 控制按钮
            mid_layout = QtWidgets.QHBoxLayout()
            root_layout.addLayout(mid_layout, 1)

            # 参数树
            self._tree = _ParamTreeWidget(self)
            self._tree.setColumnCount(3)
            self._tree.setHeaderLabels(["分组 / 参数", "ID", "类型"])
            self._tree.header().setStretchLastSection(False)
            self._tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            self._tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            self._tree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self._tree.itemSelectionChanged.connect(self._on_selection_changed)
            mid_layout.addWidget(self._tree, 1)

            # 右侧控制按钮列
            btn_col = QtWidgets.QVBoxLayout()
            btn_col.setAlignment(QtCore.Qt.AlignTop)
            mid_layout.addLayout(btn_col)

            self._btn_up = QtWidgets.QPushButton("↑  上移分组", self)
            self._btn_down = QtWidgets.QPushButton("↓  下移分组", self)
            self._btn_refresh = QtWidgets.QPushButton("⟳  刷新", self)
            btn_expand = QtWidgets.QPushButton("⊞  全部展开", self)
            btn_collapse = QtWidgets.QPushButton("⊟  全部收起", self)
            self._btn_up.setEnabled(False)
            self._btn_down.setEnabled(False)
            self._btn_up.clicked.connect(self._move_group_up)
            self._btn_down.clicked.connect(self._move_group_down)
            self._btn_refresh.clicked.connect(self._refresh)
            btn_expand.clicked.connect(self._tree.expandAll)
            btn_collapse.clicked.connect(self._tree.collapseAll)

            for btn in (self._btn_up, self._btn_down, self._btn_refresh, btn_expand, btn_collapse):
                btn.setMinimumWidth(110)
                btn_col.addWidget(btn)

            btn_col.addStretch(1)

            # 底部状态 + 操作按钮
            bottom_layout = QtWidgets.QHBoxLayout()
            root_layout.addLayout(bottom_layout)

            self._status = QtWidgets.QLabel("就绪", self)
            self._status.setWordWrap(True)
            bottom_layout.addWidget(self._status, 1)

            self._btn_apply = QtWidgets.QPushButton("✔  应用排序", self)
            self._btn_apply.setToolTip("备份并重排 SBS XML，然后重新加载 Package")
            btn_close = QtWidgets.QPushButton("关闭", self)
            self._btn_apply.clicked.connect(self._apply_sort)
            btn_close.clicked.connect(self.reject)
            bottom_layout.addWidget(self._btn_apply)
            bottom_layout.addWidget(btn_close)

        # ── 刷新 ────────────────────────────────────────────────────────── #

        def _refresh(self):
            from . import sorting_logic

            self._graph = sdcompat.get_current_graph()
            self._scope = sorting_logic.get_graph_scope(self._graph)
            self._tree.clear()

            if self._graph is None:
                self._set_status("⚠  未找到当前 Graph，请先在 SD 中打开一个图。", error=True)
                self._btn_apply.setEnabled(False)
                return

            groups = sorting_logic.collect_groups(self._graph)
            if not groups:
                self._set_status("当前 Graph 没有暴露参数。", error=False)
                self._btn_apply.setEnabled(False)
                return

            total_params = 0
            font_bold = QtGui.QFont()
            font_bold.setBold(True)

            for group_name, params in groups:
                display_group = group_name if group_name else "（未分组）"
                suffix = f"  ({len(params)} 个参数)"

                group_item = QtWidgets.QTreeWidgetItem(self._tree)
                group_item.setText(0, display_group + suffix)
                group_item.setText(1, "")
                group_item.setText(2, "")
                group_item.setFont(0, font_bold)
                group_item.setData(0, _ROLE_IS_GROUP, True)
                # 存储原始 (group_name, params) 快照，供 apply 时使用
                group_item.setData(0, _ROLE_SNAPSHOT, (group_name, params))

                for p in params:
                    param_item = QtWidgets.QTreeWidgetItem(group_item)
                    param_item.setText(0, "    " + p["label"])
                    param_item.setText(1, p["id"])
                    param_item.setText(2, p["type_label"])
                    param_item.setData(0, _ROLE_IS_GROUP, False)
                    param_item.setData(0, _ROLE_SNAPSHOT, p)

                    total_params += 1

                group_item.setExpanded(True)

            self._tree.resizeColumnToContents(1)
            self._tree.resizeColumnToContents(2)

            group_count = len(groups)
            package_name = self._scope.get("package_path") or "<未保存 SBS>"
            graph_id = self._scope.get("graph_id") or "<未知 Graph>"
            status_msg = (
                f"范围：{package_name} / {graph_id}\n"
                f"已扫描：{group_count} 个分组，{total_params} 个 INPUT PARAMETERS；"
                "INPUTS / OUTPUTS 已排除。")
            self._set_status(status_msg)
            self._btn_apply.setEnabled(total_params > 0)
            self._on_selection_changed()

        # ── 分组移动 ─────────────────────────────────────────────────────── #

        def _selected_group_item(self):
            """返回当前选中的顶级分组 QTreeWidgetItem；不是分组则返回 None。"""
            selected = self._tree.selectedItems()
            if not selected:
                return None
            item = selected[0]
            if item.data(0, _ROLE_IS_GROUP):
                return item
            # 若选中了子参数，返回其父分组
            parent = item.parent()
            if parent is not None and parent.data(0, _ROLE_IS_GROUP):
                return parent
            return None

        def _on_selection_changed(self):
            group_item = self._selected_group_item()
            if group_item is None:
                self._btn_up.setEnabled(False)
                self._btn_down.setEnabled(False)
                return
            root = self._tree.invisibleRootItem()
            idx = root.indexOfChild(group_item)
            self._btn_up.setEnabled(idx > 0)
            self._btn_down.setEnabled(idx < root.childCount() - 1)

        def _move_group(self, direction):
            """direction: -1 = 上移, +1 = 下移。"""
            group_item = self._selected_group_item()
            if group_item is None:
                return
            root = self._tree.invisibleRootItem()
            idx = root.indexOfChild(group_item)
            new_idx = idx + direction
            if new_idx < 0 or new_idx >= root.childCount():
                return

            # takeChild / insertChild 移动整个子树
            was_expanded = group_item.isExpanded()
            taken = root.takeChild(idx)
            root.insertChild(new_idx, taken)
            taken.setExpanded(was_expanded)
            self._tree.setCurrentItem(taken)
            self._on_selection_changed()

        def _move_group_up(self):
            self._move_group(-1)

        def _move_group_down(self):
            self._move_group(+1)

        # ── 应用排序 ─────────────────────────────────────────────────────── #

        def _current_ordered_groups(self):
            """从树中读取当前分组顺序，返回 [(group_name, [snapshot_dict]), ...]。"""
            root = self._tree.invisibleRootItem()
            result = []
            for i in range(root.childCount()):
                group_item = root.child(i)
                snap = group_item.data(0, _ROLE_SNAPSHOT)
                if snap is not None:
                    result.append(snap)
            return result

        def _apply_sort(self):
            if self._graph is None:
                self._set_status("⚠  没有可操作的 Graph，请先刷新。", error=True)
                return

            from . import sorting_logic
            active_graph = sdcompat.get_current_graph()
            active_scope = sorting_logic.get_graph_scope(active_graph)
            if not sorting_logic._same_graph_scope(self._scope or {}, active_scope):
                self._set_status("⚠  当前活动 Graph 已变化，请刷新后再执行。", error=True)
                QtWidgets.QMessageBox.warning(
                    self, "执行范围已变化",
                    "你在扫描后切换了 Graph 或 SBS。为避免修改错误文件，操作已中止。\n"
                    "请切回目标 Graph 并点击「刷新」。")
                return

            ordered_groups = self._current_ordered_groups()
            if not ordered_groups:
                self._set_status("⚠  树为空，无法应用。", error=True)
                return

            # 确认对话框
            group_names = [g or "（未分组）" for g, _ in ordered_groups]
            preview = "\n".join(f"  {i + 1}. {name}" for i, name in enumerate(group_names))
            package_path = self._scope.get("package_path") or "<未保存 SBS>"
            graph_id = self._scope.get("graph_id") or "<未知 Graph>"
            reply = QtWidgets.QMessageBox.question(
                self,
                "确认应用排序",
                "工具将先保存当前 Package 并创建备份，然后关闭 Package、"
                "调整 SBS XML 并重新加载。此操作不支持 Ctrl+Z。\n\n"
                f"唯一执行范围：\nSBS: {package_path}\nGraph: {graph_id}\n\n"
                f"目标分组顺序：\n{preview}\n\n是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            self._set_status("正在应用排序……")
            QtWidgets.QApplication.processEvents()

            success, messages = sorting_logic.apply_group_order(self._graph, ordered_groups)

            summary = messages[0] if messages else ("成功" if success else "失败")
            details = "\n".join(messages[1:]) if len(messages) > 1 else ""

            if success:
                self._set_status(f"✔  {summary}", error=False)
                QtWidgets.QMessageBox.information(
                    self, "应用排序完成",
                    f"{summary}\n\n{details}" if details else summary)
                self._graph = None
                self._scope = None
                self._tree.clear()
                self._btn_apply.setEnabled(False)
            else:
                self._set_status(f"✘  {summary}", error=True)
                QtWidgets.QMessageBox.critical(
                    self, "应用排序失败",
                    f"{summary}\n\n{details}" if details else summary)

        # ── 辅助 ─────────────────────────────────────────────────────────── #

        def _set_status(self, text, error=False):
            self._status.setText(text)
            color = "#ef5350" if error else "#cccccc"
            self._status.setStyleSheet(f"color: {color};")


# ─────────────────────────────────────────────────────────────────────────── #
# 入口：供 menu.py 通过 _add_category 调用
# ─────────────────────────────────────────────────────────────────────────── #

def show_window(parent=None):
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return

    sdcompat.qt_patch()

    if _dialog_ref is not None:
        try:
            _dialog_ref.raise_()
            _dialog_ref.activateWindow()
            return
        except Exception:
            _dialog_ref = None

    dlg = ExposeParamSortingDialog(parent)
    _dialog_ref = dlg
    dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    dlg.destroyed.connect(lambda: _clear_dialog_ref())
    dlg.show()


def _clear_dialog_ref():
    global _dialog_ref
    _dialog_ref = None
