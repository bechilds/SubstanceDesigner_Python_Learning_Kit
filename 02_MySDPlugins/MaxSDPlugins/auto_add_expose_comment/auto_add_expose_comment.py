# -*- coding: utf-8 -*-
"""给当前 SBS 文件中使用曝光参数的节点自动添加描述 Comment。"""

from .. import sdcompat

QtWidgets = sdcompat.QtWidgets
QtCore = sdcompat.QtCore

_LOG = "[MaxSDPlugin/AutoAddExposeCommentToNode]"
_dialog_ref = None
_COMMENT_OFFSET_Y = 75.0

try:
    from sd.api.sdbasetypes import float2
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment
    from sd.api.sdproperty import SDPropertyCategory
except Exception:  # pragma: no cover - 仅普通 Python 环境
    float2 = None
    SDGraphObjectComment = None
    SDPropertyCategory = None

try:
    from sd.api.apiexception import APIException
    _SD_ERRORS = (Exception, APIException)
except Exception:  # pragma: no cover - 仅普通 Python 环境
    _SD_ERRORS = (Exception,)


def _as_list(value):
    """把 SDArray 等可索引对象安全转换为 Python list。"""
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


def _value_to_text(value):
    """读取 Get 节点的变量名，并去掉序列化值外层引号。"""
    if value is None:
        return ""
    try:
        getter = getattr(value, "get", None)
        if callable(getter):
            text = str(getter())
            if text:
                return text
    except Exception:
        pass
    try:
        from sd.api.sdvalueserializer import SDValueSerializer
        text = SDValueSerializer.sToString(value)
    except Exception:
        text = str(value)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _is_get_node(node):
    """保守识别函数图中的 Get Variable 节点。"""
    try:
        definition = node.getDefinition()
        definition_id = str(definition.getId() or "") if definition else ""
        label = str(definition.getLabel() or "") if definition else ""
        return "get" in definition_id.lower() or label.lower().startswith("get")
    except Exception:
        return False


def _function_references(function_graph):
    """读取属性函数图中的 Get Variable，并保留诊断所需的原始信息。"""
    references = []
    try:
        function_nodes = _as_list(function_graph.getNodes())
    except Exception as error:
        return references, [f"读取函数节点失败: {error}"]
    diagnostics = []
    for function_node in function_nodes:
        try:
            definition = function_node.getDefinition()
            definition_id = str(definition.getId() or "") if definition else ""
            definition_label = str(definition.getLabel() or "") if definition else ""
        except Exception as error:
            diagnostics.append(f"读取函数节点定义失败: {error}")
            continue
        if not _is_get_node(function_node):
            continue
        try:
            value = function_node.getPropertyValueFromId(
                "__constant__", SDPropertyCategory.Input)
            parameter_id = _value_to_text(value).strip()
            if parameter_id:
                references.append({
                    "parameter_id": parameter_id,
                    "definition_id": definition_id,
                    "definition_label": definition_label,
                })
            else:
                diagnostics.append(
                    f"Get Variable {definition_id or definition_label or '<未知定义>'} 的 __constant__ 为空")
        except Exception as error:
            diagnostics.append(
                f"读取 Get Variable {definition_id or definition_label or '<未知定义>'} 失败: {error}")
    return references, diagnostics


def _referenced_parameter_ids(function_graph):
    """兼容旧调用：返回一个属性函数图中 Get 节点引用的变量 id。"""
    references, _ = _function_references(function_graph)
    return {item["parameter_id"] for item in references}


def _parameter_group(graph, prop):
    """读取曝光参数的 Group 注解；未分组或读取失败时返回空串。"""
    try:
        value = graph.getPropertyAnnotationValueFromId(prop, "group")
        return _value_to_text(value).strip()
    except _SD_ERRORS:
        return ""


def _parameter_comment_name(parameter):
    """按 ``分组|-参数`` 格式生成单个曝光参数的 Comment 行。"""
    label = parameter["label"]
    group = parameter.get("group", "")
    return f"{group}|-{label}" if group else f"-{label}"


def _graph_parameters(graph):
    """返回当前 Graph 的非内置输入参数映射及读取错误。"""
    names = {}
    try:
        properties = _as_list(graph.getProperties(SDPropertyCategory.Input))
    except Exception as error:
        return names, [f"读取 Graph Input Properties 失败: {error}"]
    diagnostics = []
    for prop in properties:
        try:
            parameter_id = str(prop.getId() or "")
            if not parameter_id or parameter_id.startswith("$"):
                continue
            names[parameter_id] = {
                "id": parameter_id,
                "label": str(prop.getLabel() or parameter_id),
                "group": _parameter_group(graph, prop),
            }
        except Exception as error:
            diagnostics.append(f"读取一个 Graph Input Property 失败: {error}")
    return names, diagnostics


def _graph_parameter_names(graph):
    """兼容旧调用：返回 Graph 参数 id -> Label。"""
    parameters, _ = _graph_parameters(graph)
    return {parameter_id: item["label"] for parameter_id, item in parameters.items()}


def collect_node_exposed_parameters(graph):
    """收集 Graph 中各节点实际引用的曝光参数名称。

    返回 ``[(node, [name, ...]), ...]``，参数名称按首次发现顺序排列。
    """
    parameters, _ = _graph_parameters(graph)
    if not parameters:
        return []
    result = []
    try:
        nodes = _as_list(graph.getNodes())
    except Exception as error:
        print(f"{_LOG} 读取节点失败: {error}")
        return result
    for node in nodes:
        referenced_ids = set()
        try:
            properties = _as_list(node.getProperties(SDPropertyCategory.Input))
        except Exception:
            continue
        for prop in properties:
            try:
                function_graph = node.getPropertyGraph(prop)
            except Exception:
                function_graph = None
            if function_graph is not None:
                referenced_ids.update(_referenced_parameter_ids(function_graph))
        names = [_parameter_comment_name(parameter)
                 for parameter_id, parameter in parameters.items()
             if parameter_id in referenced_ids]
        if names:
            result.append((node, names))
    return result


def collect_package_graphs(current_graph):
    """返回当前 SBS Package 内所有支持节点和 Graph Object 的 Graph。"""
    if current_graph is None:
        return []
    graphs = [current_graph]
    try:
        package = current_graph.getPackage()
        resources = _as_list(package.getChildrenResources(True)) if package else []
    except Exception as error:
        print(f"{_LOG} 读取当前文件资源失败，仅处理当前 Graph: {error}")
        return graphs
    for resource in resources:
        if not hasattr(resource, "getNodes") or not hasattr(resource, "getGraphObjects"):
            continue
        try:
            if resource.getUrl() == current_graph.getUrl():
                continue
        except Exception:
            if resource is current_graph:
                continue
        graphs.append(resource)
    return graphs


def _graph_name(graph):
    for getter_name in ("getIdentifier", "getUrl"):
        try:
            value = getattr(graph, getter_name)()
            if value:
                return str(value)
        except Exception:
            pass
    return "<未知 Graph>"


def _node_name(node):
    try:
        definition = node.getDefinition()
        label = str(definition.getLabel() or definition.getId() or "") if definition else ""
    except Exception:
        label = ""
    try:
        node_id = str(node.getIdentifier() or "")
    except Exception:
        node_id = ""
    return node_id, label or node_id or "<未知节点>"


def _is_comment(graph_object):
    try:
        if SDGraphObjectComment is not None and isinstance(graph_object, SDGraphObjectComment):
            return True
        return "GraphObjectComment" in str(graph_object.getClassName() or "")
    except Exception:
        return False


def _find_node_comment(graph, node):
    """查找绑定到指定节点的已有 Comment。"""
    try:
        graph_objects = _as_list(graph.getGraphObjects())
    except Exception:
        return None
    for graph_object in graph_objects:
        if not _is_comment(graph_object):
            continue
        try:
            parent = graph_object.getParent()
            if parent is node:
                return graph_object
            if parent and parent.getIdentifier() == node.getIdentifier():
                return graph_object
        except Exception:
            continue
    return None


def _comment_text(parameters):
    return "Exposed Parameters:\n" + "\n".join(
        _parameter_comment_name(parameter) for parameter in parameters)


def scan_package(current_graph):
    """只读扫描当前 Package，返回待确认计划、逐层统计和诊断信息。

    本函数不创建 Comment、不修改描述和位置，也不打开 Undo Group。
    """
    stats = {
        "graphs": 0,
        "graph_parameters": 0,
        "nodes": 0,
        "node_properties": 0,
        "property_graphs": 0,
        "function_references": 0,
        "matched_references": 0,
        "matched_nodes": 0,
    }
    result = {"plans": [], "diagnostics": [], "stats": stats}
    if current_graph is None or SDPropertyCategory is None:
        result["diagnostics"].append("没有可扫描的当前 Graph，或 SDPropertyCategory API 不可用。")
        return result

    graphs = collect_package_graphs(current_graph)
    stats["graphs"] = len(graphs)
    for graph in graphs:
        graph_name = _graph_name(graph)
        parameters, graph_diagnostics = _graph_parameters(graph)
        stats["graph_parameters"] += len(parameters)
        result["diagnostics"].extend(
            f"[{graph_name}] {message}" for message in graph_diagnostics)
        try:
            nodes = _as_list(graph.getNodes())
        except Exception as error:
            result["diagnostics"].append(f"[{graph_name}] 读取节点失败: {error}")
            continue
        stats["nodes"] += len(nodes)

        for node in nodes:
            node_id, node_label = _node_name(node)
            matched = {}
            matched_properties = {}
            raw_get_nodes = []
            try:
                properties = _as_list(node.getProperties(SDPropertyCategory.Input))
            except Exception as error:
                result["diagnostics"].append(
                    f"[{graph_name}/{node_label}] 读取 Input Properties 失败: {error}")
                continue
            stats["node_properties"] += len(properties)
            for prop in properties:
                try:
                    property_id = str(prop.getId() or "")
                    property_label = str(prop.getLabel() or property_id)
                    function_graph = node.getPropertyGraph(prop)
                except Exception as error:
                    result["diagnostics"].append(
                        f"[{graph_name}/{node_label}] 读取节点属性函数失败: {error}")
                    continue
                if function_graph is None:
                    continue
                stats["property_graphs"] += 1
                references, function_diagnostics = _function_references(function_graph)
                stats["function_references"] += len(references)
                result["diagnostics"].extend(
                    f"[{graph_name}/{node_label}/{property_id}] {message}"
                    for message in function_diagnostics)
                for reference in references:
                    parameter_id = reference["parameter_id"]
                    raw_get_nodes.append(
                        f"{reference['definition_id'] or reference['definition_label']} -> {parameter_id}")
                    if parameter_id not in parameters:
                        result["diagnostics"].append(
                            f"[{graph_name}/{node_label}/{property_id}] Get Variable '{parameter_id}' "
                            "未匹配到 Graph Input Parameter")
                        continue
                    matched[parameter_id] = parameters[parameter_id]
                    matched_properties[property_id] = property_label
                    stats["matched_references"] += 1
            if not matched:
                continue

            parameter_items = list(matched.values())
            comment = _find_node_comment(graph, node)
            try:
                existing_text = str(comment.getDescription() or "") if comment else ""
            except Exception as error:
                existing_text = ""
                result["diagnostics"].append(
                    f"[{graph_name}/{node_label}] 读取已有 Comment 失败: {error}")
            try:
                position = node.getPosition()
                target_position = (float(position.x), float(position.y) + _COMMENT_OFFSET_Y)
            except Exception as error:
                target_position = None
                result["diagnostics"].append(
                    f"[{graph_name}/{node_label}] 读取节点位置失败: {error}")
            result["plans"].append({
                "graph": graph,
                "graph_name": graph_name,
                "node": node,
                "node_id": node_id,
                "node_label": node_label,
                "property_ids": list(matched_properties),
                "property_labels": list(matched_properties.values()),
                "parameters": parameter_items,
                "raw_get_nodes": raw_get_nodes,
                "existing_comment": comment,
                "existing_text": existing_text,
                "target_position": target_position,
                "generated_text": _comment_text(parameter_items),
            })
            stats["matched_nodes"] += 1
    return result


def _set_comment_position(comment, node):
    """设置绑定到节点的 Comment 相对位置。

    `sNewAsChild(node)` 创建的是节点子对象，坐标以父节点为原点；这里不能再次写入
    node.getPosition() 的 Graph 绝对坐标，否则父节点坐标会被重复叠加而严重错位。
    """
    comment_position = float2()
    comment_position.x = 0.0
    comment_position.y = _COMMENT_OFFSET_Y
    comment.setPosition(comment_position)


def apply_comment_plans(plans, append_existing=True):
    """应用用户确认的扫描计划；本函数不再重新扫描 Graph。"""
    result = {"selected": len(plans), "created": 0, "updated": 0, "failures": []}
    if SDGraphObjectComment is None or float2 is None or SDPropertyCategory is None:
        result["failures"].append("当前 Designer 未提供 Comment 图对象 API。")
        return result
    history = None
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        history = SDHistoryUtils.UndoGroup("自动添加曝光参数描述")
    except Exception:
        pass
    try:
        if history is not None:
            history.__enter__()
        for plan in plans:
            node = plan["node"]
            try:
                comment = plan.get("existing_comment")
                text = plan["generated_text"]
                if comment is None:
                    comment = SDGraphObjectComment.sNewAsChild(node)
                    result["created"] += 1
                else:
                    if append_existing:
                        old_text = str(comment.getDescription() or "").rstrip()
                        text = f"{old_text}\n\n{text}" if old_text else text
                    result["updated"] += 1
                comment.setDescription(text)
                _set_comment_position(comment, node)
            except Exception as error:
                result["failures"].append(f"{plan.get('node_id') or '<未知节点>'}: {error}")
    finally:
        if history is not None:
            history.__exit__(None, None, None)
    return result


def apply_comments(current_graph, append_existing=True):
    """兼容旧入口：扫描后应用全部计划。新 UI 不调用此函数。"""
    scan_result = scan_package(current_graph)
    return apply_comment_plans(scan_result["plans"], append_existing)


if QtWidgets is not None:

    class AutoAddExposeCommentDialog(QtWidgets.QDialog):
        """先只读扫描并展示计划，用户确认后再写入 Comment。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("AutoAddExposeCommentToNode")
            self.resize(1100, 720)
            self._plans = []
            self._scan_result = None
            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(QtWidgets.QLabel(
                "第一步仅扫描并展示拟写内容，不会修改 Graph。勾选确认后，第二步才会创建或更新 Comment。",
                self))

            mode_group = QtWidgets.QGroupBox("已有 Comment 的处理方式", self)
            mode_layout = QtWidgets.QHBoxLayout(mode_group)
            self._append_radio = QtWidgets.QRadioButton("追加曝光参数名称", self)
            self._overwrite_radio = QtWidgets.QRadioButton("覆盖原 Comment 内容", self)
            self._append_radio.setChecked(True)
            self._append_radio.toggled.connect(self._refresh_plan_display)
            mode_layout.addWidget(self._append_radio)
            mode_layout.addWidget(self._overwrite_radio)
            mode_layout.addStretch(1)
            layout.addWidget(mode_group)

            self._summary = QtWidgets.QLabel("尚未扫描。", self)
            self._summary.setWordWrap(True)
            layout.addWidget(self._summary)

            search_layout = QtWidgets.QHBoxLayout()
            search_layout.addWidget(QtWidgets.QLabel("搜索名称或 ID", self))
            self._search_edit = QtWidgets.QLineEdit(self)
            self._search_edit.setPlaceholderText(
                "节点名称 / 节点 ID / 节点属性 / 曝光参数 ID / 分组 / 显示名称")
            self._search_edit.setClearButtonEnabled(True)
            self._search_edit.textChanged.connect(self._filter_plans)
            self._search_edit.returnPressed.connect(self._select_first_visible_plan)
            self._search_count = QtWidgets.QLabel("0 / 0", self)
            search_layout.addWidget(self._search_edit, 1)
            search_layout.addWidget(self._search_count)
            layout.addLayout(search_layout)

            self._table = QtWidgets.QTableWidget(0, 9, self)
            self._table.setHorizontalHeaderLabels([
                "选择", "Graph", "节点", "节点属性", "曝光参数 ID",
                "分组|显示名称", "已有 Comment", "计划操作", "目标位置",
            ])
            self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self._table.itemSelectionChanged.connect(self._show_selected_plan)
            self._table.itemDoubleClicked.connect(lambda _item: self._locate_selected_node())
            self._table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self._table, 1)

            details = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
            preview_group = QtWidgets.QGroupBox("选中项将填入的最终内容", self)
            preview_layout = QtWidgets.QVBoxLayout(preview_group)
            self._preview = QtWidgets.QPlainTextEdit(self)
            self._preview.setReadOnly(True)
            preview_layout.addWidget(self._preview)
            details.addWidget(preview_group)

            diagnostics_group = QtWidgets.QGroupBox("扫描诊断", self)
            diagnostics_layout = QtWidgets.QVBoxLayout(diagnostics_group)
            self._diagnostics = QtWidgets.QPlainTextEdit(self)
            self._diagnostics.setReadOnly(True)
            diagnostics_layout.addWidget(self._diagnostics)
            details.addWidget(diagnostics_group)
            details.setSizes([520, 520])
            layout.addWidget(details, 1)

            buttons = QtWidgets.QHBoxLayout()
            scan_button = QtWidgets.QPushButton("扫描预览", self)
            select_all_button = QtWidgets.QPushButton("全选", self)
            select_none_button = QtWidgets.QPushButton("全不选", self)
            self._locate_button = QtWidgets.QPushButton("查找节点", self)
            self._apply_button = QtWidgets.QPushButton("应用选中项", self)
            close_button = QtWidgets.QPushButton("关闭", self)
            self._locate_button.setEnabled(False)
            self._apply_button.setEnabled(False)
            scan_button.clicked.connect(self._scan)
            select_all_button.clicked.connect(lambda: self._set_all_checked(True))
            select_none_button.clicked.connect(lambda: self._set_all_checked(False))
            self._locate_button.clicked.connect(self._locate_selected_node)
            self._apply_button.clicked.connect(self._apply_selected)
            close_button.clicked.connect(self.reject)
            buttons.addWidget(scan_button)
            buttons.addWidget(select_all_button)
            buttons.addWidget(select_none_button)
            buttons.addWidget(self._locate_button)
            buttons.addStretch(1)
            buttons.addWidget(self._apply_button)
            buttons.addWidget(close_button)
            layout.addLayout(buttons)

        def _final_text(self, plan):
            generated_text = plan["generated_text"]
            if not self._append_radio.isChecked() or not plan["existing_text"].strip():
                return generated_text
            return f"{plan['existing_text'].rstrip()}\n\n{generated_text}"

        def _plan_action(self, plan):
            if plan["existing_comment"] is None:
                return "新建"
            return "追加" if self._append_radio.isChecked() else "覆盖"

        def _scan(self):
            current_graph = sdcompat.get_current_graph()
            if current_graph is None:
                QtWidgets.QMessageBox.warning(self, self.windowTitle(), "请先打开一个 SBS Graph。")
                return
            self._scan_result = scan_package(current_graph)
            self._plans = self._scan_result["plans"]
            self._populate_table()
            stats = self._scan_result["stats"]
            self._summary.setText(
                f"Graph {stats['graphs']} 个；Graph 曝光参数 {stats['graph_parameters']} 个；"
                f"节点 {stats['nodes']} 个；节点属性 {stats['node_properties']} 个；"
                f"Property Graph {stats['property_graphs']} 个；Get Variable {stats['function_references']} 个；"
                f"匹配引用 {stats['matched_references']} 个；待确认节点 {stats['matched_nodes']} 个。")
            diagnostics = self._scan_result["diagnostics"]
            if not diagnostics:
                diagnostics = ["扫描完成，没有捕获到 API 错误或未匹配的 Get Variable。"]
            if not self._plans:
                diagnostics.append(
                    "没有生成计划项。请根据上方统计判断中断位置：曝光参数、Property Graph、"
                    "Get Variable 或匹配引用中的第一个零值就是优先排查点。")
            self._diagnostics.setPlainText("\n".join(diagnostics))
            self._apply_button.setEnabled(bool(self._plans))
            self._show_selected_plan()

        def _populate_table(self):
            self._table.setRowCount(len(self._plans))
            for row, plan in enumerate(self._plans):
                check_item = QtWidgets.QTableWidgetItem()
                check_item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
                check_item.setCheckState(QtCore.Qt.Checked)
                check_item.setData(QtCore.Qt.UserRole, row)
                self._table.setItem(row, 0, check_item)
                parameter_ids = ", ".join(item["id"] for item in plan["parameters"])
                parameter_labels = ", ".join(
                    f"{item['group']}|{item['label']}" if item["group"] else item["label"]
                    for item in plan["parameters"])
                target_position = plan["target_position"]
                position_text = (
                    f"({target_position[0]:.0f}, {target_position[1]:.0f})"
                    if target_position else "读取失败")
                values = (
                    plan["graph_name"],
                    f"{plan['node_label']} ({plan['node_id']})" if plan["node_id"] else plan["node_label"],
                    ", ".join(plan["property_labels"]),
                    parameter_ids,
                    parameter_labels,
                    "有" if plan["existing_comment"] is not None else "无",
                    self._plan_action(plan),
                    position_text,
                )
                for column, value in enumerate(values, 1):
                    self._table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            self._table.resizeColumnsToContents()
            self._filter_plans()
            if self._plans:
                self._select_first_visible_plan()
            else:
                self._preview.clear()

        def _plan_search_text(self, plan):
            values = [
                plan.get("graph_name", ""),
                plan.get("node_id", ""),
                plan.get("node_label", ""),
            ]
            values.extend(plan.get("property_ids", []))
            values.extend(plan.get("property_labels", []))
            for parameter in plan.get("parameters", []):
                values.extend((
                    parameter.get("id", ""),
                    parameter.get("group", ""),
                    parameter.get("label", ""),
                ))
            return " ".join(str(value) for value in values).lower()

        def _filter_plans(self):
            if not hasattr(self, "_table"):
                return
            keywords = [word.lower() for word in self._search_edit.text().split() if word]
            visible_rows = []
            for row, plan in enumerate(self._plans):
                search_text = self._plan_search_text(plan)
                visible = all(keyword in search_text for keyword in keywords)
                self._table.setRowHidden(row, not visible)
                if visible:
                    visible_rows.append(row)
            self._search_count.setText(f"{len(visible_rows)} / {len(self._plans)}")
            current_row = self._table.currentRow()
            if current_row < 0 or self._table.isRowHidden(current_row):
                if visible_rows:
                    self._table.selectRow(visible_rows[0])
                else:
                    self._table.clearSelection()
                    self._preview.clear()
                    self._locate_button.setEnabled(False)

        def _select_first_visible_plan(self):
            for row in range(self._table.rowCount()):
                if not self._table.isRowHidden(row):
                    self._table.selectRow(row)
                    self._table.scrollToItem(self._table.item(row, 1))
                    return

        def _refresh_plan_display(self):
            for row, plan in enumerate(self._plans):
                item = self._table.item(row, 7)
                if item is not None:
                    item.setText(self._plan_action(plan))
            self._show_selected_plan()

        def _show_selected_plan(self):
            row = self._table.currentRow()
            if row < 0 or row >= len(self._plans):
                self._preview.clear()
                self._locate_button.setEnabled(False)
                return
            self._locate_button.setEnabled(bool(self._plans[row].get("node_id")))
            plan = self._plans[row]
            raw_get_nodes = "\n".join(plan["raw_get_nodes"]) or "<无>"
            preview = (
                f"Graph: {plan['graph_name']}\n"
                f"节点: {plan['node_label']} ({plan['node_id']})\n"
                f"节点属性: {', '.join(plan['property_labels'])}\n"
                f"Get Variable: {raw_get_nodes}\n"
                f"计划操作: {self._plan_action(plan)}\n\n"
                f"{self._final_text(plan)}")
            self._preview.setPlainText(preview)

        def _locate_selected_node(self):
            row = self._table.currentRow()
            if row < 0 or row >= len(self._plans):
                QtWidgets.QMessageBox.information(self, self.windowTitle(), "请先选择一个扫描结果。")
                return
            plan = self._plans[row]
            node_id = plan.get("node_id")
            graph = plan.get("graph")
            if not node_id or graph is None:
                QtWidgets.QMessageBox.information(self, self.windowTitle(), "该扫描结果没有可定位的节点。")
                return
            ok, message = sdcompat.focus_node(graph, node_id)
            if message:
                method = QtWidgets.QMessageBox.information if ok else QtWidgets.QMessageBox.warning
                method(self, "查找节点", message)

        def _set_all_checked(self, checked):
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 0)
                if item is not None:
                    item.setCheckState(state)

        def _selected_plans(self):
            selected = []
            for row, plan in enumerate(self._plans):
                item = self._table.item(row, 0)
                if item is not None and item.checkState() == QtCore.Qt.Checked:
                    selected.append(plan)
            return selected

        def _apply_selected(self):
            plans = self._selected_plans()
            if not plans:
                QtWidgets.QMessageBox.information(self, self.windowTitle(), "请先勾选至少一个计划项。")
                return
            reply = QtWidgets.QMessageBox.question(
                self,
                "确认修改 Graph",
                f"即将对 {len(plans)} 个节点创建或更新 Comment。\n"
                "本操作会修改当前 SBS 文件，可在 SD 中按 Ctrl+Z 一次撤销。\n\n继续吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            if reply != QtWidgets.QMessageBox.Yes:
                return
            result = apply_comment_plans(plans, self._append_radio.isChecked())
            message = (
                f"已应用 {result['selected']} 个确认项。\n"
                f"新建 Comment：{result['created']} 个；更新：{result['updated']} 个。\n\n"
                "可在 Substance Designer 中按 Ctrl+Z 一次撤销。")
            if result["failures"]:
                message += "\n\n失败：\n" + "\n".join(result["failures"][:10])
            method = QtWidgets.QMessageBox.warning if result["failures"] else QtWidgets.QMessageBox.information
            method(self, self.windowTitle(), message)
            if not result["failures"]:
                self._scan()


def show_window(main_win=None):
    """菜单入口：显示覆盖/追加选择窗口。"""
    global _dialog_ref
    if QtWidgets is None:
        print(f"{_LOG} PySide 不可用，无法打开窗口。")
        return
    try:
        _dialog_ref = AutoAddExposeCommentDialog(main_win or sdcompat.get_main_window())
        _dialog_ref.show()
    except Exception as error:
        print(f"{_LOG} 打开窗口失败: {error}")
        QtWidgets.QMessageBox.critical(main_win, "AutoAddExposeCommentToNode", str(error))