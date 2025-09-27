# This script prints the names of the main menu items in Substance Designer.
import sd
from PySide2 import QtWidgets
app = sd.getContext().getSDApplication()
mw = app.getQtForPythonUIMgr().getMainWindow()
mb = mw.menuBar()
print([a.text() for a in mb.actions()])