# -*- coding: utf-8 -*-
"""跨版本（SD16 / SD13）SD + Qt 接口兼容层 —— 唯一真源。

**为什么存在**：SD16=PySide6/Qt6，SD13=PySide2/Qt5，且 SD 自身的 UI 管理器
（QtForPythonUIMgr / SDUIMgr）在不同版本上方法名与能力都不同。若各功能模块各自
硬编码 `app.getQtForPythonUIMgr()` / `app.getUIMgr()` / `focusGraphNode(...)`，就会
在旧版本上零散地抛「接口不存在」的错。

**机制**：所有版本脆弱的接口统一走本模块，采用
  1) 能力探测（hasattr / 遍历多个候选管理器与候选方法名）；
  2) 多策略降级（定位不了就退而选中/高亮；再不行给出友好提示）；
  3) 永不向外抛异常 + 精确日志（打印缺失的接口名，便于定位）。

**维护**：新发现一处跨版本差异，就在这里加一个候选，不要散落到功能模块里。
配套查找表见 `../docs/SD_API_Compatibility.md`。本模块**不含相对 import**，
可被 OutputTools 直接打包进导出物（作为 `_maxsd_bundle.root_sdcompat`）。
"""

_LOG = "[MaxSDPlugin/compat]"


# --------------------------------------------------------------------------- #
# Qt 绑定解析（PySide6 优先，PySide2 回退）
# --------------------------------------------------------------------------- #
QtWidgets = None
QtCore = None
QtGui = None
PYSIDE = None
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    PYSIDE = "PySide6"
except Exception:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        PYSIDE = "PySide2"
    except Exception as _e:  # pragma: no cover - 仅非 SD/无 Qt 环境
        print(f"{_LOG} PySide 不可用: {_e}")


def qt_patch():
    """抹平 Qt6/Qt5 差异：QAction 所在模块 + exec/exec_ 互为别名。

    - PySide6: QAction 在 QtGui，模态用 exec()；
    - PySide2: QAction 在 QtWidgets，模态用 exec_()。
    调用后两种写法在两个版本上都可用。多次调用安全（幂等）。
    """
    if QtWidgets is None:
        return
    # QAction 位置双向补全
    try:
        if not hasattr(QtWidgets, "QAction") and QtGui is not None and hasattr(QtGui, "QAction"):
            QtWidgets.QAction = QtGui.QAction
        if QtGui is not None and not hasattr(QtGui, "QAction") and hasattr(QtWidgets, "QAction"):
            QtGui.QAction = QtWidgets.QAction
    except Exception:
        pass
    # exec / exec_ 互为别名（部分 Shiboken 类型不可赋属性 -> 包 try）
    for _cn in ("QMenu", "QDialog", "QApplication", "QMessageBox", "QFileDialog", "QInputDialog"):
        _cls = getattr(QtWidgets, _cn, None)
        if _cls is None:
            continue
        try:
            if not hasattr(_cls, "exec") and hasattr(_cls, "exec_"):
                _cls.exec = _cls.exec_
            if not hasattr(_cls, "exec_") and hasattr(_cls, "exec"):
                _cls.exec_ = _cls.exec
        except Exception:
            pass


def get_qaction():
    """返回当前可用的 QAction 类（PySide6=QtGui / PySide2=QtWidgets）；无则 None。"""
    if QtGui is not None and hasattr(QtGui, "QAction"):
        return QtGui.QAction
    if QtWidgets is not None and hasattr(QtWidgets, "QAction"):
        return QtWidgets.QAction
    return None


def exec_widget(widget, *args):
    """兼容调用模态：优先 exec()，回退 exec_()。widget 为 None 或都没有则返回 None。"""
    if widget is None:
        return None
    fn = getattr(widget, "exec", None) or getattr(widget, "exec_", None)
    return fn(*args) if callable(fn) else None


# --------------------------------------------------------------------------- #
# SD 应用 / UI 管理器
# --------------------------------------------------------------------------- #
def get_app(app=None):
    """返回 SDApplication；传入则原样返回。取不到返回 None（不抛）。"""
    if app is not None:
        return app
    try:
        import sd
        return sd.getContext().getSDApplication()
    except Exception as e:
        print(f"{_LOG} 取 SDApplication 失败: {e}")
        return None


def _ui_mgrs(app):
    """返回可用的 UI 管理器对象列表（QtForPython 优先，再退 SDUIMgr / UIMgr）。

    不同 SD 版本图视图/选择相关接口挂在不同管理器上，返回全部候选，由调用方逐个探测。
    """
    mgrs = []
    for name in ("getQtForPythonUIMgr", "getUIMgr", "getSDUIMgr"):
        fn = getattr(app, name, None)
        if fn is None:
            continue
        try:
            m = fn()
            if m is not None and m not in mgrs:
                mgrs.append(m)
        except Exception:
            pass
    return mgrs


def get_current_graph(app=None):
    """返回当前图视图里打开的 SDGraph；取不到返回 None（不抛）。"""
    app = get_app(app)
    if app is None:
        return None
    for m in _ui_mgrs(app):
        fn = getattr(m, "getCurrentGraph", None)
        if callable(fn):
            try:
                g = fn()
                if g is not None:
                    return g
            except Exception:
                pass
    return None


def get_main_window(app=None):
    """尽力拿到 SD 主窗口作为父窗口；取不到返回 None（不抛）。"""
    app = get_app(app)
    if app is None:
        return None
    for m in _ui_mgrs(app):
        fn = getattr(m, "getMainWindow", None)
        if callable(fn):
            try:
                w = fn()
                if w is not None:
                    return w
            except Exception:
                pass
    return None


def focus_node(graph, node_id, app=None):
    """在图视图里定位/选中指定节点。返回 (ok, 信息)。

    版本现状（已核对：SD16/SD14 的 UI 管理器有 focusGraphNode；本机 SD13.0.0 实测没有）：
      - SD16 / SD14：`focusGraphNode(graphViewID, node)` 可用 -> 策略1 居中定位，Goto 正常。
      - SD13：两个 UI 管理器都只有 getXxxSelection 读取接口，没有 focusGraphNode /
        getGraphViewIDCount / setCurrentGraphSelection / selectNode(s)，但节点图坐标与
        QGraphicsScene 坐标 1:1 对应 -> 走策略3（Qt 层 fitInView 缩放居中）实现跳转。

    多策略探测（按优先级）：
      策略1：`focusGraphNode` + 图视图枚举（`getGraphViewIDCount/At` /
             `getGraphFromGraphViewID`）——SD16/SD14 路径，能真正居中。
      策略2：选中节点高亮（`setCurrentGraphSelection` / `selectNodes` 等）——若某版本提供则用。
      策略3：`node.getPosition()` + QGraphicsView.fitInView——SD13 等无 focusGraphNode 时的
             纯 Qt 定位路径（已在 SD13.0.0 验证：缩放+居中，效果接近 F 键）。
      全部不可用 -> 回显节点 `label (id) @ (x,y)` + 把 id 复制到剪贴板 + 友好提示，永不抛异常。
    """
    if not node_id:
        return False, "该行无节点 id。"
    app = get_app(app)
    if app is None:
        return False, "取不到 SDApplication。"
    try:
        node = graph.getNodeFromId(node_id)
    except Exception as e:
        return False, f"取节点失败: {e}"
    if node is None:
        return False, f"未找到节点: {node_id}"

    mgrs = _ui_mgrs(app)

    # 策略1：图视图居中（SD16 / SD14）
    for m in mgrs:
        if hasattr(m, "getGraphViewIDCount") and hasattr(m, "focusGraphNode"):
            try:
                cnt = m.getGraphViewIDCount()
                target_vid = None
                for i in range(cnt):
                    vid = m.getGraphViewIDAt(i)
                    try:
                        if m.getGraphFromGraphViewID(vid) is graph:
                            target_vid = vid
                            break
                    except Exception:
                        pass
                if target_vid is None and cnt > 0:
                    target_vid = m.getGraphViewIDAt(0)
                if target_vid is not None:
                    m.focusGraphNode(target_vid, node)
                    return True, ""
            except Exception as e:
                print(f"{_LOG} focusGraphNode 失败: {e}")

    # 策略2：选中/高亮节点（若某版本提供 set/select 接口）
    for m in mgrs:
        for sel in ("setCurrentGraphSelection", "setCurrentGraphSelectedNodes",
                    "selectNodes", "selectNode"):
            fn = getattr(m, sel, None)
            if not callable(fn):
                continue
            try:
                try:
                    fn([node])
                except Exception:
                    fn(node)
                return True, "已选中节点（该 SD 版本不支持自动居中，请在图中查看高亮）。"
            except Exception as e:
                print(f"{_LOG} {sel} 失败: {e}")

    # 策略3（SD13 等无 focusGraphNode 时）：Qt 层用 node.getPosition() 在图视图
    # QGraphicsView 上 fitInView 缩放居中，不需要选中、也不用 F 键。纯 UI、不改数据。
    ok3, info3 = _try_center_on_node(app, node)
    if ok3:
        return True, info3
    print(f"{_LOG} 定位未成功: {info3}")

    # 都不支持（SD13 的现状）：回显节点标识 + 坐标 + 复制 id 到剪贴板，供手动查找。
    desc = _node_desc(node, node_id)
    copied = _copy_to_clipboard(str(node_id))
    tip = "（id 已复制到剪贴板）" if copied else ""
    return False, ("当前 SD 版本（如 SD13）未提供程序化定位/选中节点的接口，无法自动跳转。\n"
                   f"请在图中手动查找：{desc}{tip}。\n"
                   "提示：@ 后为该节点在图中的坐标 (x, y)。")


def _copy_to_clipboard(text):
    """把文本放进系统剪贴板，成功返回 True，失败返回 False（不抛）。"""
    try:
        app = QtWidgets.QApplication.instance() if QtWidgets is not None else None
        if app is None:
            return False
        cb = app.clipboard()
        if cb is None:
            return False
        cb.setText(text)
        return True
    except Exception as e:
        print(f"{_LOG} 复制剪贴板失败: {e}")
        return False


def _node_desc(node, node_id):
    """拼一个便于人肉查找的节点描述：<标签> (id:<id>) @ (x, y)。取不到的部分自动省略。"""
    label = ""
    try:
        d = node.getDefinition()
        if d is not None:
            label = d.getLabel() or d.getId() or ""
    except Exception:
        pass
    pos_str = _node_pos_str(node)
    head = f"{label} (id:{node_id})" if label else f"id:{node_id}"
    return f"{head} @ {pos_str}" if pos_str else head


def _node_pos_str(node):
    """节点在图里的坐标 (x, y)，取不到返回空串（不抛）。已在 SD13 验证可用。"""
    try:
        pos = node.getPosition()
    except Exception:
        return ""
    x = getattr(pos, "x", None)
    y = getattr(pos, "y", None)
    if x is None or y is None:
        try:
            x, y = pos[0], pos[1]
        except Exception:
            return ""
    try:
        return f"({x:.0f}, {y:.0f})"
    except Exception:
        return ""


def _isvalid_fn():
    """返回 shiboken 的 isValid(obj)（判活，过滤已删除的 C++ 对象）；拿不到返回 None。"""
    for modname in ("shiboken6", "shiboken2"):
        try:
            mod = __import__(modname, fromlist=["isValid"])
            if hasattr(mod, "isValid"):
                return mod.isValid
        except Exception:
            pass
    return None


def _graph_views(app):
    """枚举当前应用里「存活且可见」的 QGraphicsView。

    用 QApplication.allWidgets() + shiboken.isValid() 过滤已删除的 C++ 对象，
    避免 findChildren 返回 SD 已销毁的残留视图导致 'already deleted'。
    """
    if QtWidgets is None:
        return []
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        return []
    isvalid = _isvalid_fn()
    out = []
    try:
        widgets = list(qapp.allWidgets())
    except Exception as e:
        print(f"{_LOG} allWidgets 失败: {e}")
        return []
    for w in widgets:
        try:
            if isvalid is not None and not isvalid(w):
                continue
            if not isinstance(w, QtWidgets.QGraphicsView):
                continue
            if not w.isVisible():
                continue
            out.append(w)
        except Exception:
            pass
    return out


def _frame_in_view(view, scene, x, y):
    """把视图缩放并居中到节点位置 (x, y)，返回一句描述。

    优先用鼠标点位命中的节点图元精确框住（接近 F 键效果）；命中不到就用固定窗口。
    纯 UI，失败自动回退到只居中。
    """
    rect = None
    mode = "固定窗口"
    # 1) 尝试拿到该位置的节点图元，精确框选
    try:
        if scene is not None and QtCore is not None:
            pt = QtCore.QPointF(x, y)
            item = None
            try:
                item = scene.itemAt(pt, view.transform())
            except Exception:
                # 少数绑定的 itemAt 只接受一个参数
                try:
                    item = scene.itemAt(pt)
                except Exception:
                    item = None
            if item is not None:
                top = item
                try:
                    tl = item.topLevelItem()
                    if tl is not None:
                        top = tl
                except Exception:
                    pass
                br = top.sceneBoundingRect()
                if br is not None and br.width() > 1 and br.height() > 1:
                    m = max(br.width(), br.height()) * 0.05  # 几乎贴边框住节点，最大化放大
                    rect = br.adjusted(-m, -m, m, m)
                    mode = "节点图元"
    except Exception as e:
        print(f"{_LOG} [locate] 取节点图元失败: {e}")
    # 2) 没命中图元：用固定大小窗口（图坐标==场景坐标，已验证）
    if rect is None and QtCore is not None:
        S = 140.0
        rect = QtCore.QRectF(x - S / 2.0, y - S / 2.0, S, S)
    # 3) fitInView 缩放+居中；失败回退只居中
    try:
        view.fitInView(rect, QtCore.Qt.KeepAspectRatio)
    except Exception as e:
        print(f"{_LOG} [locate] fitInView 失败, 回退 centerOn: {e}")
        try:
            view.centerOn(x, y)
        except Exception:
            pass
        return "仅居中(缩放失败)"
    try:
        view.centerOn(x, y)
    except Exception:
        pass
    return f"缩放+居中({mode})"


def _try_center_on_node(app, node):
    """SD13 定位路径：用 node.getPosition() 在图视图 QGraphicsView 上 fitInView 缩放居中。

    不需要选中、也不用 F 键；纯 UI，不改数据，失败不抛。已在 SD13.0.0 验证：节点图坐标
    与 QGraphicsScene 坐标 1:1 对应。取到视图后立刻使用并再次判活（shiboken.isValid），
    规避 SD 图视图被销毁重建导致的 'already deleted'。
    """
    # 1) 节点图坐标
    try:
        pos = node.getPosition()
    except Exception as e:
        return False, f"getPosition 失败: {e}"
    x = getattr(pos, "x", None)
    y = getattr(pos, "y", None)
    if x is None or y is None:
        try:
            x, y = pos[0], pos[1]
        except Exception:
            return False, "节点位置无 x/y"
    x = float(x)
    y = float(y)

    isvalid = _isvalid_fn()
    views = _graph_views(app)
    if not views:
        return False, "未找到存活的 QGraphicsView"

    # 2) 取到即用：优先定位「场景含此点」的视图；否则记住第一个可见视图兜底
    fallback = None
    for v in views:
        try:
            if isvalid is not None and not isvalid(v):
                continue
            sc = v.scene()
            ibr = sc.itemsBoundingRect() if sc is not None else None
            inside = False
            try:
                inside = bool(ibr is not None and ibr.contains(x, y))
            except Exception:
                inside = False
            if fallback is None:
                fallback = v
            if inside:
                info = _frame_in_view(v, sc, x, y)
                return True, f"已定位到节点 ({x:.0f}, {y:.0f})【{info}】"
        except Exception:
            pass

    # 3) 没有场景命中：尽力定位第一个可见视图
    if fallback is not None:
        try:
            if isvalid is None or isvalid(fallback):
                info = _frame_in_view(fallback, fallback.scene(), x, y)
                return True, (f"已尝试定位到 ({x:.0f}, {y:.0f})（{info}，未精确命中场景，"
                              "若位置不对请反馈日志）")
        except Exception as e:
            return False, f"兜底 fitInView 失败: {e}"
    return False, "所有候选视图均已失效或不可用"



