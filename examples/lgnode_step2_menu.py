"""LGNode Step 2 - Adds a top-level menu without actions.
Requires plugin.txt mapping: lgnode=LGNodeMenuOnly
"""
from sd.api.sdplugin import SDPluginLibrary, SDPluginInfo
from PySide2 import QtWidgets

class LGNodeMenuOnly(SDPluginLibrary):
    def __init__(self):
        self._menu = None

    def initializeSDPlugin(self):
        return SDPluginInfo(
            'LGNode', 'Adds a top-level LGNode menu', 'You', '0.2.0', '2025',
            SDPluginInfo.LibraryType.Python
        )

    def onInitializeSDUIMgr(self, uiMgr):
        mw = uiMgr.getMainWindow()
        bar = mw.menuBar()
        for act in bar.actions():
            if act.text() == 'LGNode':
                self._menu = act.menu()
                return True
        self._menu = QtWidgets.QMenu('LGNode', bar)
        bar.addMenu(self._menu)
        print('LGNode menu added (no actions yet)')
        return True

    def onDeinitializeSDPlugin(self):
        if self._menu:
            self._menu.deleteLater()
        return True
