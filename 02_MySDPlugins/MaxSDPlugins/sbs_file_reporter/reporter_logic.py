# -*- coding: utf-8 -*-
"""SBSFileRepoter 静态复杂度分析逻辑。

只读取当前 Graph，不触发计算、不汇总节点 Timing。评分从 Published Output 反向遍历，
因此未参与输出的废弃节点不会污染结果。所有 SD API 调用都采用防御式读取，以便同一份
代码运行在 Substance Designer 13/PySide2 与 16/PySide6。
"""

import math
import ntpath
import os
import re

try:
    from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
except Exception:  # pragma: no cover - 仅普通 Python 环境
    SDPropertyCategory = None
    SDPropertyInheritanceMethod = None

try:
    from sd.api.sdvalueserializer import SDValueSerializer
except Exception:  # pragma: no cover
    SDValueSerializer = None


_WEIGHTS = (
    (("fxmap", "fx-map"), 10.0, "FX-Map"),
    (("non_uniform_blur", "nonuniformblur"), 7.0, "Non-Uniform Blur"),
    (("pixelprocessor", "pixel_processor"), 5.0, "Pixel Processor"),
    (("tilesampler", "tile_sampler", "tilegenerator", "tile_generator"), 4.0, "Tile Generator/Sampler"),
    (("distance",), 4.0, "Distance"),
    (("curvature", "bevel"), 3.5, "Bevel/Curvature"),
    (("slopeblur", "slope_blur", "directionalwarp", "directional_warp"), 3.0, "Blur/Warp"),
    (("blur", "warp"), 2.0, "Blur/Warp"),
    (("histogram", "levels", "blend"), 0.8, "Standard Filter"),
    (("uniform", "convert", "grayscale", "gradient"), 0.2, "Simple"),
)

_PARAMETER_HINTS = {
    "xamount": (8.0, 0.5, 4.0),
    "yamount": (8.0, 0.5, 4.0),
    "amountx": (8.0, 0.5, 4.0),
    "amounty": (8.0, 0.5, 4.0),
    "samples": (16.0, 0.75, 4.0),
    "iterations": (4.0, 0.75, 6.0),
    "iteration": (4.0, 0.75, 6.0),
    "quality": (1.0, 1.0, 3.0),
}

_APPROVED_LIBRARY_ROOT = ntpath.normcase(ntpath.normpath(r"D:\LG_SDNodes"))
_RISK_WEIGHTS = {
    "missing_node": 60.0,
    "missing_dependency": 60.0,
    "missing_resource": 40.0,
    "external_dependency": 15.0,
    "external_resource": 10.0,
}


def _as_list(value):
    try:
        return list(value)
    except Exception:
        return []


def _properties(owner, category):
    if owner is None or category is None:
        return []
    try:
        return _as_list(owner.getProperties(category))
    except Exception:
        return []


def _property_id(prop):
    for name in ("getId", "getIdentifier"):
        try:
            result = getattr(prop, name)()
            if result:
                return str(result)
        except Exception:
            pass
    return ""


def _value_numbers(value):
    """把 SDValue 标量/向量安全转换为数字列表。"""
    if value is None:
        return []
    raw = value
    try:
        raw = value.get()
    except Exception:
        pass
    if isinstance(raw, (int, float)):
        return [float(raw)]
    vector = []
    for component in ("x", "y", "z", "w"):
        if not hasattr(raw, component):
            break
        try:
            vector.append(float(getattr(raw, component)))
        except Exception:
            break
    if vector:
        return vector
    if isinstance(raw, (tuple, list)):
        result = []
        for item in raw:
            try:
                result.append(float(item))
            except Exception:
                pass
        if result:
            return result
    try:
        text = SDValueSerializer.sToString(value) if SDValueSerializer else str(value)
    except Exception:
        text = str(value)
    # 避免把类型名中的数字（例如 int2 / float4）误当成参数值。
    return [float(item) for item in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text)]


def _property_value(owner, prop):
    try:
        return owner.getPropertyValue(prop)
    except Exception:
        pass
    try:
        return owner.getPropertyValueFromId(_property_id(prop), SDPropertyCategory.Input)
    except Exception:
        return None


def _definition_id(node):
    try:
        definition = node.getDefinition()
        return str(definition.getId() or "") if definition else ""
    except Exception:
        return ""


def _node_id(node):
    try:
        return str(node.getIdentifier() or "")
    except Exception:
        return ""


def _node_label(node):
    identifier = _node_id(node)
    label = ""
    try:
        definition = node.getDefinition()
        label = str(definition.getLabel() or definition.getId() or "") if definition else ""
    except Exception:
        pass
    return f"{label} ({identifier})" if identifier else (label or "<未知节点>")


def _inheritance_name(owner, prop):
    """返回 Absolute/RelativeToParent/RelativeToInput；不可读返回空串。"""
    try:
        method = owner.getPropertyInheritanceMethod(prop)
        name = getattr(method, "name", "")
        if name:
            return str(name)
        value = getattr(method, "value", method)
        if SDPropertyInheritanceMethod is not None:
            return SDPropertyInheritanceMethod(value).name
    except Exception:
        pass
    return ""


def _graph_resolution(graph):
    """读取 Graph 输出尺寸；动态继承时按 1K 评分并明确标记为估算。"""
    if SDPropertyCategory is not None:
        try:
            prop = graph.getPropertyFromId("$outputsize", SDPropertyCategory.Input)
            value = graph.getPropertyValue(prop) if prop is not None else None
            numbers = _value_numbers(value)
            inheritance = _inheritance_name(graph, prop) if prop is not None else ""
            if len(numbers) >= 2 and inheritance == "Absolute":
                width = int(2 ** max(0, min(14, int(numbers[0]))))
                height = int(2 ** max(0, min(14, int(numbers[1]))))
                return width, height, False, f"Graph 绝对尺寸 {width} x {height}"
            if inheritance:
                return 1024, 1024, True, f"Graph 尺寸为 {inheritance}，评分按 1024 x 1024 基准"
        except Exception:
            pass
    return 1024, 1024, True, "Graph 尺寸不可可靠读取，评分按 1024 x 1024 基准"


def _node_resolution(node, graph_size, graph_resolution_estimated):
    """读取节点评分尺寸，并返回 (宽, 高, 是否估算, 说明)。"""
    if SDPropertyCategory is None:
        return graph_size[0], graph_size[1], True, "尺寸 API 不可用，按 Graph 基准估算"
    try:
        prop = node.getPropertyFromId("$outputsize", SDPropertyCategory.Input)
        if prop is None:
            return graph_size[0], graph_size[1], graph_resolution_estimated, "继承 Graph 尺寸"
        numbers = _value_numbers(_property_value(node, prop))
        if len(numbers) < 2:
            return graph_size[0], graph_size[1], True, "节点尺寸不可读，按 Graph 基准估算"
        inheritance = _inheritance_name(node, prop)
        base_x = int(round(math.log(max(1, graph_size[0]), 2)))
        base_y = int(round(math.log(max(1, graph_size[1]), 2)))
        if inheritance == "Absolute":
            exp_x, exp_y = int(numbers[0]), int(numbers[1])
            estimated = False
            basis = "绝对尺寸"
        elif inheritance == "RelativeToParent":
            exp_x, exp_y = base_x + int(numbers[0]), base_y + int(numbers[1])
            estimated = graph_resolution_estimated
            basis = "相对 Graph" if not estimated else "相对动态 Graph，按 1K 基准估算"
        elif inheritance == "RelativeToInput":
            return graph_size[0], graph_size[1], True, "相对输入，暂按 Graph 基准估算"
        else:
            return graph_size[0], graph_size[1], True, "继承方式不可读，按 Graph 基准估算"
        width = 2 ** max(0, min(14, exp_x))
        height = 2 ** max(0, min(14, exp_y))
        return width, height, estimated, f"{basis} {width} x {height}"
    except Exception:
        return graph_size[0], graph_size[1], True, "尺寸读取失败，按 Graph 基准估算"


def _is_graph_instance(node):
    """仅把实际引用 Graph 资源的节点判定为 Graph Instance。"""
    try:
        resource = node.getReferencedResource()
        if resource is None:
            return False
        class_name = ""
        try:
            class_name = str(resource.getClassName() or "").lower()
        except Exception:
            pass
        return "graph" in class_name or hasattr(resource, "getNodes")
    except Exception:
        return False


def _classify(node):
    definition_id = _definition_id(node).lower().replace(" ", "")
    if _is_graph_instance(node):
        return 8.0, "Graph Instance"
    for patterns, weight, group in _WEIGHTS:
        if any(pattern in definition_id for pattern in patterns):
            return weight, group
    if "output" in definition_id or "input" in definition_id:
        return 0.05, "Input/Output"
    return 1.0, "Other"


def _parameter_factor(node):
    """读取少量跨版本稳定的数值参数，未知参数不阻断分析。"""
    factor = 1.0
    reasons = []
    for prop in _properties(node, getattr(SDPropertyCategory, "Input", None)):
        prop_id = _property_id(prop).lower().replace("_", "")
        for hint, (baseline, minimum, maximum) in _PARAMETER_HINTS.items():
            if hint != prop_id:
                continue
            numbers = _value_numbers(_property_value(node, prop))
            if numbers:
                correction = max(minimum, min(maximum, numbers[0] / baseline))
                factor *= correction
                reasons.append(f"{_property_id(prop)}={numbers[0]:g} (x{correction:.2f})")
            break
    return max(0.5, min(12.0, factor)), reasons


def _upstream_by_property(node):
    groups = []
    for prop in _properties(node, getattr(SDPropertyCategory, "Input", None)):
        try:
            if not prop.isConnectable():
                continue
        except Exception:
            continue
        upstream = []
        try:
            for connection in _as_list(node.getPropertyConnections(prop)):
                candidate = connection.getInputPropertyNode()
                if candidate is not None:
                    upstream.append(candidate)
        except Exception:
            pass
        if upstream:
            groups.append((_property_id(prop), upstream))
    return groups


def _switch_selection(node):
    for prop in _properties(node, getattr(SDPropertyCategory, "Input", None)):
        prop_id = _property_id(prop).lower().replace("_", "")
        if "inputselection" not in prop_id and "switch" not in prop_id:
            continue
        numbers = _value_numbers(_property_value(node, prop))
        if numbers:
            return max(0, int(numbers[0]))
    return 0


def _reachable_nodes(graph, switch_mode="all", node_scores=None):
    """从 Published Output 反向遍历，并按模式处理 Switch 输入分支。"""
    try:
        roots = _as_list(graph.getOutputNodes())
    except Exception:
        roots = []

    if switch_mode == "maximum":
        score_map = node_scores or {}
        memo = {}

        def collect_upstream(node, active):
            key = _node_id(node) or str(id(node))
            if key in memo:
                return set(memo[key])
            if key in active:
                return {key}
            active = set(active)
            active.add(key)
            groups = _upstream_by_property(node)
            if "switch" in _definition_id(node).lower() and groups:
                candidates = []
                for _prop_id, upstream in groups:
                    branch = set()
                    for candidate in upstream:
                        branch.update(collect_upstream(candidate, active))
                    branch_score = sum(score_map.get(item, 0.0) for item in branch)
                    candidates.append((branch_score, branch))
                groups_nodes = max(candidates, key=lambda item: item[0])[1]
            else:
                groups_nodes = set()
                for _prop_id, upstream in groups:
                    for candidate in upstream:
                        groups_nodes.update(collect_upstream(candidate, active))
            result = groups_nodes | {key}
            memo[key] = result
            return set(result)

        selected = set()
        for root in roots:
            selected.update(collect_upstream(root, set()))
        all_nodes = _reachable_nodes(graph, switch_mode="all")
        return {key: node for key, node in all_nodes.items() if key in selected}

    visited = {}
    stack = list(roots)
    while stack:
        node = stack.pop()
        key = _node_id(node) or str(id(node))
        if key in visited:
            continue
        visited[key] = node
        groups = _upstream_by_property(node)
        is_switch = "switch" in _definition_id(node).lower()
        if switch_mode == "current" and is_switch and groups:
            groups = [groups[min(_switch_selection(node), len(groups) - 1)]]
        for _prop_id, upstream in groups:
            stack.extend(upstream)
    return visited


def _score_node(node, graph_size, graph_resolution_estimated):
    width, height, resolution_estimated, resolution_basis = _node_resolution(
        node, graph_size, graph_resolution_estimated)
    weight, group = _classify(node)
    pixel_factor = (width * height) / float(1024 * 1024)
    output_count = max(1, len(_properties(node, getattr(SDPropertyCategory, "Output", None))))
    output_factor = 1.0 + min(0.5, (output_count - 1) * 0.15)
    parameter_factor, parameter_reasons = _parameter_factor(node)
    score = weight * pixel_factor * parameter_factor * output_factor
    return {
        "id": _node_id(node),
        "label": _node_label(node),
        "definition_id": _definition_id(node),
        "group": group,
        "width": width,
        "height": height,
        "resolution_estimated": resolution_estimated,
        "resolution_basis": resolution_basis,
        "base_weight": weight,
        "pixel_factor": pixel_factor,
        "parameter_factor": parameter_factor,
        "parameter_reasons": parameter_reasons,
        "output_factor": output_factor,
        "score_basis": "；".join([
            resolution_basis,
            "参数 " + ("、".join(parameter_reasons) if parameter_reasons else "无修正"),
            f"输出系数 x{output_factor:.2f}",
        ]),
        "score": round(score, 2),
    }


def _level(score):
    if score <= 150:
        return "Low"
    if score <= 400:
        return "Medium"
    if score <= 800:
        return "High"
    return "Very High"


def _health_level(risks):
    """文件完整性独立评级，不再与性能复杂度混合。"""
    if any(float(item.get("score", 0.0)) >= 40.0 for item in risks):
        return "Error"
    if risks:
        return "Warning"
    return "Healthy"


def _graph_name(graph):
    for name in ("getIdentifier", "getLabel"):
        try:
            value = getattr(graph, name)()
            if value:
                return str(value)
        except Exception:
            pass
    return "<当前 Graph>"


def _file_name(graph):
    """返回当前 Graph 所属 .sbs 文件名；尚未保存时返回友好占位文字。"""
    try:
        package = graph.getPackage()
        path = str(package.getFilePath() or "") if package is not None else ""
        if path:
            return ntpath.basename(path)
    except Exception:
        pass
    return "<未保存文件>"


def _score_histogram(nodes):
    """按固定得分区间统计节点数量，便于不同 Graph 之间横向比较。"""
    bins = [
        {"label": "0-0.5", "minimum": 0.0, "maximum": 0.5, "count": 0},
        {"label": "0.5-1", "minimum": 0.5, "maximum": 1.0, "count": 0},
        {"label": "1-3", "minimum": 1.0, "maximum": 3.0, "count": 0},
        {"label": "3-8", "minimum": 3.0, "maximum": 8.0, "count": 0},
        {"label": "8+", "minimum": 8.0, "maximum": None, "count": 0},
    ]
    for node in nodes:
        try:
            score = float(node.get("score", 0.0))
        except Exception:
            score = 0.0
        for bucket in bins:
            maximum = bucket["maximum"]
            if score >= bucket["minimum"] and (maximum is None or score < maximum):
                bucket["count"] += 1
                break
    return bins


def _local_path(path):
    """返回规范化本地路径；内置协议或空路径返回空串。"""
    if not path:
        return ""
    text = str(path).strip()
    if text.lower().startswith(("sbs://", "pkg://")):
        return ""
    return ntpath.normcase(ntpath.normpath(text))


def _official_package_roots():
    """返回当前 SD 安装自带的 resources/packages 目录。

    优先从 `sd.__file__` 反推当前实际安装位置，因此兼容不同盘符、Adobe/Allegorithmic
    目录名以及 SD13/SD16；普通 Python 环境下取不到时返回空列表。
    """
    roots = []
    try:
        import sd
        sd_file = getattr(sd, "__file__", "") or ""
        normalized = _local_path(sd_file)
        marker = ntpath.normcase(ntpath.normpath(r"resources\python\sd"))
        marker_index = normalized.rfind(marker)
        if marker_index >= 0:
            install_root = normalized[:marker_index]
            official_root = ntpath.normpath(ntpath.join(install_root, "resources", "packages"))
            roots.append(ntpath.normcase(official_root))
    except Exception:
        pass
    return roots


def _is_under_root(path, root):
    try:
        return ntpath.commonpath([path, root]) == root
    except Exception:
        return False


def _is_approved_path(path):
    normalized = _local_path(path)
    if not normalized:
        return True
    approved_roots = [_APPROVED_LIBRARY_ROOT] + _official_package_roots()
    return any(_is_under_root(normalized, root) for root in approved_roots)


def _resource_path(resource):
    try:
        return str(resource.getFilePath() or "") if resource is not None else ""
    except Exception:
        return ""


def _risk_item(category, score, message, node_id=""):
    return {
        "category": category,
        "score": float(score),
        "message": message,
        "node_id": node_id,
    }


def _is_ghost_node(node, definition_id):
    """识别引用子图丢失后仍保留 Definition 外壳的 Ghost Node。"""
    if "bitmap" in definition_id or "svg" in definition_id:
        return False
    try:
        if node.getReferencedResource() is not None:
            return False
        definition = node.getDefinition()
        if definition is None:
            return True
        label = str(definition.getLabel() or "").lower()
        input_count = len(_properties(definition, getattr(SDPropertyCategory, "Input", None)))
        output_count = len(_properties(definition, getattr(SDPropertyCategory, "Output", None)))
        return "ghost" in label or (input_count == 0 and output_count == 0)
    except Exception:
        return False


def _collect_file_risks(graph):
    """扫描缺失节点、package 依赖和节点 Resource，返回文件级风险项。"""
    risks = []
    seen = set()

    try:
        nodes = _as_list(graph.getNodes())
    except Exception:
        nodes = []

    for node in nodes:
        node_id = _node_id(node)
        label = _node_label(node)
        definition_id = _definition_id(node).lower()
        if not definition_id or _is_ghost_node(node, definition_id):
            key = ("missing_node", node_id)
            if key not in seen:
                seen.add(key)
                risks.append(_risk_item(
                    "节点丢失", _RISK_WEIGHTS["missing_node"],
                    f"{label} 的节点定义丢失", node_id))
            continue

        expects_resource = any(token in definition_id for token in ("instance", "bitmap", "svg"))
        try:
            resource = node.getReferencedResource()
        except Exception:
            resource = None
        if expects_resource and resource is None:
            key = ("missing_resource", node_id)
            if key not in seen:
                seen.add(key)
                risks.append(_risk_item(
                    "Resource 丢失", _RISK_WEIGHTS["missing_resource"],
                    f"{label} 引用的 Resource 或子 Graph 丢失", node_id))
            continue

        resource_path = _resource_path(resource)
        normalized = _local_path(resource_path)
        if not normalized:
            continue
        if not os.path.exists(resource_path):
            key = ("missing_resource_path", normalized)
            if key not in seen:
                seen.add(key)
                risks.append(_risk_item(
                    "Resource 丢失", _RISK_WEIGHTS["missing_resource"],
                    f"{label} 引用的文件不存在: {resource_path}", node_id))
        elif not _is_approved_path(resource_path):
            key = ("external_resource", normalized)
            if key not in seen:
                seen.add(key)
                risks.append(_risk_item(
                    "非标准 Resource", _RISK_WEIGHTS["external_resource"],
                    f"{label} 引用了可信目录之外的 Resource: {resource_path}", node_id))

    try:
        package = graph.getPackage()
        dependencies = _as_list(package.getDependencies()) if package is not None else []
    except Exception:
        dependencies = []
    for dependency in dependencies:
        try:
            dependency_path = str(dependency.getFilePath() or "")
        except Exception:
            dependency_path = ""
        normalized = _local_path(dependency_path)
        if not normalized:
            continue
        try:
            resolved_package = dependency.getPackage()
        except Exception:
            resolved_package = None
        if resolved_package is None or not os.path.exists(dependency_path):
            key = ("missing_dependency", normalized)
            if key not in seen:
                seen.add(key)
                risks.append(_risk_item(
                    "依赖丢失", _RISK_WEIGHTS["missing_dependency"],
                    f"Package 依赖不存在或无法解析: {dependency_path}"))
        elif not _is_approved_path(dependency_path):
            key = ("external_dependency", normalized)
            if key not in seen:
                seen.add(key)
                risks.append(_risk_item(
                    "非标准依赖", _RISK_WEIGHTS["external_dependency"],
                    f"Package 引用了可信目录之外的本地依赖: {dependency_path}"))
    return risks


def analyze_graph(graph):
    """分析 Graph，返回可直接交给 UI/JSON 使用的报告字典。"""
    if graph is None:
        raise ValueError("未找到当前 Graph。")
    graph_width, graph_height, resolution_estimated, resolution_basis = _graph_resolution(graph)
    graph_size = (graph_width, graph_height)
    potential_nodes = _reachable_nodes(graph, switch_mode="all")
    current_nodes = _reachable_nodes(graph, switch_mode="current")
    node_rows = [
        _score_node(node, graph_size, resolution_estimated)
        for node in potential_nodes.values()
    ]
    node_rows.sort(key=lambda item: item["score"], reverse=True)
    by_id = {item["id"]: item for item in node_rows}
    node_scores = {item["id"]: item["score"] for item in node_rows}
    maximum_nodes = _reachable_nodes(graph, switch_mode="maximum", node_scores=node_scores)
    all_branches_complexity_score = round(sum(item["score"] for item in node_rows), 2)
    potential_complexity_score = round(sum(by_id[key]["score"] for key in maximum_nodes if key in by_id), 2)
    current_complexity_score = round(sum(by_id[key]["score"] for key in current_nodes if key in by_id), 2)
    risk_items = _collect_file_risks(graph)
    file_risk_score = round(sum(item["score"] for item in risk_items), 2)
    potential_score = potential_complexity_score
    current_score = current_complexity_score

    warnings = []
    for risk in risk_items:
        warnings.append({
            "severity": "High" if risk["score"] >= 40 else "Warning",
            "message": f"[+{risk['score']:.0f} 风险分] {risk['message']}",
            "node_id": risk["node_id"],
        })
    expensive_count = 0
    instance_count = 0
    four_k_count = 0
    for row in node_rows:
        if row["score"] >= 8:
            expensive_count += 1
        if not row["resolution_estimated"] and (row["width"] >= 4096 or row["height"] >= 4096):
            four_k_count += 1
            severity = "High" if row["base_weight"] >= 3 else "Warning"
            warnings.append({"severity": severity, "message":
                             f"{row['label']} 运行在 {row['width']} x {row['height']}", "node_id": row["id"]})
        if row["group"] == "Graph Instance":
            instance_count += 1
            warnings.append({"severity": "Warning", "message":
                             f"{row['label']} 使用固定风险权重，尚未递归展开子 Graph", "node_id": row["id"]})
        if row["group"] == "Pixel Processor":
            warnings.append({"severity": "Warning", "message":
                             f"{row['label']} 的内部函数无法可靠静态分析", "node_id": row["id"]})

    # 检查昂贵节点的相同类型+相同直接输入，提示可能存在可复用计算。
    fingerprints = {}
    for node in potential_nodes.values():
        row = by_id.get(_node_id(node))
        if row is None or row["base_weight"] < 2:
            continue
        upstream_ids = tuple(sorted(_node_id(item) for _name, items in _upstream_by_property(node) for item in items))
        fingerprint = (row["definition_id"], upstream_ids)
        if fingerprint in fingerprints:
            warnings.append({"severity": "Warning", "message":
                             f"{row['label']} 与 {fingerprints[fingerprint]} 具有相同类型和输入，可能可复用",
                             "node_id": row["id"]})
        else:
            fingerprints[fingerprint] = row["label"]

    if resolution_estimated:
        warnings.insert(0, {"severity": "Info", "message":
                            resolution_basis, "node_id": ""})
    if not potential_nodes:
        warnings.append({"severity": "Warning", "message":
                         "没有找到 Published Output 或可达节点", "node_id": ""})

    return {
        "file_name": _file_name(graph),
        "graph_name": _graph_name(graph),
        "target_width": graph_width,
        "target_height": graph_height,
        "resolution_estimated": resolution_estimated,
        "resolution_basis": resolution_basis,
        "current_score": current_score,
        "potential_score": potential_score,
        "current_complexity_score": current_complexity_score,
        "potential_complexity_score": potential_complexity_score,
        "all_branches_complexity_score": all_branches_complexity_score,
        "file_risk_score": file_risk_score,
        "risk_items": risk_items,
        "file_health": _health_level(risk_items),
        "current_level": _level(current_score),
        "potential_level": _level(potential_score),
        "reachable_count": len(node_rows),
        "current_reachable_count": len(current_nodes),
        "four_k_count": four_k_count,
        "instance_count": instance_count,
        "expensive_count": expensive_count,
        "nodes": node_rows,
        "score_histogram": _score_histogram(node_rows),
        "warnings": warnings,
        "measured_recompute_ms": None,
    }