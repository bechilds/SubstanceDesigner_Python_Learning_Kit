import sd
from PySide2 import QtWidgets, QtCore, QtGui


#本文件解决界面布局跑出屏幕的问题

# 获取应用与主窗口
ctx = sd.getContext()
app = ctx.getSDApplication()
uiMgr = app.getQtForPythonUIMgr()
mainWin = uiMgr.getMainWindow()

# 屏幕几何工具函数
screens = [s.availableGeometry() for s in QtGui.QGuiApplication.screens()]
primary = QtGui.QGuiApplication.primaryScreen().availableGeometry()

def nearestScreenRect(rect):
    c = rect.center()
    best = screens[0]
    bestDist = float('inf')
    for g in screens:
        gc = g.center()
        d = (gc.x() - c.x())**2 + (gc.y() - c.y())**2
        if d < bestDist:
            bestDist = d
            best = g
    return best

def clampMove(widget, targetGeo):
    fg = widget.frameGeometry()
    x = max(targetGeo.left(), min(fg.left(), targetGeo.right() - fg.width()))
    y = max(targetGeo.top(), min(fg.top(), targetGeo.bottom() - fg.height()))
    widget.move(x, y)

# 主窗口居中并适当缩放
try:
    mainWin.resize(min(primary.width() - 100, 1600), min(primary.height() - 100, 1000))
    centerPos = primary.center() - mainWin.rect().center()
    mainWin.move(centerPos)
except Exception as e:
    print("主窗口调整失败：", e)

# 取消所有面板的浮动并保持原始可见性
python_editor_dock = None
for dock in mainWin.findChildren(QtWidgets.QDockWidget):
    try:
        title = (dock.windowTitle() or "").lower()
        object_name = (dock.objectName() or "").lower()
        was_visible = dock.isVisible()
        was_floating = dock.isFloating()

        # 把所有面板取消浮动，避免 float 在脱屏位置
        if was_floating:
            dock.setFloating(False)

        # 特别处理 Python Editor：确保在右侧区域可见
        if "python editor" in title or "python" in object_name:
            python_editor_dock = dock
            current_area = mainWin.dockWidgetArea(dock)
            if current_area != QtCore.Qt.RightDockWidgetArea:
                mainWin.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        # 恢复原始可见性，避免影响菜单栏选项
        dock.setVisible(was_visible)
    except Exception as e:
        print("处理 Dock 面板失败：", e)

# 把所有顶层窗口（包括可能的弹窗/工具窗口）拉回可见区域
for w in QtWidgets.QApplication.topLevelWidgets():
    try:
        if w is mainWin:
            continue
        if not w.isWindow():
            continue

        title = w.windowTitle() or ""
        object_name = w.objectName() or ""
        was_visible = w.isVisible()

        rect = w.frameGeometry()

        # 跳过缺少标题和对象名、且原本不可见的内部窗口
        if not was_visible and not title and not object_name:
            continue

        target = None
        for geo in screens:
            if geo.contains(rect.center()):
                target = geo
                break

        if target is None:
            target = nearestScreenRect(rect)

        fully_inside = target.contains(rect)

        if not fully_inside:
            clampMove(w, target)
            if was_visible:
                w.show()
    except Exception as e:
        print("调整顶层窗口失败：", e)

print("已尝试重置并拉回可见界面到屏幕范围内（含 Python Editor）。")