# -*- coding: utf-8 -*-
"""开关管理工具的数据层：创建 Boolean 参数并批量设置 Visible If。"""

import contextlib
import os
import xml.etree.ElementTree as ET

from .. import sdcompat

APIException = sdcompat.APIException
_SD_API_ERRORS = sdcompat.SD_API_ERRORS

try:
    from sd.api.sdproperty import SDPropertyCategory
    from sd.api.sdtypebool import SDTypeBool
    from sd.api.sdvaluebool import SDValueBool
    from sd.api.sdvaluestring import SDValueString
except Exception:
    SDPropertyCategory = None
    SDTypeBool = None
    SDValueBool = None
    SDValueString = None

from ..output import output_data

_LOG = "[MaxSDPlugin/switch_manager]"
_VISIBLE_IF_CANDIDATES = ("visibleIf", "visible_if", "visibleif")


def get_current_graph(app=None):
    """返回当前活动 Graph；不可用时返回 None。"""
    return sdcompat.get_current_graph(app)


def get_graph_scope(graph):
    """记录扫描对象；未保存 Package 用 UID 区分，读取失败时禁止写入。"""
    if graph is None:
        return None
    try:
        package = graph.getPackage()
        uid = str(package.getUID() or "")
        identifier = str(graph.getIdentifier() or "")
        path = str(package.getFilePath() or "")
        if not uid or not identifier:
            return None
        return (uid, os.path.normcase(os.path.abspath(path)) if path else "", identifier)
    except _SD_API_ERRORS:
        return None


def _error_text(error):
    text = str(error).strip()
    if text:
        return text
    error_code = getattr(error, "mErrorCode", None)
    return str(error_code) if error_code is not None else type(error).__name__


def _undo_group(name):
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        return SDHistoryUtils.UndoGroup(name)
    except Exception:
        return contextlib.nullcontext()


def _metadata(graph, prop):
    if SDPropertyCategory is None:
        return None
    try:
        return graph.getPropertyMetadataDictFromId(
            prop.getId(), SDPropertyCategory.Input)
    except _SD_API_ERRORS:
        return None


def _setting_ids(graph, prop):
    """返回参数实际提供的 annotation 与 metadata ID。"""
    annotation_ids = set()
    metadata_ids = set()
    try:
        annotations = graph.getPropertyAnnotations(prop)
        annotation_ids = {
            annotations[index].getId() for index in range(len(annotations))
        }
    except _SD_API_ERRORS:
        pass
    metadata = _metadata(graph, prop)
    if metadata is not None:
        try:
            properties = metadata.getProperties()
            metadata_ids = {
                properties[index].getId() for index in range(len(properties))
            }
        except _SD_API_ERRORS:
            pass
    return annotation_ids, metadata_ids


def _visible_if_id(graph, prop):
    """根据属性能力探测 Visible If 的真实设置 ID。"""
    annotation_ids, metadata_ids = _setting_ids(graph, prop)
    available_ids = annotation_ids | metadata_ids
    normalized_ids = {
        setting_id.replace("_", "").replace(" ", "").lower(): setting_id
        for setting_id in available_ids if setting_id
    }
    detected = normalized_ids.get("visibleif")
    if detected:
        return detected, annotation_ids, metadata_ids
    return _VISIBLE_IF_CANDIDATES[0], annotation_ids, metadata_ids


def _value_text(value):
    return output_data.scalar_value_to_text(
        output_data._value_to_str(value)) if value is not None else ""


def _read_visible_if(graph, prop):
    setting_id, annotation_ids, metadata_ids = _visible_if_id(graph, prop)
    if setting_id in annotation_ids:
        try:
            return _value_text(
                graph.getPropertyAnnotationValueFromId(prop, setting_id))
        except _SD_API_ERRORS:
            pass
    metadata = _metadata(graph, prop)
    if metadata is not None and setting_id in metadata_ids:
        try:
            return _value_text(metadata.getPropertyValueFromId(setting_id))
        except _SD_API_ERRORS:
            pass
    return ""


def _read_group(graph, prop):
    """读取 Group；INPUTS 不提供该字段时返回空串，不跳过参数。"""
    try:
        value = graph.getPropertyAnnotationValueFromId(prop, "group")
        if value is not None:
            return _value_text(value)
    except _SD_API_ERRORS:
        pass
    metadata = _metadata(graph, prop)
    if metadata is not None:
        try:
            value = metadata.getPropertyValueFromId("group")
            return _value_text(value) if value is not None else ""
        except _SD_API_ERRORS:
            pass
    return ""


def _safe_call(callback, fallback=None):
    """调用单个 SD 属性读取器；失败时只回退该字段。"""
    try:
        return callback()
    except _SD_API_ERRORS:
        return fallback


def _xml_child_value(element, child_name):
    child = element.find(child_name) if element is not None else None
    return child.get("v", "") if child is not None else ""


def _xml_default_value(element):
    """读取 paraminput 的首个 defaultValue 常量并转为简洁文本。"""
    default_value = element.find("defaultValue")
    if default_value is None or not list(default_value):
        return ""
    value_text = list(default_value)[0].get("v", "")
    if list(default_value)[0].tag == "constantValueBool":
        return "True" if value_text == "1" else "False"
    return value_text


def parameter_value_text(parameter):
    """返回适合参数树展示的当前值文本。"""
    value = parameter.get("value")
    if value not in (None, ""):
        text = output_data.scalar_value_to_text(value)
        if text.lower() == "true":
            return "True"
        if text.lower() == "false":
            return "False"
        return text
    return str(parameter.get("default") or "")


def supports_value_edit(parameter):
    """仅允许 Graph API 可写的常见标量类型编辑当前值。"""
    if parameter.get("xml_only"):
        return False
    type_id = (parameter.get("type") or "").lower()
    return (
        "string" in type_id
        or "bool" in type_id
        or type_id.endswith("int")
        or type_id in ("int", "integer")
        or "int1" in type_id
        or ("float" in type_id and not any(
            name in type_id for name in ("float2", "float3", "float4")))
    )


def _graph_identifier(graph):
    identifier = _safe_call(graph.getIdentifier, "")
    if identifier:
        return str(identifier)
    url = str(_safe_call(graph.getUrl, "") or "")
    return url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]


def _graph_file_path(graph):
    package = _safe_call(graph.getPackage)
    if package is None:
        return ""
    return str(_safe_call(package.getFilePath, "") or "")


def save_graph_package(graph):
    """保存当前 Graph 所属 Package，使随后 XML 读取反映最新 Group。"""
    if graph is None:
        return False, "未找到当前 Graph"
    package = _safe_call(graph.getPackage)
    package_path = _graph_file_path(graph)
    if package is None or not package_path:
        return False, "当前 Package 尚未保存到磁盘"
    try:
        import sd
        app = sd.getContext().getSDApplication()
        app.getPackageMgr().savePackage(package)
        return True, ""
    except _SD_API_ERRORS as error:
        return False, _error_text(error)


def _xml_parameter_snapshots(graph):
    """从已保存 SBS 读取当前 Graph 的完整 paraminputs。"""
    package_path = _graph_file_path(graph)
    graph_identifier = _graph_identifier(graph)
    if not package_path or not os.path.isfile(package_path) or not graph_identifier:
        return []
    try:
        root = ET.parse(package_path).getroot()
        graph_elements = [
            element for element in root.iter("graph")
            if _xml_child_value(element, "identifier") == graph_identifier
        ]
        if len(graph_elements) != 1:
            return []
        paraminputs = graph_elements[0].find("paraminputs")
        if paraminputs is None:
            return []
        snapshots = []
        for element in paraminputs.findall("paraminput"):
            parameter_id = _xml_child_value(element, "identifier")
            if not parameter_id or parameter_id.startswith("$"):
                continue
            attributes = element.find("attributes")
            connectable = _xml_child_value(element, "isConnectable") == "1"
            snapshots.append({
                "id": parameter_id,
                "label": _xml_child_value(attributes, "label") or parameter_id,
                "type": _xml_child_value(element, "type"),
                "default": _xml_default_value(element),
                "value": "",
                "connectable": connectable,
                "category": (
                    output_data.CATEGORY_INPUTS if connectable
                    else output_data.CATEGORY_PARAMETERS),
                "group": _xml_child_value(element, "group"),
                "visible_if": _xml_child_value(element, "visibleIf"),
                "xml_only": True,
            })
        return snapshots
    except (OSError, ET.ParseError) as error:
        print(f"{_LOG} 读取 SBS 参数 XML 失败: {_error_text(error)}")
        return []


def collect_parameters(graph):
    """列出 INPUT PARAMETERS 与 INPUTS，并附带当前 Visible If 表达式。"""
    if graph is None or SDPropertyCategory is None:
        return []
    try:
        properties = graph.getProperties(SDPropertyCategory.Input)
    except _SD_API_ERRORS as error:
        print(f"{_LOG} 读取 Graph 输入属性失败: {_error_text(error)}")
        return []
    parameters = []
    for index in range(len(properties)):
        try:
            prop = properties[index]
            parameter_id = prop.getId()
            if not parameter_id or parameter_id.startswith("$"):
                continue
            connectable = bool(_safe_call(prop.isConnectable, False))
            property_type = _safe_call(prop.getType)
            parameters.append({
                "id": parameter_id,
                "label": _safe_call(prop.getLabel, parameter_id),
                "type": (
                    _safe_call(property_type.getId, "")
                    if property_type is not None else ""),
                "default": output_data._value_to_str(
                    _safe_call(prop.getDefaultValue)),
                "value": output_data._value_to_str(
                    _safe_call(lambda: graph.getPropertyValue(prop))),
                "connectable": connectable,
                "category": (
                    output_data.CATEGORY_INPUTS if connectable
                    else output_data.CATEGORY_PARAMETERS),
                "group": _read_group(graph, prop),
                "visible_if": _read_visible_if(graph, prop),
            })
        except _SD_API_ERRORS as error:
            print(f"{_LOG} 跳过无法读取的输入属性: {_error_text(error)}")
    parameters_by_id = {parameter["id"]: parameter for parameter in parameters}
    for xml_parameter in _xml_parameter_snapshots(graph):
        parameter_id = xml_parameter["id"]
        existing = parameters_by_id.get(parameter_id)
        if existing is None:
            parameters.append(xml_parameter)
            parameters_by_id[parameter_id] = xml_parameter
            continue
        existing["group"] = xml_parameter["group"]
        existing["visible_if"] = xml_parameter["visible_if"]
        if xml_parameter["connectable"]:
            existing["connectable"] = True
            existing["category"] = output_data.CATEGORY_INPUTS
        existing["xml_only"] = False
    return parameters


def collect_group_names(parameters):
    """按首次出现顺序返回当前 Graph 的现有 Group 名称。"""
    return list(dict.fromkeys(
        (parameter.get("group") or "").strip()
        for parameter in parameters
        if (parameter.get("group") or "").strip()
    ))


def _set_text_setting(graph, prop, setting_id, text):
    value = SDValueString.sNew(text)
    resolved_id, annotation_ids, metadata_ids = _visible_if_id(graph, prop)
    if setting_id == "visible_if":
        candidate_ids = list(dict.fromkeys(
            (resolved_id,) + _VISIBLE_IF_CANDIDATES))
    else:
        candidate_ids = [setting_id]
    changed = False
    errors = []
    metadata = _metadata(graph, prop)
    allow_direct_annotation = setting_id in ("group", "visible_if")
    for candidate_id in candidate_ids:
        if metadata is not None and (
                candidate_id in metadata_ids or not metadata_ids):
            try:
                metadata.setPropertyValueFromId(candidate_id, value)
                changed = True
            except _SD_API_ERRORS as error:
                errors.append(
                    f"metadata/{candidate_id}: {_error_text(error)}")
        if candidate_id in annotation_ids or allow_direct_annotation:
            try:
                graph.setPropertyAnnotationValueFromId(
                    prop, candidate_id, value)
                changed = True
            except _SD_API_ERRORS as error:
                errors.append(
                    f"annotation/{candidate_id}: {_error_text(error)}")
    if changed:
        return True, []
    if not changed and not errors:
        errors.append(f"当前 Designer 未提供可写的 {setting_id} 设置")
    return False, errors


def _is_boolean_parameter(parameter):
    """兼容不同 Designer 版本的 Boolean 类型 ID 表示。"""
    type_id = (parameter.get("type") or "").lower()
    return type_id == "bool" or type_id.endswith("typebool")


def collect_switches(parameters, switch_group):
    """仅返回指定开关 Group 中的非连接型 Boolean 参数。"""
    switch_group = (switch_group or "").strip()
    if not switch_group:
        return []
    return [
        parameter for parameter in parameters
        if (not parameter.get("connectable")
            and _is_boolean_parameter(parameter)
            and (parameter.get("group") or "").strip() == switch_group)
    ]


def create_boolean_switch(
        graph, parameter_id, label, group="", initial_value=True):
    """在 INPUT PARAMETERS 的指定 Group 创建 Boolean 参数。"""
    if graph is None or None in (
            SDPropertyCategory, SDTypeBool, SDValueBool, SDValueString):
        raise RuntimeError("当前环境缺少创建 Boolean 参数所需的 SD API")
    parameter_id = (parameter_id or "").strip()
    group = (group or "").strip()
    if not parameter_id:
        raise ValueError("开关参数 ID 不能为空")
    if not group:
        raise ValueError("开关 Group 不能为空")
    existing = graph.getPropertyFromId(parameter_id, SDPropertyCategory.Input)
    if existing is not None:
        raise ValueError(f"参数 ID 已存在: {parameter_id}")
    with _undo_group("MaxSDPlugin 创建开关参数"):
        prop = graph.newProperty(
            parameter_id, SDTypeBool.sNew(), SDPropertyCategory.Input)
        if prop is None:
            raise RuntimeError("graph.newProperty() 未能创建 Boolean 参数")
        try:
            _ensure_boolean_editor(graph, prop, force=True)
        except _SD_API_ERRORS as error:
            # 不能将缺少发布控件的参数当作成功创建；只清理本次新参数。
            try:
                graph.deleteProperty(prop)
            except _SD_API_ERRORS as cleanup_error:
                raise RuntimeError(
                    f"按钮控件设置失败：{_error_text(error)}；"
                    f"新参数清理失败，请撤销或删除 {parameter_id}："
                    f"{_error_text(cleanup_error)}") from error
            raise RuntimeError(
                f"按钮控件设置失败，已移除本次新参数：{_error_text(error)}") from error
        label_changed, label_errors = _set_text_setting(
            graph, prop, "label", (label or parameter_id).strip())
        group_changed, group_errors = _set_text_setting(
            graph, prop, "group", group)
        graph.setPropertyValue(prop, SDValueBool.sNew(bool(initial_value)))
    return {
        "id": parameter_id,
        "initial_value": bool(initial_value),
        "label_changed": label_changed,
        "group_changed": group_changed,
        "warnings": label_errors + group_errors,
    }


def _ensure_boolean_editor(graph, prop, force=False):
    """通过 Adobe editor 注解补齐空控件；已有自定义控件保持不变。

    本地官方 sample_sbs_graph_inputs.py 使用 editor 注解；官方
    test_write_content.py 明确包含 buttons。不能写普通 metadata 替代它。
    """
    value = graph.getPropertyAnnotationValueFromId(prop, "editor")
    editor = value.get() if value is not None else ""
    if editor and not force:
        return False
    graph.setPropertyAnnotationValueFromId(
        prop, "editor", SDValueString.sNew("buttons"))
    value = graph.getPropertyAnnotationValueFromId(prop, "editor")
    if value is None or value.get() != "buttons":
        raise RuntimeError("editor=buttons 写入后读回不一致")
    return True


def repair_boolean_switch_editors(graph, switch_group):
    """只补齐当前 Group 中非连接型 Boolean 的空 editor，可撤销。"""
    summary = {"updated": [], "skipped": [], "failed": []}
    switch_group = (switch_group or "").strip()
    if graph is None or not switch_group or None in (
            SDPropertyCategory, SDValueString):
        summary["failed"].append(("<graph>", "请选择当前 Graph 和开关 Group"))
        return summary
    try:
        properties = graph.getProperties(SDPropertyCategory.Input)
        with _undo_group("MaxSDPlugin 补齐开关按钮控件"):
            for prop in properties:
                parameter_id = "<unknown>"
                try:
                    parameter_id = prop.getId()
                    if (parameter_id.startswith("$") or prop.isConnectable()
                            or not _is_boolean_parameter({"type": prop.getType().getId()})
                            or _read_group(graph, prop).strip() != switch_group):
                        continue
                    changed = _ensure_boolean_editor(graph, prop)
                    summary["updated" if changed else "skipped"].append(parameter_id)
                except _SD_API_ERRORS as error:
                    summary["failed"].append((parameter_id, _error_text(error)))
    except _SD_API_ERRORS as error:
        summary["failed"].append(("<graph>", _error_text(error)))
    return summary


def update_parameter_values(graph, updates):
    """批量修改标量参数当前值，返回 updated/failed 汇总。"""
    summary = {"updated": [], "failed": []}
    if graph is None or SDPropertyCategory is None:
        summary["failed"].append(("<graph>", "当前环境缺少所需的 SD API"))
        return summary
    with _undo_group("MaxSDPlugin 批量修改参数当前值"):
        for update in updates or []:
            parameter_id = update.get("id")
            try:
                prop = graph.getPropertyFromId(
                    parameter_id, SDPropertyCategory.Input)
                if prop is None:
                    raise ValueError("当前 Graph API 中未找到参数")
                value = output_data._build_sdvalue(
                    update.get("type"), update.get("value"))
                if value is None:
                    raise ValueError("该参数类型不支持文本修改当前值")
                graph.setPropertyValue(prop, value)
                summary["updated"].append(parameter_id)
            except _SD_API_ERRORS as error:
                summary["failed"].append((parameter_id, _error_text(error)))
    return summary


def clear_visible_if(graph, target_ids):
    """批量清空目标参数的 Visible If。"""
    summary = {"updated": [], "failed": []}
    if graph is None or SDPropertyCategory is None or SDValueString is None:
        summary["failed"].append(("<graph>", "当前环境缺少所需的 SD API"))
        return summary
    with _undo_group("MaxSDPlugin 批量清除 Visible If"):
        for target_id in dict.fromkeys(target_ids or []):
            try:
                prop = graph.getPropertyFromId(
                    target_id, SDPropertyCategory.Input)
                if prop is None:
                    raise ValueError("当前 Graph API 中未找到参数")
                changed, errors = _set_text_setting(
                    graph, prop, "visible_if", "")
                if changed:
                    summary["updated"].append(target_id)
                if errors:
                    summary["failed"].append(
                        (target_id, "; ".join(errors)))
            except _SD_API_ERRORS as error:
                summary["failed"].append((target_id, _error_text(error)))
    return summary


def assign_switch(graph, switch_id, target_ids, switch_group=""):
    """将开关表达式批量写入目标参数的 Visible If。"""
    summary = {"updated": [], "failed": []}
    if graph is None or SDPropertyCategory is None or SDValueString is None:
        summary["failed"].append(("<graph>", "当前环境缺少所需的 SD API"))
        return summary
    switch_id = (switch_id or "").strip()
    switch_prop = graph.getPropertyFromId(
        switch_id, SDPropertyCategory.Input)
    if switch_prop is None:
        summary["failed"].append((switch_id, "未找到开关参数"))
        return summary
    switch_snapshot = {
        "type": _safe_call(lambda: switch_prop.getType().getId(), ""),
        "connectable": bool(_safe_call(switch_prop.isConnectable, False)),
        "group": _read_group(graph, switch_prop),
    }
    if not _is_boolean_parameter(switch_snapshot):
        summary["failed"].append((switch_id, "开关参数不是 Boolean 类型"))
        return summary
    switch_group = (switch_group or "").strip()
    if not switch_group or switch_snapshot["group"].strip() != switch_group:
        summary["failed"].append(
            (switch_id, "开关参数不在当前设定的开关 Group 中"))
        return summary
    expression = f'input["{switch_id}"]'
    with _undo_group("MaxSDPlugin 批量设置 Visible If"):
        for target_id in dict.fromkeys(target_ids or []):
            if not target_id or target_id == switch_id:
                continue
            try:
                prop = graph.getPropertyFromId(
                    target_id, SDPropertyCategory.Input)
                if prop is None:
                    raise ValueError("当前 Graph 中未找到参数")
                changed, errors = _set_text_setting(
                    graph, prop, "visible_if", expression)
                if changed:
                    summary["updated"].append(target_id)
                if errors:
                    summary["failed"].append(
                        (target_id, "; ".join(errors)))
            except _SD_API_ERRORS as error:
                summary["failed"].append((target_id, _error_text(error)))
    return summary
