# -*- coding: utf-8 -*-
"""曝光参数分组扫描与 SBS XML 重排。"""

import datetime
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

_LOG = "[MaxSDPlugin/ExposeParamSorting]"

try:
    from sd.api.sdproperty import SDPropertyCategory
except Exception:
    SDPropertyCategory = None

try:
    from sd.api.apiexception import APIException
    _SD_ERRORS = (Exception, APIException)
except Exception:
    _SD_ERRORS = (Exception,)


def _scalar_text(value):
    if value is None:
        return ""
    try:
        from sd.api.sdvalueserializer import SDValueSerializer
        text = (SDValueSerializer.sToString(value) or "").strip()
    except _SD_ERRORS:
        text = str(value).strip()
    wrapper = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\((.*)\)$", re.DOTALL)
    while True:
        match = wrapper.match(text)
        if match is None:
            break
        text = match.group(1).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _read_group(graph, prop):
    try:
        value = graph.getPropertyAnnotationValueFromId(prop, "group")
        if value is not None:
            return _scalar_text(value)
    except _SD_ERRORS:
        pass
    if SDPropertyCategory is not None:
        try:
            metadata = graph.getPropertyMetadataDictFromId(
                prop.getId(), SDPropertyCategory.Input)
            if metadata is not None:
                return _scalar_text(metadata.getPropertyValueFromId("group"))
        except _SD_ERRORS:
            pass
    return ""


def _read_label(prop):
    try:
        return str(prop.getLabel() or prop.getId() or "")
    except _SD_ERRORS:
        return ""


def _read_type_label(prop):
    try:
        property_type = prop.getType()
        type_id = property_type.getId() if property_type is not None else ""
        return str(type_id).split("/")[-1].split("::")[-1]
    except _SD_ERRORS:
        return ""


def collect_param_snapshot(graph, prop):
    """生成 INPUT PARAMETERS 的 UI 快照；连接型 INPUTS 返回 None。"""
    try:
        parameter_id = str(prop.getId() or "")
        if not parameter_id or parameter_id.startswith("$"):
            return None
        try:
            connectable = bool(prop.isConnectable())
        except _SD_ERRORS:
            connectable = False
        if connectable:
            return None
        return {
            "id": parameter_id,
            "label": _read_label(prop),
            "type_label": _read_type_label(prop),
            "group": _read_group(graph, prop),
        }
    except _SD_ERRORS as error:
        print(f"{_LOG} 读取参数失败: {error}")
        return None


def collect_groups(graph):
    """按当前顺序返回非连接型 INPUT PARAMETERS，不包含 INPUTS/OUTPUTS。"""
    if graph is None or SDPropertyCategory is None:
        return []
    try:
        properties = graph.getProperties(SDPropertyCategory.Input)
        property_count = len(properties)
    except _SD_ERRORS as error:
        print(f"{_LOG} 读取 Graph 参数失败: {error}")
        return []

    group_order = []
    grouped_parameters = {}
    for index in range(property_count):
        snapshot = collect_param_snapshot(graph, properties[index])
        if snapshot is None:
            continue
        group_name = snapshot["group"]
        if group_name not in grouped_parameters:
            grouped_parameters[group_name] = []
            group_order.append(group_name)
        grouped_parameters[group_name].append(snapshot)
    return [(name, grouped_parameters[name]) for name in group_order]


def _child_value(element, child_tag):
    child = element.find(child_tag)
    return child.get("v", "") if child is not None else ""


def _set_xml_group(parameter_node, group_name):
    """同步 paraminput 的直接 Group 与 metadata Group。"""
    group_name = str(group_name or "")
    group_element = parameter_node.find("group")
    if group_element is None:
        group_element = ET.Element("group")
        metadata = parameter_node.find("metadata")
        if metadata is None:
            parameter_node.append(group_element)
        else:
            parameter_node.insert(list(parameter_node).index(metadata), group_element)
    group_element.set("v", group_name)

    metadata = parameter_node.find("metadata")
    if metadata is None:
        metadata = ET.SubElement(parameter_node, "metadata")
    group_metadata = None
    for entry in metadata.findall("treestr"):
        if _child_value(entry, "name") == "group":
            group_metadata = entry
            break
    if group_metadata is None:
        group_metadata = ET.SubElement(metadata, "treestr")
        ET.SubElement(group_metadata, "name", {"v": "group"})
        ET.SubElement(group_metadata, "value")
    value_element = group_metadata.find("value")
    if value_element is None:
        value_element = ET.SubElement(group_metadata, "value")
    value_element.set("v", group_name)


def _graph_identifier(graph):
    try:
        identifier = graph.getIdentifier()
        if identifier:
            return str(identifier)
    except _SD_ERRORS:
        pass
    try:
        url = str(graph.getUrl() or "")
        return url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    except _SD_ERRORS:
        return ""


def get_graph_scope(graph):
    """返回用于执行前一致性校验的当前 Graph 范围。"""
    if graph is None:
        return {"package_path": "", "package_uid": "", "graph_id": ""}
    try:
        package = graph.getPackage()
        package_path = os.path.normcase(os.path.abspath(str(package.getFilePath() or "")))
        try:
            package_uid = str(package.getUID() or "")
        except _SD_ERRORS:
            package_uid = ""
        return {
            "package_path": package_path,
            "package_uid": package_uid,
            "graph_id": _graph_identifier(graph),
        }
    except _SD_ERRORS:
        return {"package_path": "", "package_uid": "", "graph_id": ""}


def _same_graph_scope(left, right):
    return bool(
        left.get("package_path")
        and left.get("package_path") == right.get("package_path")
        and left.get("graph_id")
        and left.get("graph_id") == right.get("graph_id"))


def _find_xml_graph(root, graph_identifier):
    matches = [element for element in root.iter("graph")
               if _child_value(element, "identifier") == graph_identifier]
    if len(matches) != 1:
        raise ValueError(
            f"在 SBS 中找到 {len(matches)} 个标识为 '{graph_identifier}' 的 Graph，无法唯一定位。")
    return matches[0]


def _stage_reordered_xml(
        source_path, graph_identifier, ordered_ids, group_by_id=None):
    """生成已验证的临时 SBS，同时同步参数顺序和目标分组。"""
    tree = ET.parse(source_path)
    graph_element = _find_xml_graph(tree.getroot(), graph_identifier)
    paraminputs = graph_element.find("paraminputs")
    if paraminputs is None:
        raise ValueError("目标 Graph 没有 <paraminputs>。")

    parameter_nodes = list(paraminputs.findall("paraminput"))
    nodes_by_id = {}
    for node in parameter_nodes:
        parameter_id = _child_value(node, "identifier")
        if not parameter_id or parameter_id in nodes_by_id:
            raise ValueError(f"SBS 中存在空 ID 或重复参数 ID: {parameter_id!r}")
        nodes_by_id[parameter_id] = node

    requested_ids = set(ordered_ids)
    if len(ordered_ids) != len(requested_ids):
        raise ValueError("UI 排序列表中存在重复参数 ID，请刷新后重试。")

    sortable_ids = [parameter_id for parameter_id in ordered_ids
                    if parameter_id in nodes_by_id]
    skipped_ids = [parameter_id for parameter_id in ordered_ids
                   if parameter_id not in nodes_by_id]
    if not sortable_ids:
        raise ValueError("当前 UI 参数均未序列化到 SBS，无法通过 XML 排序。")

    if group_by_id:
        for parameter_id in sortable_ids:
            if parameter_id in group_by_id:
                _set_xml_group(nodes_by_id[parameter_id], group_by_id[parameter_id])

    sortable_positions = [index for index, node in enumerate(parameter_nodes)
                          if _child_value(node, "identifier") in requested_ids]
    if len(sortable_positions) != len(sortable_ids):
        raise ValueError("SBS 中可排序参数数量异常，为避免破坏顺序已中止。")

    reordered_nodes = list(parameter_nodes)
    for position, parameter_id in zip(sortable_positions, sortable_ids):
        reordered_nodes[position] = nodes_by_id[parameter_id]

    for node in parameter_nodes:
        paraminputs.remove(node)
    for node in reordered_nodes:
        paraminputs.append(node)

    file_descriptor, staged_path = tempfile.mkstemp(
        prefix=".mxsort_", suffix=".sbs", dir=os.path.dirname(source_path))
    os.close(file_descriptor)
    try:
        tree.write(staged_path, encoding="UTF-8", xml_declaration=True)
        ET.parse(staged_path)
        return staged_path, sortable_ids, skipped_ids
    except Exception:
        try:
            os.remove(staged_path)
        except OSError:
            pass
        raise


def apply_group_order(graph, ordered_groups):
    """保存并卸载 Package，通过重排 XML 节点修改参数顺序，再重新加载。"""
    if graph is None:
        return False, ["没有可操作的 Graph。"]

    ordered_ids = [parameter["id"]
                   for _group_name, parameters in ordered_groups
                   for parameter in parameters]
    group_by_id = {
        parameter["id"]: group_name
        for group_name, parameters in ordered_groups
        for parameter in parameters
    }
    if not ordered_ids:
        return False, ["没有可排序的曝光参数。"]

    try:
        import sd
        from .. import sdcompat
        app = sd.getContext().getSDApplication()
        package_manager = app.getPackageMgr()
        package = graph.getPackage()
        package_path = str(package.getFilePath() or "")
        graph_identifier = _graph_identifier(graph)
    except _SD_ERRORS as error:
        return False, [f"获取当前 Package 信息失败: {error}"]

    if not package_path:
        return False, ["当前 Package 尚未保存，请先 Save As 后再排序。"]
    if not os.path.isfile(package_path):
        return False, [f"找不到 SBS 文件: {package_path}"]
    if not graph_identifier:
        return False, ["无法读取当前 Graph 标识。"]

    requested_scope = get_graph_scope(graph)
    active_scope = get_graph_scope(sdcompat.get_current_graph(app))
    if not _same_graph_scope(requested_scope, active_scope):
        return False, [
            "当前活动 Graph 已变化。为避免修改错误的 SBS，操作已中止；请刷新后重试。"]

    try:
        loaded_package = package_manager.getUserPackageFromFilePath(package_path)
        if loaded_package is None:
            return False, ["当前 SBS 不是已加载的 User Package，操作已中止。"]
        loaded_uid = str(loaded_package.getUID() or "")
        requested_uid = requested_scope.get("package_uid", "")
        if requested_uid and loaded_uid and requested_uid != loaded_uid:
            return False, ["当前 SBS 路径对应的已加载 Package UID 不一致，操作已中止。"]
    except _SD_ERRORS as error:
        return False, [f"验证当前 SBS 加载状态失败: {error}"]

    staged_path = None
    backup_path = None
    package_unloaded = False
    try:
        package_manager.savePackage(package)
        staged_path, sorted_ids, skipped_ids = _stage_reordered_xml(
            package_path, graph_identifier, ordered_ids, group_by_id)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{package_path}.ExposeParameterAutoSorting_{timestamp}.bak"
        shutil.copy2(package_path, backup_path)

        package_manager.unloadUserPackage(package)
        package_unloaded = True
        os.replace(staged_path, package_path)
        staged_path = None
        package_manager.loadUserPackage(package_path, True, False)
        package_unloaded = False

        messages = [
            f"已通过 XML 排序并同步分组 {len(sorted_ids)} 个参数。",
            f"备份文件: {backup_path}",
            "Package 已重新加载；请在 Explorer 中双击原 Graph 重新打开。",
        ]
        if skipped_ids:
            messages.append(
                "以下运行时/继承参数未写入当前 SBS，已安全跳过: "
                + ", ".join(skipped_ids))
        return True, messages
    except _SD_ERRORS as error:
        recovery_messages = []
        if package_unloaded and backup_path and os.path.isfile(backup_path):
            try:
                shutil.copy2(backup_path, package_path)
                package_manager.loadUserPackage(package_path, True, False)
                package_unloaded = False
                recovery_messages.append("已从备份恢复并重新加载原 Package。")
            except _SD_ERRORS as recovery_error:
                recovery_messages.append(f"自动恢复失败: {recovery_error}")
        return False, [f"XML 排序失败: {error}"] + recovery_messages
    finally:
        if staged_path and os.path.isfile(staged_path):
            try:
                os.remove(staged_path)
            except OSError:
                pass
