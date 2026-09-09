# -*- coding: utf-8 -*-
"""SBSFileRepoter 对话框：显示复杂度、热点与结构性警告。"""

import html
import os

from .. import sdcompat
from . import reporter_logic

QtWidgets = sdcompat.QtWidgets
QtCore = sdcompat.QtCore
QtGui = sdcompat.QtGui

_LOG = "[MaxSDPlugin/SBSFileRepoter]"
_dialog_ref = None
_SETTINGS_ORGANIZATION = "MaxSDPlugin"
_SETTINGS_APPLICATION = "SBSFileRepoter"
_REPORT_DIRECTORY_KEY = "report_directory"


if QtWidgets is not None:

    class ScoreHistogramWidget(QtWidgets.QWidget):
        """按节点得分区间绘制数量直方图，不依赖额外的 QtCharts 模块。"""

        _COLORS = ("#d8d8d8", "#66bb6a", "#8bc34a", "#ef5350", "#ba68c8")

        def __init__(self, parent=None):
            super().__init__(parent)
            self._bins = []
            self.setMinimumHeight(150)
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        def set_bins(self, bins):
            self._bins = list(bins or [])
            self.update()

        def paintEvent(self, event):
            del event
            painter = QtGui.QPainter(self)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                bounds = self.rect().adjusted(44, 18, -12, -30)
                if not self._bins or bounds.width() <= 0 or bounds.height() <= 0:
                    painter.setPen(QtGui.QColor("#aaaaaa"))
                    painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "无可达节点")
                    return

                baseline = bounds.bottom()
                painter.setPen(QtGui.QColor("#777777"))
                painter.drawLine(bounds.left(), baseline, bounds.right(), baseline)
                maximum = max(1, max(item.get("count", 0) for item in self._bins))
                gap = 12.0
                bar_width = max(12.0, (bounds.width() - gap * (len(self._bins) + 1)) / len(self._bins))

                for index, bucket in enumerate(self._bins):
                    count = int(bucket.get("count", 0))
                    x = bounds.left() + gap + index * (bar_width + gap)
                    height = (bounds.height() - 18.0) * count / float(maximum)
                    bar = QtCore.QRectF(x, baseline - height, bar_width, height)
                    painter.fillRect(bar, QtGui.QColor(self._COLORS[index % len(self._COLORS)]))
                    painter.setPen(QtGui.QColor("#eeeeee"))
                    count_rect = QtCore.QRectF(x, baseline - height - 20, bar_width, 18)
                    painter.drawText(count_rect, QtCore.Qt.AlignCenter, str(count))
                    label_rect = QtCore.QRectF(x - 4, baseline + 4, bar_width + 8, 20)
                    painter.drawText(label_rect, QtCore.Qt.AlignCenter, str(bucket.get("label", "")))
            finally:
                painter.end()

    class SBSFileRepoterDialog(QtWidgets.QDialog):
        """当前 Graph 的发布前复杂度审计窗口。"""

        _NODE_ROLE = QtCore.Qt.UserRole if QtCore is not None else 32

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("SBSFileRepoter - Complexity Audit")
            self.resize(860, 680)
            self._graph = None
            self._report = None
            self._settings = QtCore.QSettings(
                _SETTINGS_ORGANIZATION, _SETTINGS_APPLICATION, self)
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            path_box = QtWidgets.QGroupBox("默认报告保存路径", self)
            path_layout = QtWidgets.QHBoxLayout(path_box)
            self._report_directory_edit = QtWidgets.QLineEdit(self)
            self._report_directory_edit.setText(
                str(self._settings.value(_REPORT_DIRECTORY_KEY, "") or ""))
            self._report_directory_edit.setPlaceholderText("未设置时使用当前 SBS 所在目录")
            browse_directory_button = QtWidgets.QPushButton("选择路径", self)
            open_directory_button = QtWidgets.QPushButton("打开路径", self)
            self._report_directory_edit.editingFinished.connect(
                self._save_report_directory_setting)
            browse_directory_button.clicked.connect(self._choose_report_directory)
            open_directory_button.clicked.connect(self._open_report_directory)
            path_layout.addWidget(self._report_directory_edit, 1)
            path_layout.addWidget(browse_directory_button)
            path_layout.addWidget(open_directory_button)
            layout.addWidget(path_box)

            self._report_content = QtWidgets.QWidget(self)
            report_layout = QtWidgets.QVBoxLayout(self._report_content)
            report_layout.setContentsMargins(0, 0, 0, 0)

            rules_box = QtWidgets.QGroupBox("当前评分规则", self._report_content)
            rules_layout = QtWidgets.QVBoxLayout(rules_box)
            self._rules = QtWidgets.QLabel(
                "统计范围：从 Published Output 反向遍历；未连接到输出的节点不计分。\n"
                "节点得分 = 基础类型权重 x 像素系数 x 参数系数 x 输出系数。\n"
                "尺寸基准：1024 x 1024 = 1.00；动态尺寸无法静态确定时按 1K 估算并明确标记。\n"
                "分支规则：Current 统计当前 Switch 路径；Potential Maximum 在每个 Switch 选择最高成本分支。\n"
                "文件健康：缺失内容记为 Error，非标准本地路径记为 Warning；不再加入复杂度分。\n"
                "等级阈值：Low <= 150，Medium <= 400，High <= 800，Very High > 800。",
                self)
            self._rules.setWordWrap(True)
            rules_layout.addWidget(self._rules)
            report_layout.addWidget(rules_box)

            score_box = QtWidgets.QGroupBox("评分结果", self._report_content)
            score_layout = QtWidgets.QVBoxLayout(score_box)
            self._score = QtWidgets.QLabel("等待检查", self)
            self._score.setWordWrap(True)
            score_layout.addWidget(self._score)
            report_layout.addWidget(score_box)

            tabs = QtWidgets.QTabWidget(self._report_content)
            report_layout.addWidget(tabs, 1)
            layout.addWidget(self._report_content, 1)

            cost_page = QtWidgets.QWidget(self)
            cost_layout = QtWidgets.QVBoxLayout(cost_page)
            cost_layout.setContentsMargins(4, 4, 4, 4)
            histogram_box = QtWidgets.QGroupBox(
                "节点最终权重分布（横轴：得分区间，柱顶：节点数量）", cost_page)
            histogram_layout = QtWidgets.QVBoxLayout(histogram_box)
            self._histogram = ScoreHistogramWidget(histogram_box)
            histogram_layout.addWidget(self._histogram)
            cost_layout.addWidget(histogram_box)

            self._node_table = QtWidgets.QTableWidget(0, 5, cost_page)
            self._node_table.setHorizontalHeaderLabels(
                ["节点", "规则分类", "基础权重", "计分依据", "得分"])
            self._node_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._node_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._node_table.itemDoubleClicked.connect(lambda *_: self._locate_expensive_node())
            cost_layout.addWidget(self._node_table, 1)
            tabs.addTab(cost_page, "主要成本")

            self._warning_table = QtWidgets.QTableWidget(0, 2, self)
            self._warning_table.setHorizontalHeaderLabels(["级别", "警告"])
            self._warning_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._warning_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._warning_table.itemDoubleClicked.connect(lambda *_: self._locate_warning_node())
            tabs.addTab(self._warning_table, "结构警告")

            for table in (self._node_table, self._warning_table):
                header = table.horizontalHeader()
                header.setStretchLastSection(True)

            row = QtWidgets.QHBoxLayout()
            refresh_button = QtWidgets.QPushButton("重新检查", self)
            locate_button = QtWidgets.QPushButton("定位高成本节点", self)
            save_report_button = QtWidgets.QPushButton("保存报告截图", self)
            publish_button = QtWidgets.QPushButton("Publish Anyway", self)
            cancel_button = QtWidgets.QPushButton("Cancel", self)
            refresh_button.clicked.connect(self._refresh)
            locate_button.clicked.connect(self._locate_expensive_node)
            save_report_button.clicked.connect(self._save_report_screenshot)
            publish_button.clicked.connect(self._publish)
            cancel_button.clicked.connect(self.reject)
            row.addWidget(refresh_button)
            row.addWidget(locate_button)
            row.addWidget(save_report_button)
            row.addStretch(1)
            row.addWidget(publish_button)
            row.addWidget(cancel_button)
            layout.addLayout(row)

        def _refresh(self):
            self._graph = sdcompat.get_current_graph()
            if self._graph is None:
                self._report = None
                self._score.setText("未找到当前 Graph。请先在图视图中打开要检查的 Graph。")
                self._histogram.set_bins([])
                self._node_table.setRowCount(0)
                self._warning_table.setRowCount(0)
                return
            if not self._report_directory_edit.text().strip():
                default_directory = self._current_package_directory()
                if default_directory:
                    self._report_directory_edit.setText(default_directory)
                    self._save_report_directory_setting()
            try:
                self._report = reporter_logic.analyze_graph(self._graph)
            except sdcompat.SD_API_ERRORS as error:
                self._report = None
                self._score.setText(f"分析失败：{error}")
                self._histogram.set_bins([])
                self._node_table.setRowCount(0)
                self._warning_table.setRowCount(0)
                print(f"{_LOG} 分析失败: {error}")
                return
            report = self._report
            current_color = self._score_color(report["current_level"])
            potential_color = self._score_color(report["potential_level"])
            self._score.setText(
                f"<b>文件：</b>{html.escape(report['file_name'])}<br>"
                f"<b>Current：</b><span style='font-size:18px;color:{current_color}'>"
                f"{report['current_score']:.2f} / {report['current_level']}</span>　　"
                f"<b>Potential Maximum：</b><span style='font-size:18px;color:{potential_color}'>"
                f"{report['potential_score']:.2f} / {report['potential_level']}</span><br>"
                f"Current 复杂度 {report['current_complexity_score']:.2f}　　"
                f"Potential 复杂度 {report['potential_complexity_score']:.2f}　　"
                f"全部分支总量 {report['all_branches_complexity_score']:.2f}<br>"
                f"<b>文件健康：</b>{report['file_health']}"
                f"（{len(report['risk_items'])} 项文件问题，不计入复杂度）<br>"
                f"<span style='color:#aaaaaa'>{report['resolution_basis']}</span>")
            self._histogram.set_bins(report["score_histogram"])
            self._fill_nodes(report["nodes"])
            self._fill_warnings(report["warnings"])

        @staticmethod
        def _score_color(level):
            return {
                "Low": "#f2f2f2",
                "Medium": "#4caf50",
                "High": "#ef5350",
                "Very High": "#ba68c8",
            }.get(level, "#f2f2f2")

        def _fill_nodes(self, nodes):
            self._node_table.setRowCount(len(nodes))
            for row_index, node in enumerate(nodes):
                values = [node["label"], node["group"], f"{node['base_weight']:.2f}",
                          node["score_basis"], f"{node['score']:.2f}"]
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(self._NODE_ROLE, node["id"])
                    self._node_table.setItem(row_index, column, item)
            self._node_table.resizeColumnsToContents()

        def _fill_warnings(self, warnings):
            self._warning_table.setRowCount(len(warnings))
            for row_index, warning in enumerate(warnings):
                for column, value in enumerate((warning["severity"], warning["message"])):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(self._NODE_ROLE, warning.get("node_id", ""))
                    self._warning_table.setItem(row_index, column, item)
            self._warning_table.resizeColumnsToContents()

        def _selected_node_id(self, table):
            row = table.currentRow()
            item = table.item(row, 0) if row >= 0 else None
            return item.data(self._NODE_ROLE) if item is not None else ""

        def _locate_expensive_node(self):
            node_id = self._selected_node_id(self._node_table)
            if not node_id and self._report and self._report["nodes"]:
                node_id = self._report["nodes"][0]["id"]
            self._locate(node_id)

        def _locate_warning_node(self):
            self._locate(self._selected_node_id(self._warning_table))

        def _locate(self, node_id):
            if not node_id or self._graph is None:
                QtWidgets.QMessageBox.information(self, "SBSFileRepoter", "该行没有可定位的节点。")
                return
            ok, message = sdcompat.focus_node(self._graph, node_id)
            if message:
                method = QtWidgets.QMessageBox.information if ok else QtWidgets.QMessageBox.warning
                method(self, "SBSFileRepoter", message)

        def _current_package_directory(self):
            """返回当前 SBS 所在目录；未保存或读取失败时返回空字符串。"""
            try:
                package = self._graph.getPackage() if self._graph is not None else None
                package_path = str(package.getFilePath() or "") if package is not None else ""
                return os.path.dirname(os.path.abspath(package_path)) if package_path else ""
            except sdcompat.SD_API_ERRORS as error:
                print(f"{_LOG} 读取当前 SBS 路径失败: {error}")
                return ""

        def _save_report_directory_setting(self):
            """把用户输入的报告目录写入当前插件的持久化设置。"""
            directory = os.path.normpath(
                os.path.expandvars(os.path.expanduser(
                    self._report_directory_edit.text().strip())))
            if directory == ".":
                directory = ""
            self._report_directory_edit.setText(directory)
            self._settings.setValue(_REPORT_DIRECTORY_KEY, directory)
            self._settings.sync()

        def _choose_report_directory(self):
            """选择默认报告目录并立即缓存。"""
            start_directory = (
                self._report_directory_edit.text().strip()
                or self._current_package_directory()
                or os.getcwd())
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self, "选择默认报告保存路径", start_directory)
            if not directory:
                return
            self._report_directory_edit.setText(os.path.normpath(directory))
            self._save_report_directory_setting()

        def _report_directory(self, create=False):
            """返回已配置目录，可选创建；失败时抛出便于 UI 展示的错误。"""
            self._save_report_directory_setting()
            directory = self._report_directory_edit.text().strip()
            if not directory:
                directory = self._current_package_directory()
            if not directory:
                raise RuntimeError("请先选择默认报告保存路径")
            if create:
                os.makedirs(directory, exist_ok=True)
            if not os.path.isdir(directory):
                raise RuntimeError(f"报告路径不是有效文件夹：{directory}")
            return directory

        def _open_report_directory(self):
            """使用 Windows 资源管理器打开当前设置的报告目录。"""
            try:
                directory = self._report_directory(create=True)
                os.startfile(directory)
            except sdcompat.SD_API_ERRORS as error:
                QtWidgets.QMessageBox.warning(
                    self, "SBSFileRepoter", f"无法打开报告路径：{error}")
                print(f"{_LOG} 打开报告路径失败: {error}")

        def _report_file_name(self):
            """根据当前 SBS 名称生成 Windows 可用的报告文件名。"""
            package_name = ""
            try:
                package = self._graph.getPackage() if self._graph is not None else None
                package_path = str(package.getFilePath() or "") if package is not None else ""
                package_name = os.path.splitext(os.path.basename(package_path))[0]
            except sdcompat.SD_API_ERRORS:
                pass
            if not package_name and self._report:
                package_name = os.path.splitext(str(self._report.get("file_name", "")))[0]
            safe_name = "".join(
                character if character not in '<>:"/\\|?*' else "_"
                for character in package_name).strip(" ._")
            return (safe_name or "sbs_report") + "_complexity_report.png"

        def _save_report_screenshot(self):
            """把规则、评分和当前报告页保存为 PNG，不包含底部操作按钮。"""
            if self._report is None:
                QtWidgets.QMessageBox.information(
                    self, "SBSFileRepoter", "当前没有可保存的报告，请先完成检查。")
                return
            try:
                output_path = os.path.join(
                    self._report_directory(create=True), self._report_file_name())
                pixmap = self._report_content.grab()
                if pixmap.isNull() or not pixmap.save(output_path, "PNG"):
                    raise RuntimeError("Qt 无法生成或写入 PNG 图片")
                QtWidgets.QMessageBox.information(
                    self, "SBSFileRepoter", f"报告截图已保存：\n{output_path}")
            except sdcompat.SD_API_ERRORS as error:
                QtWidgets.QMessageBox.critical(
                    self, "SBSFileRepoter", f"保存报告截图失败：{error}")
                print(f"{_LOG} 保存报告截图失败: {error}")

        def _publish(self):
            if self._graph is None:
                QtWidgets.QMessageBox.warning(self, "SBSFileRepoter", "未找到当前 Graph。")
                return
            if self._report and self._report["potential_level"] in ("High", "Very High"):
                answer = QtWidgets.QMessageBox.question(
                    self, "复杂度预警",
                    f"Potential Maximum 为 {self._report['potential_score']:.2f} / "
                    f"{self._report['potential_level']}。仍然发布吗？",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if answer != QtWidgets.QMessageBox.Yes:
                    return
            try:
                package = self._graph.getPackage()
                package_path = package.getFilePath() if package else ""
                default_name = os.path.splitext(package_path or "material.sbs")[0] + ".sbsar"
                output_path, _filter = QtWidgets.QFileDialog.getSaveFileName(
                    self, "发布 SBSAR", default_name, "Substance Archive (*.sbsar)")
                if not output_path:
                    return
                from sd.api.sbs.sdsbsarexporter import SDSBSARExporter
                exporter = SDSBSARExporter.sNew()
                exporter.exportPackageToSBSAR(package, output_path)
                QtWidgets.QMessageBox.information(self, "SBSFileRepoter", f"发布完成：\n{output_path}")
            except sdcompat.SD_API_ERRORS as error:
                QtWidgets.QMessageBox.critical(self, "SBSFileRepoter", f"发布失败：{error}")
                print(f"{_LOG} 发布失败: {error}")


def show_window(main_win=None):
    """公开入口：统一单实例、关闭释放；兼容旧调用签名。"""
    from ..shared.lifecycle import show_dialog
    from .. import sdcompat
    if QtWidgets is None:
        print('[MaxSDPlugin] Qt 不可用，无法显示窗口。')
        return None
    try:
        return show_dialog(__name__, lambda: SBSFileRepoterDialog(main_win or sdcompat.get_main_window()), globals())
    except sdcompat.SD_API_ERRORS as error:
        QtWidgets.QMessageBox.critical(main_win, "MaxSDPlugin", sdcompat.error_text(error))
        return None
