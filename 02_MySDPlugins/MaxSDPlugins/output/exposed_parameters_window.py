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
from .. import sdcompat

_LOG = "[MaxSDPlugin/output]"

# 模块级保存窗口引用，防止被 Python 垃圾回收导致窗口一闪而过
_dialog_ref = None


if QtWidgets is not None:

    def _replace_keyword_text(text, find_text, replace_text, case_sensitive):
        """替换文本并返回 (命中次数, 新文本)。"""
        if case_sensitive:
            return text.count(find_text), text.replace(find_text, replace_text)
        lowered_text = text.lower()
        lowered_find = find_text.lower()
        parts = []
        start = 0
        matches = 0
        while True:
            index = lowered_text.find(lowered_find, start)
            if index < 0:
                parts.append(text[start:])
                break
            parts.append(text[start:index])
            parts.append(replace_text)
            start = index + len(find_text)
            matches += 1
        return matches, "".join(parts)


    def _split_filter_keywords(text):
        """解析逗号、分号或换行分隔的多个筛选关键字。"""
        normalized = text
        for separator in ("，", ";", "；", "\n", "\r"):
            normalized = normalized.replace(separator, ",")
        return [keyword.strip() for keyword in normalized.split(",") if keyword.strip()]


    class BatchCopyParametersDialog(QtWidgets.QDialog):
        """预览勾选参数的批量副本，并批量替换新 ID / Label。"""

        def __init__(self, parameters, existing_ids, parent=None):
            super().__init__(parent)
            self._parameters = parameters
            self._existing_ids = set(existing_ids)
            self.copies = []
            self.setWindowTitle("批量复制参数 - MaxSDPlugin")
            self.resize(820, 440)
            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            info = QtWidgets.QLabel(
                "每行将通过 Designer 参数面板 + 对应的创建接口生成一个真实副本。"
                "可先批量替换新 ID / Label，再手动调整个别结果。",
                self,
            )
            info.setWordWrap(True)
            layout.addWidget(info)

            replace_row = QtWidgets.QHBoxLayout()
            replace_row.addWidget(QtWidgets.QLabel("作用字段：", self))
            self._replace_scope = QtWidgets.QComboBox(self)
            self._replace_scope.addItems(["新 ID + 新 Label", "新 ID", "新 Label"])
            replace_row.addWidget(self._replace_scope)
            replace_row.addWidget(QtWidgets.QLabel("查找关键字：", self))
            self._find_text = QtWidgets.QLineEdit(self)
            self._find_text.setPlaceholderText("例如 ChannelR")
            replace_row.addWidget(self._find_text, 1)
            replace_row.addWidget(QtWidgets.QLabel("替换为：", self))
            self._replace_text = QtWidgets.QLineEdit(self)
            self._replace_text.setPlaceholderText("例如 ChannelG")
            replace_row.addWidget(self._replace_text, 1)
            self._case_sensitive = QtWidgets.QCheckBox("区分大小写", self)
            replace_row.addWidget(self._case_sensitive)
            preview_button = QtWidgets.QPushButton("预览替换", self)
            preview_button.clicked.connect(self._preview_keyword_replace)
            replace_row.addWidget(preview_button)
            layout.addLayout(replace_row)

            self._replace_result = QtWidgets.QLabel("尚未执行关键字替换。", self)
            layout.addWidget(self._replace_result)

            self._table = QtWidgets.QTableWidget(len(self._parameters), 4, self)
            self._table.setHorizontalHeaderLabels(
                ["源 ID", "源 Label", "新 ID", "新 Label"])
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._table.verticalHeader().setVisible(False)
            reserved_ids = set(self._existing_ids)
            for row, parameter in enumerate(self._parameters):
                source_id = parameter.get("id") or ""
                source_label = parameter.get("label") or source_id
                copy_index = 1
                new_id = f"{source_id}_copy"
                while new_id in reserved_ids:
                    copy_index += 1
                    new_id = f"{source_id}_copy_{copy_index}"
                reserved_ids.add(new_id)
                values = (source_id, source_label, new_id, f"{source_label} Copy")
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    if column in (0, 1):
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    self._table.setItem(row, column, item)
            self._table.horizontalHeader().setStretchLastSection(True)
            self._table.resizeColumnsToContents()
            layout.addWidget(self._table, 1)

            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel,
                parent=self,
            )
            buttons.button(QtWidgets.QDialogButtonBox.Apply).setText("创建全部副本")
            buttons.clicked.connect(self._button_clicked)
            layout.addWidget(buttons)

        def _target_columns(self):
            scope = self._replace_scope.currentText()
            if scope == "新 ID":
                return (2,)
            if scope == "新 Label":
                return (3,)
            return (2, 3)

        def _preview_keyword_replace(self):
            find_text = self._find_text.text()
            if not find_text:
                QtWidgets.QMessageBox.warning(
                    self, self.windowTitle(), "查找关键字不能为空。")
                return
            matches = 0
            for row in range(self._table.rowCount()):
                for column in self._target_columns():
                    item = self._table.item(row, column)
                    count, new_text = _replace_keyword_text(
                        item.text(), find_text, self._replace_text.text(),
                        self._case_sensitive.isChecked(),
                    )
                    if count:
                        item.setText(new_text)
                        matches += count
            self._replace_result.setText(f"预览完成：替换 {matches} 处。")

        def _button_clicked(self, button):
            role = self.sender().buttonRole(button)
            if role == QtWidgets.QDialogButtonBox.RejectRole:
                self.reject()
                return
            if role != QtWidgets.QDialogButtonBox.ApplyRole:
                return
            copies = []
            new_ids = []
            for row in range(self._table.rowCount()):
                source_id = self._table.item(row, 0).text()
                new_id = self._table.item(row, 2).text().strip()
                new_label = self._table.item(row, 3).text().strip() or new_id
                if not new_id:
                    QtWidgets.QMessageBox.warning(
                        self, self.windowTitle(), f"第 {row + 1} 行的新 ID 不能为空。")
                    return
                new_ids.append(new_id)
                copies.append({
                    "source_id": source_id,
                    "new_id": new_id,
                    "new_label": new_label,
                })
            duplicate_ids = sorted({
                new_id for new_id in new_ids if new_ids.count(new_id) > 1})
            conflicting_ids = sorted(set(new_ids) & self._existing_ids)
            if duplicate_ids or conflicting_ids:
                messages = []
                if duplicate_ids:
                    messages.append("新 ID 重复：" + ", ".join(duplicate_ids))
                if conflicting_ids:
                    messages.append("新 ID 已存在：" + ", ".join(conflicting_ids))
                QtWidgets.QMessageBox.warning(
                    self, self.windowTitle(), "\n".join(messages))
                return
            self.copies = copies
            self.accept()

    class BatchParameterSettingsDialog(QtWidgets.QDialog):
        """逐行编辑勾选曝光参数的 Label、Group 和标量当前值。"""

        _ORIGINAL_VALUE_ROLE = (
            QtCore.Qt.UserRole + 1 if QtCore is not None else 33)

        def __init__(self, graph, parameters, parent=None):
            super().__init__(parent)
            self._graph = graph
            self._parameters = parameters
            self._group_checkboxes = {}
            self._syncing_group_checks = False
            self.summary = None
            self.setWindowTitle("批量替换参数设置 - MaxSDPlugin")
            self.resize(820, 440)
            self._build_ui()

        @staticmethod
        def _supports_text_value(type_id):
            type_id = (type_id or "").lower()
            return (
                "string" in type_id
                or "bool" in type_id
                or type_id.endswith("int")
                or type_id in ("int", "integer")
                or "int1" in type_id
                or ("float" in type_id and not any(
                    name in type_id for name in ("float2", "float3", "float4")))
            )

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            info = QtWidgets.QLabel(
                "逐行修改 Label、Group 和当前值。向量、颜色、图像等复杂类型的值只读，"
                "但仍可修改 Label 与 Group。",
                self,
            )
            info.setWordWrap(True)
            layout.addWidget(info)

            replace_row = QtWidgets.QHBoxLayout()
            replace_row.addWidget(QtWidgets.QLabel("作用字段：", self))
            self._replace_scope = QtWidgets.QComboBox(self)
            self._replace_scope.addItems(
                ["Label", "Group", "当前值", "Label + Group"])
            replace_row.addWidget(self._replace_scope)
            replace_row.addWidget(QtWidgets.QLabel("查找关键字：", self))
            self._find_text = QtWidgets.QLineEdit(self)
            self._find_text.setPlaceholderText("例如 ChannelR")
            replace_row.addWidget(self._find_text, 1)
            replace_row.addWidget(QtWidgets.QLabel("替换为：", self))
            self._replace_text = QtWidgets.QLineEdit(self)
            self._replace_text.setPlaceholderText("例如 ChannelG")
            replace_row.addWidget(self._replace_text, 1)
            self._case_sensitive = QtWidgets.QCheckBox("区分大小写", self)
            replace_row.addWidget(self._case_sensitive)
            self._btn_preview_replace = QtWidgets.QPushButton("预览替换", self)
            self._btn_preview_replace.clicked.connect(
                self._preview_keyword_replace)
            replace_row.addWidget(self._btn_preview_replace)
            layout.addLayout(replace_row)

            exclude_row = QtWidgets.QHBoxLayout()
            exclude_row.addWidget(QtWidgets.QLabel("排除 Group 关键字：", self))
            self._exclude_group_text = QtWidgets.QLineEdit(self)
            self._exclude_group_text.setPlaceholderText(
                "多个类别用逗号、分号或换行分隔；命中后整行不替换")
            exclude_row.addWidget(self._exclude_group_text, 1)
            layout.addLayout(exclude_row)

            self._replace_result = QtWidgets.QLabel("尚未执行关键字替换。", self)
            layout.addWidget(self._replace_result)

            group_row = QtWidgets.QHBoxLayout()
            group_row.addWidget(QtWidgets.QLabel("选择 Group：", self))
            for group_name in dict.fromkeys(
                    parameter.get("group") or "" for parameter in self._parameters):
                checkbox = QtWidgets.QCheckBox(group_name or "（未分组）", self)
                checkbox.setTristate(True)
                checkbox.setCheckState(QtCore.Qt.Checked)
                checkbox.stateChanged.connect(
                    lambda _state, name=group_name: self._set_group_checked(name))
                self._group_checkboxes[group_name] = checkbox
                group_row.addWidget(checkbox)
            group_row.addStretch(1)
            layout.addLayout(group_row)

            self._table = QtWidgets.QTableWidget(len(self._parameters), 6, self)
            self._table.setHorizontalHeaderLabels(
                ["选择", "ID", "Type", "Label", "Group", "当前值"])
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._table.verticalHeader().setVisible(False)
            for row, parameter in enumerate(self._parameters):
                check_item = QtWidgets.QTableWidgetItem()
                check_item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                check_item.setCheckState(QtCore.Qt.Checked)
                self._table.setItem(row, 0, check_item)
                values = (
                    parameter.get("id") or "",
                    parameter.get("type") or "",
                    parameter.get("label") or parameter.get("id") or "",
                    parameter.get("group") or "",
                    od.scalar_value_to_text(parameter.get("value")),
                )
                for column, value in enumerate(values, start=1):
                    item = QtWidgets.QTableWidgetItem(value)
                    if column in (1, 2):
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    if column == 5:
                        item.setData(self._ORIGINAL_VALUE_ROLE, value)
                        if not self._supports_text_value(parameter.get("type")):
                            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                            item.setToolTip("复杂类型当前值不可用文本安全修改。")
                    self._table.setItem(row, column, item)
            self._table.itemChanged.connect(self._table_item_changed)
            self._table.horizontalHeader().setStretchLastSection(True)
            self._table.resizeColumnsToContents()
            layout.addWidget(self._table, 1)

            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel,
                parent=self,
            )
            buttons.button(QtWidgets.QDialogButtonBox.Apply).setText("应用全部修改")
            buttons.clicked.connect(self._button_clicked)
            layout.addWidget(buttons)

        def _target_columns(self):
            scope = self._replace_scope.currentText()
            if scope == "Label":
                return (3,)
            if scope == "Group":
                return (4,)
            if scope == "当前值":
                return (5,)
            return (3, 4)

        def _row_is_checked(self, row):
            item = self._table.item(row, 0)
            return item is not None and item.checkState() == QtCore.Qt.Checked

        def _set_group_checked(self, group_name):
            state = self._group_checkboxes[group_name].checkState()
            if self._syncing_group_checks or state == QtCore.Qt.PartiallyChecked:
                return
            self._syncing_group_checks = True
            try:
                for row, parameter in enumerate(self._parameters):
                    if (parameter.get("group") or "") == group_name:
                        self._table.item(row, 0).setCheckState(state)
            finally:
                self._syncing_group_checks = False

        def _table_item_changed(self, item):
            if self._syncing_group_checks or item.column() != 0:
                return
            group_name = self._parameters[item.row()].get("group") or ""
            states = [
                self._table.item(row, 0).checkState()
                for row, parameter in enumerate(self._parameters)
                if (parameter.get("group") or "") == group_name
            ]
            self._syncing_group_checks = True
            try:
                if all(state == QtCore.Qt.Checked for state in states):
                    group_state = QtCore.Qt.Checked
                elif all(state == QtCore.Qt.Unchecked for state in states):
                    group_state = QtCore.Qt.Unchecked
                else:
                    group_state = QtCore.Qt.PartiallyChecked
                self._group_checkboxes[group_name].setCheckState(group_state)
            finally:
                self._syncing_group_checks = False

        def _preview_keyword_replace(self):
            """在表格中预览关键字替换，不立即写入 Graph。"""
            find_text = self._find_text.text()
            replace_text = self._replace_text.text()
            if not find_text:
                QtWidgets.QMessageBox.warning(
                    self, self.windowTitle(), "查找关键字不能为空。")
                return
            case_sensitive = self._case_sensitive.isChecked()
            excluded_keywords = _split_filter_keywords(
                self._exclude_group_text.text())
            matches = 0
            skipped_read_only = 0
            skipped_excluded = 0
            skipped_unchecked = 0
            for row in range(self._table.rowCount()):
                if not self._row_is_checked(row):
                    skipped_unchecked += 1
                    continue
                group_text = self._table.item(row, 4).text()
                compare_group = group_text if case_sensitive else group_text.lower()
                compare_keywords = (
                    excluded_keywords if case_sensitive
                    else [keyword.lower() for keyword in excluded_keywords]
                )
                if any(keyword in compare_group for keyword in compare_keywords):
                    skipped_excluded += 1
                    continue
                for column in self._target_columns():
                    item = self._table.item(row, column)
                    if item is None:
                        continue
                    if not (item.flags() & QtCore.Qt.ItemIsEditable):
                        skipped_read_only += 1
                        continue
                    old_text = item.text()
                    count, new_text = _replace_keyword_text(
                        old_text, find_text, replace_text, case_sensitive)
                    if count:
                        item.setText(new_text)
                        matches += count
            result = f"预览完成：替换 {matches} 处。"
            if skipped_unchecked:
                result += f" 跳过未勾选参数 {skipped_unchecked} 行。"
            if skipped_excluded:
                result += f" 按 Group 关键字排除 {skipped_excluded} 行。"
            if skipped_read_only:
                result += f" 跳过只读单元格 {skipped_read_only} 个。"
            self._replace_result.setText(result)

        def _button_clicked(self, button):
            role = self.sender().buttonRole(button)
            if role == QtWidgets.QDialogButtonBox.RejectRole:
                self.reject()
                return
            if role != QtWidgets.QDialogButtonBox.ApplyRole:
                return
            updates = []
            for row, parameter in enumerate(self._parameters):
                if not self._row_is_checked(row):
                    continue
                value_item = self._table.item(row, 5)
                value = value_item.text()
                updates.append({
                    "id": parameter.get("id"),
                    "type": parameter.get("type"),
                    "label": self._table.item(row, 3).text().strip(),
                    "group": self._table.item(row, 4).text().strip(),
                    "value": value,
                    "value_changed": value != value_item.data(
                        self._ORIGINAL_VALUE_ROLE),
                })
            if not updates:
                QtWidgets.QMessageBox.warning(
                    self, self.windowTitle(), "请至少勾选一个要应用的参数。")
                return
            self.summary = od.update_exposed_parameter_settings(
                self._graph, updates)
            self.accept()

    class ExposedParametersDialog(QtWidgets.QDialog):
        """已暴露参数管理对话框（分组树 + 勾选 + 缓存/导出/加载/删除）。"""

        # 自定义角色：把参数 id 存到 tree item 上
        _ID_ROLE = (QtCore.Qt.UserRole if QtCore is not None else 32)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._syncing_parameter_checks = False
            self.setWindowTitle("曝光参数 - MaxSDPlugin")
            self.resize(900, 760)
            self._build_ui()
            self._refresh()

        # ---------------- UI 搭建 ----------------
        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            content_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
            layout.addWidget(content_splitter, 1)

            parameters_group = QtWidgets.QGroupBox("已暴露参数", self)
            parameters_layout = QtWidgets.QVBoxLayout(parameters_group)
            content_splitter.addWidget(parameters_group)

            self._info_label = QtWidgets.QLabel(self)
            self._info_label.setWordWrap(True)
            parameters_layout.addWidget(self._info_label)

            # 分组树：分类 → 分组 → 参数（参数为可勾选叶子）
            self._tree = QtWidgets.QTreeWidget(self)
            self._tree.setHeaderLabels(["参数", "ID", "当前值", "引用状态"])
            self._tree.setColumnWidth(0, 240)
            self._tree.setColumnWidth(1, 160)
            self._tree.setColumnWidth(3, 120)
            self._tree.itemChanged.connect(self._parameter_item_changed)
            parameters_layout.addWidget(self._tree, 1)

            # —— 曝光参数列表专属按钮：刷新 / 全选 / 全不选 / 删除勾选 / 缓存 / 导出 / 加载 ——
            exp_row = QtWidgets.QHBoxLayout()
            self._btn_refresh = QtWidgets.QPushButton("刷新", self)
            self._btn_check_all = QtWidgets.QPushButton("全选", self)
            self._btn_uncheck_all = QtWidgets.QPushButton("全不选", self)
            self._btn_copy = QtWidgets.QPushButton("复制勾选参数", self)
            self._btn_replace = QtWidgets.QPushButton("批量替换参数设置", self)
            self._btn_remove_copy = QtWidgets.QPushButton("去除 Copy", self)
            self._btn_sort = QtWidgets.QPushButton("参数分组排序", self)
            self._btn_copy.setToolTip(
                "批量复制所有勾选参数；创建前可按关键字替换新 ID 和新 Label。")
            self._btn_replace.setToolTip(
                "勾选目标参数，打开窗口按关键字或逐行修改 Label、Group 和当前值。")
            self._btn_remove_copy.setToolTip(
                "批量去除勾选参数 Label 和 ID 中独立的 Copy；ID 通过安全迁移实现。")
            self._btn_sort.setToolTip(
                "按 Group 调整 INPUT PARAMETERS 顺序；会备份并重载当前 SBS。")
            self._btn_delete = QtWidgets.QPushButton("删除勾选项", self)
            self._btn_cache = QtWidgets.QPushButton("缓存到当前目录", self)
            self._btn_export = QtWidgets.QPushButton("导出…", self)
            self._btn_load = QtWidgets.QPushButton("加载历史…", self)
            self._btn_refresh.clicked.connect(self._refresh)
            self._btn_check_all.clicked.connect(lambda: self._set_all_checked(True))
            self._btn_uncheck_all.clicked.connect(lambda: self._set_all_checked(False))
            self._btn_copy.clicked.connect(self._copy_current_parameter)
            self._btn_replace.clicked.connect(self._replace_checked_parameter_settings)
            self._btn_remove_copy.clicked.connect(self._remove_copy_checked)
            self._btn_sort.clicked.connect(self._open_parameter_sorting)
            self._btn_delete.clicked.connect(self._delete_checked)
            self._btn_cache.clicked.connect(self._cache)
            self._btn_export.clicked.connect(self._export)
            self._btn_load.clicked.connect(self._load_history)
            for b in (self._btn_refresh, self._btn_check_all, self._btn_uncheck_all,
                      self._btn_copy, self._btn_replace, self._btn_remove_copy,
                      self._btn_sort):
                exp_row.addWidget(b)
            exp_row.addStretch(1)
            parameters_layout.addLayout(exp_row)

            file_row = QtWidgets.QHBoxLayout()
            for b in (self._btn_delete, self._btn_cache, self._btn_export, self._btn_load):
                file_row.addWidget(b)
            file_row.addStretch(1)
            parameters_layout.addLayout(file_row)

            # 损坏节点（画布上报 Empty variable 的节点）：可勾选；双击/右键 Goto 定位
            broken_group = QtWidgets.QGroupBox("画布损坏节点", self)
            broken_layout = QtWidgets.QVBoxLayout(broken_group)
            content_splitter.addWidget(broken_group)
            self._broken_label = QtWidgets.QLabel(self)
            self._broken_label.setWordWrap(True)
            broken_layout.addWidget(self._broken_label)
            self._broken_tree = QtWidgets.QTreeWidget(self)
            self._broken_tree.setHeaderLabels(
                ["有曝光参数的节点", "对应的损坏节点属性", "警告类型"])
            self._broken_tree.setColumnWidth(0, 280)
            self._broken_tree.setColumnWidth(1, 140)
            self._broken_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self._broken_tree.customContextMenuRequested.connect(self._broken_context_menu)
            self._broken_tree.itemDoubleClicked.connect(lambda *_: self._goto_broken())
            broken_layout.addWidget(self._broken_tree, 1)

            # —— 画布损坏节点列表专属按钮：刷新 / 全选 / 全不选 / 重置函数 ——
            brk_row = QtWidgets.QHBoxLayout()
            self._btn_brk_refresh = QtWidgets.QPushButton("刷新", self)
            self._btn_brk_check_all = QtWidgets.QPushButton("全选", self)
            self._btn_brk_uncheck_all = QtWidgets.QPushButton("全不选", self)
            self._btn_repair = QtWidgets.QPushButton("重置函数", self)
            self._btn_repair.setToolTip(
                "把勾选的损坏节点重置回常量值；未勾选则修复全图。可在 SD 中 Ctrl+Z 撤销。"
            )
            self._btn_del_node = QtWidgets.QPushButton("删除当前节点", self)
            self._btn_del_node.setToolTip("删除当前选中的损坏节点（可在 SD 中 Ctrl+Z 撤销）。")
            self._btn_brk_refresh.clicked.connect(self._refresh_broken)
            self._btn_brk_check_all.clicked.connect(lambda: self._set_all_broken_checked(True))
            self._btn_brk_uncheck_all.clicked.connect(lambda: self._set_all_broken_checked(False))
            self._btn_repair.clicked.connect(self._repair_broken)
            self._btn_del_node.clicked.connect(self._delete_current_node)
            for b in (self._btn_brk_refresh, self._btn_brk_check_all,
                      self._btn_brk_uncheck_all, self._btn_repair, self._btn_del_node):
                brk_row.addWidget(b)
            brk_row.addStretch(1)
            broken_layout.addLayout(brk_row)
            content_splitter.setSizes([470, 250])

            # 关闭
            close_row = QtWidgets.QHBoxLayout()
            close_row.addStretch(1)
            self._btn_close = QtWidgets.QPushButton("关闭", self)
            self._btn_close.clicked.connect(self.close)
            close_row.addWidget(self._btn_close)
            layout.addLayout(close_row)

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
            self._fill_broken(graph)

        def _refresh_broken(self):
            """只刷新画布损坏节点列表（不动曝光参数树）。"""
            graph = od.get_current_graph()
            if graph is None:
                self._broken_tree.clear()
                self._broken_label.setText("未找到当前图。")
                return
            self._fill_broken(graph)

        def _fill_broken(self, graph):
            """扫描并列出画布上有警告的节点（可勾选），含警告类型列。"""
            self._broken_tree.clear()
            broken = od.collect_broken_nodes(graph)
            if broken:
                self._broken_label.setText(
                    f"画布损坏节点：{len(broken)} 个 —— 勾选后“重置”，选中后可“删除当前节点”，双击/右键 Goto 定位")
            else:
                self._broken_label.setText("画布损坏节点：0 个")
            for b in broken:
                wtypes = "、".join(b.get("warnings", []))
                it = QtWidgets.QTreeWidgetItem(
                    self._broken_tree, [b["label"], b.get("prop", ""), wtypes])
                it.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                it.setCheckState(0, QtCore.Qt.Unchecked)
                it.setData(0, self._ID_ROLE, b["id"])

        def _delete_current_node(self):
            """删除当前选中的损坏节点。可在 SD 中 Ctrl+Z 撤销。"""
            it = self._broken_tree.currentItem()
            if it is None:
                self._warn("请先在列表中选中一个节点。")
                return
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            nid = it.data(0, self._ID_ROLE)
            confirm = QtWidgets.QMessageBox.question(
                self, "删除节点",
                f"将从图中删除节点：\n{it.text(0)}\n\n可在 SD 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            ok, msg = od.delete_node(graph, nid)
            if ok:
                self._refresh()
            else:
                self._warn(msg)

        def _set_all_broken_checked(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for i in range(self._broken_tree.topLevelItemCount()):
                self._broken_tree.topLevelItem(i).setCheckState(0, state)

        def _checked_broken_ids(self):
            ids = []
            for i in range(self._broken_tree.topLevelItemCount()):
                it = self._broken_tree.topLevelItem(i)
                if it.checkState(0) == QtCore.Qt.Checked:
                    ids.append(it.data(0, self._ID_ROLE))
            return ids

        def _broken_context_menu(self, pos):
            it = self._broken_tree.itemAt(pos)
            if it is None:
                return
            self._broken_tree.setCurrentItem(it)
            menu = QtWidgets.QMenu(self)
            menu.addAction("Goto（在图中定位）").triggered.connect(self._goto_broken)
            menu.addAction("删除当前节点").triggered.connect(self._delete_current_node)
            sdcompat.exec_widget(menu, self._broken_tree.viewport().mapToGlobal(pos))

        def _goto_broken(self):
            it = self._broken_tree.currentItem()
            if it is None:
                return
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            ok, msg = od.goto_node(graph, it.data(0, self._ID_ROLE))
            if not ok:
                self._warn(msg)

        def _fill_tree(self, grouped):
            """grouped: [(category_label, [(group_name, [param,...]), ...]), ...]。"""
            self._tree.blockSignals(True)
            try:
                for cat_label, groups in grouped:
                    cat_item = QtWidgets.QTreeWidgetItem(self._tree, [cat_label])
                    cat_item.setFlags(
                        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                    cat_item.setCheckState(0, QtCore.Qt.Unchecked)
                    for group_name, plist in groups:
                        parent = cat_item
                        if group_name:
                            grp_item = QtWidgets.QTreeWidgetItem(cat_item, [group_name])
                            grp_item.setFlags(
                                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                            grp_item.setCheckState(0, QtCore.Qt.Unchecked)
                            parent = grp_item
                        for p in plist:
                            leaf = QtWidgets.QTreeWidgetItem(
                                parent,
                                [p.get("label") or p.get("id"), p.get("id"),
                                   str(p.get("value")),
                                   "已被节点引用" if p.get("referenced")
                                   else "未被节点引用"],
                            )
                            leaf.setFlags(
                                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
                            )
                            leaf.setCheckState(0, QtCore.Qt.Unchecked)
                            leaf.setData(0, self._ID_ROLE, p.get("id"))
                            if not p.get("referenced"):
                                leaf.setToolTip(3, "当前 Graph 的节点属性函数没有引用此参数。")
            finally:
                self._tree.blockSignals(False)

        def _open_parameter_sorting(self):
            """从曝光参数面板打开参数分组排序窗口。"""
            try:
                from ..expose_param_sorting import show_window
                show_window(self)
            except Exception as error:
                self._warn(f"打开参数分组排序失败：{error}")

        def _parameter_item_changed(self, item, column):
            """组/分类勾选向下同步，参数变化向上汇总三态。"""
            if self._syncing_parameter_checks or column != 0:
                return
            self._syncing_parameter_checks = True
            try:
                if item.childCount() > 0:
                    state = item.checkState(0)
                    if state != QtCore.Qt.PartiallyChecked:
                        self._set_descendant_check_state(item, state)
                self._update_parent_check_states(item.parent())
            finally:
                self._syncing_parameter_checks = False

        def _set_descendant_check_state(self, item, state):
            for index in range(item.childCount()):
                child = item.child(index)
                child.setCheckState(0, state)
                self._set_descendant_check_state(child, state)

        def _update_parent_check_states(self, parent):
            while parent is not None:
                states = [
                    parent.child(index).checkState(0)
                    for index in range(parent.childCount())
                ]
                if states and all(state == QtCore.Qt.Checked for state in states):
                    parent.setCheckState(0, QtCore.Qt.Checked)
                elif states and all(state == QtCore.Qt.Unchecked for state in states):
                    parent.setCheckState(0, QtCore.Qt.Unchecked)
                else:
                    parent.setCheckState(0, QtCore.Qt.PartiallyChecked)
                parent = parent.parent()

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
            self._syncing_parameter_checks = True
            try:
                for index in range(self._tree.topLevelItemCount()):
                    top_item = self._tree.topLevelItem(index)
                    top_item.setCheckState(0, state)
                    self._set_descendant_check_state(top_item, state)
            finally:
                self._syncing_parameter_checks = False

        def _checked_ids(self):
            return [
                leaf.data(0, self._ID_ROLE)
                for leaf in self._iter_leaves()
                if leaf.checkState(0) == QtCore.Qt.Checked
            ]

        def _copy_current_parameter(self):
            """批量复制所有勾选参数，并允许先替换新 ID / Label 关键字。"""
            source_ids = self._checked_ids()
            if not source_ids:
                self._warn("请先勾选至少一个要复制的源参数。")
                return
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            source_id_set = set(source_ids)
            parameters = [
                parameter for parameter in od.collect_exposed_parameters(graph)
                if parameter.get("id") in source_id_set
            ]
            existing_ids = {
                parameter.get("id") for parameter in od.collect_exposed_parameters(graph)
            }
            dialog = BatchCopyParametersDialog(parameters, existing_ids, self)
            if sdcompat.exec_widget(dialog) != QtWidgets.QDialog.Accepted:
                return
            summary = od.duplicate_exposed_parameters(graph, dialog.copies)
            self._refresh()
            lines = [f"已创建参数副本：{len(summary['created'])} 个"]
            if summary["failed"]:
                lines.append(
                    f"创建失败：{len(summary['failed'])} 个\n  "
                    + "\n  ".join(
                        f"{source_id} -> {new_id}: {reason}"
                        for source_id, new_id, reason in summary["failed"][:20]
                    )
                )
            if summary["warnings"]:
                lines.append(f"部分注解未复制：{len(summary['warnings'])} 项")
            lines.append("\n如需撤销，请在 SD 中按 Ctrl+Z。")
            self._info("\n".join(lines))

        def _replace_checked_parameter_settings(self):
            """打开窗口，逐行批量修改勾选参数的设置。"""
            target_ids = self._checked_ids()
            if not target_ids:
                self._warn("请先勾选要批量替换设置的目标参数。")
                return
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            target_id_set = set(target_ids)
            parameters = [
                parameter for parameter in od.collect_exposed_parameters(graph)
                if parameter.get("id") in target_id_set
            ]
            dialog = BatchParameterSettingsDialog(graph, parameters, self)
            if sdcompat.exec_widget(dialog) != QtWidgets.QDialog.Accepted:
                return
            summary = dialog.summary or {"updated": [], "skipped": []}
            self._refresh()
            lines = [f"已修改设置：{len(summary['updated'])} 个"]
            if summary["skipped"]:
                lines.append(
                    f"已跳过：{len(summary['skipped'])} 个\n  "
                    + "\n  ".join(
                        f"{parameter_id}: {reason}"
                        for parameter_id, reason in summary["skipped"][:20]
                    )
                )
            lines.append("\n如需撤销，请在 SD 中按 Ctrl+Z。")
            self._info("\n".join(lines))

        def _remove_copy_checked(self):
            """去除勾选参数 Label 和 ID 中独立的 Copy。"""
            parameter_ids = self._checked_ids()
            if not parameter_ids:
                self._warn("请先勾选要去除 Copy 的参数或参数组。")
                return
            confirm = QtWidgets.QMessageBox.question(
                self,
                "去除 Copy",
                f"将处理 {len(parameter_ids)} 个参数，去除 Label 和 ID 中独立的 Copy。\n\n"
                "ID 会通过创建新参数、更新 Get Variable 引用、删除旧参数完成迁移。"
                "操作可在 SD 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            summary = od.remove_copy_from_parameters(graph, parameter_ids)
            self._refresh()
            reference_count = sum(item[2] for item in summary["renamed"])
            lines = [
                f"已迁移 ID：{len(summary['renamed'])} 个",
                f"已更新 Get Variable 引用：{reference_count} 处",
                f"仅修改 Label：{len(summary['label_only'])} 个",
                f"无需修改：{len(summary['unchanged'])} 个",
            ]
            if summary["failed"]:
                lines.append(
                    f"失败：{len(summary['failed'])} 个\n  "
                    + "\n  ".join(
                        f"{parameter_id}: {reason}"
                        for parameter_id, reason in summary["failed"][:20]
                    )
                )
            lines.append("\n如需撤销，请在 SD 中按 Ctrl+Z。")
            self._info("\n".join(lines))

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
            """重置函数：勾选了节点就只重置这些；未勾选则重置全图。可 Ctrl+Z 撤销。"""
            graph = od.get_current_graph()
            if graph is None:
                self._warn("未找到当前图。")
                return
            ids = self._checked_broken_ids()
            scope = f"勾选的 {len(ids)} 个节点" if ids else "全图所有损坏节点"
            confirm = QtWidgets.QMessageBox.question(
                self,
                "重置函数",
                f"将把{scope}里损坏的 Get 函数重置回常量值"
                "（修复 Empty variable 悬空引用）。\n\n"
                "操作可在 SD 中按 Ctrl+Z 撤销。是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            reset = od.repair_broken_node_functions(graph, node_ids=ids or None)
            self._refresh()
            if reset:
                self._info(f"已重置 {reset} 个损坏的节点参数（恢复常量）。\n\n如需撤销，请在 SD 中按 Ctrl+Z。")
            else:
                self._info("未发现需要重置的损坏 Get 函数。")

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
