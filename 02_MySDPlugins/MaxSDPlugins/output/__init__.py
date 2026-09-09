# -*- coding: utf-8 -*-
"""Output 功能分类包。

目前包含「曝光参数」功能，对外暴露 `show_window(main_win)` 入口，
由 MaxSDPlugin.py 注册到 `MaxSDPlugin/Output` 子菜单。
"""

TOOL_VERSION = "0.21.2"

from .exposed_parameters_window import show_window

__all__ = ["show_window"]
