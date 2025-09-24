"""Example for Tutorial D: Cleanup orphan (unused) nodes in current graph"""
from PySide2 import QtWidgets
import sd

class GraphCleaner:
    def __init__(self, log_func=print):
        self._log = log_func

    def run_cleanup(self):
        ctx = sd.getContext(); app = ctx.getSDApplication(); ui = app.getQtForPythonUIMgr()
        graph = ui.getCurrentGraph()
        if graph is None:
            QtWidgets.QMessageBox.warning(ui.getMainWindow(), 'Cleanup', 'No active graph.')
            return
        orphans, reachable, outputs = self.find_orphans(graph)
        if not outputs:
            QtWidgets.QMessageBox.information(ui.getMainWindow(), 'Cleanup', 'No output nodes found; aborting.')
            return
        if not orphans:
            QtWidgets.QMessageBox.information(ui.getMainWindow(), 'Cleanup', 'No orphan nodes detected.')
            return
        details = '\n'.join(sorted([n.getIdentifier() for n in orphans])[:25])
        if len(orphans) > 25:
            details += f"\n... (+{len(orphans)-25} more)"
        msg = QtWidgets.QMessageBox(ui.getMainWindow())
        msg.setWindowTitle('Cleanup Orphan Nodes')
        msg.setText(f"Orphan Nodes Found: {len(orphans)}\nDelete them? (Dry Run = list only)")
        msg.setDetailedText(details)
        dry_btn = msg.addButton('Dry Run', QtWidgets.QMessageBox.ActionRole)
        del_btn = msg.addButton('Delete', QtWidgets.QMessageBox.DestructiveRole)
        cancel_btn = msg.addButton('Cancel', QtWidgets.QMessageBox.RejectRole)
        msg.exec_()
        clicked = msg.clickedButton()
        if clicked == cancel_btn:
            return
        if clicked == dry_btn:
            self._log('[Cleanup] Dry run complete.')
            return
        if clicked == del_btn:
            self.delete_nodes(graph, orphans)
            self._log(f"[Cleanup] Deleted {len(orphans)} orphan nodes.")

    def find_orphans(self, graph):
        all_nodes = set(graph.getNodes())
        outputs = [n for n in all_nodes if self._is_output_node(n)]
        if not outputs:
            return set(), set(), []
        reachable = self._collect_reachable(graph, outputs)
        orphans = all_nodes - reachable
        return orphans, reachable, outputs

    def _is_output_node(self, node):
        rid = node.getDefinition().getId() if node.getDefinition() else ''
        return 'output' in rid

    def _collect_reachable(self, graph, start_nodes):
        stack = list(start_nodes)
        visited = set()
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            for prop in n.getInputProperties():
                for conn in graph.getPropertyConnections(prop):
                    src_prop = conn.getSrc()
                    src_node = src_prop.getNode()
                    if src_node not in visited:
                        stack.append(src_node)
        return visited

    def delete_nodes(self, graph, nodes):
        for n in nodes:
            try:
                graph.deleteNode(n)
            except Exception as e:
                self._log(f"[Cleanup] Failed to delete {n.getIdentifier()}: {e}")
