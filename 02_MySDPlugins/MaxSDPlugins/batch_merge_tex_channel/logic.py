# -*- coding: utf-8 -*-
"""BatchMergeTexChannel 数据层：文件分组、SBS 契约检查与纹理计算。"""

import os
import re
import shutil
import tempfile

from .. import sdcompat

_LOG = "[MaxSDPlugin/BatchMergeTexChannel]"

GRAPH_ID = "Substance_graph"
OUTPUT_ID = "output"
IMAGE_EXTENSIONS = {".png", ".tga", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp", ".exr"}

INPUTS = (
    ("color", "InputColorMap", "Color Map"),
    ("gray01", "InputGrayMap01", "Gray Map 01"),
    ("gray02", "InputGrayMap02", "Gray Map 02"),
    ("gray03", "InputGrayMap03", "Gray Map 03"),
    ("gray04", "InputGrayMap04", "Gray Map 04"),
)

OUTPUT_CHANNELS = (
    ("r", "Channel R", "ChannelR"),
    ("g", "Channel G", "ChannelG"),
    ("b", "Channel B", "ChannelB"),
    ("a", "Channel A", "ChannelA"),
)

# 每个输出通道可从 ColorMap 的 RGBA 或四张 GrayMap 中选择一个来源。
CHANNEL_SOURCES = (
    ("color_r", "ColorMap R", "ColorMapR_On", "color"),
    ("color_g", "ColorMap G", "ColorMapG_On", "color"),
    ("color_b", "ColorMap B", "ColorMapB_On", "color"),
    ("color_a", "ColorMap A", "ColorMapA_On", "color"),
    ("gray01", "GrayMap 01", "GrayMap01_On", "gray01"),
    ("gray02", "GrayMap 02", "GrayMap02_On", "gray02"),
    ("gray03", "GrayMap 03", "GrayMap03_On", "gray03"),
    ("gray04", "GrayMap 04", "GrayMap04_On", "gray04"),
)

SWITCHES = tuple(
    (f"{channel_key}_{source_key}", f"{channel_label} / {source_label}",
     f"{channel_prefix}_{source_suffix}", input_key)
    for channel_key, channel_label, channel_prefix in OUTPUT_CHANNELS
    for source_key, source_label, source_suffix, input_key in CHANNEL_SOURCES
)

try:
    from sd.api.sdproperty import SDPropertyCategory
    from sd.api.sdtexture import SDTexture
    from sd.api.sdvaluebool import SDValueBool
    from sd.api.sdvaluetexture import SDValueTexture
except sdcompat.SD_API_ERRORS:  # pragma: no cover - 仅普通 Python 环境
    SDPropertyCategory = None
    SDTexture = None
    SDValueBool = None
    SDValueTexture = None


def _as_list(value):
    try:
        return list(value)
    except sdcompat.SD_API_ERRORS:
        result = []
        try:
            for index in range(len(value)):
                result.append(value[index])
        except sdcompat.SD_API_ERRORS:
            pass
        return result


def _clean_group_name(text):
    text = re.sub(r"[\s._\-]+", "_", text).strip("_")
    return text or "merged"


def _remove_keyword(stem, keyword):
    """从文件名中移除首次出现的关键字，得到不区分大小写的分组名。"""
    index = stem.lower().find(keyword.lower())
    if index < 0:
        return ""
    return _clean_group_name(stem[:index] + stem[index + len(keyword):])


def scan_texture_groups(source_folder, keywords, recursive=True):
    """按自定义关键字扫描并分组贴图，不访问任何 SD API。

    返回按 group 排序的列表；每项包含 files、duplicates 和 source_files。
    同一文件只匹配关键字最长的输入，避免短关键字抢占。
    """
    groups = {}
    if not source_folder or not os.path.isdir(source_folder):
        return []
    keyword_items = [
        (key, str(keywords.get(key, "")).strip())
        for key, _property_id, _label in INPUTS
        if str(keywords.get(key, "")).strip()
    ]
    keyword_items.sort(key=lambda item: len(item[1]), reverse=True)
    walker = os.walk(source_folder)
    for folder, _directories, names in walker:
        for name in names:
            extension = os.path.splitext(name)[1].lower()
            if extension not in IMAGE_EXTENSIONS:
                continue
            stem = os.path.splitext(name)[0]
            matched_key = ""
            matched_keyword = ""
            for key, keyword in keyword_items:
                if keyword.lower() in stem.lower():
                    matched_key = key
                    matched_keyword = keyword
                    break
            if not matched_key:
                continue
            group_name = _remove_keyword(stem, matched_keyword)
            path = os.path.join(folder, name)
            item = groups.setdefault(group_name.lower(), {
                "group": group_name,
                "files": {},
                "duplicates": {},
                "source_files": [],
            })
            item["source_files"].append(path)
            if matched_key in item["files"]:
                item["duplicates"].setdefault(matched_key, [item["files"][matched_key]]).append(path)
            else:
                item["files"][matched_key] = path
        if not recursive:
            break
    return sorted(groups.values(), key=lambda item: item["group"].lower())


def validate_channel_assignments(channel_assignments):
    """检查 RGBA 是否都且仅选择一个合法来源。"""
    errors = []
    valid_sources = {source_key for source_key, _label, _suffix, _input_key in CHANNEL_SOURCES}
    for channel_key, channel_label, _prefix in OUTPUT_CHANNELS:
        source_key = channel_assignments.get(channel_key)
        if source_key not in valid_sources:
            errors.append(f"{channel_label} 未选择有效来源")
    return errors


def validate_group(group, channel_assignments):
    """根据 RGBA 来源配置检查一组文件是否齐全，返回错误文本列表。"""
    errors = []
    errors.extend(validate_channel_assignments(channel_assignments))
    source_inputs = {
        source_key: input_key
        for source_key, _label, _suffix, input_key in CHANNEL_SOURCES
    }
    required_inputs = {
        source_inputs[source_key]
        for source_key in channel_assignments.values()
        if source_key in source_inputs
    }
    for input_key in sorted(required_inputs):
        if input_key not in group.get("files", {}):
            errors.append(f"缺少 {input_key}")
    for input_key in group.get("duplicates", {}):
        errors.append(f"{input_key} 匹配到多个文件")
    return errors


def default_sbs_path():
    """返回插件根目录中的 BatchMergeTexChannel.sbs。"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "BatchMergeTexChannel.sbs")


def _find_graph(package):
    try:
        resources = _as_list(package.getChildrenResources(True))
    except sdcompat.SD_API_ERRORS:
        resources = []
    for resource in resources:
        try:
            if resource.getIdentifier() == GRAPH_ID and hasattr(resource, "compute"):
                return resource
        except sdcompat.SD_API_ERRORS:
            continue
    return None


def load_processor(app=None, sbs_path=None):
    """加载处理 SBS 并返回处理上下文；调用方结束后必须 cleanup_processor。"""
    app = sdcompat.get_app(app)
    sbs_path = os.path.abspath(sbs_path or default_sbs_path())
    if app is None:
        raise RuntimeError("未找到 SDApplication。")
    if not os.path.isfile(sbs_path):
        raise FileNotFoundError(f"未找到处理文件: {sbs_path}")
    package_mgr = app.getPackageMgr()
    temp_folder = tempfile.mkdtemp(prefix="MaxSD_BatchMerge_")
    temp_sbs_path = os.path.join(temp_folder, os.path.basename(sbs_path))
    package = None
    try:
        shutil.copy2(sbs_path, temp_sbs_path)
        package = package_mgr.loadUserPackage(temp_sbs_path, True, False)
    except sdcompat.SD_API_ERRORS:
        shutil.rmtree(temp_folder, ignore_errors=True)
        raise
    graph = _find_graph(package)
    if graph is None:
        if package is not None:
            package_mgr.unloadUserPackage(package)
        shutil.rmtree(temp_folder, ignore_errors=True)
        raise RuntimeError(f"SBS 中未找到 Graph: {GRAPH_ID}")
    expected_input_ids = (
        [property_id for _key, property_id, _label in INPUTS]
        + [property_id for _key, _label, property_id, _input_key in SWITCHES]
    )
    input_ids = set()
    output_ids = set()
    lookup_errors = []
    for property_id in expected_input_ids:
        try:
            prop = graph.getPropertyFromId(property_id, SDPropertyCategory.Input)
            if prop is not None:
                input_ids.add(property_id)
        except sdcompat.SD_API_ERRORS as error:
            lookup_errors.append(f"读取输入 {property_id} 失败: {error}")
    try:
        output_property = graph.getPropertyFromId(OUTPUT_ID, SDPropertyCategory.Output)
        if output_property is not None:
            output_ids.add(OUTPUT_ID)
    except sdcompat.SD_API_ERRORS as error:
        lookup_errors.append(f"读取输出 {OUTPUT_ID} 失败: {error}")
    resolved_switches = {}
    missing_switches = []
    for switch_key, label, property_id, _input_key in SWITCHES:
        resolved_switches[switch_key] = property_id if property_id in input_ids else ""
        if property_id not in input_ids:
            missing_switches.append(f"{label}: {property_id}")
    missing_inputs = [property_id for _key, property_id, _label in INPUTS if property_id not in input_ids]
    errors = []
    if lookup_errors:
        errors.append("SBS 接口读取失败: " + "; ".join(lookup_errors))
    if missing_inputs:
        errors.append("缺少贴图输入: " + ", ".join(missing_inputs))
    if missing_switches:
        errors.append("缺少通道开关: " + "; ".join(missing_switches))
    if OUTPUT_ID not in output_ids:
        errors.append(f"缺少输出属性: {OUTPUT_ID}")
    return {
        "app": app,
        "package_mgr": package_mgr,
        "package": package,
        "graph": graph,
        "owns_package": True,
        "temp_folder": temp_folder,
        "input_ids": input_ids,
        "output_ids": output_ids,
        "switch_ids": resolved_switches,
        "missing_switches": missing_switches,
        "errors": errors,
        "sbs_path": sbs_path,
    }


def cleanup_processor(context):
    if not context or not context.get("owns_package"):
        return
    try:
        context["package_mgr"].unloadUserPackage(context["package"])
    except sdcompat.SD_API_ERRORS as error:
        print(f"{_LOG} 卸载处理 Package 失败: {error}")
    try:
        shutil.rmtree(context.get("temp_folder", ""), ignore_errors=True)
    except sdcompat.SD_API_ERRORS as error:
        print(f"{_LOG} 删除临时处理目录失败: {error}")


def process_group(context, group, channel_assignments, output_path):
    """给 Graph 设置一组纹理和开关，计算后保存 output。"""
    if context.get("errors"):
        raise RuntimeError("；".join(context["errors"]))
    if SDTexture is None or SDValueTexture is None or SDValueBool is None:
        raise RuntimeError("当前 Designer 未提供纹理或布尔值 API。")
    group_errors = validate_group(group, channel_assignments)
    if group_errors:
        raise ValueError("；".join(group_errors))
    graph = context["graph"]
    for input_key, property_id, _label in INPUTS:
        path = group["files"].get(input_key)
        if not path:
            continue
        texture = SDTexture.sFromFile(os.path.abspath(path))
        if texture is None:
            raise RuntimeError(f"无法读取贴图: {path}")
        graph.setInputPropertyValueFromId(property_id, SDValueTexture.sNew(texture))
    for switch_key, _label, property_id, _input_key in SWITCHES:
        channel_key, source_key = switch_key.split("_", 1)
        enabled = channel_assignments.get(channel_key) == source_key
        graph.setInputPropertyValueFromId(property_id, SDValueBool.sNew(enabled))
    graph.compute()
    output_property = graph.getPropertyFromId(OUTPUT_ID, SDPropertyCategory.Output)
    if output_property is None:
        raise RuntimeError(f"找不到输出属性: {OUTPUT_ID}")
    output_value = graph.getPropertyValue(output_property)
    output_texture = output_value.get() if output_value is not None else None
    if output_texture is None:
        raise RuntimeError("Graph 计算完成但输出纹理为空。")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    output_texture.save(os.path.abspath(output_path))
    return output_path
