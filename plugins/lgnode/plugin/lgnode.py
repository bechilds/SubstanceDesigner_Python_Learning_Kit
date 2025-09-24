"""
LGNode Plugin for Substance Designer
"""

import sd
import logging
from PySide2 import QtWidgets

def getSDPlugin():
    """Return the plugin instance."""
    import sd.api.sdplugin
    return LGNode()

class LGNode(sd.api.sdplugin.SDPlugin):
    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        self._menu = None
        print("LGNode plugin initialized")

def getSDPlugin():
    """Return the plugin instance to Substance Designer."""
    global plugin_instance
    if plugin_instance is None:
        plugin_instance = LGNodePlugin()
    return plugin_instance

class LGNodePlugin(SDPlugin):
    """Main plugin class that creates the LGNode menu."""
    
    def __init__(self):
        """Initialize the plugin instance."""
        super().__init__()
        print("LGNode plugin instance created")
    
    def initializeSDPlugin(self):
        """Initialize the plugin when Substance Designer loads it."""
        try:
            print("LGNode plugin initializing...")
            return SDPluginStatus.Success
        except Exception as e:
            print("Error during initialization:", str(e))
            return SDPluginStatus.Failure

    def uninitializeSDPlugin(self):
        """Clean up when the plugin is unloaded."""
        try:
            print("LGNode plugin uninitializing...")
            return SDPluginStatus.Success
        except Exception as e:
            print("Error during uninitialization:", str(e))
            return SDPluginStatus.Failure

    def getHelp(self):
        """Return help text for the plugin."""
        return "LGNode Plugin - Basic plugin structure for debugging"