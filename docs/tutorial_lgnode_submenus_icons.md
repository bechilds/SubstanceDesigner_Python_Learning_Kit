# LGNode Advanced Tutorial E: Submenus, Icons & Shortcuts

> Goal: Polish the `LGNode` menu by adding submenus, icons, keyboard shortcuts, separators, and basic internationalization patterns.

## Why UI Polish Matters
A clear, well-structured menu:
- Improves discoverability
- Communicates feature grouping
- Looks professional and trustworthy

## Features We'll Add
1. Submenus: Organize actions (e.g., Generators, Tools, Maintenance)
2. Icons: Load from plugin `icons/` folder using `QIcon`
3. Shortcuts: Assign keyboard accelerators (e.g., Ctrl+Alt+R)
4. Separators: Visual grouping
5. About Dialog: Central place for version & links
6. Graceful fallback if icon files missing

## Directory Structure Example
```
plugins/lgnode/
    core.py
    plugin.txt
    icons/
        rename.png
        template.png
        cleanup.png
        about.png
```
Icons should be small PNGs (16–32px). Keep names lowercase and descriptive.

## Loading Icons Safely
```python
import os
from PySide2.QtGui import QIcon

 def _icon(self, name):
     try:
         base = os.path.dirname(__file__)
         path = os.path.join(base, 'icons', name)
         if os.path.exists(path):
             return QIcon(path)
     except Exception:
         pass
     return QIcon()  # empty fallback
```

## Creating Submenus
```python
menu_generators = menu.addMenu('Generators')
menu_tools = menu.addMenu('Tools')
menu_maintenance = menu.addMenu('Maintenance')
```
Add actions to the appropriate submenu for clarity.

## Assigning Shortcuts
```python
action = QtWidgets.QAction('Batch Rename', main_win)
action.setShortcut('Ctrl+Alt+R')  # visible in menu
```
(Ensure no conflict with Designer built-ins.)

## About Dialog Example
```python
def show_about(self):
    QtWidgets.QMessageBox.information(
        main_win,
        'About LGNode',
        'LGNode Tools\nVersion 1.0\nhttps://your-repo-url'
    )
```

## Full Integration Pattern (Excerpt)
Below is a trimmed example focusing on UI assembly. Integrate with earlier classes (BatchRenamer, TemplateBuilder, GraphCleaner) by importing them.

```python
# Inside LGNodeLibrary.onInitializeSDUIMgr()
from PySide2 import QtWidgets
from PySide2.QtGui import QIcon
import os

main_win = ui_mgr.getMainWindow()
menu = self._ensure_menu(main_win)  # assume helper that creates/finds top-level

# --- Icon helper
base_dir = os.path.dirname(__file__)
icons_dir = os.path.join(base_dir, 'icons')

def icon(name):
    p = os.path.join(icons_dir, name)
    return QIcon(p) if os.path.exists(p) else QIcon()

# Submenus
sub_gen = menu.addMenu(icon('template.png'), 'Generators')
sub_tools = menu.addMenu(icon('rename.png'), 'Tools')
sub_main = menu.addMenu(icon('cleanup.png'), 'Maintenance')
menu.addSeparator()

# Actions (assume self.batch_renamer, self.template_builder, self.graph_cleaner exist)
act_template = QtWidgets.QAction(icon('template.png'), 'Create Noise Template', main_win)
act_template.triggered.connect(self.template_builder.run_basic_noise_chain)
sub_gen.addAction(act_template)

act_rename = QtWidgets.QAction(icon('rename.png'), 'Batch Rename Nodes', main_win)
act_rename.setShortcut('Ctrl+Alt+R')
act_rename.triggered.connect(self.batch_renamer.run)
sub_tools.addAction(act_rename)

act_cleanup = QtWidgets.QAction(icon('cleanup.png'), 'Cleanup Orphan Nodes', main_win)
act_cleanup.setShortcut('Ctrl+Alt+C')
act_cleanup.triggered.connect(self.graph_cleaner.run_cleanup)
sub_main.addAction(act_cleanup)

menu.addSeparator()

about_act = QtWidgets.QAction(icon('about.png'), 'About LGNode...', main_win)
about_act.triggered.connect(lambda: QtWidgets.QMessageBox.information(
    main_win, 'About LGNode', 'LGNode Tools\nVersion 1.0'))
menu.addAction(about_act)
```

## Internationalization (Basic Placeholder)
If you plan for multi-language, abstract user-visible strings:
```python
STRINGS = {
    'en': {
        'batch_rename': 'Batch Rename Nodes',
    },
    'zh': {
        'batch_rename': '批量重命名节点',
    }
}
LANG = 'en'
QtWidgets.QAction(STRINGS[LANG]['batch_rename'], main_win)
```
For full i18n you might integrate `.qm` translation files, but a dict works for small tools.

## Error Handling & Fallbacks
- Missing icons: Provide empty `QIcon()` silently.
- Invalid shortcut: Designer might ignore; keep logging minimal.
- Duplicate submenu creation: Write an idempotent finder (`_find_menu_by_title`).

## Polishing Tips
- Group destructive actions (cleanup) into Maintenance with a separator.
- Keep action names concise (< 25 chars).
- If you add many generators, create nested menus: Generators -> Noise / Patterns / Utility.
- Consider a preferences dialog storing user settings in JSON next to the plugin.

## Exercises
1. Add an icon for the top-level `LGNode` menu (some platforms render it; others ignore).
2. Add a submenu "Dev" with an action that reloads the plugin modules (for faster iteration).
3. Implement a dynamic language toggle between English and Chinese.
4. Add a recently used templates list (update submenu each run).
5. Add tooltips (`QAction.setToolTip`) explaining each action succinctly.

## Next Steps
You now have:
- Core menu + actions (Tutorial A)
- Batch rename dialog (Tutorial B)
- Template builder (Tutorial C)
- Cleanup tool (Tutorial D)
- Polished UI with submenus & icons (Tutorial E)

Possible advanced follow-ons:
- Dockable panel for logs
- Undo/redo grouping integration
- Preferences persistence
- Asset library manager
- Bulk parameter randomizer

---
**Tip:** Keep UI discoverable. If users must hover to guess functionality, add concise tooltips.
