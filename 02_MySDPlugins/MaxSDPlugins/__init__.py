# -*- coding: utf-8 -*-
"""MaxSDPlugins 插件包入口。

让 SD 把本目录当作一个插件包加载：当 `02_MySDPlugins/` 被加入 SD 的
「插件搜索路径」后，SD 会发现 `MaxSDPlugins` 包并调用下面转发的两个入口函数。
真正的逻辑写在 MaxSDPlugin.py 里（见 AGENTS.md §1.3）。
"""

from .MaxSDPlugin import initializeSDPlugin, uninitializeSDPlugin

__all__ = ["initializeSDPlugin", "uninitializeSDPlugin"]
