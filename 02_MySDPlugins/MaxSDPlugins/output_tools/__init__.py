# -*- coding: utf-8 -*-
"""OutputTools 功能分类包：展示当前插件的所有功能/分支，
把勾选的功能打包导出成一个独立的 Python 文件，便于其他工具集成。

对外暴露 `show_window(main_win)` 入口，由 menu.py 注册到 `MaxSDPlugin/OutputTools`。
"""

TOOL_VERSION = "0.23.0"

from .output_tools import show_window

__all__ = ["show_window"]
