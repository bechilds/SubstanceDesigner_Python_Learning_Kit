"""LGNode Substance Designer Plugin Package

Exports the factory `getSDPlugin` and the library class `LGNodeLibrary`.
The implementation lives in `core.py` and follows a pattern similar to
your existing `LG_Tool.py`: it returns an SDPluginInfo object and builds
the menu in `onInitializeSDUIMgr`.
"""
from .core import getSDPlugin, LGNodeLibrary  # re-export for loader
