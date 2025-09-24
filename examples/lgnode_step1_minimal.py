"""LGNode Step 1 - Minimal recognizable plugin (Library style)
Copy this (with a proper plugin.txt) to your sduserplugins/lgnode folder to test
basic initialization without UI.
"""
from sd.api.sdplugin import SDPluginLibrary, SDPluginInfo

class LGNodeMini(SDPluginLibrary):
    def initializeSDPlugin(self):  # Return plugin info (critical)
        return SDPluginInfo(
            'LGNodeMini',
            'Minimal test plugin',
            'You', '0.0.1', '2025',
            SDPluginInfo.LibraryType.Python
        )

    def onInitializeSDUIMgr(self, uiMgr):
        print('LGNodeMini: onInitializeSDUIMgr called')
        return True

    def onDeinitializeSDPlugin(self):
        return True
