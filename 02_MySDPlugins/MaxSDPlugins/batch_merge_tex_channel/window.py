# -*- coding: utf-8 -*-
"""BatchMergeTexChannel 窗口：配置文件匹配并执行批量通道合并。"""

import os
import re

from .. import sdcompat
from . import logic

QtWidgets = sdcompat.QtWidgets
QtCore = sdcompat.QtCore

_LOG = "[MaxSDPlugin/BatchMergeTexChannel]"
_dialog_ref = None


def _safe_filename(text):
    text = re.sub(r'[<>:"/\\|?*]+', "_", str(text)).strip(" .")
    return text or "merged"


if QtWidgets is not None:

    class BatchMergeTexChannelDialog(QtWidgets.QDialog):
        """贴图文件分组预览和批量合并窗口。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("BatchMergeTexChannel")
            self.resize(1180, 780)
            self._processor = None
            self._groups = []
            self._keyword_edits = {}
            self._channel_buttons = {}
            self._channel_button_groups = []
            self._cancel_requested = False
            self._build_ui()
            self._inspect_processor()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            self._tool_status = QtWidgets.QLabel("工具功能异常：尚未检查处理 SBS。", self)
            self._tool_status.setWordWrap(True)
            self._tool_status.setMinimumHeight(38)
            layout.addWidget(self._tool_status)

            paths_group = QtWidgets.QGroupBox("路径", self)
            paths_form = QtWidgets.QFormLayout(paths_group)
            self._source_edit = QtWidgets.QLineEdit(self)
            self._output_edit = QtWidgets.QLineEdit(self)
            self._sbs_edit = QtWidgets.QLineEdit(logic.default_sbs_path(), self)
            self._sbs_edit.textChanged.connect(self._mark_processor_unchecked)
            paths_form.addRow("输入文件夹", self._path_row(self._source_edit, self._browse_source))
            paths_form.addRow("输出文件夹", self._path_row(self._output_edit, self._browse_output))
            paths_form.addRow("处理 SBS", self._path_row(self._sbs_edit, self._browse_sbs))
            layout.addWidget(paths_group)

            config_row = QtWidgets.QHBoxLayout()
            keyword_group = QtWidgets.QGroupBox("文件名关键字", self)
            keyword_form = QtWidgets.QFormLayout(keyword_group)
            defaults = {
                "color": "ColorMap",
                "gray01": "GrayMap01",
                "gray02": "GrayMap02",
                "gray03": "GrayMap03",
                "gray04": "GrayMap04",
            }
            for key, _property_id, label in logic.INPUTS:
                edit = QtWidgets.QLineEdit(defaults[key], self)
                edit.setToolTip("文件名包含此关键字时归入对应输入；匹配不区分大小写。")
                self._keyword_edits[key] = edit
                keyword_form.addRow(label, edit)
            config_row.addWidget(keyword_group, 1)

            self._channel_group = QtWidgets.QGroupBox("最终输出 RGBA 来源（每组只能选择一个）", self)
            channel_layout = QtWidgets.QHBoxLayout(self._channel_group)
            default_sources = {"r": "color_r", "g": "color_g", "b": "color_b", "a": "color_a"}
            for channel_key, channel_label, _prefix in logic.OUTPUT_CHANNELS:
                group_box = QtWidgets.QGroupBox(channel_label, self)
                group_layout = QtWidgets.QVBoxLayout(group_box)
                button_group = QtWidgets.QButtonGroup(group_box)
                button_group.setExclusive(True)
                self._channel_button_groups.append(button_group)
                self._channel_buttons[channel_key] = {}
                for source_key, source_label, _suffix, _input_key in logic.CHANNEL_SOURCES:
                    radio = QtWidgets.QRadioButton(source_label, group_box)
                    radio.setChecked(source_key == default_sources[channel_key])
                    radio.toggled.connect(self._refresh_group_statuses)
                    button_group.addButton(radio)
                    self._channel_buttons[channel_key][source_key] = radio
                    group_layout.addWidget(radio)
                group_layout.addStretch(1)
                channel_layout.addWidget(group_box)
            config_row.addWidget(self._channel_group, 2)

            output_group = QtWidgets.QGroupBox("输出设置", self)
            output_form = QtWidgets.QFormLayout(output_group)
            self._name_template = QtWidgets.QLineEdit("{group}_Merged", self)
            self._name_template.setToolTip("使用 {group} 代表自动识别的公共文件名。")
            self._format_combo = QtWidgets.QComboBox(self)
            self._format_combo.addItems(["png", "tga", "tif", "exr"])
            self._recursive_check = QtWidgets.QCheckBox("递归扫描子文件夹", self)
            self._recursive_check.setChecked(True)
            self._overwrite_check = QtWidgets.QCheckBox("覆盖已存在输出", self)
            self._name_template.textChanged.connect(self._refresh_group_statuses)
            self._format_combo.currentTextChanged.connect(self._refresh_group_statuses)
            self._overwrite_check.toggled.connect(self._refresh_group_statuses)
            output_form.addRow("命名模板", self._name_template)
            output_form.addRow("格式", self._format_combo)
            output_form.addRow("", self._recursive_check)
            output_form.addRow("", self._overwrite_check)
            config_row.addWidget(output_group, 1)
            layout.addLayout(config_row)

            self._table = QtWidgets.QTableWidget(0, 9, self)
            self._table.setHorizontalHeaderLabels([
                "选择", "文件组", "Color", "Gray01", "Gray02", "Gray03", "Gray04", "状态", "输出",
            ])
            self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self._table, 1)

            self._progress = QtWidgets.QProgressBar(self)
            self._progress.setRange(0, 1)
            self._progress.setValue(0)
            layout.addWidget(self._progress)
            self._log = QtWidgets.QPlainTextEdit(self)
            self._log.setReadOnly(True)
            self._log.setMaximumHeight(120)
            layout.addWidget(self._log)

            buttons = QtWidgets.QHBoxLayout()
            inspect_button = QtWidgets.QPushButton("检查 SBS 接口", self)
            self._scan_button = QtWidgets.QPushButton("扫描预览", self)
            select_all_button = QtWidgets.QPushButton("全选有效组", self)
            select_none_button = QtWidgets.QPushButton("全不选", self)
            self._run_button = QtWidgets.QPushButton("开始批处理", self)
            self._cancel_button = QtWidgets.QPushButton("取消", self)
            close_button = QtWidgets.QPushButton("关闭", self)
            self._run_button.setEnabled(False)
            self._scan_button.setEnabled(False)
            self._cancel_button.setEnabled(False)
            inspect_button.clicked.connect(self._inspect_processor)
            self._scan_button.clicked.connect(self._scan)
            select_all_button.clicked.connect(lambda: self._set_all_checked(True))
            select_none_button.clicked.connect(lambda: self._set_all_checked(False))
            self._run_button.clicked.connect(self._run_batch)
            self._cancel_button.clicked.connect(self._request_cancel)
            close_button.clicked.connect(self.close)
            buttons.addWidget(inspect_button)
            buttons.addWidget(self._scan_button)
            buttons.addWidget(select_all_button)
            buttons.addWidget(select_none_button)
            buttons.addStretch(1)
            buttons.addWidget(self._run_button)
            buttons.addWidget(self._cancel_button)
            buttons.addWidget(close_button)
            layout.addLayout(buttons)

        def _path_row(self, line_edit, callback):
            container = QtWidgets.QWidget(self)
            row = QtWidgets.QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            browse = QtWidgets.QPushButton("浏览...", self)
            browse.clicked.connect(callback)
            row.addWidget(line_edit, 1)
            row.addWidget(browse)
            return container

        def _browse_source(self):
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输入贴图文件夹")
            if path:
                self._source_edit.setText(path)
                if not self._output_edit.text().strip():
                    self._output_edit.setText(os.path.join(path, "Merged"))

        def _browse_output(self):
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输出文件夹")
            if path:
                self._output_edit.setText(path)

        def _browse_sbs(self):
            path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
                self, "选择 BatchMergeTexChannel.sbs", self._sbs_edit.text(), "Substance (*.sbs)")
            if path:
                self._sbs_edit.setText(path)
                self._inspect_processor()

        def _set_tool_status(self, normal, detail):
            if normal:
                self._tool_status.setText(f"工具功能正常：{detail}")
                self._tool_status.setStyleSheet(
                    "QLabel { color: #dff7df; background: #276738; border: 1px solid #4caf50; "
                    "padding: 8px; font-weight: bold; }")
            else:
                self._tool_status.setText(f"工具功能异常：{detail}")
                self._tool_status.setStyleSheet(
                    "QLabel { color: #ffe1e1; background: #742f2f; border: 1px solid #d85b5b; "
                    "padding: 8px; font-weight: bold; }")
            self._scan_button.setEnabled(normal)
            self._channel_group.setEnabled(normal)
            if not normal:
                self._run_button.setEnabled(False)

        def _mark_processor_unchecked(self):
            logic.cleanup_processor(self._processor)
            self._processor = None
            self._set_tool_status(False, "处理 SBS 路径已变化，请点击“检查 SBS 接口”。")

        def _inspect_processor(self):
            logic.cleanup_processor(self._processor)
            self._processor = None
            try:
                self._processor = logic.load_processor(sbs_path=self._sbs_edit.text().strip())
            except Exception as error:
                self._set_tool_status(False, str(error))
                return
            if self._processor["errors"]:
                self._set_tool_status(False, " | ".join(self._processor["errors"]))
            else:
                self._set_tool_status(
                    True, "处理 SBS 已找到，5 个贴图输入、32 个通道开关和 output 输出完全一致。")
            self._refresh_group_statuses()

        def _keywords(self):
            return {key: edit.text().strip() for key, edit in self._keyword_edits.items()}

        def _channel_assignments(self):
            assignments = {}
            for channel_key, buttons in self._channel_buttons.items():
                assignments[channel_key] = next(
                    (source_key for source_key, button in buttons.items() if button.isChecked()), None)
            return assignments

        def _output_path(self, group):
            template = self._name_template.text().strip() or "{group}_Merged"
            try:
                name = template.format(group=group["group"])
            except Exception:
                name = f"{group['group']}_Merged"
            extension = self._format_combo.currentText()
            return os.path.join(self._output_edit.text().strip(), f"{_safe_filename(name)}.{extension}")

        def _scan(self):
            if self._processor is None or self._processor.get("errors"):
                QtWidgets.QMessageBox.warning(self, self.windowTitle(), "工具功能异常，处理 SBS 接口未通过检查。")
                return
            source = self._source_edit.text().strip()
            output = self._output_edit.text().strip()
            if not os.path.isdir(source):
                QtWidgets.QMessageBox.warning(self, self.windowTitle(), "请选择有效的输入文件夹。")
                return
            if not output:
                QtWidgets.QMessageBox.warning(self, self.windowTitle(), "请选择输出文件夹。")
                return
            self._groups = logic.scan_texture_groups(
                source, self._keywords(), self._recursive_check.isChecked())
            self._populate_table()
            self._append_log(f"扫描完成：找到 {len(self._groups)} 个文件组。")

        def _populate_table(self):
            self._table.setRowCount(len(self._groups))
            for row, group in enumerate(self._groups):
                check_item = QtWidgets.QTableWidgetItem()
                check_item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
                check_item.setData(QtCore.Qt.UserRole, row)
                self._table.setItem(row, 0, check_item)
                values = [group["group"]]
                for input_key, _property_id, _label in logic.INPUTS:
                    path = group["files"].get(input_key, "")
                    values.append(os.path.basename(path) if path else "-")
                values.extend(["", self._output_path(group)])
                for column, value in enumerate(values, 1):
                    self._table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            self._refresh_group_statuses()
            self._table.resizeColumnsToContents()

        def _refresh_group_statuses(self):
            if not hasattr(self, "_table"):
                return
            channel_assignments = self._channel_assignments()
            valid_count = 0
            output_paths = {}
            for row, group in enumerate(self._groups):
                errors = logic.validate_group(group, channel_assignments)
                output_path = self._output_path(group)
                output_key = os.path.normcase(os.path.abspath(output_path))
                if output_key in output_paths:
                    errors.append(f"输出路径与 {output_paths[output_key]} 冲突")
                else:
                    output_paths[output_key] = group["group"]
                if os.path.exists(output_path) and not self._overwrite_check.isChecked():
                    errors.append("输出已存在")
                status = "可处理" if not errors else "；".join(errors)
                status_item = self._table.item(row, 7)
                output_item = self._table.item(row, 8)
                check_item = self._table.item(row, 0)
                if status_item is not None:
                    status_item.setText(status)
                if output_item is not None:
                    output_item.setText(output_path)
                if check_item is not None:
                    if errors:
                        check_item.setCheckState(QtCore.Qt.Unchecked)
                        check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    else:
                        check_item.setFlags(
                            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
                        check_item.setCheckState(QtCore.Qt.Checked)
                        valid_count += 1
            self._run_button.setEnabled(
                valid_count > 0 and self._processor is not None and not self._processor.get("errors"))

        def _set_all_checked(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 0)
                if item is not None and item.flags() & QtCore.Qt.ItemIsUserCheckable:
                    item.setCheckState(state)

        def _selected_groups(self):
            selected = []
            for row, group in enumerate(self._groups):
                item = self._table.item(row, 0)
                if item is not None and item.checkState() == QtCore.Qt.Checked:
                    selected.append(group)
            return selected

        def _run_batch(self):
            groups = self._selected_groups()
            if not groups:
                QtWidgets.QMessageBox.information(self, self.windowTitle(), "没有勾选可处理的文件组。")
                return
            if self._processor is None:
                self._inspect_processor()
            if self._processor is None or self._processor.get("errors"):
                QtWidgets.QMessageBox.warning(self, self.windowTitle(), "处理 SBS 接口检查未通过。")
                return
            self._cancel_requested = False
            self._run_button.setEnabled(False)
            self._cancel_button.setEnabled(True)
            self._progress.setRange(0, len(groups))
            self._progress.setValue(0)
            succeeded = 0
            failed = []
            channel_assignments = self._channel_assignments()
            for index, group in enumerate(groups, 1):
                QtWidgets.QApplication.processEvents()
                if self._cancel_requested:
                    self._append_log("用户取消，停止后续任务。")
                    break
                output_path = self._output_path(group)
                try:
                    logic.process_group(
                        self._processor, group, channel_assignments, output_path)
                    succeeded += 1
                    self._append_log(f"成功 [{group['group']}] -> {output_path}")
                except Exception as error:
                    failed.append((group["group"], str(error)))
                    self._append_log(f"失败 [{group['group']}]：{error}")
                self._progress.setValue(index)
            self._cancel_button.setEnabled(False)
            self._refresh_group_statuses()
            message = f"处理完成：成功 {succeeded}，失败 {len(failed)}。"
            if self._cancel_requested:
                message += "\n任务已取消。"
            if failed:
                message += "\n\n" + "\n".join(f"{name}: {error}" for name, error in failed[:10])
            method = QtWidgets.QMessageBox.warning if failed else QtWidgets.QMessageBox.information
            method(self, self.windowTitle(), message)

        def _request_cancel(self):
            self._cancel_requested = True
            self._cancel_button.setEnabled(False)

        def _append_log(self, message):
            self._log.appendPlainText(message)
            print(f"{_LOG} {message}")

        def closeEvent(self, event):
            logic.cleanup_processor(self._processor)
            self._processor = None
            super().closeEvent(event)


def show_window(main_win=None):
    """菜单入口。"""
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return
    try:
        _dialog_ref = BatchMergeTexChannelDialog(main_win or sdcompat.get_main_window())
        _dialog_ref.show()
        _dialog_ref.raise_()
        _dialog_ref.activateWindow()
    except Exception as error:
        print(f"{_LOG} 打开窗口失败: {error}")
        QtWidgets.QMessageBox.critical(main_win, "BatchMergeTexChannel", str(error))