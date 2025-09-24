# LGNode Advanced Tutorial D: Unused Resource & Orphan Node Cleanup

> Goal: Add a menu action that scans the current graph for nodes that are not contributing to any final output ("orphans") and optionally deletes them (with a confirmation dialog and dry‑run mode).

## Why Cleanup Matters
Large graphs accumulate experimental nodes. These unused nodes:
- Increase visual clutter
- Slow down evaluation
- Cause confusion for collaborators
An automated cleanup tool speeds iteration and keeps graphs healthy.

## Definitions
- Output Nodes: Nodes of type `sbs::output` (or those with usage marking them as outputs).
- Reachable Nodes: Any node that can be traversed upstream (following input connections) from at least one output node.
- Orphan Nodes: Nodes present in the graph but not in the reachable set.

## High-Level Algorithm
1. Collect all nodes in graph -> `all_nodes`.
2. Identify all output nodes -> `outputs`.
3. Traverse upstream from each output to build `reachable` set.
4. Orphans = `all_nodes - reachable`.
5. (Optional) Filter out mandatory or protected node types (e.g., resource instances, frames) if needed.
6. Present a summary dialog (count + list) with options:
   - Dry Run (do nothing, just list)
   - Delete All Orphans
   - Cancel

## Traversal Logic
We treat node connections as dependencies. For a given node, its input properties may be connected to outputs of other nodes. We recursively visit those source nodes.

Pseudocode:
```python
def collect_reachable(graph, starts):
    stack = list(starts)
    visited = set()
    while stack:
        n = stack.pop()
        if n in visited:
            continue
        visited.add(n)
        # For each input property, find its connection source node
        for prop in n.getInputProperties():
            conns = graph.getPropertyConnections(prop)
            for c in conns:
                src_prop = c.getSrc()
                src_node = src_prop.getNode()
                if src_node not in visited:
                    stack.append(src_node)
    return visited
```

## Edge Cases
- Graph with zero outputs: All nodes become orphans? We instead treat as: show message "No output nodes; cleanup skipped.".
- Cycles: The visited set prevents infinite loops.
- Locked nodes / read-only: Skip deletion if API forbids.
- External resource references: We only act on graph nodes, not underlying dependencies.

## Implementation Strategy
We'll create `GraphCleaner` with methods:
- `find_orphans(graph) -> (orphans, reachable, outputs)`
- `delete_nodes(graph, nodes)`
- `run_cleanup()` orchestrates UI prompts.

## Full Example Code
```python
# examples/lgnode_cleanup.py
from PySide2 import QtWidgets
import sd

class GraphCleaner:
    def __init__(self, log_func=print):
        self._log = log_func

    # Public entry
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
        # Summary dialog
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

    # Core analysis
    def find_orphans(self, graph):
        all_nodes = set(graph.getNodes())
        outputs = [n for n in all_nodes if self._is_output_node(n)]
        if not outputs:
            return set(), set(), []
        reachable = self._collect_reachable(graph, outputs)
        orphans = all_nodes - reachable
        # Optionally filter out frames or backdrops if they appear
        return orphans, reachable, outputs

    def _is_output_node(self, node):
        rid = node.getDefinition().getId() if node.getDefinition() else ''
        return 'output' in rid  # heuristic; refine if needed

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
```

## Menu Integration
```python
from examples.lgnode_cleanup import GraphCleaner
self.graph_cleaner = GraphCleaner(self._log)
act_cleanup = QtWidgets.QAction('Cleanup Orphan Nodes', main_win)
act_cleanup.triggered.connect(self.graph_cleaner.run_cleanup)
menu.addAction(act_cleanup)
```
(Adjust import path to match your plugin package structure.)

## Safety Considerations
- Always offer Dry Run.
- Consider adding Undo grouping (if API feature available in your SD version).
- Provide a max preview list length to keep dialogs responsive.
- Potential improvement: classify node types (generators, filters, outputs) for more refined pruning.

## Extensions
1. Add a checkbox dialog instead of message box, letting user deselect nodes before deletion.
2. Add a mode to move orphans to a special frame node instead of deleting.
3. Track last cleanup timestamp and show in plugin about dialog.
4. Provide statistics: total nodes, reachable %, orphan %.
5. Integrate with a logging panel in a dock widget.

## Next Tutorial
Proceed to Tutorial E: Submenus & Icons – polish your LGNode menu with icons, grouping, and shortcuts.

---
**Tip:** Keep logging very clear. A cleanup tool must be transparent so users trust it.
