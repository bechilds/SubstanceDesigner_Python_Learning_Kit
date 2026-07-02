# -*- coding: utf-8 -*-
"""方向 A 验证脚本 —— 在 SD13 里读「当前选中节点」的 label / id / 坐标。

用途：验证 SD13 上能否用公开 API 拿到节点位置（SDNode.getPosition()），
      为「Goto 降级时回显节点坐标」这个方案（方向 A）提供依据。

怎么用：
  1. 在 SD 图视图里点选一个（或多个）节点。
  2. 打开 SD 的 Python Editor（Windows > Python Editor），把本文件内容整段粘进去运行；
     或者在 Python Editor 里 exec 本文件路径。
  3. 看底部 [MSG] 输出：应打印出每个选中节点的 标识 / 类型 / 位置(x, y)。

不需要安装任何东西，纯官方 API，只读，不修改任何节点。
"""

import sd


def _fmt_pos(pos):
    """把 getPosition() 返回值格式化成 (x, y) 字符串；拿不到就回退到 repr。"""
    # SD 的 getPosition() 返回 float2，通常有 .x / .y 属性。
    x = getattr(pos, "x", None)
    y = getattr(pos, "y", None)
    if x is not None and y is not None:
        return f"({x:.1f}, {y:.1f})"
    # 少数情况可能是可下标序列，兜底再试一次。
    try:
        return f"({pos[0]:.1f}, {pos[1]:.1f})"
    except Exception:
        return repr(pos)


def _node_label(node):
    """尽量取一个人类可读的节点名：优先定义的 label，其次定义 id。"""
    try:
        d = node.getDefinition()
        if d is not None:
            return d.getLabel() or d.getId() or "<无标签>"
    except Exception:
        pass
    return "<无定义>"


def _get_ui_mgr(app):
    """按 SD13 的现状取一个可用的 UI 管理器（优先 QtForPython，再退 SDUIMgr）。"""
    for name in ("getQtForPythonUIMgr", "getUIMgr"):
        fn = getattr(app, name, None)
        if fn is None:
            continue
        try:
            m = fn()
            if m is not None:
                return m, name
        except Exception as e:
            print(f"[MSG] {name}() 调用失败: {e}")
    return None, None


def main():
    app = sd.getContext().getSDApplication()
    ui, ui_name = _get_ui_mgr(app)
    if ui is None:
        print("[MSG] 取不到 UI 管理器，无法继续。")
        return
    print(f"[MSG] 使用 UI 管理器: {ui_name}")

    # 1) 当前图（验证 getCurrentGraph 在 SD13 可用）
    graph = None
    try:
        graph = ui.getCurrentGraph()
    except Exception as e:
        print(f"[MSG] getCurrentGraph 失败: {e}")
    print(f"[MSG] 当前图: {graph!r}")

    # 2) 当前选中节点（SD13 只有 getter，这一步应该能成功）
    nodes = None
    try:
        nodes = ui.getCurrentGraphSelectedNodes()
    except Exception as e:
        print(f"[MSG] getCurrentGraphSelectedNodes 失败: {e}")

    if not nodes or nodes.getSize() == 0:
        print("[MSG] 当前没有选中任何节点。请在图里点选一个节点再运行本脚本。")
        return

    count = nodes.getSize()
    print(f"[MSG] 选中节点数: {count}")
    print("[MSG] ---- 逐个读取 label / id / 位置 ----")
    for i in range(count):
        node = nodes.getItem(i)
        try:
            node_id = node.getIdentifier()
        except Exception:
            node_id = "<无id>"
        label = _node_label(node)
        # 关键验证点：getPosition() 是否可用、坐标是否合理
        try:
            pos = node.getPosition()
            pos_str = _fmt_pos(pos)
            pos_type = type(pos).__name__
        except Exception as e:
            pos_str = f"<读取失败: {e}>"
            pos_type = "?"
        print(f"[MSG]   [{i}] {label}  (id:{node_id})  pos={pos_str}  [{pos_type}]")

    print("[MSG] ---- 结束 ----")
    print("[MSG] 若上面每个节点都打印出了合理的 pos=(x, y)，说明方向 A 可行：")
    print("[MSG]   Goto 降级时可以把坐标一并显示给用户，方便手动定位。")


# 直接在 Python Editor 里整段运行即可
main()
