"""
LGNode Menu Plugin for Substance Designer
This plugin adds a custom menu called 'LGNode' to the Substance Designer menu bar.
"""

from sd.api.sdplugin import SDPluginInfo, SDPluginLibrary
from sd.api.sdapplication import SDApplication
from sd.api.sdmenu import SDMenu
from sd.api.sdaction import SDAction
from sd.api.sduimgr import SDUIMgr
from PySide2 import QtWidgets

# Global plugin instance
plugin_instance = None

def getSDPlugin():
    """Return the plugin instance to Substance Designer."""
    global plugin_instance
    if plugin_instance is None:
        plugin_instance = LGNodePlugin()
    return plugin_instance

class LGNodePlugin(SDPluginLibrary):
    """Main plugin class that creates the LGNode menu."""
    
    def __init__(self):
        """Initialize the plugin instance."""
        self.menu = None
        self.test_action = None
    
    def initializeSDPlugin(self):
        """Initialize the plugin when Substance Designer loads it."""
        # Return plugin info
        return SDPluginInfo(
            "LGNode Plugin",  # Plugin name
            "Adds LGNode menu to Substance Designer",  # Description
            "Author",  # Author
            "v1.0",  # Version
            "2025",  # Year
            SDPluginInfo.LibraryType.Python  # Plugin type
        )

    def onDeinitializeSDPlugin(self):
        """Called when the plugin is being unloaded."""
        if self.menu is not None:
            self.menu.deleteLater()
            self.menu = None
        return True

    def onInitializeSDUIMgr(self, uiMgr):
        """Called when the UI manager is initialized."""
        try:
            # Create the main menu
            menuBar = uiMgr.getMainWindow().menuBar()
            self.menu = SDMenu(menuBar)
            self.menu.setTitle('LGNode')
            
            # Add a test action
            self.test_action = SDAction("Test Action", self.menu)
            self.test_action.triggered.connect(self.test_function)
            self.menu.addAction(self.test_action)
            
            # Add the menu to the menu bar
            menuBar.addMenu(self.menu)
            
            print("LGNode plugin menu initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Error initializing LGNode plugin menu: {str(e)}")
            return False
    
    def uninitializeSDPlugin(self):
        """Clean up when the plugin is unloaded."""
        try:
            if self.menu:
                self.menu.deleteLater()
            return True
        except Exception as e:
            print(f"Error uninitializing LGNode plugin: {str(e)}")
            return False
    
    def test_function(self):
        """Test function to verify the menu is working."""
        QtWidgets.QMessageBox.information(
            SDApplication.get().getQtForPythonUIMgr().getMainWindow(),
            "LGNode Plugin",
            "LGNode plugin is working!"
        )
    
    def getHelp(self):
        """Return help text for the plugin."""
        return "LGNode Plugin - Adds custom functionality to Substance Designer"