# -*- coding: utf-8 -*-
"""曝光参数功能的数据层：枚举当前图的已暴露参数，以及 OutputData 的读写/导出。

不含任何 Qt UI，纯逻辑 + 文件 IO，方便单独复用与测试。
SD 专有的 `sd` / `sd.api.*` 仅在 SD 进程内可用，这里全部包 try/except，
取不到时优雅返回 None / 空列表，不让异常冒泡到 SD 主进程。
"""

import os
import json
import datetime

import sd  # SD 提供的 Python 包；只在 SD 进程内可用

from .. import sdcompat  # 跨版本 SD/Qt 接口兼容层（唯一真源）

# SD 专有类型：用 try 包住，工作区 lint 找不到属正常
try:
    from sd.api.sdproperty import SDPropertyCategory
except Exception:  # pragma: no cover - 仅在非 SD 环境触发
    SDPropertyCategory = None

try:
    from sd.api.sdvalueserializer import SDValueSerializer
except Exception:  # pragma: no cover
    SDValueSerializer = None

# OutputData 文件名与数据结构版本
OUTPUT_DATA_FILENAME = "OutputData.json"
SCHEMA_VERSION = "0.1.0"

_LOG = "[MaxSDPlugin/output]"


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
    except Exception as e:
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
    except Exception:
        return str(value)


def _type_id(prop):
    """读取属性类型标识，失败返回空串。"""
    try:
        t = prop.getType()
        if t is None:
            return ""
        return t.getId() if hasattr(t, "getId") else str(t)
    except Exception:
        return ""


def _safe_graph_value(graph, prop):
    try:
        return graph.getPropertyValue(prop)
    except Exception:
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


def _read_group(graph, prop):
    """读取属性的分组（group 注解）。无分组 / 读取失败返回空串。

    分组是非破坏性读取；即使 'group' 注解 id 在某些版本不存在，最坏只是显示为未分组。
    """
    try:
        v = graph.getPropertyAnnotationValueFromId(prop, "group")
        if v is None:
            return ""
        return _strip_quotes(_value_to_str(v)) or ""
    except Exception:
        return ""


# UI 顶层分类顺序与中文标签（对应 SD 参数面板的两个区）
CATEGORY_PARAMETERS = "parameters"
CATEGORY_INPUTS = "inputs"
CATEGORY_LABELS = (
    (CATEGORY_PARAMETERS, "INPUT PARAMETERS"),
    (CATEGORY_INPUTS, "INPUTS"),
)


def collect_exposed_parameters(graph):
    """枚举图的已暴露输入参数，返回 list[dict]。

    仅包含「INPUT PARAMETERS」与「INPUTS」两类——即排除以 '$' 开头的内置基础参数。
    每项: {id, label, type, default, value, connectable, category, group}。
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
    except Exception as e:
        print(f"{_LOG} 读取输入属性失败: {e}")
        return result

    try:
        count = len(props)
    except Exception:
        count = 0

    for i in range(count):
        try:
            prop = props[i]
            pid = prop.getId()
            if _is_base_parameter(pid):
                continue  # 跳过 $outputsize 等内置基础参数

            try:
                connectable = bool(prop.isConnectable())
            except Exception:
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
            })
        except Exception as e:
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
    except Exception:
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
# 删除（取消暴露） / 加载应用
# --------------------------------------------------------------------------- #
def _undo_group(name):
    """返回一个可用作 with 上下文的 UndoGroup；取不到时返回一个空上下文。

    用 SDHistoryUtils.UndoGroup 包住破坏性操作，用户可在 SD 里 Ctrl+Z 撤销。
    """
    try:
        from sd.api.sdhistoryutils import SDHistoryUtils
        return SDHistoryUtils.UndoGroup(name)
    except Exception:
        import contextlib
        return contextlib.nullcontext()


def _is_get_function_node(fnode):
    """判断函数图里的节点是不是一个「Get 变量」节点（get_float1 / get_integer1 ...）。"""
    try:
        d = fnode.getDefinition()
        did = (d.getId() or "") if d else ""
        if "get" in did.lower():
            return True
        lbl = (d.getLabel() or "") if d else ""
        return lbl.lower().startswith("get")
    except Exception:
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
            except Exception:
                pass
    except Exception:
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
    except Exception:
        return names, has_empty
    set_names = _collect_set_var_names(func_graph)
    for i in range(n):
        try:
            fnode = fnodes[i]
        except Exception:
            continue
        if not _is_get_function_node(fnode):
            continue
        try:
            cval = fnode.getPropertyValueFromId("__constant__", SDPropertyCategory.Input)
        except Exception:
            cval = None
        if cval is None:
            has_empty = True
            continue
        try:
            s = _strip_quotes(_value_to_str(cval)) or ""
        except Exception:
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
            except Exception:
                did = ""
            if "set" not in did:
                continue
            try:
                cval = fn.getPropertyValueFromId("__constant__", SDPropertyCategory.Input)
                s = _strip_quotes(_value_to_str(cval)) or ""
                if s:
                    out.add(s)
            except Exception:
                pass
    except Exception:
        pass
    return out


def _reset_dependent_node_params(graph, var_ids):
    """删除前：把「引用 var_ids 变量的 Get 函数」驱动的节点参数重置回常量值。

    趁变量还存在时重置，SDNode.deletePropertyGraph(prop) 能恢复出合理的常量值。
    返回被重置的节点参数个数。
    """
    if not var_ids or SDPropertyCategory is None:
        return 0
    want = set(var_ids)
    reset_count = 0
    try:
        nodes = graph.getNodes()
        ncount = len(nodes)
    except Exception as e:
        print(f"{_LOG} 读取节点失败，跳过重置: {e}")
        return 0
    for i in range(ncount):
        try:
            node = nodes[i]
            props = node.getProperties(SDPropertyCategory.Input)
            pcount = len(props)
        except Exception:
            continue
        for j in range(pcount):
            try:
                prop = props[j]
                pg = node.getPropertyGraph(prop)
            except Exception:
                pg = None
            if not pg:
                continue
            try:
                names, _ = _collect_get_var_status(pg)
                if names & want:
                    node.deletePropertyGraph(prop)
                    reset_count += 1
            except Exception as e:
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
    except Exception as e:
        print(f"{_LOG} 读取节点失败，跳过损坏函数扫描: {e}")
        return 0
    for i in range(ncount):
        try:
            node = nodes[i]
        except Exception:
            continue
        if only is not None:
            try:
                if (node.getIdentifier() or "") not in only:
                    continue
            except Exception:
                continue
        for cat in categories:
            try:
                props = node.getProperties(cat)
                pcount = len(props)
            except Exception:
                continue
            for j in range(pcount):
                try:
                    prop = props[j]
                    pg = node.getPropertyGraph(prop)
                except Exception:
                    pg = None
                if not pg:
                    continue
                try:
                    names, has_empty = _collect_get_var_status(pg, valid_ids)
                    if has_empty or (names & deleted):
                        node.deletePropertyGraph(prop)
                        reset_count += 1
                except Exception as e:
                    print(f"{_LOG} 重置某损坏节点参数失败（已跳过）: {e}")
    return reset_count


def delete_exposed_parameters(graph, ids):
    """删除（取消暴露）指定 id 的输入属性。返回 (deleted, failed, reset)。

    - deleted: 成功删除的 id 列表。
    - failed: [(id, 原因)]。
    - reset: 被重置回常量值的节点参数个数。
    流程（同一个 UndoGroup 内，可在 SD 里一次性 Ctrl+Z 撤销）：
      1) 删除前：重置「引用这些变量的 Get 函数」驱动的节点参数（恢复合理常量值）。
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
        # 1) 删除前重置（趁变量还在，恢复出合理常量值）
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
            except Exception as e:
                failed.append((pid, str(e)))
        # 3) 删除后兜底：扫描并重置残留的损坏 Get 函数（变量名已空）
        reset += _reset_broken_node_functions(graph, ids)

    try:
        with _undo_group("MaxSDPlugin 删除曝光参数"):
            _do()
    except Exception as e:
        print(f"{_LOG} 删除时出现异常，已尽量完成: {e}")
    print(f"{_LOG} 删除完成：成功 {len(deleted)} 个，失败 {len(failed)} 个，重置节点参数 {reset} 个")
    return deleted, failed, reset


def _node_label(node):
    """节点显示名：定义标签 + 标识符，便于在图里定位。"""
    try:
        ident = node.getIdentifier() or ""
    except Exception:
        ident = ""
    try:
        d = node.getDefinition()
        lbl = (d.getLabel() or d.getId()) if d else ""
    except Exception:
        lbl = ""
    return f"{lbl} (id:{ident})" if ident else (lbl or "<未知节点>")


def _is_ghost_instance(node):
    """判断是否为子图丢失的 Ghost 实例（Cooker 报 Can't find subgraph）。

    子图实例引用的子图（getReferencedResource）丢失时，节点变成 Ghost：
    引用资源为 None，且拿不到 I/O 定义；cook 报 "Can't find subgraph"。
    """
    try:
        if hasattr(node, "getReferencedResource") and node.getReferencedResource() is not None:
            return False
        d = node.getDefinition()
        if d is None:
            return True
        lbl = (d.getLabel() or "").lower()
        ins = len(d.getProperties(SDPropertyCategory.Input)) if SDPropertyCategory else 0
        outs = len(d.getProperties(SDPropertyCategory.Output)) if SDPropertyCategory else 0
        return ("ghost" in lbl) or (ins == 0 and outs == 0)
    except Exception:
        return False


def collect_broken_nodes(graph):
    """扫描全图，列出有问题的节点及其警告类型。

    返回 list[dict]: {id, label, prop, warnings} ——
      - id: 节点标识，用于 Goto / 删除；
      - prop: 首个损坏属性名（可空）；
      - warnings: 警告类型列表，如 ["Empty variable", "缺失资源", "未连接输出", "悬挂节点"]。
    只读，不修改图。
    """
    import os as _os
    out = []
    if graph is None or SDPropertyCategory is None:
        return out
    valid_ids = _graph_input_ids(graph)
    output_ids = set()
    try:
        outs = graph.getOutputNodes()
        for i in range(len(outs)):
            output_ids.add(outs[i].getIdentifier())
    except Exception:
        pass
    categories = [SDPropertyCategory.Input, SDPropertyCategory.Output, SDPropertyCategory.Annotation]
    try:
        nodes = graph.getNodes()
        ncount = len(nodes)
    except Exception as e:
        print(f"{_LOG} 读取节点失败，跳过损坏节点扫描: {e}")
        return out
    for i in range(ncount):
        try:
            node = nodes[i]
            nid = node.getIdentifier() or ""
        except Exception:
            continue
        warnings = []
        broken_prop = ""
        # 1) Empty variable / 悬空 Get 函数
        for cat in categories:
            try:
                props = node.getProperties(cat)
            except Exception:
                continue
            for j in range(len(props)):
                try:
                    pg = node.getPropertyGraph(props[j])
                    if not pg:
                        continue
                    _, has_empty = _collect_get_var_status(pg, valid_ids)
                    if has_empty:
                        broken_prop = props[j].getId()
                        break
                except Exception:
                    continue
            if broken_prop:
                break
        if broken_prop:
            warnings.append("Empty variable")
        # 2) 缺失资源：节点引用的资源不存在（外部文件丢失或 pkg:/// 依赖找不到）
        try:
            d = node.getDefinition()
            did = (d.getId() or "").lower() if d else ""
            res = None
            if hasattr(node, "getReferencedResource"):
                res = node.getReferencedResource()
            if "bitmap" in did or "svg" in did:
                if res is None:
                    warnings.append("缺失资源")
                else:
                    path = res.getFilePath() if hasattr(res, "getFilePath") else ""
                    if path and not path.startswith("pkg://") and not _os.path.exists(path):
                        warnings.append("缺失资源")
            if "缺失资源" not in warnings and res is not None:
                path = res.getFilePath() if hasattr(res, "getFilePath") else ""
                if path and not path.startswith("pkg://") and not _os.path.exists(path):
                    warnings.append("缺失资源")
            # 子图实例引用的子图丢失 → Ghost Instance（Can't find subgraph）。
            # 原子节点（bitmap/svg 等）有 I/O 不会判 ghost；缺子图实例无 I/O 或带 ghost 标签。
            if "bitmap" not in did and "svg" not in did and _is_ghost_instance(node):
                warnings.append("缺失子图(Ghost)")
        except Exception:
            pass
        # 3 & 4) 未连接输出 / 悬挂节点
        try:
            conn_out = 0
            for p in node.getProperties(SDPropertyCategory.Output):
                conn_out += len(node.getPropertyConnections(p))
            if nid in output_ids:
                conn_in = sum(len(node.getPropertyConnections(p))
                              for p in node.getProperties(SDPropertyCategory.Input))
                if conn_in == 0:
                    warnings.append("未连接输出")
            elif conn_out == 0:
                warnings.append("悬挂节点")
        except Exception:
            pass
        if warnings:
            out.append({"id": nid, "label": _node_label(node), "prop": broken_prop,
                        "warnings": warnings})
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
    except Exception as e:
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
    except Exception as e:
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
    try:
        if "string" in tid:
            from sd.api.sdvaluestring import SDValueString
            return SDValueString.sNew(_strip_quotes(str(raw)))
        if "bool" in tid:
            from sd.api.sdvaluebool import SDValueBool
            return SDValueBool.sNew(str(raw).strip().lower() in ("1", "true", "yes"))
        # 整型：放在 float 判断之前，避免被 "float" 子串误命中
        if tid.endswith("int") or tid in ("int", "integer") or "int1" in tid:
            from sd.api.sdvalueint import SDValueInt
            return SDValueInt.sNew(int(float(str(raw).strip())))
        if "float" in tid and not any(v in tid for v in ("float2", "float3", "float4")):
            from sd.api.sdvaluefloat import SDValueFloat
            return SDValueFloat.sNew(float(str(raw).strip()))
    except Exception as e:
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
        except Exception:
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
        except Exception as e:
            summary["skipped"].append((pid, str(e)))

    try:
        with _undo_group("MaxSDPlugin 加载并应用 OutputData"):
            for p in params:
                _apply_one(p)
    except Exception as e:
        print(f"{_LOG} 应用时出现异常，已尽量完成: {e}")
    print(
        f"{_LOG} 应用完成：还原 {len(summary['restored'])} 个，"
        f"缺失 {len(summary['missing'])} 个，跳过 {len(summary['skipped'])} 个"
    )
    return summary
