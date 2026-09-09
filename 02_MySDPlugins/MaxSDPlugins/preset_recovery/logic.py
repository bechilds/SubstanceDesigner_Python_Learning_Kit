# -*- coding: utf-8 -*-
"""预设效果找回的解析、匹配与 Graph Preset 写入逻辑。"""

import contextlib
import math
import re
import xml.etree.ElementTree as ET

from .. import sdcompat

_LOG = "[MaxSDPlugin/preset_recovery]"

try:
    from sd.api.sdproperty import SDPropertyCategory
except Exception:
    SDPropertyCategory = None

APIException = sdcompat.APIException
_SD_ERRORS = sdcompat.SD_API_ERRORS


def _local_name(tag):
    """移除 XML 命名空间并返回小写标签名。"""
    return str(tag).rsplit("}", 1)[-1].lower()


def _attribute(element, *names):
    """按不区分大小写的属性名读取第一个非空值。"""
    attributes = {str(key).lower(): value for key, value in element.attrib.items()}
    for name in names:
        value = attributes.get(name.lower())
        if value is not None:
            return str(value)
    return ""


def _attribute_name(element, *names):
    """返回元素中实际存在的属性名，保留原始大小写。"""
    candidates = {name.lower() for name in names}
    for key in element.attrib:
        if str(key).lower() in candidates:
            return key
    return ""


def parse_preset_file(path):
    """解析 .sbsprs，返回预设列表；格式错误时抛出 ValueError。"""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError(f"无法读取预设文件: {error}") from error

    preset_elements = [
        element for element in root.iter()
        if _local_name(element.tag) in ("sbspreset", "preset")
    ]
    if not preset_elements:
        preset_elements = [root]

    presets = []
    for preset_index, preset_element in enumerate(preset_elements, 1):
        inputs = []
        input_elements = [
            element for element in preset_element.iter()
            if _local_name(element.tag) in ("presetinput", "input")
        ]
        for input_index, element in enumerate(input_elements):
            if _local_name(element.tag) not in ("presetinput", "input"):
                continue
            name_attribute = _attribute_name(
                element, "identifier", "id", "name", "label")
            source_name = str(element.attrib.get(name_attribute, ""))
            value = _attribute(element, "value")
            if not source_name or value == "":
                continue
            inputs.append({
                "source_name": source_name,
                "name_attribute": name_attribute,
                "xml_index": input_index,
                "type": _attribute(element, "type", "datatype"),
                "value": value,
            })
        if inputs:
            presets.append({
                "name": _attribute(preset_element, "label", "name", "identifier")
                        or f"预设 {preset_index}",
                "target": _attribute(
                    preset_element, "pkgurl", "packageurl", "graph", "url"),
                "xml_index": preset_index - 1,
                "inputs": inputs,
            })
    if not presets:
        raise ValueError("文件中没有找到可读取的 presetinput 参数。")
    return presets


def describe_graph(graph):
    """返回当前 Graph 的文件路径、Identifier 和 URL，仅用于界面确认。"""
    description = {"package_path": "", "identifier": "", "url": ""}
    if graph is None:
        return description
    try:
        description["identifier"] = str(graph.getIdentifier() or "")
    except _SD_ERRORS:
        pass
    try:
        description["url"] = str(graph.getUrl() or "")
    except _SD_ERRORS:
        pass
    try:
        package = graph.getPackage()
        if package is not None:
            description["package_path"] = str(package.getFilePath() or "")
    except _SD_ERRORS:
        pass
    return description


def collect_target_parameters(graph):
    """收集当前 Graph 的非内置输入参数。"""
    parameters = []
    if graph is None or SDPropertyCategory is None:
        return parameters
    try:
        properties = graph.getProperties(SDPropertyCategory.Input)
        for index in range(len(properties)):
            prop = properties[index]
            identifier = str(prop.getId() or "")
            if not identifier or identifier.startswith("$"):
                continue
            try:
                if prop.isConnectable():
                    continue
            except _SD_ERRORS:
                pass
            parameters.append({
                "id": identifier,
                "label": str(prop.getLabel() or identifier),
                "type": _type_id(prop),
                "editor": _read_editor(graph, prop),
            })
    except _SD_ERRORS as error:
        print(f"{_LOG} 读取当前 Graph 参数失败: {error}")
    return parameters


def _type_id(prop):
    try:
        prop_type = prop.getType()
        return str(prop_type.getId() if hasattr(prop_type, "getId") else prop_type)
    except _SD_ERRORS:
        return ""


def _read_editor(graph, prop):
    """读取参数 editor 注解；不存在时返回空串。"""
    try:
        value = graph.getPropertyAnnotationValueFromId(prop, "editor")
        if value is None:
            return ""
        getter = getattr(value, "get", None)
        if callable(getter):
            return str(getter() or "")
        from sd.api.sdvalueserializer import SDValueSerializer
        text = str(SDValueSerializer.sToString(value) or "").strip()
        wrapper = re.match(r"^[A-Za-z_][A-Za-z0-9_]*\((.*)\)$", text)
        while wrapper is not None:
            text = wrapper.group(1).strip()
            wrapper = re.match(r"^[A-Za-z_][A-Za-z0-9_]*\((.*)\)$", text)
        return text.strip("\"'")
    except _SD_ERRORS:
        return ""


def build_mappings(inputs, targets):
    """按当前 Identifier 自动匹配预设参数；返回带 target_id 的行。"""
    exact = {target["id"]: target["id"] for target in targets}
    folded = {target["id"].casefold(): target["id"] for target in targets}
    mappings = []
    for item in inputs:
        source_name = item["source_name"]
        target_id = exact.get(source_name) or folded.get(source_name.casefold()) or ""
        mapping = dict(item)
        mapping["target_id"] = target_id
        mapping["auto_target_id"] = target_id
        mappings.append(mapping)
    return mappings


def collect_preset_labels(graph):
    """返回当前 Graph 的 Presets 名称列表。"""
    labels = []
    try:
        presets = graph.getPresets()
        for index in range(len(presets)):
            labels.append(str(presets[index].getLabel() or ""))
    except _SD_ERRORS as error:
        print(f"{_LOG} 读取当前 Graph Presets 失败: {error}")
    return [label for label in labels if label]


def _undo_group(name):
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        return SDHistoryUtils.UndoGroup(name)
    except Exception:
        return contextlib.nullcontext()


def _components(raw, count, converter):
    parts = [part.strip() for part in str(raw).split(",")]
    if len(parts) != count:
        raise ValueError(f"需要 {count} 个分量，实际得到 {len(parts)} 个")
    values = [converter(part) for part in parts]
    if converter is float and not all(math.isfinite(value) for value in values):
        raise ValueError("数值包含 NaN 或 Infinity")
    return values


def _boolean_value(raw):
    text = str(raw).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise ValueError("布尔值必须是 true/false、yes/no、on/off 或 1/0")


def _effective_type(type_id, editor):
    """用 Editor 表现补充底层类型判定，但不修改参数自身类型。"""
    target_type = (type_id or "").lower()
    editor_type = re.sub(r"[^a-z0-9]", "", (editor or "").lower())
    if "bool" in editor_type or "toggle" in editor_type:
        return "bool"
    if "dropdown" in editor_type or "enum" in editor_type or "combobox" in editor_type:
        return "int"
    if "colorrgba" in editor_type:
        return "float4"
    if "colorrgb" in editor_type:
        return "float3"
    if "position" in editor_type and not any(
            dimension in target_type for dimension in ("float2", "float3", "float4")):
        return "float2"
    if "angle" in editor_type or "slider" in editor_type:
        return target_type or "float"
    return target_type


def describe_editor_conversion(target):
    """返回供 UI 核对的 `Editor -> 原生类型` 文本。"""
    editor = target.get("editor") or "默认"
    native_type = _effective_type(target.get("type", ""), target.get("editor", ""))
    return f"{editor} → {native_type or '未知'}"


def _build_sdvalue(type_id, editor, file_type, raw):
    """根据当前目标参数底层类型和 Editor 构造原生 SDValue。"""
    target_type = _effective_type(type_id, editor)
    type_code = str(file_type or "")
    if not target_type:
        target_type = {
            "0": "float", "1": "float2", "2": "float3", "3": "float4",
            "4": "int", "6": "string", "8": "int2", "9": "int3",
            "10": "int4",
        }.get(type_code, "")
    try:
        if "string" in target_type:
            from sd.api.sdvaluestring import SDValueString
            return SDValueString.sNew(str(raw))
        if "bool" in target_type:
            from sd.api.sdvaluebool import SDValueBool
            return SDValueBool.sNew(_boolean_value(raw))
        for count in (2, 3, 4):
            if f"int{count}" in target_type:
                from sd.api import sdbasetypes
                module = __import__(f"sd.api.sdvalueint{count}", fromlist=[f"SDValueInt{count}"])
                value_class = getattr(module, f"SDValueInt{count}")
                base_class = getattr(sdbasetypes, f"int{count}")
                return value_class.sNew(base_class(*_components(raw, count, lambda text: int(float(text)))))
        if "int" in target_type or "enum" in target_type:
            from sd.api.sdvalueint import SDValueInt
            return SDValueInt.sNew(int(float(str(raw).strip())))
        for count in (2, 3, 4):
            if f"float{count}" in target_type or f"color{count}" in target_type:
                from sd.api import sdbasetypes
                module = __import__(f"sd.api.sdvaluefloat{count}", fromlist=[f"SDValueFloat{count}"])
                value_class = getattr(module, f"SDValueFloat{count}")
                base_class = getattr(sdbasetypes, f"float{count}")
                return value_class.sNew(base_class(*_components(raw, count, float)))
        if "float" in target_type or "double" in target_type:
            value = float(str(raw).strip())
            if not math.isfinite(value):
                raise ValueError("数值包含 NaN 或 Infinity")
            from sd.api.sdvaluefloat import SDValueFloat
            return SDValueFloat.sNew(value)
    except _SD_ERRORS as error:
        target_description = type_id or type_code
        if editor:
            target_description += f" / Editor={editor}"
        raise ValueError(f"值 '{raw}' 无法转换为 {target_description}: {error}") from error
    target_description = type_id or type_code or "未知"
    if editor:
        target_description += f" / Editor={editor}"
    raise ValueError(f"暂不支持目标参数类型: {target_description}")


def prepare_preset_inputs(mappings, targets):
    """先校验并构造全部 Preset 输入，任何一项失败都不修改 Graph。"""
    targets_by_id = {target["id"]: target for target in targets}
    prepared = []
    errors = []
    seen_ids = set()
    for mapping in mappings:
        target_id = mapping.get("target_id") or ""
        if not target_id:
            continue
        target = targets_by_id.get(target_id)
        if target is None:
            errors.append((mapping.get("source_name", ""), "目标参数不存在"))
            continue
        if target_id in seen_ids:
            errors.append((mapping.get("source_name", ""), f"目标 Identifier 重复: {target_id}"))
            continue
        try:
            value = _build_sdvalue(
                target.get("type", ""), target.get("editor", ""),
                mapping.get("type", ""), mapping.get("value", ""))
            prepared.append((target_id, value))
            seen_ids.add(target_id)
        except ValueError as error:
            errors.append((mapping.get("source_name", ""), str(error)))
    return prepared, errors


def _snapshot_preset(preset):
    tags = str(preset.getUserTags() or "")
    inputs = []
    preset_inputs = preset.getInputs()
    for index in range(len(preset_inputs)):
        item = preset_inputs[index]
        inputs.append((str(item.getIdentifier() or ""), item.getValue()))
    return tags, inputs


def _restore_preset(graph, label, snapshot):
    restored = graph.newPreset(label)
    tags, inputs = snapshot
    if tags:
        restored.setUserTags(tags)
    for identifier, value in inputs:
        restored.addInput(identifier, value)


def create_or_replace_preset(graph, label, prepared_inputs, overwrite=False):
    """在当前 Graph 的 Presets 中新建或完整覆盖同名预设。"""
    label = str(label or "").strip()
    if not label:
        raise ValueError("预设名称不能为空。")
    if not prepared_inputs:
        raise ValueError("没有可写入的预设参数。")
    try:
        existing = graph.getPreset(label)
    except _SD_ERRORS as error:
        raise ValueError(f"读取同名预设失败: {error}") from error
    if existing is not None and not overwrite:
        raise ValueError(f"当前 Graph 已存在同名预设: {label}")

    try:
        snapshot = _snapshot_preset(existing) if existing is not None else None
    except _SD_ERRORS as error:
        raise ValueError(
            f"备份同名 Preset 失败，已取消覆盖: {str(error) or type(error).__name__}") from error
    try:
        with _undo_group("MaxSDPlugin 创建或覆盖 Graph Preset"):
            if existing is not None:
                graph.deletePreset(label)
            try:
                created = graph.newPreset(label)
                for identifier, value in prepared_inputs:
                    created.addInput(identifier, value)
            except _SD_ERRORS as write_error:
                try:
                    # 创建也可能在抛错前留下半成品；仅在确实存在时清理。
                    if graph.getPreset(label) is not None:
                        graph.deletePreset(label)
                    if snapshot is not None:
                        _restore_preset(graph, label, snapshot)
                except _SD_ERRORS as recovery_error:
                    raise ValueError(
                        f"写入失败: {str(write_error) or type(write_error).__name__}；"
                        f"恢复失败: {str(recovery_error) or type(recovery_error).__name__}。"
                        "请检查当前 Preset，尝试撤销；确认恢复前不要保存 SBS。"
                    ) from write_error
                raise
    except _SD_ERRORS as error:
        raise ValueError(f"创建 Preset 失败: {str(error) or type(error).__name__}") from error
    print(f"{_LOG} 已{'覆盖' if snapshot is not None else '创建'} Graph Preset: {label}")
    return "replaced" if snapshot is not None else "created"
