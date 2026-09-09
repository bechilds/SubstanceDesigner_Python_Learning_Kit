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
    - 拖拽分组可调整分组顺序；拖拽参数可调整组内顺序或更改分组。
    - [↑/↓]       移动选中分组或组内参数，也可使用 Ctrl+↑/Ctrl+↓。
    - [更改分组]  将选中参数移动到已有分组。
    - [应用排序]  保存并重载 Package，通过 XML 调整参数顺序和 Group。
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
        """约束拖拽层级，并向窗口转发排序快捷键。"""

        order_changed = QtCore.Signal()
        move_requested = QtCore.Signal(int)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDefaultDropAction(QtCore.Qt.MoveAction)
            self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        def keyPressEvent(self, event):
            if event.modifiers() & QtCore.Qt.ControlModifier:
                if event.key() == QtCore.Qt.Key_Up:
                    self.move_requested.emit(-1)
                    event.accept()
                    return
                if event.key() == QtCore.Qt.Key_Down:
                    self.move_requested.emit(1)
                    event.accept()
                    return
            super().keyPressEvent(event)

        def dropEvent(self, event):
            selected = self.selectedItems()
            moving_item = selected[0] if len(selected) == 1 else None
            event_position = (
                event.position().toPoint()
                if hasattr(event, "position") else event.pos())
            target_item = self.itemAt(event_position)
            if moving_item is None or target_item is None or moving_item is target_item:
                event.ignore()
                return

            indicator = self.dropIndicatorPosition()
            above = QtWidgets.QAbstractItemView.AboveItem
            below = QtWidgets.QAbstractItemView.BelowItem
            on_item = QtWidgets.QAbstractItemView.OnItem
            moving_is_group = bool(moving_item.data(0, _ROLE_IS_GROUP))
            target_is_group = bool(target_item.data(0, _ROLE_IS_GROUP))

            if moving_is_group:
                if not target_is_group or indicator not in (above, below):
                    event.ignore()
                    return
                root = self.invisibleRootItem()
                source_index = root.indexOfChild(moving_item)
                insert_index = root.indexOfChild(target_item)
                if indicator == below:
                    insert_index += 1
                taken = root.takeChild(source_index)
                if source_index < insert_index:
                    insert_index -= 1
                root.insertChild(insert_index, taken)
            else:
                source_parent = moving_item.parent()
                if source_parent is None:
                    event.ignore()
                    return
                if target_is_group:
                    if indicator != on_item:
                        event.ignore()
                        return
                    target_parent = target_item
                    insert_index = target_parent.childCount()
                else:
                    target_parent = target_item.parent()
                    if target_parent is None or indicator not in (above, below):
                        event.ignore()
                        return
                    insert_index = target_parent.indexOfChild(target_item)
                    if indicator == below:
                        insert_index += 1
                source_index = source_parent.indexOfChild(moving_item)
                taken = source_parent.takeChild(source_index)
                if source_parent is target_parent and source_index < insert_index:
                    insert_index -= 1
                target_parent.insertChild(insert_index, taken)
                target_parent.setExpanded(True)

            self.setCurrentItem(taken)
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
            self.order_changed.emit()

        def mouseDoubleClickEvent(self, event):
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
                "拖拽分组可调整组顺序；拖拽参数可调整组内顺序或移入其他组。"
                "选中项目后也可用按钮或 Ctrl+↑/Ctrl+↓ 快速移动。\n"
                "调整完毕后点击「应用排序」保存、关闭并重新加载 Package。"
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
            self._tree.order_changed.connect(self._on_tree_order_changed)
            self._tree.move_requested.connect(self._move_selected)
            mid_layout.addWidget(self._tree, 1)

            # 右侧控制按钮列
            btn_col = QtWidgets.QVBoxLayout()
            btn_col.setAlignment(QtCore.Qt.AlignTop)
            mid_layout.addLayout(btn_col)

            self._btn_up = QtWidgets.QPushButton("↑  上移选中项", self)
            self._btn_down = QtWidgets.QPushButton("↓  下移选中项", self)
            self._btn_change_group = QtWidgets.QPushButton("更改分组…", self)
            self._btn_refresh = QtWidgets.QPushButton("⟳  刷新", self)
            btn_expand = QtWidgets.QPushButton("⊞  全部展开", self)
            btn_collapse = QtWidgets.QPushButton("⊟  全部收起", self)
            self._btn_up.setEnabled(False)
            self._btn_down.setEnabled(False)
            self._btn_change_group.setEnabled(False)
            self._btn_up.clicked.connect(self._move_group_up)
            self._btn_down.clicked.connect(self._move_group_down)
            self._btn_change_group.clicked.connect(self._change_parameter_group)
            self._btn_refresh.clicked.connect(self._refresh)
            btn_expand.clicked.connect(self._tree.expandAll)
            btn_collapse.clicked.connect(self._tree.collapseAll)

            for btn in (self._btn_up, self._btn_down, self._btn_change_group,
                        self._btn_refresh, btn_expand, btn_collapse):
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
                group_item.setFlags(
                    group_item.flags()
                    | QtCore.Qt.ItemIsDragEnabled
                    | QtCore.Qt.ItemIsDropEnabled)

                for p in params:
                    param_item = QtWidgets.QTreeWidgetItem(group_item)
                    param_item.setText(0, "    " + p["label"])
                    param_item.setText(1, p["id"])
                    param_item.setText(2, p["type_label"])
                    param_item.setData(0, _ROLE_IS_GROUP, False)
                    param_item.setData(0, _ROLE_SNAPSHOT, p)
                    param_item.setFlags(
                        (param_item.flags() | QtCore.Qt.ItemIsDragEnabled)
                        & ~QtCore.Qt.ItemIsDropEnabled)

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

        # ── 分组与参数移动 ───────────────────────────────────────────────── #

        def _selected_item(self):
            selected = self._tree.selectedItems()
            return selected[0] if selected else None

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
            item = self._selected_item()
            if item is None:
                self._btn_up.setEnabled(False)
                self._btn_down.setEnabled(False)
                self._btn_change_group.setEnabled(False)
                return
            is_group = bool(item.data(0, _ROLE_IS_GROUP))
            parent = self._tree.invisibleRootItem() if is_group else item.parent()
            if parent is None:
                self._btn_up.setEnabled(False)
                self._btn_down.setEnabled(False)
                self._btn_change_group.setEnabled(False)
                return
            idx = parent.indexOfChild(item)
            self._btn_up.setEnabled(idx > 0)
            self._btn_down.setEnabled(idx < parent.childCount() - 1)
            self._btn_change_group.setEnabled(
                not is_group
                and self._tree.invisibleRootItem().childCount() > 1)

        def _move_selected(self, direction):
            """在当前层级中移动选中的分组或参数。"""
            item = self._selected_item()
            if item is None:
                return
            is_group = bool(item.data(0, _ROLE_IS_GROUP))
            parent = self._tree.invisibleRootItem() if is_group else item.parent()
            if parent is None:
                return
            idx = parent.indexOfChild(item)
            new_idx = idx + direction
            if new_idx < 0 or new_idx >= parent.childCount():
                return

            was_expanded = item.isExpanded()
            taken = parent.takeChild(idx)
            parent.insertChild(new_idx, taken)
            if is_group:
                taken.setExpanded(was_expanded)
            self._tree.setCurrentItem(taken)
            self._on_tree_order_changed()

        def _move_group_up(self):
            self._move_selected(-1)

        def _move_group_down(self):
            self._move_selected(+1)

        def _change_parameter_group(self):
            parameter_item = self._selected_item()
            if parameter_item is None or parameter_item.data(0, _ROLE_IS_GROUP):
                return
            source_group = parameter_item.parent()
            root = self._tree.invisibleRootItem()
            target_groups = [
                root.child(index) for index in range(root.childCount())
                if root.child(index) is not source_group
            ]
            if not target_groups:
                return
            target_names = []
            for group_item in target_groups:
                group_name, _params = group_item.data(0, _ROLE_SNAPSHOT)
                target_names.append(group_name or "（未分组）")
            selected_name, accepted = QtWidgets.QInputDialog.getItem(
                self, "更改参数分组", "目标分组：", target_names, 0, False)
            if not accepted:
                return
            target_group = target_groups[target_names.index(selected_name)]
            source_index = source_group.indexOfChild(parameter_item)
            taken = source_group.takeChild(source_index)
            target_group.addChild(taken)
            target_group.setExpanded(True)
            self._tree.setCurrentItem(taken)
            self._on_tree_order_changed()

        def _update_group_labels(self):
            root = self._tree.invisibleRootItem()
            for index in range(root.childCount()):
                group_item = root.child(index)
                group_name, _params = group_item.data(0, _ROLE_SNAPSHOT)
                display_group = group_name if group_name else "（未分组）"
                group_item.setText(
                    0, f"{display_group}  ({group_item.childCount()} 个参数)")

        def _on_tree_order_changed(self):
            self._update_group_labels()
            self._on_selection_changed()
            self._set_status("排序已调整；点击「应用排序」写入当前 SBS。")

        # ── 应用排序 ─────────────────────────────────────────────────────── #

        def _current_ordered_groups(self):
            """从树中读取当前分组顺序，返回 [(group_name, [snapshot_dict]), ...]。"""
            root = self._tree.invisibleRootItem()
            result = []
            for i in range(root.childCount()):
                group_item = root.child(i)
                group_snapshot = group_item.data(0, _ROLE_SNAPSHOT)
                if group_snapshot is None:
                    continue
                group_name, _original_parameters = group_snapshot
                parameters = []
                for child_index in range(group_item.childCount()):
                    parameter_snapshot = group_item.child(child_index).data(
                        0, _ROLE_SNAPSHOT)
                    if parameter_snapshot is None:
                        continue
                    current_snapshot = dict(parameter_snapshot)
                    current_snapshot["group"] = group_name
                    parameters.append(current_snapshot)
                result.append((group_name, parameters))
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
    """公开入口：统一单实例、关闭释放；兼容旧调用签名。"""
    from ..shared.lifecycle import show_dialog
    from .. import sdcompat
    if QtWidgets is None:
        print('[MaxSDPlugin] Qt 不可用，无法显示窗口。')
        return None
    try:
        return show_dialog(__name__, lambda: ExposeParamSortingDialog(parent or sdcompat.get_main_window()), globals())
    except sdcompat.SD_API_ERRORS as error:
        QtWidgets.QMessageBox.critical(parent, "MaxSDPlugin", sdcompat.error_text(error))
        return None


def _clear_dialog_ref():
    global _dialog_ref
    _dialog_ref = None
