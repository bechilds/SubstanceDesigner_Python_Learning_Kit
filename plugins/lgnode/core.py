"""LGNode Substance Designer Plugin (Library style)

Implements a SDPluginLibrary subclass (older but still recognized style)
that returns an SDPluginInfo object on initialization and registers a
top-level Qt menu. This pattern matches the loader expectation when a
"The Python module is not a Designer plugin" warning appears for a
plain SDPlugin subclass.

Lifecycle methods:
 - initializeSDPlugin -> return SDPluginInfo
 - onInitializeSDUIMgr(uiMgr) -> build menu/UI
 - onDeinitializeSDPlugin -> cleanup
"""
from __future__ import annotations
import os
import time
import traceback
from typing import Optional

import sd
from PySide2 import QtWidgets

try:
    from sd.api.sdplugin import SDPluginLibrary, SDPluginInfo
except Exception:  # pragma: no cover
    SDPluginLibrary = object  # type: ignore
    SDPluginInfo = None  # type: ignore

# Where to write an optional debug log (user can enable)
_LOG_PATH = os.path.join(os.path.expanduser('~'), 'lgnode_plugin.log')
_ENABLE_FILE_LOG = True  # Set False to disable file logging


def _log(msg: str) -> None:
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[LGNode][{ts}] {msg}"
    print(line)
    if _ENABLE_FILE_LOG:
        try:
            with open(_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass


class LGNodeLibrary(SDPluginLibrary):  # type: ignore[misc]
    """LGNode library-style plugin.

    Uses SDPluginLibrary so Designer expects an SDPluginInfo object on
    initialization, then builds UI in onInitializeSDUIMgr.
    """

    def __init__(self):
        self._menu: Optional[QtWidgets.QMenu] = None
        _log('LGNodeLibrary.__init__')

    # Return SDPluginInfo (not a status) so the loader recognizes it.
    def initializeSDPlugin(self):  # noqa: N802 (SDK naming)
        _log('LGNodeLibrary.initializeSDPlugin')
        try:
            if SDPluginInfo is None:
                raise RuntimeError('SDPluginInfo unavailable')
            return SDPluginInfo(
                'LGNode',
                'Adds a custom LGNode menu with test action',
                'LG',
                '1.0.0',
                '2025',
                SDPluginInfo.LibraryType.Python
            )
        except Exception:
            _log('initializeSDPlugin failed: ' + traceback.format_exc())
            return None

    def onDeinitializeSDPlugin(self):  # noqa: N802
        _log('LGNodeLibrary.onDeinitializeSDPlugin')
        try:
            if self._menu is not None:
                self._menu.deleteLater()
                self._menu = None
            return True
        except Exception:
            _log('onDeinitializeSDPlugin failed: ' + traceback.format_exc())
            return False

    def onInitializeSDUIMgr(self, uiMgr):  # noqa: N802
        _log('LGNodeLibrary.onInitializeSDUIMgr')
        try:
            mainwindow = uiMgr.getMainWindow()
            menubar = mainwindow.menuBar()
            # Prevent duplicates on reload
            for act in menubar.actions():
                if act.text() == 'LGNode':
                    _log('LGNode menu already present')
                    self._menu = act.menu()
                    return True

            self._menu = QtWidgets.QMenu('LGNode', menubar)
            test_action = QtWidgets.QAction('Test Action', self._menu)
            test_action.triggered.connect(self._on_test_clicked)  # type: ignore[arg-type]
            self._menu.addAction(test_action)
            menubar.addMenu(self._menu)
            _log('LGNode menu added to menubar')
            return True
        except Exception:
            _log('onInitializeSDUIMgr failed: ' + traceback.format_exc())
            return False

    # Help text
    def getHelp(self):  # noqa: N802
        return 'LGNode Plugin: Adds a top-level menu with sample actions.'

    # QAction slot
    def _on_test_clicked(self):
        _log('Test Action triggered')
        try:
            ctx = sd.getContext()
            app = ctx.getSDApplication()
            mainwindow = app.getQtForPythonUIMgr().getMainWindow()
            QtWidgets.QMessageBox.information(mainwindow, 'LGNode', 'LGNode plugin is working!')
        except Exception:
            _log('Test action failed: ' + traceback.format_exc())


# Factory expected by the plugin loader
_def_instance_note = 'Each reload returns a fresh instance.'

def getSDPlugin():  # Factory for SD
    _log('getSDPlugin (library) called. ' + _def_instance_note)
    try:
        return LGNodeLibrary()
    except Exception:
        _log('getSDPlugin failed: ' + traceback.format_exc())
        return None
