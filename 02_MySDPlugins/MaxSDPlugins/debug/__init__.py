# -*- coding: utf-8 -*-
"""Debug 功能分类包。

目前包含「Publish Checker（发布检查）」功能，
对外暴露 `show_window(main_win)` 入口，
由 MaxSDPlugin.py 注册到 `MaxSDPlugin/Debug` 子菜单。
"""

TOOL_VERSION = "0.4.9"

from .check_dependencies import show_window

__all__ = ["show_window"]
