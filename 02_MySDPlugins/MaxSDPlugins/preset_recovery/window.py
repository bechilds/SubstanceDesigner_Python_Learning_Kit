# -*- coding: utf-8 -*-
"""预设效果找回窗口：把旧预设恢复到当前 Graph 的 Presets。"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except Exception:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except Exception as error:
        QtCore = None
        QtGui = None
        QtWidgets = None
        print(f"[MaxSDPlugin/preset_recovery] PySide 不可用: {error}")

from .. import sdcompat
from . import logic

_LOG = "[MaxSDPlugin/preset_recovery]"
_dialog_ref = None


if QtWidgets is not None:

    class PresetRecoveryDialog(QtWidgets.QDialog):
        """预览旧预设参数与当前 Identifier 的映射。"""

        def __init__(self, graph, parent=None):
            super().__init__(parent)
            self._graph = graph
            self._presets = []
            self._graph_description = logic.describe_graph(graph)
            self._targets = logic.collect_target_parameters(graph)
            self._existing_preset_labels = logic.collect_preset_labels(graph)
            self._mappings = []
            self.setWindowTitle("预设效果找回 - MaxSDPlugin")
            self.resize(920, 560)
            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            description = QtWidgets.QLabel(
                "导入旧 .sbsprs 后，工具按旧参数名匹配当前 Graph 的 Identifier。"
                "确认映射后，在当前 INPUT PARAMETERS > Presets 中新建预设；"
                "目标名称已存在时可确认覆盖同名预设。找不到的参数会标红，可手动指定。",
                self,
            )
            description.setWordWrap(True)
            layout.addWidget(description)

            context_group = QtWidgets.QGroupBox("匹配对象确认", self)
            context_layout = QtWidgets.QFormLayout(context_group)
            package_path = self._graph_description["package_path"] or "未保存的 SBS"
            graph_name = (self._graph_description["identifier"]
                          or self._graph_description["url"] or "未知 Graph")
            self._current_sbs_label = QtWidgets.QLabel(package_path, context_group)
            self._current_sbs_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self._current_sbs_label.setWordWrap(True)
            context_layout.addRow("当前 SBS（将修改）：", self._current_sbs_label)
            context_layout.addRow("当前 Graph（写入目标）：", QtWidgets.QLabel(graph_name, context_group))
            self._source_preset_label = QtWidgets.QLabel("尚未导入", context_group)
            self._source_preset_label.setWordWrap(True)
            context_layout.addRow("导入的源预设：", self._source_preset_label)
            output_note = QtWidgets.QLabel(
                "执行后写入当前 Graph 的 INPUT PARAMETERS > Presets；"
                "导入的 .sbsprs 文件不会修改。完成后请保存当前 SBS。",
                context_group,
            )
            output_note.setWordWrap(True)
            context_layout.addRow("执行方式：", output_note)
            layout.addWidget(context_group)

            file_row = QtWidgets.QHBoxLayout()
            self._path_edit = QtWidgets.QLineEdit(self)
            self._path_edit.setReadOnly(True)
            self._path_edit.setPlaceholderText("请选择 Substance Designer 预设文件 (.sbsprs)")
            browse_button = QtWidgets.QPushButton("导入预设...", self)
            browse_button.clicked.connect(self._browse)
            file_row.addWidget(self._path_edit, 1)
            file_row.addWidget(browse_button)
            layout.addLayout(file_row)

            preset_row = QtWidgets.QHBoxLayout()
            preset_row.addWidget(QtWidgets.QLabel("源文件内预设：", self))
            self._preset_combo = QtWidgets.QComboBox(self)
            self._preset_combo.setEnabled(False)
            self._preset_combo.currentIndexChanged.connect(self._show_preset)
            preset_row.addWidget(self._preset_combo, 1)
            self._status_label = QtWidgets.QLabel("尚未导入", self)
            preset_row.addWidget(self._status_label)
            layout.addLayout(preset_row)

            target_row = QtWidgets.QHBoxLayout()
            target_row.addWidget(QtWidgets.QLabel("目标 Preset 名称：", self))
            self._target_name_edit = QtWidgets.QLineEdit(self)
            self._target_name_edit.setPlaceholderText("输入要在当前 Graph 中创建的 Preset 名称")
            self._target_name_edit.textChanged.connect(self._update_target_status)
            target_row.addWidget(self._target_name_edit, 1)
            self._target_status_label = QtWidgets.QLabel("尚未指定", self)
            target_row.addWidget(self._target_status_label)
            layout.addLayout(target_row)

            self._mapping_summary_label = QtWidgets.QLabel(
                "导入参数：0 · 已匹配：0 · 未匹配：0", self)
            layout.addWidget(self._mapping_summary_label)

            self._table = QtWidgets.QTableWidget(0, 6, self)
            self._table.setHorizontalHeaderLabels(
                ["旧预设参数名", "源类型", "预设值", "匹配状态",
                 "目标 Editor", "当前 Identifier 目标"])
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._table.verticalHeader().setVisible(False)
            header = self._table.horizontalHeader()
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
            layout.addWidget(self._table, 1)

            action_row = QtWidgets.QHBoxLayout()
            action_row.addStretch(1)
            self._apply_button = QtWidgets.QPushButton("执行", self)
            cancel_button = QtWidgets.QPushButton("取消", self)
            self._apply_button.setEnabled(False)
            self._apply_button.clicked.connect(self._apply)
            cancel_button.clicked.connect(self.close)
            action_row.addWidget(self._apply_button)
            action_row.addWidget(cancel_button)
            layout.addLayout(action_row)

        def _browse(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "导入 Substance Designer 预设", "",
                "Substance Designer Preset (*.sbsprs);;XML 文件 (*.xml);;所有文件 (*.*)")
            if not path:
                return
            try:
                presets = logic.parse_preset_file(path)
            except (ValueError, OSError) as error:
                QtWidgets.QMessageBox.critical(self, "预设读取失败", str(error))
                return
            self._path_edit.setText(path)
            self._presets = presets
            self._source_preset_label.setText(
                f"{path}\n共 {len(presets)} 个预设；请选择下方源预设进行映射。")
            self._preset_combo.blockSignals(True)
            self._preset_combo.clear()
            self._preset_combo.addItems([preset["name"] for preset in presets])
            self._preset_combo.blockSignals(False)
            self._preset_combo.setEnabled(True)
            self._preset_combo.setCurrentIndex(0)
            self._show_preset(0)

        def _show_preset(self, index):
            if index < 0 or index >= len(self._presets):
                return
            self._mappings = logic.build_mappings(
                self._presets[index]["inputs"], self._targets)
            self._table.setRowCount(len(self._mappings))
            target_ids = [target["id"] for target in self._targets]
            for row, mapping in enumerate(self._mappings):
                for column, key in enumerate(("source_name", "type", "value")):
                    item = QtWidgets.QTableWidgetItem(str(mapping.get(key, "")))
                    self._table.setItem(row, column, item)
                self._table.setItem(row, 3, QtWidgets.QTableWidgetItem())
                self._table.setItem(row, 4, QtWidgets.QTableWidgetItem())

                combo = QtWidgets.QComboBox(self._table)
                combo.addItem("不写入", "")
                for target in self._targets:
                    combo.addItem(
                        f"{target['label']}  ({target['id']}) · "
                        f"{logic.describe_editor_conversion(target)}",
                        target["id"])
                target_id = mapping.get("target_id", "")
                if target_id in target_ids:
                    combo.setCurrentIndex(target_ids.index(target_id) + 1)
                else:
                    warning_color = QtGui.QColor("#b42318")
                    self._table.item(row, 0).setForeground(warning_color)
                    self._table.item(row, 0).setToolTip(
                        "当前 Graph 中没有同名 Identifier，请手动选择目标参数；"
                        "保持“不写入”时该参数不会进入目标 Preset。")
                combo.currentIndexChanged.connect(
                    lambda _index: self._refresh_mapping_summary())
                self._table.setCellWidget(row, 5, combo)

            preset = self._presets[index]
            self._target_name_edit.setText(preset["name"])
            source_target = preset.get("target") or "源文件未记录目标 Graph"
            self._status_label.setText(
                f"第 {index + 1}/{len(self._presets)} 个 · 原目标：{source_target}")
            self._refresh_mapping_summary()
            self._apply_button.setEnabled(bool(self._mappings and self._targets))

        def _refresh_mapping_summary(self):
            targets_by_id = {target["id"]: target for target in self._targets}
            matched_count = 0
            automatic_count = 0
            for row, mapping in enumerate(self._mappings):
                combo = self._table.cellWidget(row, 5)
                if combo is None:
                    continue
                target_id = combo.currentData() or ""
                target = targets_by_id.get(target_id)
                source_item = self._table.item(row, 0)
                status_item = self._table.item(row, 3)
                editor_item = self._table.item(row, 4)
                if target is None:
                    source_item.setForeground(QtGui.QColor("#b42318"))
                    status_item.setText("未匹配（不写入）")
                    status_item.setForeground(QtGui.QColor("#b42318"))
                    editor_item.setText("-")
                    continue
                matched_count += 1
                source_item.setForeground(QtGui.QColor("#2e7d32"))
                if target_id == mapping.get("auto_target_id"):
                    automatic_count += 1
                    status_item.setText("已自动匹配")
                else:
                    status_item.setText("已手动匹配")
                status_item.setForeground(QtGui.QColor("#2e7d32"))
                editor_item.setText(logic.describe_editor_conversion(target))

            total_count = len(self._mappings)
            unmatched_count = total_count - matched_count
            manual_count = matched_count - automatic_count
            self._mapping_summary_label.setText(
                f"导入参数：{total_count} · 已匹配：{matched_count} "
                f"（自动 {automatic_count} / 手动 {manual_count}） · "
                f"未匹配：{unmatched_count}")

        def _update_target_status(self, text):
            name = text.strip()
            if not name:
                self._target_status_label.setText("名称不能为空")
            elif name in self._existing_preset_labels:
                self._target_status_label.setText("当前 Graph 已存在，将询问是否覆盖")
            else:
                self._target_status_label.setText("将在当前 Graph 中新建")

        def _apply(self):
            selected_mappings = []
            for row, mapping in enumerate(self._mappings):
                combo = self._table.cellWidget(row, 5)
                updated_mapping = dict(mapping)
                updated_mapping["target_id"] = combo.currentData() or ""
                selected_mappings.append(updated_mapping)

            prepared_inputs, errors = logic.prepare_preset_inputs(
                selected_mappings, self._targets)
            write_count = len(prepared_inputs)
            if write_count == 0:
                QtWidgets.QMessageBox.information(
                    self, "没有可写入项", "请至少为一个旧预设参数选择目标 Identifier。")
                return
            if errors:
                details = "\n".join(f"- {name}: {reason}" for name, reason in errors)
                QtWidgets.QMessageBox.warning(
                    self, "部分参数无法转换",
                    "以下参数无法转换为当前目标参数类型。未修改当前 Graph：\n\n" + details)
                return

            target_name = self._target_name_edit.text().strip()
            if not target_name:
                QtWidgets.QMessageBox.information(
                    self, "Preset 名称为空", "请输入要创建或覆盖的目标 Preset 名称。")
                return

            overwrite = target_name in self._existing_preset_labels
            if overwrite:
                overwrite_answer = QtWidgets.QMessageBox.warning(
                    self, "确认覆盖当前同名 Preset",
                    f"当前 Graph 的 Presets 中已经存在：{target_name}\n\n"
                    "执行后会删除并重建这个同名 Preset，其参数将替换为当前映射结果。\n"
                    "此操作不会修改导入的 .sbsprs 文件。\n\n确认覆盖吗？",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if overwrite_answer != QtWidgets.QMessageBox.Yes:
                    return

            preset = self._presets[self._preset_combo.currentIndex()]
            graph_name = (self._graph_description["identifier"]
                          or self._graph_description["url"] or "未知 Graph")
            confirm_answer = QtWidgets.QMessageBox.question(
                self, "确认执行预设找回",
                f"源预设：{preset['name']}\n"
                f"写入当前 Graph：{graph_name}\n"
                f"目标 Preset：{target_name}\n"
                f"操作：{'覆盖同名 Preset' if overwrite else '新建 Preset'}\n"
                f"写入参数：{write_count} 个\n\n"
                "将修改当前 Graph；导入的 .sbsprs 文件不会修改。\n"
                "完成后需要保存当前 SBS 才会写入磁盘。\n\n"
                "确认执行吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm_answer != QtWidgets.QMessageBox.Yes:
                return
            try:
                result = logic.create_or_replace_preset(
                    self._graph, target_name, prepared_inputs, overwrite=overwrite)
            except ValueError as error:
                QtWidgets.QMessageBox.critical(self, "Preset 写入失败", str(error))
                return
            if target_name not in self._existing_preset_labels:
                self._existing_preset_labels.append(target_name)
            self._update_target_status(target_name)
            QtWidgets.QMessageBox.information(
                self, "预设找回完成",
                f"已在当前 Graph 的 INPUT PARAMETERS > Presets 中"
                f"{'覆盖' if result == 'replaced' else '创建'}：{target_name}\n\n"
                f"共写入 {write_count} 个参数。请保存当前 SBS。")


def show_window(main_win=None):
    """公开入口：统一单实例、关闭释放；兼容旧调用签名。"""
    from ..shared.lifecycle import show_dialog
    from .. import sdcompat
    if QtWidgets is None:
        print('[MaxSDPlugin] Qt 不可用，无法显示窗口。')
        return None
    graph = sdcompat.get_current_graph()
    if graph is None:
        QtWidgets.QMessageBox.information(main_win, "预设效果找回", "请先打开目标 Graph。")
        return None
    try:
        return show_dialog(__name__, lambda: PresetRecoveryDialog(graph, main_win or sdcompat.get_main_window()), globals())
    except sdcompat.SD_API_ERRORS as error:
        QtWidgets.QMessageBox.critical(main_win, "MaxSDPlugin", sdcompat.error_text(error))
        return None
