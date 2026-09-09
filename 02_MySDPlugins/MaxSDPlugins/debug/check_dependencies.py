# -*- coding: utf-8 -*-
"""Publish Checker（发布检查）：发布 .sbsar 前，扫描当前图里可能在
publish/cook 时产生「警告」的节点 + package 依赖，列成清单，便于发布前自查。

菜单位置：`MaxSDPlugin/Debug/Publish Checker`。

检查的问题类型（对应 SD 发布 sbsar 时常见的告警）：
  1. 损坏的 Get 节点：节点参数被函数图驱动，但 Get 节点变量名为空
     （SD 日志：「Some Get nodes don't have a variable name」/「Empty variable」）。
  2. 缺失/外部依赖资源：bitmap / svg 节点引用了不存在的本地资源文件。
  3. 缺失依赖包：package 引用的其他 .sbs 找不到（复制别的图常带来）。
  4. 可清理节点：未连到任何 output，Clean graph(s) 会删除。
  5. 未连接的 output：标记为输出的节点没有输入连线，cook 出来会是空图。
  6. 悬挂节点：既不是 output、又没有任何下游连接的孤立节点。

可选「试发布」：把当前 package 导出成临时 .sbsar，验证能否成功发布；详细的逐节点
警告会打印在 SD 自带的日志面板里（C++ cooker 的日志无法在 Python 内完整截获）。

扫描逻辑与旧公开入口暂时保留，SD 专有 API 使用统一异常边界，
取不到时优雅返回，不让异常冒泡到 SD 主进程。
"""

import os
import tempfile

import sd  # SD 提供的 Python 包；只在 SD 进程内可用

from .. import sdcompat  # 跨版本 SD/Qt 接口兼容层（唯一真源）

# SD 专有类型：工作区 lint 找不到属正常，运行时在 SD 内可用
try:
    from sd.api.sdproperty import SDPropertyCategory
except sdcompat.SD_API_ERRORS:  # pragma: no cover
    SDPropertyCategory = None

try:
    from sd.api.sdvalueserializer import SDValueSerializer
except sdcompat.SD_API_ERRORS:  # pragma: no cover
    SDValueSerializer = None

# --- PySide 导入：SD 16.0.1 = PySide6；保留 PySide2 回退以兼容旧版 ---
try:
    from PySide6 import QtWidgets, QtCore
except sdcompat.SD_API_ERRORS:
    try:
        from PySide2 import QtWidgets, QtCore  # 旧版 SD 回退
    except sdcompat.SD_API_ERRORS as _e:
        QtWidgets = None
        QtCore = None
        print(f"[MaxSDPlugin/debug] PySide 导入失败，UI 不可用: {_e}")

_LOG = "[MaxSDPlugin/debug]"

# 模块级保存窗口引用，防止被 Python 垃圾回收导致窗口一闪而过
_dialog_ref = None


# --------------------------------------------------------------------------- #
# 数据层：获取当前图 + 扫描警告
# --------------------------------------------------------------------------- #
def get_current_graph(app=None):
    """返回当前在图视图中打开的 SDGraph；取不到返回 None。"""
    return sdcompat.get_current_graph(app)


def get_package(graph):
    """返回该图所属 package；取不到返回 None。"""
    try:
        return graph.getPackage() if graph else None
    except sdcompat.SD_API_ERRORS:
        return None


def _value_to_str(value):
    if value is None:
        return None
    try:
        if SDValueSerializer is not None:
            return SDValueSerializer.sToString(value)
        return str(value)
    except sdcompat.SD_API_ERRORS:
        return str(value)


def _strip_quotes(s):
    if isinstance(s, str) and len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _node_label(node):
    """节点显示名：标识符 + 定义标签，便于在图里定位。"""
    try:
        ident = node.getIdentifier() or ""
    except sdcompat.SD_API_ERRORS:
        ident = ""
    try:
        d = node.getDefinition()
        lbl = (d.getLabel() or d.getId()) if d else ""
    except sdcompat.SD_API_ERRORS:
        lbl = ""
    return f"{lbl} (id:{ident})" if ident else (lbl or "<未知节点>")


def _has_empty_get_var(func_graph):
    """函数图里是否存在「变量名为空」的 Get 节点（删除暴露参数后残留的损坏函数）。"""
    if func_graph is None or SDPropertyCategory is None:
        return False
    try:
        fnodes = func_graph.getNodes()
    except sdcompat.SD_API_ERRORS:
        return False
    for i in range(len(fnodes)):
        try:
            fnode = fnodes[i]
            d = fnode.getDefinition()
            did = (d.getId() or "") if d else ""
            if "get" not in did.lower():
                continue
            cval = fnode.getPropertyValueFromId("__constant__", SDPropertyCategory.Input)
        except sdcompat.SD_API_ERRORS:
            continue
        if cval is None or (_strip_quotes(_value_to_str(cval)) or "") == "":
            return True
    return False


# 告警类别（供 UI 筛选用）
CAT_BROKEN_FUNC = "损坏函数"
CAT_MISSING_RES = "缺失资源"
CAT_MISSING_DEP = "缺失依赖包"
CAT_UNUSED = "可清理(未使用)"
CAT_UNCONNECTED = "未连接输出"
CAT_DANGLING = "悬挂节点"
ALL_CATEGORIES = (CAT_BROKEN_FUNC, CAT_MISSING_RES, CAT_MISSING_DEP, CAT_UNUSED,
                  CAT_UNCONNECTED, CAT_DANGLING)

# Clean graph(s) 里固定保留的输入节点（同 SD 自带 graph_cleaner）
INPUT_NODES_COMP = (
    "sbs::compositing::input_color",
    "sbs::compositing::input_grayscale",
    "sbs::compositing::input_value",
)


def collect_unused_node_ids(graph):
    """复刻 SD「Clean graph(s)」的未使用节点判定：从所有 output 节点反向沿输入连线
    遍历，凡是没被任一 output 链路用到、且不是 input 节点的，即视为可清理。返回 id 集合。"""
    if graph is None or SDPropertyCategory is None:
        return set()
    all_ids, used, ignored = set(), set(), set()
    try:
        nodes = graph.getNodes()
    except sdcompat.SD_API_ERRORS:
        return set()
    for i in range(len(nodes)):
        try:
            node = nodes[i]
            all_ids.add(node.getIdentifier())
            d = node.getDefinition()
            if d and d.getId() in INPUT_NODES_COMP:
                ignored.add(node.getIdentifier())
        except sdcompat.SD_API_ERRORS:
            pass

    def _walk(node):
        try:
            nid = node.getIdentifier()
        except sdcompat.SD_API_ERRORS:
            return
        if nid in used:
            return
        used.add(nid)
        try:
            for p in node.getProperties(SDPropertyCategory.Input):
                if not p.isConnectable():
                    continue
                for c in node.getPropertyConnections(p):
                    _walk(c.getInputPropertyNode())
        except sdcompat.SD_API_ERRORS:
            pass

    try:
        for out in graph.getOutputNodes():
            _walk(out)
    except sdcompat.SD_API_ERRORS:
        pass
    return all_ids - used - ignored


def scan_missing_deps(graph):
    """检查 package 依赖：复制别的图过来时常带上原文件依赖（如 dobe_leather01.sbs），
    若该 .sbs 找不到，发布就会报「Cannot publish package, dependencies cannot be found」。
    返回 [(类别, 描述, 说明, ""), ...]。"""
    out = []
    pkg = get_package(graph)
    if pkg is None:
        return out
    try:
        deps = pkg.getDependencies()
    except sdcompat.SD_API_ERRORS:
        return out
    for i in range(len(deps)):
        try:
            dep = deps[i]
            fp = dep.getFilePath() if hasattr(dep, "getFilePath") else ""
            resolved = dep.getPackage() if hasattr(dep, "getPackage") else None
            if resolved is None and fp:
                exists = fp.startswith("sbs://") or fp.startswith("pkg://") or os.path.exists(fp)
                if not exists:
                    # 找出引用了缺失依赖的子图实例节点（res 为 None 的 sbscompgraph_instance）
                    culprits = _find_dep_culprit_nodes(graph)
                    if culprits:
                        for nid, label in culprits:
                            out.append((CAT_MISSING_DEP, label,
                                        f"引用缺失依赖包: {fp}，删掉本节点或重新定位", nid))
                    else:
                        out.append((CAT_MISSING_DEP, fp, "依赖包找不到，发布会失败；删掉引用它的节点或重新定位", ""))
        except sdcompat.SD_API_ERRORS:
            continue
    return out


def _find_dep_culprit_nodes(graph):
    """列出可能引用缺失依赖的节点：res 为 None 的子图实例 / bitmap / svg 节点。
    依赖丢失后这些节点的引用资源都会断成 None。返回 [(node_id, label), ...] 供 Goto。"""
    found = []
    try:
        nodes = graph.getNodes()
    except sdcompat.SD_API_ERRORS:
        return found
    for i in range(len(nodes)):
        try:
            node = nodes[i]
            d = node.getDefinition()
            did = (d.getId() or "").lower() if d else ""
            if ("instance" in did or "bitmap" in did or "svg" in did) \
                    and node.getReferencedResource() is None:
                found.append((node.getIdentifier() or "", _node_label(node)))
        except sdcompat.SD_API_ERRORS:
            continue
    return found


def scan_warnings(graph):
    """扫描一个图，返回告警列表：[(类别, 节点描述, 说明, 节点id), ...]。"""
    warnings = []
    if graph is None or SDPropertyCategory is None:
        return warnings
    try:
        nodes = graph.getNodes()
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 读取节点失败: {e}")
        return warnings

    output_ids = set()
    try:
        for i in range(len(graph.getOutputNodes())):
            output_ids.add(graph.getOutputNodes()[i].getIdentifier())
    except sdcompat.SD_API_ERRORS:
        pass

    unused_ids = collect_unused_node_ids(graph)

    for i in range(len(nodes)):
        try:
            node = nodes[i]
        except sdcompat.SD_API_ERRORS:
            continue
        label = _node_label(node)
        try:
            nid = node.getIdentifier() or ""
        except sdcompat.SD_API_ERRORS:
            nid = ""

        # 1. 损坏的 Get 节点（输入参数被空变量函数驱动）
        try:
            for p in node.getProperties(SDPropertyCategory.Input):
                if _has_empty_get_var(node.getPropertyGraph(p)):
                    warnings.append((CAT_BROKEN_FUNC, label, "Get 节点变量名为空，cook 时报 Empty variable", nid))
                    break
        except sdcompat.SD_API_ERRORS:
            pass

        # 2. 缺失/外部依赖资源（bitmap / svg）
        try:
            d = node.getDefinition()
            did = (d.getId() or "").lower() if d else ""
            if "bitmap" in did or "svg" in did:
                res = node.getReferencedResource()
                if res is None:
                    warnings.append((CAT_MISSING_RES, label, "未引用任何资源，发布后输出为空", nid))
                else:
                    path = res.getFilePath() if hasattr(res, "getFilePath") else ""
                    if path and not os.path.exists(path):
                        warnings.append((CAT_MISSING_RES, label, f"外部资源文件不存在: {path}", nid))
        except sdcompat.SD_API_ERRORS:
            pass

        # 3 & 4. output 未连接 / 悬挂节点
        try:
            conn_out = 0
            for p in node.getProperties(SDPropertyCategory.Output):
                conn_out += len(node.getPropertyConnections(p))
            is_output = node.getIdentifier() in output_ids
            if is_output:
                conn_in = sum(
                    len(node.getPropertyConnections(p))
                    for p in node.getProperties(SDPropertyCategory.Input)
                )
                if conn_in == 0:
                    warnings.append((CAT_UNCONNECTED, label, "输出节点没有输入连线", nid))
            elif conn_out == 0:
                warnings.append((CAT_DANGLING, label, "节点无任何下游连接，发布时被忽略", nid))
        except sdcompat.SD_API_ERRORS:
            pass

        # 5. Clean graph(s) 同款：未连到任何 output 的可清理节点
        if nid and nid in unused_ids:
            warnings.append((CAT_UNUSED, label, "未连到任何 output，Clean graph(s) 会删除", nid))

    # 6. package 缺失依赖（如复制别的图带来的源 .sbs 找不到）
    warnings.extend(scan_missing_deps(graph))

    return warnings


def goto_node(graph, node_id, app=None):
    """在图视图里定位/选中指定节点。返回 (ok, 信息)。

    跨版本逻辑统一收敛到 sdcompat.focus_node（多策略探测 + 优雅降级），
    这里只做转发，避免在功能模块里硬编码版本脆弱的接口。
    """
    return sdcompat.focus_node(graph, node_id, app)


def delete_nodes(graph, node_ids):
    """删除一组节点，包 UndoGroup（可 Ctrl+Z）。返回 (删除数, 信息)。"""
    if graph is None or not node_ids:
        return 0, "没有可删除的节点。"
    n = 0
    ctx = None
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        ctx = SDHistoryUtils.UndoGroup("Publish Checker 删除节点")
    except sdcompat.SD_API_ERRORS:
        ctx = None
    try:
        if ctx is not None:
            ctx.__enter__()
        for nid in node_ids:
            try:
                node = graph.getNodeFromId(nid)
                if node:
                    graph.deleteNode(node)
                    n += 1
            except sdcompat.SD_API_ERRORS as e:
                print(f"{_LOG} 删除节点 {nid} 失败: {e}")
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)
    return n, f"已删除 {n} 个节点。"


def clean_current_graph(graph):
    """清理当前图：删除与 Clean graph(s) 同款的未使用节点。返回 (删除数, 信息)。"""
    ids = list(collect_unused_node_ids(graph))
    if not ids:
        return 0, "没有可清理的未使用节点。"
    n, _ = delete_nodes(graph, ids)
    return n, f"已清理 {n} 个未使用节点。"


def test_publish(graph):
    """把当前 package 导出成临时 .sbsar，验证能否发布。返回 (ok, 信息)。"""
    pkg = get_package(graph)
    if pkg is None:
        return False, "未找到 package。"
    try:
        from sd.api.sbs.sdsbsarexporter import SDSBSARExporter
        exporter = SDSBSARExporter.sNew()
        out = os.path.join(tempfile.gettempdir(), "maxsd_check_dependencies.sbsar")
        exporter.exportPackageToSBSAR(pkg, out)
        return True, f"试发布成功，详细警告见 SD 日志面板。\n输出: {out}"
    except sdcompat.SD_API_ERRORS as e:
        return False, f"试发布失败: {e}\n详细警告见 SD 日志面板。"


# --------------------------------------------------------------------------- #
# UI 层
# --------------------------------------------------------------------------- #
if QtWidgets is not None:

    class CheckDependenciesDialog(QtWidgets.QDialog):
        """发布前警告自查对话框：列出当前图里可能产生 cook 警告的节点 + 缺失依赖。"""

        _ID_ROLE = (QtCore.Qt.UserRole if QtCore is not None else 32)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Publish Checker - MaxSDPlugin")
            self.resize(640, 480)
            self._all_warns = []  # 缓存最近一次扫描结果，筛选时无需重扫
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            self._info = QtWidgets.QLabel(self)
            self._info.setWordWrap(True)
            layout.addWidget(self._info)

            # 类别筛选：每类一个复选框，勾掉即从列表隐藏
            filt_row = QtWidgets.QHBoxLayout()
            filt_row.addWidget(QtWidgets.QLabel("筛选：", self))
            self._cat_boxes = {}
            for cat in ALL_CATEGORIES:
                cb = QtWidgets.QCheckBox(cat, self)
                cb.setChecked(True)
                cb.stateChanged.connect(self._apply_filter)
                self._cat_boxes[cat] = cb
                filt_row.addWidget(cb)
            filt_row.addStretch(1)
            layout.addLayout(filt_row)

            self._table = QtWidgets.QTreeWidget(self)
            self._table.setHeaderLabels(["选择", "类别", "节点", "说明"])
            self._table.setColumnWidth(0, 44)
            self._table.setColumnWidth(1, 100)
            self._table.setColumnWidth(2, 240)
            self._table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self._table.customContextMenuRequested.connect(self._show_context_menu)
            self._table.itemDoubleClicked.connect(lambda *_: self._goto_selected())
            layout.addWidget(self._table, 1)

            row = QtWidgets.QHBoxLayout()
            self._btn_refresh = QtWidgets.QPushButton("重新扫描", self)
            self._btn_all = QtWidgets.QPushButton("全选", self)
            self._btn_none = QtWidgets.QPushButton("全不选", self)
            self._btn_delete = QtWidgets.QPushButton("删除选中节点", self)
            self._btn_clean = QtWidgets.QPushButton("清理当前图形", self)
            self._btn_publish = QtWidgets.QPushButton("试发布到临时 .sbsar", self)
            self._btn_close = QtWidgets.QPushButton("关闭", self)
            self._btn_refresh.clicked.connect(lambda: self._refresh(notify=True))
            self._btn_all.clicked.connect(lambda: self._set_all_checked(True))
            self._btn_none.clicked.connect(lambda: self._set_all_checked(False))
            self._btn_delete.clicked.connect(self._delete_checked)
            self._btn_clean.clicked.connect(self._clean_graph)
            self._btn_publish.clicked.connect(self._test_publish)
            self._btn_close.clicked.connect(self.close)
            row.addWidget(self._btn_refresh)
            row.addWidget(self._btn_all)
            row.addWidget(self._btn_none)
            row.addWidget(self._btn_delete)
            row.addWidget(self._btn_clean)
            row.addWidget(self._btn_publish)
            row.addStretch(1)
            row.addWidget(self._btn_close)
            layout.addLayout(row)

        def _refresh(self, notify=False):
            graph = get_current_graph()
            if graph is None:
                self._all_warns = []
                self._table.clear()
                self._info.setText("未找到当前图。请在 SD 中打开一个图后再点“重新扫描”。")
                return
            self._all_warns = scan_warnings(graph)
            self._apply_filter()
            if notify:
                QtWidgets.QMessageBox.information(
                    self, "MaxSDPlugin · Publish Checker",
                    f"扫描完成，发现 {len(self._all_warns)} 处可能的发布警告。")

        def _apply_filter(self):
            """按勾选的类别筛选缓存结果填表，不重新扫描。"""
            self._table.clear()
            active = {c for c, cb in self._cat_boxes.items() if cb.isChecked()}
            shown = 0
            for cat, label, desc, nid in self._all_warns:
                if cat not in active:
                    continue
                item = QtWidgets.QTreeWidgetItem(self._table, ["", cat, label, desc])
                item.setData(0, self._ID_ROLE, nid)
                if nid:
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                    item.setCheckState(0, QtCore.Qt.Unchecked)
                shown += 1
            total = len(self._all_warns)
            if total == 0:
                self._info.setText("扫描完成：未发现明显的发布警告。仍建议「试发布」核对 SD 日志。")
            else:
                self._info.setText(f"扫描完成：发现 {total} 处可能在发布 sbsar 时产生警告；当前显示 {shown} 处（右键/双击可 Goto 定位）。")

        def _show_context_menu(self, pos):
            item = self._table.itemAt(pos)
            if item is None:
                return
            self._table.setCurrentItem(item)
            menu = QtWidgets.QMenu(self)
            act = menu.addAction("Goto（在图中定位）")
            act.triggered.connect(self._goto_selected)
            act_del = menu.addAction("删除当前节点")
            act_del.triggered.connect(self._delete_current)
            sdcompat.exec_widget(menu, self._table.viewport().mapToGlobal(pos))

        def _set_all_checked(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for i in range(self._table.topLevelItemCount()):
                it = self._table.topLevelItem(i)
                if it.flags() & QtCore.Qt.ItemIsUserCheckable:
                    it.setCheckState(0, state)

        def _delete_current(self):
            item = self._table.currentItem()
            if item is None:
                return
            nid = item.data(0, self._ID_ROLE)
            if nid:
                self._do_delete([nid])

        def _delete_checked(self):
            ids = []
            for i in range(self._table.topLevelItemCount()):
                it = self._table.topLevelItem(i)
                if (it.flags() & QtCore.Qt.ItemIsUserCheckable) and it.checkState(0) == QtCore.Qt.Checked:
                    nid = it.data(0, self._ID_ROLE)
                    if nid:
                        ids.append(nid)
            if not ids:
                QtWidgets.QMessageBox.information(self, "MaxSDPlugin", "请先勾选要删除的节点。")
                return
            self._do_delete(ids)

        def _do_delete(self, ids):
            answer = QtWidgets.QMessageBox.question(
                self, "删除节点确认", f"删除 {len(set(ids))} 个节点？可用 Ctrl+Z 撤销。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
            graph = get_current_graph()
            if graph is None:
                QtWidgets.QMessageBox.warning(self, "MaxSDPlugin", "未找到当前图。")
                return
            n, msg = delete_nodes(graph, ids)
            self._refresh()
            QtWidgets.QMessageBox.information(self, "MaxSDPlugin", msg)

        def _clean_graph(self):
            answer = QtWidgets.QMessageBox.question(
                self, "清理当前 Graph", "删除当前 Graph 中未连接到输出的节点？可用 Ctrl+Z 撤销。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
            graph = get_current_graph()
            if graph is None:
                QtWidgets.QMessageBox.warning(self, "MaxSDPlugin", "未找到当前图。")
                return
            n, msg = clean_current_graph(graph)
            self._refresh()
            QtWidgets.QMessageBox.information(self, "MaxSDPlugin · Clean graph(s)", msg)

        def _goto_selected(self):
            item = self._table.currentItem()
            if item is None:
                return
            graph = get_current_graph()
            if graph is None:
                QtWidgets.QMessageBox.warning(self, "MaxSDPlugin", "未找到当前图。")
                return
            ok, msg = goto_node(graph, item.data(0, self._ID_ROLE))
            if not ok:
                QtWidgets.QMessageBox.warning(self, "MaxSDPlugin", msg)

        def _test_publish(self):
            graph = get_current_graph()
            if graph is None:
                QtWidgets.QMessageBox.warning(self, "MaxSDPlugin", "未找到当前图。")
                return
            ok, msg = test_publish(graph)
            box = QtWidgets.QMessageBox.information if ok else QtWidgets.QMessageBox.warning
            box(self, "MaxSDPlugin · 试发布", msg)


def show_window(main_win=None):
    """公开入口：统一单实例、关闭释放；兼容旧调用签名。"""
    from ..shared.lifecycle import show_dialog
    from .. import sdcompat
    if QtWidgets is None:
        print('[MaxSDPlugin] Qt 不可用，无法显示窗口。')
        return None
    try:
        return show_dialog(__name__, lambda: CheckDependenciesDialog(parent=main_win or sdcompat.get_main_window()), globals())
    except sdcompat.SD_API_ERRORS as error:
        QtWidgets.QMessageBox.critical(main_win, "MaxSDPlugin", sdcompat.error_text(error))
        return None
