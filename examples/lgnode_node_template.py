"""Example for Tutorial C: Create a simple Perlin->Blend->Output template"""
from PySide2 import QtWidgets
import sd

class TemplateBuilder:
    def __init__(self, log_func=print):
        self._log = log_func

    def run_basic_noise_chain(self):
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        ui_mgr = app.getQtForPythonUIMgr()
        graph = ui_mgr.getCurrentGraph()
        if graph is None:
            QtWidgets.QMessageBox.warning(ui_mgr.getMainWindow(), 'Template', 'No active graph.')
            return
        try:
            self._build(graph)
        except Exception as e:
            self._log(f"[Template] Failed: {e}")
            QtWidgets.QMessageBox.critical(ui_mgr.getMainWindow(), 'Template Error', str(e))

    # ---------------- internal helpers ----------------
    def _unique_id(self, graph, base):
        existing = {n.getIdentifier() for n in graph.getNodes()}
        if base not in existing:
            return base
        i = 1
        while f"{base}_{i}" in existing:
            i += 1
        return f"{base}_{i}"

    def _build(self, graph):
        perlin = graph.newNode('sbs::noise::perlin')
        blend = graph.newNode('sbs::composite')
        output = graph.newNode('sbs::output')

        perlin.setIdentifier(self._unique_id(graph, 'LG_Perlin'))
        blend.setIdentifier(self._unique_id(graph, 'LG_Blend'))
        output.setIdentifier(self._unique_id(graph, 'LG_Output'))

        x0, y0, dx = 200, 200, 240
        perlin.setPosition(x0, y0)
        blend.setPosition(x0 + dx, y0)
        output.setPosition(x0 + 2*dx, y0)

        def safe_out(node, idx=0):
            outs = node.getOutputProperties()
            return outs[idx] if idx < len(outs) else None
        def safe_in(node, idx=0):
            ins = node.getInputProperties()
            return ins[idx] if idx < len(ins) else None

        p_out = safe_out(perlin)
        b_in1 = safe_in(blend, 0)
        b_out = safe_out(blend)
        o_in = safe_in(output, 0)

        graph.connectProperties(p_out, b_in1) if p_out and b_in1 else None
        graph.connectProperties(b_out, o_in) if b_out and o_in else None

        self._log('[Template] Created Perlin->Blend->Output chain.')
