# LGNode Advanced Tutorial C: Node Template (Scaffold) Creator

> Goal: Add a menu action that auto-builds a small, reusable node cluster ("template") inside the current graph (e.g., a Perlin Noise -> Blend -> Output pipeline) with proper positioning, naming, and basic parameter settings.

## What You'll Learn
- Accessing the current Substance graph
- Creating new nodes programmatically
- Setting node identifiers and parameters
- Positioning nodes to avoid overlap
- Connecting node input/output slots
- Wrapping all logic into a reusable TemplateBuilder class
- Integrating a new action into the existing `LGNode` menu

## Why Templates?
When you repeatedly build the same structure (e.g., noise source + adjustments + output), a template action saves time and reduces mistakes. You press one menu item and instantly get a clean, named cluster of nodes ready for tweaking.

## Final Result Preview
After invoking the action, you'll see (example identifiers):
```
LG_Perlin
LG_Blend
LG_Output
```
Arranged horizontally and already connected: Perlin -> Blend -> Output.

## Step 1: Access the Active Graph
We always begin by acquiring context and the current graph:
```python
ctx = sd.getContext()
app = ctx.getSDApplication()
ui_mgr = app.getQtForPythonUIMgr()
graph = ui_mgr.getCurrentGraph()
```
If `graph` is `None`, show a user warning and abort.

## Step 2: Create Nodes
We'll create three nodes:
1. A noise (e.g., `sbs::noise::perlin`) – adjust name if API changes.
2. A blend/composite node (e.g., `sbs::composite`) – acts as adjustable middle processor.
3. An output node (identifier must be unique; using standard output definition).

Creating a node requires the unique node resource ID (format often `sbs::category::name`). You can discover IDs by:
- Dragging a node, right-click -> Copy Identifier (if available) OR
- Inspecting official docs / logs / existing graphs.

Example snippet:
```python
perlin_node = graph.newNode('sbs::noise::perlin')
blend_node = graph.newNode('sbs::composite')
output_node = graph.newNode('sbs::output')
```
Always wrap in try/except and fall back gracefully if a node type is missing.

## Step 3: Assign Identifiers
Good identifiers ease later scripting:
```python
perlin_node.setIdentifier('LG_Perlin')
blend_node.setIdentifier('LG_Blend')
output_node.setIdentifier('LG_Output')
```
If a name already exists, append a numeric suffix. We'll build a helper for uniqueness.

## Step 4: Position Nodes
Substance Designer nodes have 2D positions (usually in pixels). We can offset nodes horizontally with a simple increment:
```python
x0, y0 = 200, 200
perlin_node.setPosition(x0, y0)
blend_node.setPosition(x0 + 220, y0)
output_node.setPosition(x0 + 440, y0)
```
(Exact spacing is aesthetic; adjust to taste.)

## Step 5: Connect Slots
Composite/Blend nodes typically expose inputs like `input1`, `input2`, etc. We will connect:
- Perlin output -> Blend input1
- Blend output -> Output node input (often `unique_filter_output` or similar – but for an output node, we connect the previous node's output to the output node's input slot).

Simplified example:
```python
perlin_out = perlin_node.getOutputProperty(0)
blend_in1 = blend_node.getInputProperty(0)
blend_out = blend_node.getOutputProperty(0)
output_in = output_node.getInputProperty(0)

graph.connectProperties(perlin_out, blend_in1)
graph.connectProperties(blend_out, output_in)
```
(Indices may differ depending on versions – you can introspect properties dynamically if needed.)

## Step 6: Parameter Tweaks (Optional)
You can fetch a node's properties and set numerical parameters (e.g., seed, scale). Example:
```python
perlin_props = perlin_node.getProperties()
for p in perlin_props:
    pid = p.getId()
    if pid == 'scale':
        perlin_node.setPropertyValue(p, sd.api.sdvaluefloat.SDValueFloat.sNew(8.0))
```
Use only if you know the parameter IDs; otherwise skip or log available property IDs for discovery.

## Step 7: Wrap in a Class
We'll encapsulate logic into `TemplateBuilder` with a public `create_basic_noise_chain()` method.

## Full Example Code (Template Builder)
```python
# examples/lgnode_node_template.py
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
        # Create nodes (robust with try/except per node if desired)
        perlin = graph.newNode('sbs::noise::perlin')
        blend = graph.newNode('sbs::composite')
        output = graph.newNode('sbs::output')

        # Unique IDs
        perlin.setIdentifier(self._unique_id(graph, 'LG_Perlin'))
        blend.setIdentifier(self._unique_id(graph, 'LG_Blend'))
        output.setIdentifier(self._unique_id(graph, 'LG_Output'))

        # Positioning
        x0, y0, dx = 200, 200, 240
        perlin.setPosition(x0, y0)
        blend.setPosition(x0 + dx, y0)
        output.setPosition(x0 + 2*dx, y0)

        # Connections (defensive: check property counts)
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

        if p_out and b_in1:
            graph.connectProperties(p_out, b_in1)
        if b_out and o_in:
            graph.connectProperties(b_out, o_in)

        self._log('[Template] Created Perlin->Blend->Output chain.')
```

## Step 8: Add Menu Action Integration
In your plugin's `onInitializeSDUIMgr()` after creating / finding the `LGNode` top-level menu:
```python
from examples.lgnode_node_template import TemplateBuilder  # adjust relative import as needed

self.template_builder = TemplateBuilder(self._log)
act_template = QtWidgets.QAction('Create Noise Template', main_win)
act_template.triggered.connect(self.template_builder.run_basic_noise_chain)
menu.addAction(act_template)
```
Be sure the import path is valid relative to where the plugin executes (you might need to adjust `sys.path`). For a production plugin, consider moving the builder into a `plugins/lgnode/` submodule.

## Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| Node type not found | API node identifier changed | Print/log available node types or verify in docs |
| Connection fails | Property index wrong | Iterate properties and log their IDs to inspect |
| Duplicate identifier error | Name already used | Use `_unique_id` helper (already in code) |
| Template menu missing | Import path failure | Add repo root to `sys.path` or relocate file into plugin package |

## Exercises
1. Extend the chain: Add a Levels (or Histogram Scan) node between Blend and Output.
2. Add a dialog to choose which noise (Perlin, Clouds, BnW Spots) to instantiate.
3. Create multiple layout rows (stack vertically) if user runs it multiple times.
4. Implement parameter randomization (random seed for noise).
5. Add undo grouping if the API supports it (so one Ctrl+Z removes the whole template).

## Next Tutorial
Proceed to Tutorial D: Unused Resource Cleanup – analyzing the graph for orphaned nodes/resources and safely removing them.

---
**Tip:** Keep each template builder focused. For complex graphs, build smaller reusable functions (create_noise(), create_output()) and compose them.
