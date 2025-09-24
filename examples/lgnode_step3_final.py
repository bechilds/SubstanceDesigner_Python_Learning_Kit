"""LGNode Step 3 - Final example with menu, action, and simple logging.
Requires plugin.txt mapping: lgnode=LGNodeLibrary
This mirrors the tutorial's final integrated version.
"""
from sd.api.sdplugin import SDPluginLibrary, SDPluginInfo
from PySide2 import QtWidgets
import sd, os, time

LOG_PATH = os.path.join(os.path.expanduser('~'), 'lgnode_plugin.log')

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[LGNode][{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

class LGNodeLibrary(SDPluginLibrary):
    def __init__(self):
        self._menu = None
        _log('__init__')

    def initializeSDPlugin(self):
        _log('initializeSDPlugin')
        return SDPluginInfo(
            'LGNode', 'Adds LGNode menu with Test Action', 'You', '1.0.0', '2025',
            SDPluginInfo.LibraryType.Python
        )

    def onInitializeSDUIMgr(self, uiMgr):
        _log('onInitializeSDUIMgr')
        mw = uiMgr.getMainWindow()
        bar = mw.menuBar()
        for act in bar.actions():
            if act.text() == 'LGNode':
                _log('Menu already exists')
                self._menu = act.menu()
                return True
        self._menu = QtWidgets.QMenu('LGNode', bar)
        act = QtWidgets.QAction('Test Action', self._menu)
        act.triggered.connect(self._on_test)
        self._menu.addAction(act)
        bar.addMenu(self._menu)
        _log('Menu + action added')
        return True

    def _on_test(self):
        _log('Test Action triggered')
        try:
            ctx = sd.getContext()
            app = ctx.getSDApplication()
            mw = app.getQtForPythonUIMgr().getMainWindow()
            QtWidgets.QMessageBox.information(mw, 'LGNode', 'LGNode plugin is working!')
        except Exception as e:
            _log('Test action failed: ' + str(e))

    def onDeinitializeSDPlugin(self):
        _log('onDeinitializeSDPlugin')
        if self._menu:
            self._menu.deleteLater()
        return True
