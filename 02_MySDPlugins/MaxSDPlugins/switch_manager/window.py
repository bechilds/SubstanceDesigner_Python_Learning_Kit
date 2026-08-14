# -*- coding: utf-8 -*-
"""开关管理工具窗口。"""

try:
    from PySide6 import QtCore, QtWidgets
except Exception:
    try:
        from PySide2 import QtCore, QtWidgets
    except Exception as error:
        QtCore = None
        QtWidgets = None
        print(f"[MaxSDPlugin/switch_manager] PySide 导入失败: {error}")

from . import logic
from ..output import output_data

_dialog_ref = None


if QtWidgets is not None:

    class SwitchManagerDialog(QtWidgets.QDialog):
        """创建 Boolean 开关，并为参数或参数组批量设置 Visible If。"""

        _ID_ROLE = QtCore.Qt.UserRole
        _TYPE_ROLE = QtCore.Qt.UserRole + 1
        _ORIGINAL_VALUE_ROLE = QtCore.Qt.UserRole + 2
        _VALUE_EDITABLE_ROLE = QtCore.Qt.UserRole + 3

        def __init__(self, parent=None):
            super().__init__(parent)
            self._syncing_checks = False
            self.setWindowTitle("开关管理工具 - MaxSDPlugin")
            self.resize(880, 680)
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            create_group = QtWidgets.QGroupBox("创建 Boolean 开关参数", self)
            create_layout = QtWidgets.QGridLayout(create_group)
            create_layout.addWidget(QtWidgets.QLabel("参数 ID：", self), 0, 0)
            self._switch_id = QtWidgets.QLineEdit(self)
            self._switch_id.setPlaceholderText("例如 enable_detail")
            create_layout.addWidget(self._switch_id, 0, 1)
            create_layout.addWidget(QtWidgets.QLabel("Label：", self), 0, 2)
            self._switch_label = QtWidgets.QLineEdit(self)
            self._switch_label.setPlaceholderText("例如 Enable Detail")
            create_layout.addWidget(self._switch_label, 0, 3)
            create_layout.addWidget(QtWidgets.QLabel("开关 Group：", self), 1, 0)
            self._switch_group = QtWidgets.QComboBox(self)
            self._switch_group.setEditable(True)
            self._switch_group.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
            self._switch_group.lineEdit().setPlaceholderText(
                "选择现有 Group，或输入新 Group 名称")
            create_layout.addWidget(self._switch_group, 1, 1, 1, 3)
            create_layout.addWidget(QtWidgets.QLabel("初始值：", self), 2, 0)
            self._initial_value = QtWidgets.QComboBox(self)
            self._initial_value.addItem("True", True)
            self._initial_value.addItem("False", False)
            create_layout.addWidget(self._initial_value, 2, 1)
            self._create_button = QtWidgets.QPushButton("创建开关", self)
            self._create_button.clicked.connect(self._create_switch)
            create_layout.addWidget(self._create_button, 0, 4, 3, 1)
            layout.addWidget(create_group)

            target_group = QtWidgets.QGroupBox("设置参数可见性", self)
            target_layout = QtWidgets.QVBoxLayout(target_group)
            target_layout.addWidget(QtWidgets.QLabel(
                "使用开关（仅显示上方开关 Group 中的 Boolean 参数）：", self))
            self._switch_list = QtWidgets.QListWidget(self)
            self._switch_list.setSelectionMode(
                QtWidgets.QAbstractItemView.SingleSelection)
            self._switch_list.setMaximumHeight(130)
            self._switch_list.currentItemChanged.connect(
                self._update_expression)
            target_layout.addWidget(self._switch_list)
            switch_row = QtWidgets.QHBoxLayout()
            self._expression_label = QtWidgets.QLabel(self)
            switch_row.addWidget(self._expression_label, 1)
            refresh_switches_button = QtWidgets.QPushButton(
                "按 Group 刷新开关列表", self)
            refresh_switches_button.clicked.connect(
                lambda: self._refresh(sync_package=True))
            switch_row.addWidget(refresh_switches_button)
            target_layout.addLayout(switch_row)

            self._info_label = QtWidgets.QLabel(self)
            self._info_label.setWordWrap(True)
            target_layout.addWidget(self._info_label)

            self._tree = QtWidgets.QTreeWidget(self)
            self._tree.setHeaderLabels(
                ["参数 / Group", "ID", "Visible If", "当前数值"])
            self._tree.setColumnWidth(0, 270)
            self._tree.setColumnWidth(1, 190)
            self._tree.setColumnWidth(2, 190)
            self._tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._tree.itemDoubleClicked.connect(self._edit_current_value)
            self._tree.itemChanged.connect(self._item_changed)
            target_layout.addWidget(self._tree, 1)

            action_row = QtWidgets.QHBoxLayout()
            refresh_button = QtWidgets.QPushButton("刷新", self)
            select_all_button = QtWidgets.QPushButton("全选", self)
            clear_button = QtWidgets.QPushButton("全不选", self)
            apply_button = QtWidgets.QPushButton("应用到勾选项", self)
            apply_values_button = QtWidgets.QPushButton("应用数值修改", self)
            clear_visible_if_button = QtWidgets.QPushButton(
                "清除 Visible If", self)
            refresh_button.clicked.connect(
                lambda: self._refresh(sync_package=True))
            select_all_button.clicked.connect(lambda: self._set_all_checked(True))
            clear_button.clicked.connect(lambda: self._set_all_checked(False))
            apply_button.clicked.connect(self._apply_switch)
            apply_values_button.clicked.connect(self._apply_value_changes)
            clear_visible_if_button.clicked.connect(self._clear_visible_if)
            for button in (refresh_button, select_all_button, clear_button):
                action_row.addWidget(button)
            action_row.addStretch(1)
            action_row.addWidget(apply_values_button)
            action_row.addWidget(clear_visible_if_button)
            action_row.addWidget(apply_button)
            target_layout.addLayout(action_row)
            layout.addWidget(target_group, 1)

            close_row = QtWidgets.QHBoxLayout()
            close_row.addStretch(1)
            close_button = QtWidgets.QPushButton("关闭", self)
            close_button.clicked.connect(self.close)
            close_row.addWidget(close_button)
            layout.addLayout(close_row)

        def _refresh(self, selected_switch_id=None, sync_package=False):
            graph = logic.get_current_graph()
            self._tree.clear()
            self._switch_list.clear()
            if graph is None:
                self._info_label.setText("未找到当前 Graph。请打开 Graph 后刷新。")
                return
            sync_warning = ""
            if sync_package:
                saved, sync_warning = logic.save_graph_package(graph)
                if not saved:
                    sync_warning = "；刷新警告：" + sync_warning
            parameters = logic.collect_parameters(graph)
            current_group = self._switch_group.currentText().strip()
            group_names = logic.collect_group_names(parameters)
            self._switch_group.blockSignals(True)
            try:
                self._switch_group.clear()
                self._switch_group.addItems(group_names)
                if current_group in group_names:
                    self._switch_group.setEditText(current_group)
                elif group_names:
                    switch_groups = [
                        group_name for group_name in group_names
                        if logic.collect_switches(parameters, group_name)
                    ]
                    self._switch_group.setEditText(
                        switch_groups[0] if switch_groups else group_names[0])
            finally:
                self._switch_group.blockSignals(False)
            grouped = output_data.group_parameters(parameters)
            self._fill_tree(grouped)
            switches = logic.collect_switches(
                parameters, self._switch_group.currentText())
            selected_item = None
            for parameter in switches:
                item = QtWidgets.QListWidgetItem(
                    f"{parameter.get('label') or parameter['id']} "
                    f"({parameter['id']})")
                item.setData(self._ID_ROLE, parameter["id"])
                self._switch_list.addItem(item)
                if parameter["id"] == selected_switch_id:
                    selected_item = item
            if selected_item is not None:
                self._switch_list.setCurrentItem(selected_item)
            elif self._switch_list.count():
                self._switch_list.setCurrentRow(0)
            self._info_label.setText(
                f"当前参数：{len(parameters)} 个；INPUTS："
                f"{sum(1 for item in parameters if item.get('connectable'))} 个；"
                f"开关 Group：{self._switch_group.currentText().strip() or '（未设置）'}；"
                f"可用开关：{len(switches)} 个。勾选参数或整个 Group；"
                f"参数树仅显示每项当前的 Visible If{sync_warning}。")
            self._tree.expandAll()
            self._update_expression()

        def _fill_tree(self, grouped):
            self._tree.blockSignals(True)
            try:
                for category_label, groups in grouped:
                    category_item = self._checkable_item(
                        self._tree, [category_label, "", "", ""])
                    for group_name, parameters in groups:
                        parent = category_item
                        if group_name:
                            parent = self._checkable_item(
                                category_item, [group_name, "", "", ""])
                        for parameter in parameters:
                            leaf = self._checkable_item(parent, [
                                parameter.get("label") or parameter["id"],
                                parameter["id"],
                                parameter.get("visible_if") or "",
                                logic.parameter_value_text(parameter),
                            ])
                            leaf.setData(0, self._ID_ROLE, parameter["id"])
                            leaf.setData(3, self._TYPE_ROLE, parameter.get("type") or "")
                            leaf.setData(
                                3, self._ORIGINAL_VALUE_ROLE,
                                logic.parameter_value_text(parameter))
                            value_editable = logic.supports_value_edit(parameter)
                            leaf.setData(
                                3, self._VALUE_EDITABLE_ROLE, value_editable)
                            if value_editable:
                                leaf.setFlags(
                                    leaf.flags() | QtCore.Qt.ItemIsEditable)
                                leaf.setToolTip(3, "双击修改，完成后点击“应用数值修改”。")
                            else:
                                leaf.setToolTip(
                                    3, "复杂类型或 XML-only INPUTS 不支持文本修改。")
            finally:
                self._tree.blockSignals(False)

        @staticmethod
        def _checkable_item(parent, texts):
            item = QtWidgets.QTreeWidgetItem(parent, texts)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(0, QtCore.Qt.Unchecked)
            return item

        def _item_changed(self, item, column):
            if self._syncing_checks or column != 0:
                return
            self._syncing_checks = True
            try:
                if item.childCount():
                    self._set_descendants(item, item.checkState(0))
                self._update_ancestors(item.parent())
            finally:
                self._syncing_checks = False

        def _edit_current_value(self, item, column):
            """仅允许双击叶子的“当前数值”列进入编辑。"""
            if (column == 3
                    and item.data(0, self._ID_ROLE)
                    and item.data(3, self._VALUE_EDITABLE_ROLE)):
                self._tree.editItem(item, 3)

        def _set_descendants(self, item, state):
            for index in range(item.childCount()):
                child = item.child(index)
                child.setCheckState(0, state)
                self._set_descendants(child, state)

        def _update_ancestors(self, item):
            while item is not None:
                states = [
                    item.child(index).checkState(0)
                    for index in range(item.childCount())
                ]
                if all(state == QtCore.Qt.Checked for state in states):
                    state = QtCore.Qt.Checked
                elif all(state == QtCore.Qt.Unchecked for state in states):
                    state = QtCore.Qt.Unchecked
                else:
                    state = QtCore.Qt.PartiallyChecked
                item.setCheckState(0, state)
                item = item.parent()

        def _set_all_checked(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            self._syncing_checks = True
            try:
                for index in range(self._tree.topLevelItemCount()):
                    item = self._tree.topLevelItem(index)
                    item.setCheckState(0, state)
                    self._set_descendants(item, state)
            finally:
                self._syncing_checks = False

        def _checked_ids(self):
            parameter_ids = []

            def visit(item):
                parameter_id = item.data(0, self._ID_ROLE)
                if parameter_id and item.checkState(0) == QtCore.Qt.Checked:
                    parameter_ids.append(parameter_id)
                for index in range(item.childCount()):
                    visit(item.child(index))

            for index in range(self._tree.topLevelItemCount()):
                visit(self._tree.topLevelItem(index))
            return parameter_ids

        def _changed_values(self):
            updates = []

            def visit(item):
                parameter_id = item.data(0, self._ID_ROLE)
                if (parameter_id
                        and item.data(3, self._VALUE_EDITABLE_ROLE)
                        and item.text(3) != item.data(
                            3, self._ORIGINAL_VALUE_ROLE)):
                    updates.append({
                        "id": parameter_id,
                        "type": item.data(3, self._TYPE_ROLE),
                        "value": item.text(3),
                    })
                for index in range(item.childCount()):
                    visit(item.child(index))

            for index in range(self._tree.topLevelItemCount()):
                visit(self._tree.topLevelItem(index))
            return updates

        def _current_switch_id(self):
            item = self._switch_list.currentItem()
            return item.data(self._ID_ROLE) if item is not None else ""

        def _update_expression(self, *_args):
            switch_id = self._current_switch_id()
            expression = f'input["{switch_id}"]' if switch_id else "（无 Boolean 参数）"
            self._expression_label.setText("写入表达式：" + expression)

        def _create_switch(self):
            graph = logic.get_current_graph()
            if graph is None:
                self._warn("未找到当前 Graph。")
                return
            try:
                result = logic.create_boolean_switch(
                    graph,
                    self._switch_id.text(),
                    self._switch_label.text(),
                    self._switch_group.currentText(),
                    self._initial_value.currentData(),
                )
            except logic._SD_API_ERRORS as error:
                self._warn(f"创建开关失败：{logic._error_text(error)}")
                return
            self._refresh(result["id"], sync_package=True)
            message = (
                f"已创建 Boolean 开关：{result['id']}，"
                f"初始值为 {result['initial_value']}。")
            if result["warnings"]:
                message += "\n设置 Label 时有警告：\n" + "\n".join(
                    result["warnings"])
            QtWidgets.QMessageBox.information(self, self.windowTitle(), message)

        def _apply_switch(self):
            graph = logic.get_current_graph()
            switch_id = self._current_switch_id()
            target_ids = self._checked_ids()
            if graph is None:
                self._warn("未找到当前 Graph。")
                return
            if not switch_id:
                self._warn("请先创建或选择一个 Boolean 开关参数。")
                return
            if not target_ids:
                self._warn("请至少勾选一个参数或 Group。")
                return
            confirm = QtWidgets.QMessageBox.question(
                self,
                "批量设置 Visible If",
                f"将用 input[\"{switch_id}\"] 覆盖 {len(target_ids)} 个勾选项"
                "当前的 Visible If。\n\n可在 Designer 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            try:
                summary = logic.assign_switch(
                    graph, switch_id, target_ids,
                    self._switch_group.currentText())
            except logic._SD_API_ERRORS as error:
                self._warn(f"设置 Visible If 失败：{logic._error_text(error)}")
                return
            self._refresh(switch_id, sync_package=True)
            message = f"已更新 {len(summary['updated'])} 个参数。"
            if summary["failed"]:
                message += "\n失败：\n" + "\n".join(
                    f"{parameter_id}: {reason}"
                    for parameter_id, reason in summary["failed"])
                self._warn(message)
            else:
                QtWidgets.QMessageBox.information(
                    self, self.windowTitle(), message)

        def _apply_value_changes(self):
            graph = logic.get_current_graph()
            updates = self._changed_values()
            if graph is None:
                self._warn("未找到当前 Graph。")
                return
            if not updates:
                self._warn("没有检测到可应用的当前数值修改。")
                return
            summary = logic.update_parameter_values(graph, updates)
            self._refresh(sync_package=True)
            message = f"已更新 {len(summary['updated'])} 个参数当前值。"
            if summary["failed"]:
                message += "\n失败：\n" + "\n".join(
                    f"{parameter_id}: {reason}"
                    for parameter_id, reason in summary["failed"])
                self._warn(message)
            else:
                QtWidgets.QMessageBox.information(
                    self, self.windowTitle(), message)

        def _clear_visible_if(self):
            graph = logic.get_current_graph()
            target_ids = self._checked_ids()
            if graph is None:
                self._warn("未找到当前 Graph。")
                return
            if not target_ids:
                self._warn("请至少勾选一个要清除 Visible If 的参数或 Group。")
                return
            confirm = QtWidgets.QMessageBox.question(
                self,
                "清除 Visible If",
                f"将清除 {len(target_ids)} 个勾选项的 Visible If。\n\n"
                "可在 Designer 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            summary = logic.clear_visible_if(graph, target_ids)
            self._refresh(sync_package=True)
            message = f"已清除 {len(summary['updated'])} 个参数的 Visible If。"
            if summary["failed"]:
                message += "\n失败：\n" + "\n".join(
                    f"{parameter_id}: {reason}"
                    for parameter_id, reason in summary["failed"])
                self._warn(message)
            else:
                QtWidgets.QMessageBox.information(
                    self, self.windowTitle(), message)

        def _warn(self, message):
            QtWidgets.QMessageBox.warning(self, self.windowTitle(), message)


def show_window(parent=None):
    """显示开关管理工具窗口，并保留模块级引用。"""
    global _dialog_ref
    if QtWidgets is None:
        print("[MaxSDPlugin/switch_manager] Qt 不可用，无法显示窗口")
        return None
    try:
        if _dialog_ref is not None:
            _dialog_ref.close()
        _dialog_ref = SwitchManagerDialog(parent)
        _dialog_ref.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        _dialog_ref.destroyed.connect(lambda: _clear_dialog_ref())
        _dialog_ref.show()
        _dialog_ref.raise_()
        _dialog_ref.activateWindow()
        return _dialog_ref
    except logic._SD_API_ERRORS as error:
        print(f"[MaxSDPlugin/switch_manager] 打开窗口失败: "
              f"{logic._error_text(error)}")
        return None


def _clear_dialog_ref():
    global _dialog_ref
    _dialog_ref = None