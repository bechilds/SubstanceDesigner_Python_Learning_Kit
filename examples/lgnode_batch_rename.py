"""Example: Batch rename selected nodes (used in Tutorial B)
Integrate by importing BatchRenamer and adding a QAction in your plugin.
"""
from PySide2 import QtWidgets
import sd
import re

class BatchRenamer:
    def __init__(self, log_func=print):
        self._log = log_func

    def run(self):
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        ui_mgr = app.getQtForPythonUIMgr()
        graph = ui_mgr.getCurrentGraph()
        if graph is None:
            self._log('[BatchRename] No active graph.')
            QtWidgets.QMessageBox.warning(ui_mgr.getMainWindow(), 'Batch Rename', 'No active graph found.')
            return

        nodes = list(graph.getSelectedNodes())
        if not nodes:
            self._log('[BatchRename] No selected nodes.')
            QtWidgets.QMessageBox.information(ui_mgr.getMainWindow(), 'Batch Rename', 'Select at least one node.')
            return

        dlg = BatchRenameDialog(ui_mgr.getMainWindow())
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        cfg = dlg.get_config()
        self._apply(nodes, cfg)

    def _apply(self, nodes, cfg):
        pad = cfg['padding']
        start = cfg['start_index']
        prefix = cfg['prefix']
        suffix = cfg['suffix']
        use_original = cfg['keep_original']

        for i, node in enumerate(nodes):
            original_id = node.getIdentifier()
            base = original_id if use_original else cfg['base_name'] or 'Node'
            number = str(start + i).zfill(pad)
            new_id = f"{prefix}{base}{number}{suffix}"
            new_id = re.sub(r'[^A-Za-z0-9_\-]', '_', new_id)
            try:
                node.setIdentifier(new_id)
                self._log(f"[BatchRename] {original_id} -> {new_id}")
            except Exception as e:
                self._log(f"[BatchRename] Failed {original_id}: {e}")

class BatchRenameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Batch Rename Nodes')
        self.setMinimumWidth(320)

        self.prefix_edit = QtWidgets.QLineEdit('')
        self.base_edit = QtWidgets.QLineEdit('Base')
        self.keep_original_chk = QtWidgets.QCheckBox('Use original node name (ignore Base)')
        self.suffix_edit = QtWidgets.QLineEdit('')
        self.start_spin = QtWidgets.QSpinBox(); self.start_spin.setValue(1)
        self.padding_spin = QtWidgets.QSpinBox(); self.padding_spin.setRange(1,6); self.padding_spin.setValue(2)

        form = QtWidgets.QFormLayout()
        form.addRow('Prefix:', self.prefix_edit)
        form.addRow('Base Name:', self.base_edit)
        form.addRow('', self.keep_original_chk)
        form.addRow('Suffix:', self.suffix_edit)
        form.addRow('Start Index:', self.start_spin)
        form.addRow('Padding:', self.padding_spin)

        btn_ok = QtWidgets.QPushButton('OK')
        btn_cancel = QtWidgets.QPushButton('Cancel')
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        h = QtWidgets.QHBoxLayout(); h.addStretch(1); h.addWidget(btn_ok); h.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(h)

    def get_config(self):
        return {
            'prefix': self.prefix_edit.text(),
            'base_name': self.base_edit.text(),
            'suffix': self.suffix_edit.text(),
            'start_index': self.start_spin.value(),
            'padding': self.padding_spin.value(),
            'keep_original': self.keep_original_chk.isChecked(),
        }
