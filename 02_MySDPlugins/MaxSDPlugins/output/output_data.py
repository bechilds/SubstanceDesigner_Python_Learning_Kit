# -*- coding: utf-8 -*-
"""曝光参数功能的数据层：枚举当前图的已暴露参数，以及 OutputData 的读写/导出。

不含任何 Qt UI，纯逻辑 + 文件 IO，方便单独复用与测试。
SD 专有的 `sd` / `sd.api.*` 仅在 SD 进程内可用，这里全部包 try/except，
取不到时优雅返回 None / 空列表，不让异常冒泡到 SD 主进程。
"""

import os
import json
import datetime
import re

import sd  # SD 提供的 Python 包；只在 SD 进程内可用

from .. import sdcompat  # 跨版本 SD/Qt 接口兼容层（唯一真源）

# SD 专有类型：用 try 包住，工作区 lint 找不到属正常
try:
    from sd.api.sdproperty import SDPropertyCategory
except sdcompat.SD_API_ERRORS:  # pragma: no cover - 仅在非 SD 环境触发
    SDPropertyCategory = None

try:
    from sd.api.sdvalueserializer import SDValueSerializer
except sdcompat.SD_API_ERRORS:  # pragma: no cover
    SDValueSerializer = None

APIException = sdcompat.APIException  # 保留旧符号，定义集中在兼容层。
_SD_API_ERRORS = sdcompat.SD_API_ERRORS

# OutputData 文件名与数据结构版本
OUTPUT_DATA_FILENAME = "OutputData.json"
SCHEMA_VERSION = "0.1.0"

_LOG = "[MaxSDPlugin/output]"
_IDENTITY_SETTING_IDS = {"id", "identifier", "label"}


# --------------------------------------------------------------------------- #
# 获取当前图 / package / 路径
# --------------------------------------------------------------------------- #
def get_current_graph(app=None):
    """返回当前在图视图中打开的 SDGraph；取不到返回 None。"""
    return sdcompat.get_current_graph(app)


def get_package_file_path(graph):
    """返回该图所属 package 的磁盘路径（.sbs）；未保存或取不到返回 None。"""
    if graph is None:
        return None
    try:
        pkg = graph.getPackage()
        if pkg is None:
            return None
        path = pkg.getFilePath()
        return path or None
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 获取 package 路径失败: {e}")
        return None


def get_default_output_data_path(graph):
    """OutputData.json 的默认缓存路径：当前 .sbs 同目录。

    package 尚未保存（拿不到磁盘路径）时返回 None。
    """
    pkg_path = get_package_file_path(graph)
    if not pkg_path:
        return None
    return os.path.join(os.path.dirname(pkg_path), OUTPUT_DATA_FILENAME)


# --------------------------------------------------------------------------- #
# 枚举已暴露参数
# --------------------------------------------------------------------------- #
def _value_to_str(value):
    """把 SDValue 转成可序列化字符串；None 原样返回 None。"""
    if value is None:
        return None
    try:
        if SDValueSerializer is not None:
            return SDValueSerializer.sToString(value)
        return str(value)
    except sdcompat.SD_API_ERRORS:
        return str(value)


def _type_id(prop):
    """读取属性类型标识，失败返回空串。"""
    try:
        t = prop.getType()
        if t is None:
            return ""
        return t.getId() if hasattr(t, "getId") else str(t)
    except sdcompat.SD_API_ERRORS:
        return ""


def _safe_graph_value(graph, prop):
    try:
        return graph.getPropertyValue(prop)
    except sdcompat.SD_API_ERRORS:
        return None


def _is_base_parameter(pid):
    """图内置的基础参数（$outputsize / $format / $pixelsize 等）id 以 '$' 开头。

    这些不属于用户暴露的「INPUT PARAMETERS / INPUTS」，需要排除。
    """
    return bool(pid) and pid.startswith("$")


def _strip_quotes(s):
    if isinstance(s, str) and len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def scalar_value_to_text(value):
    """把 SDValueSerializer 的标量包装文本解成适合编辑的值。

    例如 `SDValueBool(bool(false))` -> `false`，
    `SDValueString(string(ChannelR))` -> `ChannelR`。
    """
    text = "" if value is None else str(value).strip()
    wrapper = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\((.*)\)$", re.DOTALL)
    while True:
        match = wrapper.match(text)
        if match is None:
            break
        text = match.group(1).strip()
    return _strip_quotes(text)


def _property_has_nonempty_input_value(node, prop):
    """节点属性已能读到非空输入值时返回 True；数值 0 和布尔 False 也属于有效值。"""
    try:
        value = node.getPropertyValue(prop)
    except _SD_API_ERRORS:
        return False
    if value is None:
        return False
    return scalar_value_to_text(_value_to_str(value)) != ""


def _read_annotation_text(graph, prop, annotation_id):
    """读取属性的文本注解；注解不存在或读取失败时返回空串。"""
    try:
        value = graph.getPropertyAnnotationValueFromId(prop, annotation_id)
        if value is None:
            return ""
        return scalar_value_to_text(_value_to_str(value)) or ""
    except sdcompat.SD_API_ERRORS:
        return ""


def _read_group(graph, prop):
    """读取属性的分组（group 注解）。无分组 / 读取失败返回空串。

    分组是非破坏性读取；即使 'group' 注解 id 在某些版本不存在，最坏只是显示为未分组。
    """
    return _read_annotation_text(graph, prop, "group")


# UI 顶层分类顺序与中文标签（对应 SD 参数面板的两个区）
CATEGORY_PARAMETERS = "parameters"
CATEGORY_INPUTS = "inputs"
CATEGORY_LABELS = (
    (CATEGORY_PARAMETERS, "INPUT PARAMETERS"),
    (CATEGORY_INPUTS, "INPUTS"),
)


def _collect_node_referenced_parameter_ids(graph):
    """返回节点属性函数中由 Get Variable 实际引用的 Graph 输入参数 ID。"""
    referenced_ids = set()
    if graph is None or SDPropertyCategory is None:
        return referenced_ids
    categories = [
        SDPropertyCategory.Input,
        SDPropertyCategory.Output,
        SDPropertyCategory.Annotation,
    ]
    try:
        nodes = graph.getNodes()
    except _SD_API_ERRORS:
        return referenced_ids
    for node_index in range(len(nodes)):
        node = nodes[node_index]
        for category in categories:
            try:
                properties = node.getProperties(category)
            except _SD_API_ERRORS:
                continue
            for property_index in range(len(properties)):
                try:
                    property_graph = node.getPropertyGraph(
                        properties[property_index])
                except _SD_API_ERRORS:
                    property_graph = None
                if property_graph is None:
                    continue
                try:
                    names, _ = _collect_get_var_status(property_graph)
                    referenced_ids.update(names)
                except _SD_API_ERRORS:
                    continue
    return referenced_ids


def collect_exposed_parameters(graph):
    """枚举图的已暴露输入参数，返回 list[dict]。

    仅包含「INPUT PARAMETERS」与「INPUTS」两类——即排除以 '$' 开头的内置基础参数。
    每项: {id, label, type, default, value, connectable, category, group, editor, referenced}。
    - connectable=True → 图像输入（INPUTS）；False → 数值型输入参数（INPUT PARAMETERS）。
    - category: "inputs" / "parameters"。
    - group: 该参数所属分组名（空串表示未分组）。
    任一参数读取失败只跳过该项，不中断。
    """
    result = []
    if graph is None or SDPropertyCategory is None:
        return result
    try:
        props = graph.getProperties(SDPropertyCategory.Input)
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 读取输入属性失败: {e}")
        return result

    try:
        count = len(props)
    except sdcompat.SD_API_ERRORS:
        count = 0
    referenced_ids = _collect_node_referenced_parameter_ids(graph)

    for i in range(count):
        try:
            prop = props[i]
            pid = prop.getId()
            if _is_base_parameter(pid):
                continue  # 跳过 $outputsize 等内置基础参数

            try:
                connectable = bool(prop.isConnectable())
            except sdcompat.SD_API_ERRORS:
                connectable = False

            result.append({
                "id": pid,
                "label": prop.getLabel(),
                "type": _type_id(prop),
                "default": _value_to_str(prop.getDefaultValue()),
                "value": _value_to_str(_safe_graph_value(graph, prop)),
                "connectable": connectable,
                "category": CATEGORY_INPUTS if connectable else CATEGORY_PARAMETERS,
                "group": _read_group(graph, prop),
                "editor": _read_annotation_text(graph, prop, "editor"),
                "referenced": pid in referenced_ids,
            })
        except sdcompat.SD_API_ERRORS as e:
            print(f"{_LOG} 跳过一个无法读取的参数: {e}")
    return result


def group_parameters(params):
    """把扁平参数列表组织成保留分组的结构，供 UI 渲染。

    返回: [(category_label, [(group_name, [param, ...]), ...]), ...]
    顺序：先 INPUT PARAMETERS 再 INPUTS；各分类内按参数首次出现顺序保留分组。
    """
    out = []
    for cat_key, cat_label in CATEGORY_LABELS:
        cat_params = [p for p in params if p.get("category") == cat_key]
        if not cat_params:
            continue
        order = []          # 保留分组出现顺序
        buckets = {}        # group_name -> [param]
        for p in cat_params:
            g = p.get("group") or ""
            if g not in buckets:
                buckets[g] = []
                order.append(g)
            buckets[g].append(p)
        out.append((cat_label, [(g, buckets[g]) for g in order]))
    return out


def _graph_identifier(graph):
    try:
        if hasattr(graph, "getIdentifier"):
            return graph.getIdentifier()
        if hasattr(graph, "getUrl"):
            return graph.getUrl()
    except sdcompat.SD_API_ERRORS:
        pass
    return ""


# --------------------------------------------------------------------------- #
# OutputData：构建 / 保存 / 加载
# --------------------------------------------------------------------------- #
def build_output_data(graph, selected_ids=None):
    """根据当前图构建 OutputData 字典（已暴露参数的完整快照）。

    参数:
        graph: 当前 SDGraph。
        selected_ids: 可选，勾选的参数 id 集合；提供时给每项加 `selected` 标记。
    """
    params = collect_exposed_parameters(graph)
    if selected_ids is not None:
        selected_ids = set(selected_ids)
        for p in params:
            p["selected"] = p["id"] in selected_ids
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "package": get_package_file_path(graph) or "",
        "graph": _graph_identifier(graph),
        "exposed_parameters": params,
    }


def save_output_data(data, path):
    """把 OutputData 字典写成 JSON（UTF-8，缩进 2）。返回写入路径。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{_LOG} OutputData 已写入: {path}")
    return path


def load_output_data(path):
    """读取并返回 OutputData 字典；解析失败抛出异常由调用方处理。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 参数设置复制 / 删除（取消暴露） / 加载应用
# --------------------------------------------------------------------------- #
def _undo_group(name):
    """返回一个可用作 with 上下文的 UndoGroup；取不到时返回一个空上下文。

    用 SDHistoryUtils.UndoGroup 包住破坏性操作，用户可在 SD 里 Ctrl+Z 撤销。
    """
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        return SDHistoryUtils.UndoGroup(name)
    except sdcompat.SD_API_ERRORS:
        import contextlib
        return contextlib.nullcontext()


def _new_string_value(text):
    """创建字符串 SDValue；API 不可用时返回 None。"""
    try:
        from sd.api.sdvaluestring import SDValueString
        return SDValueString.sNew(text or "")
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 创建字符串参数值失败: {e}")
        return None


def _error_text(error):
    """返回有内容的异常说明；Adobe APIException 的 str() 经常为空。"""
    text = str(error).strip()
    if text:
        return text
    error_code = getattr(error, "mErrorCode", None)
    return str(error_code) if error_code is not None else type(error).__name__


def _property_annotation_ids(graph, prop):
    """返回属性实际支持的注解 ID；读取失败返回空集合和错误。"""
    try:
        annotations = graph.getPropertyAnnotations(prop)
        return {
            annotations[index].getId()
            for index in range(len(annotations))
        }, None
    except _SD_API_ERRORS as error:
        return set(), _error_text(error)


def _property_metadata(graph, prop):
    """返回参数的可写 metadata dict；接口不可用或读取失败时返回错误。"""
    try:
        metadata = graph.getPropertyMetadataDictFromId(
            prop.getId(), SDPropertyCategory.Input)
        return metadata, None
    except _SD_API_ERRORS as error:
        return None, _error_text(error)


def _copy_property_metadata(graph, source_prop, target_prop):
    """复制非身份 metadata，避免 identifier/label 把新参数名称覆盖回旧值。"""
    skipped = []
    source_metadata, source_error = _property_metadata(graph, source_prop)
    target_metadata, target_error = _property_metadata(graph, target_prop)
    if source_error:
        return [("<source metadata>", source_error)]
    if target_error:
        return [("<target metadata>", target_error)]
    try:
        properties = source_metadata.getProperties()
        for index in range(len(properties)):
            metadata_prop = properties[index]
            metadata_id = metadata_prop.getId()
            if (metadata_id or "").lower() in _IDENTITY_SETTING_IDS:
                continue
            try:
                value = source_metadata.getPropertyValue(metadata_prop)
                if value is not None:
                    target_metadata.setPropertyValueFromId(metadata_id, value)
            except _SD_API_ERRORS as error:
                skipped.append((metadata_id, _error_text(error)))
    except _SD_API_ERRORS as error:
        skipped.append(("<metadata>", _error_text(error)))
    return skipped


def _set_property_text_setting(graph, prop, setting_id, text):
    """通过 property metadata 写文本设置，并对受支持的注解做同步。"""
    value = _new_string_value(text)
    if value is None:
        return False, ["无法创建字符串值"]
    changed = False
    errors = []
    metadata, metadata_error = _property_metadata(graph, prop)
    if metadata is not None:
        try:
            metadata.setPropertyValueFromId(setting_id, value)
            changed = True
        except _SD_API_ERRORS as error:
            errors.append(f"metadata: {_error_text(error)}")
    elif metadata_error:
        errors.append(f"metadata: {metadata_error}")

    annotation_ids, annotation_error = _property_annotation_ids(graph, prop)
    if setting_id in annotation_ids:
        try:
            graph.setPropertyAnnotationValueFromId(prop, setting_id, value)
            changed = True
        except _SD_API_ERRORS as error:
            errors.append(f"annotation: {_error_text(error)}")
    elif annotation_error:
        errors.append(f"annotation: {annotation_error}")
    return changed, errors


def _copy_property_annotations(graph, source_prop, target_prop):
    """只复制源/目标共同支持的注解，返回跳过或失败信息。"""
    skipped = []
    source_ids, source_error = _property_annotation_ids(graph, source_prop)
    target_ids, target_error = _property_annotation_ids(graph, target_prop)
    if source_error:
        skipped.append(("<source annotations>", source_error))
    if target_error:
        skipped.append(("<target annotations>", target_error))
    copy_source_ids = {
        annotation_id for annotation_id in source_ids
        if (annotation_id or "").lower() not in _IDENTITY_SETTING_IDS
    }
    for annotation_id in sorted(copy_source_ids - target_ids):
        skipped.append((annotation_id, "新参数不支持此注解"))
    for annotation_id in sorted(copy_source_ids & target_ids):
        try:
            value = graph.getPropertyAnnotationValueFromId(
                source_prop, annotation_id)
            if value is not None:
                graph.setPropertyAnnotationValueFromId(
                    target_prop, annotation_id, value)
        except _SD_API_ERRORS as error:
            skipped.append((annotation_id, _error_text(error)))
    return skipped


def _duplicate_exposed_parameter(graph, source_id, new_id, new_label):
    """创建一个真实参数副本；调用方负责 UndoGroup。"""
    if graph is None or SDPropertyCategory is None:
        raise RuntimeError("未找到当前 Graph 或 SDPropertyCategory API 不可用")
    if not source_id or not new_id:
        raise ValueError("源参数 ID 和新参数 ID 不能为空")
    try:
        source_prop = graph.getPropertyFromId(source_id, SDPropertyCategory.Input)
    except _SD_API_ERRORS as error:
        raise RuntimeError(_error_text(error))
    if source_prop is None:
        raise ValueError(f"当前图中未找到源参数: {source_id}")
    try:
        existing_prop = graph.getPropertyFromId(new_id, SDPropertyCategory.Input)
    except _SD_API_ERRORS as error:
        raise RuntimeError(_error_text(error))
    if existing_prop is not None:
        raise ValueError(f"参数 ID 已存在: {new_id}")
    try:
        if source_prop.isConnectable():
            raise ValueError("INPUTS 图像输入不能复制到 INPUT PARAMETERS")
    except AttributeError:
        pass

    warnings = []
    try:
        target_prop = graph.newProperty(
            new_id, source_prop.getType(), SDPropertyCategory.Input)
    except _SD_API_ERRORS as error:
        raise RuntimeError(_error_text(error))
    if target_prop is None:
        raise RuntimeError("graph.newProperty() 未能创建参数")
    warnings.extend(_copy_property_annotations(graph, source_prop, target_prop))
    warnings.extend(_copy_property_metadata(graph, source_prop, target_prop))

    _, label_errors = _set_property_text_setting(
        graph, target_prop, "label", new_label or new_id)
    for reason in label_errors:
        warnings.append(("label", reason))

    try:
        source_value = graph.getPropertyValue(source_prop)
        if source_value is not None:
            graph.setPropertyValue(target_prop, source_value)
    except _SD_API_ERRORS as error:
        warnings.append(("value", _error_text(error)))
    return new_id, warnings


def duplicate_exposed_parameter(graph, source_id, new_id, new_label):
    """在 Graph Input Parameters 中创建一个真实参数副本。"""
    with _undo_group("MaxSDPlugin 复制曝光参数"):
        return _duplicate_exposed_parameter(
            graph, source_id, new_id, new_label)


def duplicate_exposed_parameters(graph, copies):
    """批量创建真实参数副本，返回 {created, failed, warnings}。

    copies 每项为 {source_id, new_id, new_label}。所有成功创建项放在一个
    UndoGroup 中，可在 Designer 里一次 Ctrl+Z 撤销。
    """
    summary = {"created": [], "failed": [], "warnings": []}
    if graph is None or not copies:
        return summary
    try:
        with _undo_group("MaxSDPlugin 批量复制曝光参数"):
            for item in copies:
                source_id = item.get("source_id")
                new_id = item.get("new_id")
                try:
                    created_id, warnings = _duplicate_exposed_parameter(
                        graph, source_id, new_id, item.get("new_label"))
                    summary["created"].append(created_id)
                    for annotation_id, reason in warnings:
                        summary["warnings"].append(
                            (created_id, annotation_id, reason))
                except _SD_API_ERRORS as error:
                    summary["failed"].append(
                        (source_id, new_id, _error_text(error)))
    except _SD_API_ERRORS as error:
        print(f"{_LOG} 批量复制参数时出现异常，已尽量完成: {_error_text(error)}")
    return summary


def remove_copy_text(text):
    """移除独立的 Copy 单词，并清理多余空格、下划线和连字符。"""
    original = "" if text is None else str(text)
    cleaned = re.sub(
        r"(?i)(?<![A-Za-z0-9])copy(?![A-Za-z0-9])", "", original)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip(" _-")


def _replace_get_variable_references(graph, old_id, new_id):
    """把全图属性函数中的 Get Variable 从 old_id 更新为 new_id。"""
    changed = 0
    errors = []
    categories = [
        SDPropertyCategory.Input,
        SDPropertyCategory.Output,
        SDPropertyCategory.Annotation,
    ]
    try:
        nodes = graph.getNodes()
    except _SD_API_ERRORS as error:
        return changed, [("<nodes>", _error_text(error))]
    for node_index in range(len(nodes)):
        node = nodes[node_index]
        for category in categories:
            try:
                properties = node.getProperties(category)
            except _SD_API_ERRORS:
                continue
            for property_index in range(len(properties)):
                try:
                    property_graph = node.getPropertyGraph(
                        properties[property_index])
                except _SD_API_ERRORS:
                    property_graph = None
                if property_graph is None:
                    continue
                try:
                    function_nodes = property_graph.getNodes()
                except _SD_API_ERRORS:
                    continue
                for function_index in range(len(function_nodes)):
                    function_node = function_nodes[function_index]
                    if not _is_get_function_node(function_node):
                        continue
                    try:
                        current_value = function_node.getPropertyValueFromId(
                            "__constant__", SDPropertyCategory.Input)
                        if scalar_value_to_text(_value_to_str(current_value)) != old_id:
                            continue
                        new_value = _new_string_value(new_id)
                        if new_value is None:
                            raise RuntimeError("无法创建新的 Get Variable 字符串值")
                        function_node.setInputPropertyValueFromId(
                            "__constant__", new_value)
                        changed += 1
                    except _SD_API_ERRORS as error:
                        errors.append((old_id, _error_text(error)))
    return changed, errors


def remove_copy_from_parameters(graph, parameter_ids):
    """去除勾选参数 Label 和 ID 中独立的 Copy，返回迁移汇总。

    SDProperty ID 不支持原地重命名，因此 ID 变化时创建无 Copy 的新参数、
    更新 Get Variable 引用后删除旧参数。整批操作可一次 Ctrl+Z 撤销。
    """
    summary = {"renamed": [], "label_only": [], "unchanged": [], "failed": []}
    if graph is None or not parameter_ids or SDPropertyCategory is None:
        return summary
    requested_ids = list(dict.fromkeys(parameter_ids))
    plans = []
    planned_new_ids = []
    for old_id in requested_ids:
        try:
            prop = graph.getPropertyFromId(old_id, SDPropertyCategory.Input)
        except _SD_API_ERRORS as error:
            summary["failed"].append((old_id, _error_text(error)))
            continue
        if prop is None:
            summary["failed"].append((old_id, "当前图中未找到参数"))
            continue
        new_id = remove_copy_text(old_id)
        try:
            old_label = prop.getLabel() or old_id
        except _SD_API_ERRORS:
            old_label = old_id
        new_label = remove_copy_text(old_label) or new_id
        if not new_id:
            summary["failed"].append((old_id, "去除 Copy 后 ID 为空"))
            continue
        if new_id != old_id:
            try:
                conflict = graph.getPropertyFromId(
                    new_id, SDPropertyCategory.Input)
            except _SD_API_ERRORS as error:
                summary["failed"].append((old_id, _error_text(error)))
                continue
            if conflict is not None or new_id in planned_new_ids:
                summary["failed"].append((old_id, f"目标 ID 已存在: {new_id}"))
                continue
            planned_new_ids.append(new_id)
        plans.append((prop, old_id, old_label, new_id, new_label))

    try:
        with _undo_group("MaxSDPlugin 去除参数 Copy"):
            for prop, old_id, old_label, new_id, new_label in plans:
                if new_id == old_id:
                    if new_label == old_label:
                        summary["unchanged"].append(old_id)
                        continue
                    changed, errors = _set_property_text_setting(
                        graph, prop, "label", new_label)
                    if changed:
                        summary["label_only"].append(old_id)
                    if errors:
                        summary["failed"].append(
                            (old_id, "; ".join(errors)))
                    continue
                created_prop = None
                try:
                    created_id, warnings = _duplicate_exposed_parameter(
                        graph, old_id, new_id, new_label)
                    created_prop = graph.getPropertyFromId(
                        created_id, SDPropertyCategory.Input)
                    reference_count, reference_errors = (
                        _replace_get_variable_references(graph, old_id, new_id))
                    if reference_errors:
                        raise RuntimeError("; ".join(
                            reason for _, reason in reference_errors))
                    graph.deleteProperty(prop)
                    summary["renamed"].append(
                        (old_id, created_id, reference_count, len(warnings)))
                except _SD_API_ERRORS as error:
                    rollback_errors = []
                    _, reference_rollback_errors = (
                        _replace_get_variable_references(graph, new_id, old_id))
                    rollback_errors.extend(
                        reason for _, reason in reference_rollback_errors)
                    if created_prop is None:
                        try:
                            created_prop = graph.getPropertyFromId(
                                new_id, SDPropertyCategory.Input)
                        except _SD_API_ERRORS as rollback_error:
                            rollback_errors.append(_error_text(rollback_error))
                    if created_prop is not None:
                        try:
                            graph.deleteProperty(created_prop)
                        except _SD_API_ERRORS as rollback_error:
                            rollback_errors.append(_error_text(rollback_error))
                    reason = _error_text(error)
                    if rollback_errors:
                        reason += "; 回滚警告: " + "; ".join(rollback_errors)
                    summary["failed"].append((old_id, reason))
    except _SD_API_ERRORS as error:
        print(f"{_LOG} 去除参数 Copy 时出现异常: {_error_text(error)}")
    return summary


def update_exposed_parameter_settings(graph, updates):
    """批量更新曝光参数的 Label、Group 和标量当前值。

    updates 每项包含 id/label/group/value/type/value_changed。返回
    {updated, skipped}，整批操作可在 SD 中一次 Ctrl+Z 撤销。
    """
    summary = {"updated": [], "skipped": []}
    if graph is None or not updates or SDPropertyCategory is None:
        return summary

    def _update_one(item):
        parameter_id = item.get("id")
        try:
            prop = graph.getPropertyFromId(parameter_id, SDPropertyCategory.Input)
        except _SD_API_ERRORS:
            prop = None
        if prop is None:
            summary["skipped"].append((parameter_id, "当前图中未找到参数"))
            return
        field_errors = []
        changed = False
        for annotation_id, text in (
                ("label", item.get("label") or parameter_id),
                ("group", item.get("group") or "")):
            field_changed, errors = _set_property_text_setting(
                graph, prop, annotation_id, text)
            changed = changed or field_changed
            field_errors.extend(
                f"{annotation_id}: {reason}" for reason in errors)
        if item.get("value_changed"):
            try:
                value = _build_sdvalue(item.get("type"), item.get("value"))
                if value is None:
                    raise ValueError("该类型的当前值不支持文本批量修改")
                graph.setPropertyValue(prop, value)
                changed = True
            except _SD_API_ERRORS as error:
                field_errors.append(f"当前值: {_error_text(error)}")
        if changed:
            summary["updated"].append(parameter_id)
        if field_errors:
            summary["skipped"].append(
                (parameter_id, "; ".join(field_errors)))

    try:
        with _undo_group("MaxSDPlugin 批量修改曝光参数设置"):
            for item in updates:
                _update_one(item)
    except _SD_API_ERRORS as error:
        print(f"{_LOG} 批量修改参数设置时出现异常，已尽量完成: {_error_text(error)}")
    return summary


def _is_get_function_node(fnode):
    """判断函数图里的节点是不是一个「Get 变量」节点（get_float1 / get_integer1 ...）。"""
    try:
        d = fnode.getDefinition()
        did = (d.getId() or "") if d else ""
        if "get" in did.lower():
            return True
        lbl = (d.getLabel() or "") if d else ""
        return lbl.lower().startswith("get")
    except sdcompat.SD_API_ERRORS:
        return False


def _graph_input_ids(graph):
    """返回图所有输入参数 id 的集合，用于判定 Get 变量是否悬空（变量名仍在但参数已删）。"""
    ids = set()
    if graph is None or SDPropertyCategory is None:
        return ids
    try:
        props = graph.getProperties(SDPropertyCategory.Input)
        for i in range(len(props)):
            try:
                ids.add(props[i].getId())
            except sdcompat.SD_API_ERRORS:
                pass
    except sdcompat.SD_API_ERRORS:
        pass
    return ids


def _collect_get_var_status(func_graph, valid_ids=None):
    """收集一个属性函数图里所有 Get 节点引用的变量状态。

    返回 (names, has_empty):
      - names: 引用到的变量名集合（非空）。
      - has_empty: 是否存在「变量名为空」的 Get 节点（"Empty variable"）。
    可选 valid_ids：图的输入参数 id 集合。提供时，变量名既不在图输入、也不是图里
    存在的局部 Set 变量 → 视为悬空损坏。不提供则只判定空变量名（保守）。
    变量名存在 Get 节点的 `__constant__` 输入属性里（见官方 sample_sbs_parameter_function.py）。
    """
    names = set()
    has_empty = False
    if func_graph is None:
        return names, has_empty
    try:
        fnodes = func_graph.getNodes()
        n = len(fnodes)
    except sdcompat.SD_API_ERRORS:
        return names, has_empty
    set_names = _collect_set_var_names(func_graph)
    for i in range(n):
        try:
            fnode = fnodes[i]
        except sdcompat.SD_API_ERRORS:
            continue
        if not _is_get_function_node(fnode):
            continue
        try:
            cval = fnode.getPropertyValueFromId("__constant__", SDPropertyCategory.Input)
        except sdcompat.SD_API_ERRORS:
            cval = None
        if cval is None:
            has_empty = True
            continue
        try:
            s = scalar_value_to_text(_value_to_str(cval)) or ""
        except sdcompat.SD_API_ERRORS:
            s = ""
        if s == "":
            has_empty = True
        else:
            names.add(s)
            # 变量名非空，但既不是图输入也不是本图局部 Set 变量 → 悬空引用，算损坏
            if valid_ids is not None and s not in valid_ids and s not in set_names:
                has_empty = True
    return names, has_empty


def _collect_set_var_names(func_graph):
    """收集函数图里 Set 节点定义的局部变量名，避免把局部变量误判成悬空。"""
    out = set()
    try:
        fnodes = func_graph.getNodes()
        for i in range(len(fnodes)):
            fn = fnodes[i]
            try:
                d = fn.getDefinition()
                did = (d.getId() or "").lower() if d else ""
            except sdcompat.SD_API_ERRORS:
                did = ""
            if "set" not in did:
                continue
            try:
                cval = fn.getPropertyValueFromId("__constant__", SDPropertyCategory.Input)
                s = _strip_quotes(_value_to_str(cval)) or ""
                if s:
                    out.add(s)
            except sdcompat.SD_API_ERRORS:
                pass
    except sdcompat.SD_API_ERRORS:
        pass
    return out


def _reset_dependent_node_params(graph, var_ids):
    """删除前：重置引用 var_ids 的节点参数，并写回曝光参数当前值。

    趁变量还存在时缓存其原生 SDValue。删除属性函数后，通过
    SDNode.setPropertyValue(prop, value) 把曝光参数的当前值写成节点常量，
    避免节点回到曝光前的旧默认值。
    返回被重置的节点参数个数。
    """
    if not var_ids or SDPropertyCategory is None:
        return 0
    want = set(var_ids)
    current_values = {}
    for var_id in var_ids:
        try:
            exposed_prop = graph.getPropertyFromId(
                var_id, SDPropertyCategory.Input)
            if exposed_prop is not None:
                value = graph.getPropertyValue(exposed_prop)
                if value is not None:
                    current_values[var_id] = value
        except _SD_API_ERRORS as e:
            print(f"{_LOG} 读取曝光参数 {var_id} 当前值失败，将只重置函数: {e}")
    reset_count = 0
    try:
        nodes = graph.getNodes()
        ncount = len(nodes)
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 读取节点失败，跳过重置: {e}")
        return 0
    for i in range(ncount):
        try:
            node = nodes[i]
            props = node.getProperties(SDPropertyCategory.Input)
            pcount = len(props)
        except sdcompat.SD_API_ERRORS:
            continue
        for j in range(pcount):
            try:
                prop = props[j]
                pg = node.getPropertyGraph(prop)
            except sdcompat.SD_API_ERRORS:
                pg = None
            if not pg:
                continue
            try:
                names, _ = _collect_get_var_status(pg)
                matched_ids = names & want
                if matched_ids:
                    node.deletePropertyGraph(prop)
                    reset_count += 1
                    writable_ids = [
                        var_id for var_id in matched_ids
                        if var_id in current_values
                    ]
                    if len(writable_ids) == 1:
                        try:
                            node.setPropertyValue(
                                prop, current_values[writable_ids[0]])
                        except _SD_API_ERRORS as e:
                            print(f"{_LOG} 节点参数已重置，但写回曝光参数当前值失败: {e}")
                    elif len(writable_ids) > 1:
                        print(
                            f"{_LOG} 节点参数同时引用多个待删除曝光参数，"
                            "已重置但跳过当前值写回"
                        )
            except _SD_API_ERRORS as e:
                print(f"{_LOG} 重置某节点参数失败（已跳过）: {e}")
    return reset_count


def _reset_broken_node_functions(graph, deleted_ids, node_ids=None):
    """删除后：扫描全图，把「损坏的 Get 函数」驱动的节点参数重置回常量值。

    这是用户要的「扫描 SD Graph、找到这些有警告的参数并重置」思路：删除图输入后，
    其 Get 节点的变量名会变空（日志中的 Empty variable / Some Get nodes...），
    据此判定损坏并重置。判定条件（命中其一即重置）：
      - 该函数含变量名为空的 Get 节点；或
      - 该函数引用了刚被删除的某个变量（deleted_ids）。
    只针对 Get 节点判定，避免误伤使用了局部变量的复杂函数。
    返回重置个数。
    """
    if SDPropertyCategory is None:
        return 0
    deleted = set(deleted_ids or [])
    only = set(node_ids) if node_ids else None  # 仅重置这些节点；None=全图
    valid_ids = _graph_input_ids(graph)  # 用于判定悬空 Get（变量名仍在但参数已删）
    reset_count = 0
    # 全图节点的所有属性类别都可能挂着损坏函数（Input 参数最常见，Output/Annotation 兜底）
    categories = [SDPropertyCategory.Input, SDPropertyCategory.Output, SDPropertyCategory.Annotation]
    try:
        nodes = graph.getNodes()
        ncount = len(nodes)
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 读取节点失败，跳过损坏函数扫描: {e}")
        return 0
    for i in range(ncount):
        try:
            node = nodes[i]
        except sdcompat.SD_API_ERRORS:
            continue
        if only is not None:
            try:
                if (node.getIdentifier() or "") not in only:
                    continue
            except sdcompat.SD_API_ERRORS:
                continue
        for cat in categories:
            try:
                props = node.getProperties(cat)
                pcount = len(props)
            except sdcompat.SD_API_ERRORS:
                continue
            for j in range(pcount):
                try:
                    prop = props[j]
                    pg = node.getPropertyGraph(prop)
                except sdcompat.SD_API_ERRORS:
                    pg = None
                if not pg:
                    continue
                try:
                    names, has_empty = _collect_get_var_status(pg, valid_ids)
                    input_is_empty = not _property_has_nonempty_input_value(
                        node, prop)
                    if input_is_empty and (has_empty or (names & deleted)):
                        node.deletePropertyGraph(prop)
                        reset_count += 1
                except sdcompat.SD_API_ERRORS as e:
                    print(f"{_LOG} 重置某损坏节点参数失败（已跳过）: {e}")
    return reset_count


def delete_exposed_parameters(graph, ids):
    """删除（取消暴露）指定 id 的输入属性。返回 (deleted, failed, reset)。

    - deleted: 成功删除的 id 列表。
    - failed: [(id, 原因)]。
    - reset: 被重置回常量值的节点参数个数。
    流程（同一个 UndoGroup 内，可在 SD 里一次性 Ctrl+Z 撤销）：
            1) 删除前：缓存曝光参数当前值，重置引用函数并把当前值写成节点常量。
      2) 删除图层级的输入属性本身。
      3) 删除后：再扫描全图，重置仍残留的「损坏 Get 函数」（变量名已变空的）。
    """
    deleted, failed = [], []
    reset = 0
    if graph is None or not ids or SDPropertyCategory is None:
        return deleted, failed, reset
    ids = list(ids)

    def _do():
        nonlocal reset
        # 1) 删除前重置，并把曝光参数当前值写成节点常量
        reset += _reset_dependent_node_params(graph, ids)
        # 2) 删除图输入属性
        for pid in ids:
            try:
                prop = graph.getPropertyFromId(pid, SDPropertyCategory.Input)
                if prop is None:
                    failed.append((pid, "当前图中未找到该参数"))
                    continue
                graph.deleteProperty(prop)
                deleted.append(pid)
            except sdcompat.SD_API_ERRORS as e:
                failed.append((pid, str(e)))
        # 3) 删除后兜底：扫描并重置残留的损坏 Get 函数（变量名已空）
        reset += _reset_broken_node_functions(graph, ids)

    try:
        with _undo_group("MaxSDPlugin 删除曝光参数"):
            _do()
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 删除时出现异常，已尽量完成: {e}")
    print(f"{_LOG} 删除完成：成功 {len(deleted)} 个，失败 {len(failed)} 个，重置节点参数 {reset} 个")
    return deleted, failed, reset


def _node_label(node):
    """节点显示名：定义标签 + 标识符，便于在图里定位。"""
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


def collect_broken_nodes(graph):
    """列出曝光参数输入已丢失、会显示 Empty variable 警告的节点。

    返回 list[dict]: {id, label, prop, warnings} ——
      - id: 节点标识，用于 Goto / 删除；
      - prop: 首个丢失曝光参数输入的节点属性名；
      - warnings: ["参数输入丢失（Empty variable）"]。
    正常的曝光参数函数不算损坏；资源、连线等其它警告由 Publish Checker 负责。
    只读，不修改图。
    """
    out = []
    if graph is None or SDPropertyCategory is None:
        return out
    valid_ids = _graph_input_ids(graph)
    categories = [SDPropertyCategory.Input, SDPropertyCategory.Output, SDPropertyCategory.Annotation]
    try:
        nodes = graph.getNodes()
        ncount = len(nodes)
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 读取节点失败，跳过损坏节点扫描: {e}")
        return out
    for i in range(ncount):
        try:
            node = nodes[i]
            nid = node.getIdentifier() or ""
        except sdcompat.SD_API_ERRORS:
            continue
        broken_prop = ""
        for cat in categories:
            try:
                props = node.getProperties(cat)
            except sdcompat.SD_API_ERRORS:
                continue
            for j in range(len(props)):
                try:
                    pg = node.getPropertyGraph(props[j])
                    if not pg:
                        continue
                    _, has_empty = _collect_get_var_status(pg, valid_ids)
                    if has_empty and not _property_has_nonempty_input_value(
                            node, props[j]):
                        broken_prop = props[j].getId()
                        break
                except sdcompat.SD_API_ERRORS:
                    continue
            if broken_prop:
                break
        if broken_prop:
            out.append({"id": nid, "label": _node_label(node), "prop": broken_prop,
                        "warnings": ["参数输入丢失（Empty variable）"]})
    return out


def delete_node(graph, node_id):
    """删除图中指定 id 的节点。返回 (ok, 信息)。包 UndoGroup，可 Ctrl+Z 撤销。"""
    if graph is None or not node_id:
        return False, "缺少图或节点 id。"
    try:
        node = graph.getNodeFromId(node_id)
        if node is None:
            return False, f"未找到节点: {node_id}"
        with _undo_group("MaxSDPlugin 删除节点"):
            graph.deleteNode(node)
        return True, ""
    except sdcompat.SD_API_ERRORS as e:
        return False, f"删除失败: {e}"



def goto_node(graph, node_id, app=None):
    """在图视图里定位/选中指定节点。返回 (ok, 信息)。

    跨版本逻辑统一收敛到 sdcompat.focus_node（多策略探测 + 优雅降级），
    这里只做转发，避免在功能模块里硬编码版本脆弱的接口。
    """
    return sdcompat.focus_node(graph, node_id, app)


def repair_broken_node_functions(graph, node_ids=None):
    """扫描全图并重置「损坏的 Get 函数」（变量名已空）回常量值，返回重置个数。

    node_ids=None 表示修全图；传入节点 id 列表则只修这些节点。
    用途：之前删除暴露参数时没重置节点参数，已经在画布上留下一堆悬空的 Get 变量
    （SD 日志里的 "Empty variable" / "Some Get nodes don't have a variable name"）。
    本函数直接扫描修复这些参数，无需再次删除。包在 UndoGroup 里，可 Ctrl+Z 撤销。
    """
    if graph is None or SDPropertyCategory is None:
        return 0
    reset = 0
    try:
        with _undo_group("MaxSDPlugin 重置损坏的节点函数"):
            reset = _reset_broken_node_functions(graph, [], node_ids=node_ids)
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 重置损坏函数时出现异常，已尽量完成: {e}")
    print(f"{_LOG} 重置损坏函数完成：共重置 {reset} 个节点参数")
    return reset


def _build_sdvalue(type_id, raw):
    """据类型把字符串值还原成 SDValue；不支持的类型返回 None。

    仅支持常见标量类型（float / int / bool / string）。向量、枚举、颜色等复杂
    类型暂不自动还原（无 SDValueSerializer.sFromString，逐类型构造不可靠），交由调用方报告跳过。
    """
    if raw is None:
        return None
    tid = (type_id or "").lower()
    scalar_text = scalar_value_to_text(raw)
    try:
        if "string" in tid:
            from sd.api.sdvaluestring import SDValueString
            return SDValueString.sNew(scalar_text)
        if "bool" in tid:
            from sd.api.sdvaluebool import SDValueBool
            return SDValueBool.sNew(scalar_text.lower() in ("1", "true", "yes"))
        # 整型：放在 float 判断之前，避免被 "float" 子串误命中
        if tid.endswith("int") or tid in ("int", "integer") or "int1" in tid:
            from sd.api.sdvalueint import SDValueInt
            return SDValueInt.sNew(int(float(scalar_text)))
        if "float" in tid and not any(v in tid for v in ("float2", "float3", "float4")):
            from sd.api.sdvaluefloat import SDValueFloat
            return SDValueFloat.sNew(float(scalar_text))
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 还原值失败（type={type_id}, raw={raw}）: {e}")
        return None
    return None


def apply_output_data(graph, data):
    """把 OutputData 记录的参数值，应用回当前图中【仍然存在】的同名暴露参数。

    返回 summary: {restored, missing, skipped}
    - restored: 成功还原值的 id 列表。
    - missing: OutputData 里有、但当前图已不存在的参数 id（无法通过 API 重新暴露）。
    - skipped: [(id, 原因)]，类型不支持自动还原 / 还原失败。
    整个操作包在一个 UndoGroup 里，可在 SD 中一次性撤销。
    """
    summary = {"restored": [], "missing": [], "skipped": []}
    if graph is None or not isinstance(data, dict) or SDPropertyCategory is None:
        return summary
    params = data.get("exposed_parameters", []) or []

    def _apply_one(p):
        pid = p.get("id")
        try:
            prop = graph.getPropertyFromId(pid, SDPropertyCategory.Input)
        except sdcompat.SD_API_ERRORS:
            prop = None
        if prop is None:
            summary["missing"].append(pid)
            return
        sdval = _build_sdvalue(p.get("type"), p.get("value"))
        if sdval is None:
            summary["skipped"].append((pid, "类型不支持自动还原"))
            return
        try:
            graph.setPropertyValue(prop, sdval)
            summary["restored"].append(pid)
        except sdcompat.SD_API_ERRORS as e:
            summary["skipped"].append((pid, str(e)))

    try:
        with _undo_group("MaxSDPlugin 加载并应用 OutputData"):
            for p in params:
                _apply_one(p)
    except sdcompat.SD_API_ERRORS as e:
        print(f"{_LOG} 应用时出现异常，已尽量完成: {e}")
    print(
        f"{_LOG} 应用完成：还原 {len(summary['restored'])} 个，"
        f"缺失 {len(summary['missing'])} 个，跳过 {len(summary['skipped'])} 个"
    )
    return summary
