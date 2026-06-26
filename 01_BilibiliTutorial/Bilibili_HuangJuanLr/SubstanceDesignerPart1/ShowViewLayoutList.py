import sd
from PySide2 import QtWidgets, QtCore, QtGui

#这个脚本列出所有可见的窗口，包括面板和独立窗口

# 获取主窗口
ctx = sd.getContext()
app = ctx.getSDApplication()
uiMgr = app.getQtForPythonUIMgr()
mainWin = uiMgr.getMainWindow()

# 屏幕工具
screens = QtGui.QGuiApplication.screens()
def screen_index_for_rect(rect: QtCore.QRect):
    if not screens:
        return -1
    c = rect.center()
    best, bestd = 0, float('inf')
    for i, s in enumerate(screens):
        sc = s.geometry().center()
        d = (sc.x()-c.x())**2 + (sc.y()-c.y())**2
        if d < bestd:
            bestd, best = d, i
    return best

def flags_to_str(flags: QtCore.Qt.WindowFlags):
    names = []
    f = flags
    if f & QtCore.Qt.Window: names.append('Window')
    if f & QtCore.Qt.Dialog: names.append('Dialog')
    if f & QtCore.Qt.Tool: names.append('Tool')
    if f & QtCore.Qt.Popup: names.append('Popup')
    if f & QtCore.Qt.SubWindow: names.append('SubWindow')
    if f & QtCore.Qt.FramelessWindowHint: names.append('Frameless')
    return "|".join(names) or str(int(f))

def guess_panel(title, obj, cls, content_cls):
    t = (title or "").lower()
    o = (obj or "").lower()
    cc = (content_cls or "").lower()
    if "python" in t or "python" in o or "python" in cc: return "Python Editor"
    if "graph" in t or "graph" in o: return "Graph"
    if "explorer" in t or "package" in t or "packages" in t: return "Explorer/Packages"
    if "library" in t: return "Library"
    if "properties" in t or "parameter" in t: return "Properties"
    if "2d" in t or "2d view" in t: return "2D View"
    if "3d" in t or "3d view" in t: return "3D View"
    if "log" in t or "console" in t: return "Log/Console"
    return ""

# 收集可见的顶层 QWidget（不是面板也会被列出）
tops = [w for w in QtWidgets.QApplication.topLevelWidgets() if w.isWindow()]
widgets_info = []
for w in tops:
    if w is mainWin:
        continue
    info = {}
    info["title"] = w.windowTitle() or ""
    info["objectName"] = w.objectName() or ""
    info["class"] = w.__class__.__name__
    info["module"] = type(w).__module__
    info["visible"] = w.isVisible()
    geo = w.frameGeometry()
    info["geom"] = f"{geo.x()},{geo.y()} {geo.width()}x{geo.height()}"
    info["screen"] = screen_index_for_rect(geo)
    info["flags"] = flags_to_str(w.windowFlags())
    info["isDock"] = isinstance(w, QtWidgets.QDockWidget)
    info["isDialog"] = isinstance(w, QtWidgets.QDialog) or (w.windowFlags() & QtCore.Qt.Dialog)
    info["isTool"] = bool(w.windowFlags() & QtCore.Qt.Tool)

    # 内容控件与面板猜测
    content = None
    if info["isDock"]:
        content = w.widget()
    elif hasattr(w, "centralWidget"):
        content = w.centralWidget()
    info["contentClass"] = content.__class__.__name__ if content else "None"
    info["contentModule"] = type(content).__module__ if content else "None"
    info["panelGuess"] = guess_panel(info["title"], info["objectName"], info["class"], info["contentClass"])

    # 父链（帮助判断来源）
    chain = []
    p = w.parentWidget()
    while p:
        chain.append(f"{p.__class__.__name__}({p.objectName()})")
        p = p.parentWidget()
    info["parentChain"] = " > ".join(chain) if chain else ""

    widgets_info.append((w, info))

# 收集原生 QWindow（某些窗口不是 QWidget）
qwin_infos = []
for win in QtGui.QGuiApplication.allWindows():
    geo = win.geometry()
    qwin_infos.append({
        "title": win.title() or "",
        "class": win.__class__.__name__,
        "module": type(win).__module__,
        "visible": win.isVisible(),
        "geom": f"{geo.x()},{geo.y()} {geo.width()}x{geo.height()}",
        "screen": screen_index_for_rect(geo),
        "flags": flags_to_str(win.flags()),
    })

# 打印列表
print("=== 可见的顶层 QWidget 窗口（除主窗口） ===")
visible_count = 0
for i, (w, info) in enumerate(sorted(widgets_info, key=lambda x: (x[1]["title"].lower(), x[1]["class"])), 1):
    if not info["visible"]:
        continue
    visible_count += 1
    print(f"[{i}] title='{info['title']}' | object='{info['objectName']}'")
    print(f"     class={info['class']} module={info['module']}")
    print(f"     flags={info['flags']} | screen={info['screen']} | geom={info['geom']}")
    print(f"     content: class={info['contentClass']} module={info['contentModule']}")
    if info["panelGuess"]:
        print(f"     guess={info['panelGuess']}")
    if info["parentChain"]:
        print(f"     parentChain={info['parentChain']}")

if visible_count == 0:
    print("（没有可见的顶层 QWidget 窗口）")

print("=== 可见的顶层 QWindow（原生） ===")
qwin_visible = 0
for i, info in enumerate(qwin_infos, 1):
    if not info["visible"]:
        continue
    qwin_visible += 1
    print(f"[W{i}] title='{info['title']}'")
    print(f"     class={info['class']} module={info['module']}")
    print(f"     flags={info['flags']} | screen={info['screen']} | geom={info['geom']}")
if qwin_visible == 0:
    print("（没有可见的顶层 QWindow）")

# 可选：给可见窗口临时加编号标签，便于肉眼对应（几秒后恢复）
def label_visible_windows_temporarily(seconds=8):
    originals = {}
    # QWidget
    for i, (w, info) in enumerate(widgets_info, 1):
        if not info["visible"]:
            continue
        orig = info["title"]
        originals[w] = orig
        try:
            w.setWindowTitle(f"{orig}  [#{i}]")
        except Exception:
            pass
        try:
            w.raise_()
        except Exception:
            pass
        w.show()
    # QWindow（如果支持设置标题）
    # 这里不修改 QWindow 标题，避免影响原生窗口

    def restore():
        for w, orig in originals.items():
            try:
                w.setWindowTitle(orig)
            except Exception:
                pass
    QtCore.QTimer.singleShot(int(seconds * 1000), restore)

# 取消下一行注释以临时加编号
# label_visible_windows_temporarily(8)

print("提示：如果窗口出现在“QDialog/Tool/QWindow”列表而不是 QDockWidget，它们不是面板，而是独立窗口或原生窗口。模块路径有助于判断来源（内置/插件）。")