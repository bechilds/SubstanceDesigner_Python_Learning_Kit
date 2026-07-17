# -*- coding: utf-8 -*-
"""搜集当前画布 Frame，并批量修改颜色与全局透明度。"""

from .. import sdcompat

QtWidgets = sdcompat.QtWidgets
QtCore = sdcompat.QtCore
QtGui = sdcompat.QtGui

_LOG = "[MaxSDPlugin/FrameColorModify]"
_dialog_ref = None

try:
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame
    from sd.api.sdbasetypes import ColorRGBA
except Exception:  # pragma: no cover - 仅普通 Python 环境
    SDGraphObjectFrame = None
    ColorRGBA = None


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


def collect_frames(graph):
    """返回当前 Graph 中的全部 Frame；单个对象读取失败时跳过。"""
    if graph is None:
        return []
    try:
        graph_objects = _as_list(graph.getGraphObjects())
    except Exception as error:
        print(f"{_LOG} 读取 Graph Objects 失败: {error}")
        return []
    frames = []
    for graph_object in graph_objects:
        try:
            if SDGraphObjectFrame is not None and isinstance(graph_object, SDGraphObjectFrame):
                frames.append(graph_object)
                continue
            class_name = str(graph_object.getClassName() or "")
            if "GraphObjectFrame" in class_name:
                frames.append(graph_object)
        except Exception:
            continue
    return frames


def frame_info(frame):
    """返回 Frame 的标题与 RGBA 数据，供列表展示。"""
    title = "<未命名 Frame>"
    rgba = (0.0, 0.0, 0.0, 1.0)
    try:
        title = str(frame.getTitle() or title)
    except Exception:
        pass
    try:
        color = frame.getColor()
        rgba = (float(color.r), float(color.g), float(color.b), float(color.a))
    except Exception:
        pass
    return title, rgba


def frame_details(frame):
    """返回 Frame 标题、RGBA、位置、尺寸和描述。"""
    title, rgba = frame_info(frame)
    position = (0.0, 0.0)
    size = (0.0, 0.0)
    description = ""
    try:
        value = frame.getPosition()
        position = (float(value.x), float(value.y))
    except Exception:
        pass
    try:
        value = frame.getSize()
        size = (float(value.x), float(value.y))
    except Exception:
        pass
    try:
        description = str(frame.getDescription() or "")
    except Exception:
        pass
    return {
        "title": title,
        "rgba": rgba,
        "position": position,
        "size": size,
        "description": description,
    }


def apply_frame_color(frames, red, green, blue, alpha, modify_color=True):
    """批量设置 Frame RGBA；不修改颜色时保留每个 Frame 的原 RGB。"""
    if ColorRGBA is None:
        return 0, ["SD ColorRGBA API 不可用。"]
    failures = []
    changed = 0
    history = None
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        history = SDHistoryUtils.UndoGroup("FrameColorModify 批量修改 Frame")
    except Exception:
        history = None
    try:
        if history is not None:
            history.__enter__()
        for frame in frames:
            try:
                frame_red, frame_green, frame_blue = red, green, blue
                if not modify_color:
                    current_rgba = frame_info(frame)[1]
                    frame_red, frame_green, frame_blue = current_rgba[:3]
                color = ColorRGBA()
                color.r = float(frame_red)
                color.g = float(frame_green)
                color.b = float(frame_blue)
                color.a = float(alpha)
                frame.setColor(color)
                changed += 1
            except Exception as error:
                failures.append(f"{frame_info(frame)[0]}: {error}")
    finally:
        if history is not None:
            history.__exit__(None, None, None)
    return changed, failures


if QtWidgets is not None:

    class FrameColorModifyDialog(QtWidgets.QDialog):
        """当前画布 Frame 汇总和批量颜色设置窗口。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("FrameColorModify")
            self.resize(620, 480)
            self._graph = None
            self._frames = []
            self._color = QtGui.QColor(76, 175, 80)
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            self._summary = QtWidgets.QLabel(self)
            layout.addWidget(self._summary)

            self._table = QtWidgets.QTableWidget(0, 6, self)
            self._table.setHorizontalHeaderLabels(
                ["Frame", "位置", "尺寸", "当前颜色", "当前透明度", "描述"])
            self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self._table, 1)

            settings = QtWidgets.QGroupBox("统一设置", self)
            form = QtWidgets.QFormLayout(settings)
            self._modify_color = QtWidgets.QCheckBox("修改颜色", self)
            self._modify_color.setChecked(True)
            self._modify_color.toggled.connect(self._set_color_controls_enabled)
            form.addRow("", self._modify_color)
            color_row = QtWidgets.QHBoxLayout()
            self._color_preview = QtWidgets.QLabel(self)
            self._color_preview.setFixedSize(72, 24)
            self._choose_color_button = QtWidgets.QPushButton("选择颜色", self)
            self._choose_color_button.clicked.connect(self._choose_color)
            color_row.addWidget(self._color_preview)
            color_row.addWidget(self._choose_color_button)
            color_row.addStretch(1)
            form.addRow("颜色", color_row)
            self._alpha = QtWidgets.QSpinBox(self)
            self._alpha.setRange(0, 100)
            self._alpha.setValue(50)
            self._alpha.setSuffix(" %")
            form.addRow("全局透明度", self._alpha)
            layout.addWidget(settings)
            self._update_color_preview()

            buttons = QtWidgets.QHBoxLayout()
            refresh_button = QtWidgets.QPushButton("重新搜集", self)
            apply_button = QtWidgets.QPushButton("应用到全部 Frame", self)
            close_button = QtWidgets.QPushButton("关闭", self)
            refresh_button.clicked.connect(self._refresh)
            apply_button.clicked.connect(self._apply)
            close_button.clicked.connect(self.close)
            buttons.addWidget(refresh_button)
            buttons.addStretch(1)
            buttons.addWidget(apply_button)
            buttons.addWidget(close_button)
            layout.addLayout(buttons)

        def _choose_color(self):
            color = QtWidgets.QColorDialog.getColor(self._color, self, "选择 Frame 颜色")
            if color.isValid():
                self._color = color
                self._update_color_preview()

        def _update_color_preview(self):
            self._color_preview.setStyleSheet(
                f"background-color: {self._color.name()}; border: 1px solid #777777;")

        def _set_color_controls_enabled(self, enabled):
            self._color_preview.setEnabled(enabled)
            self._choose_color_button.setEnabled(enabled)

        def _refresh(self):
            self._graph = sdcompat.get_current_graph()
            self._frames = collect_frames(self._graph)
            self._summary.setText(f"当前画布 Frame：{len(self._frames)} 个")
            self._table.setRowCount(len(self._frames))
            for row, frame in enumerate(self._frames):
                details = frame_details(frame)
                rgba = details["rgba"]
                color_text = "#{:02X}{:02X}{:02X}".format(
                    int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))
                values = (
                    details["title"],
                    f"({details['position'][0]:.0f}, {details['position'][1]:.0f})",
                    f"{details['size'][0]:.0f} x {details['size'][1]:.0f}",
                    color_text,
                    f"{rgba[3] * 100:.0f} %",
                    details["description"],
                )
                for column, value in enumerate(values):
                    self._table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            self._table.resizeColumnsToContents()

        def _apply(self):
            if not self._frames:
                QtWidgets.QMessageBox.information(self, "FrameColorModify", "当前画布没有 Frame。")
                return
            changed, failures = apply_frame_color(
                self._frames, self._color.redF(), self._color.greenF(), self._color.blueF(),
                self._alpha.value() / 100.0, self._modify_color.isChecked())
            self._refresh()
            message = f"已修改 {changed} 个 Frame。可在 SD 中按 Ctrl+Z 撤销。"
            if failures:
                message += "\n\n失败：\n" + "\n".join(failures[:10])
            method = QtWidgets.QMessageBox.warning if failures else QtWidgets.QMessageBox.information
            method(self, "FrameColorModify", message)


def show_window(main_win=None):
    """菜单入口。"""
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return
    try:
        _dialog_ref = FrameColorModifyDialog(main_win or sdcompat.get_main_window())
        _dialog_ref.show()
        _dialog_ref.raise_()
        _dialog_ref.activateWindow()
    except Exception as error:
        print(f"{_LOG} 打开窗口失败: {error}")