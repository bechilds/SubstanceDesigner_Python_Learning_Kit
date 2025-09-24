# Substance Designer Python Scripts

Welcome to your Substance Designer Python scripting workspace! This project is designed for beginners who want to learn how to automate tasks in Adobe Substance Designer using Python.

## 🚀 Getting Started

This workspace contains examples and tutorials to help you learn Substance Designer Python scripting from scratch, even without prior programming experience.

## 📁 Project Structure

```
├── examples/              # Basic example scripts
│   ├── basic_operations.py    # Simple node operations
│   ├── material_automation.py # Material creation automation
│   └── batch_processing.py    # Batch file operations
├── tutorials/             # Step-by-step tutorials
│   ├── 01_introduction.py     # Introduction to SD Python API
│   ├── 02_working_with_nodes.py # Node manipulation
│   ├── 03_parameters.py       # Working with parameters
│   └── 04_advanced_examples.py # Advanced automation
├── utilities/             # Helper functions and utilities
│   ├── sd_helpers.py          # Common helper functions
│   └── node_templates.py     # Reusable node templates
├── scripts/               # Your custom scripts
└── docs/                  # Documentation and guides
```

## 🛠 Requirements

- Adobe Substance Designer (2019.1 or later)
- Python 3.7+ (included with Substance Designer)
- Basic understanding of Substance Designer interface

## 📖 Learning Path

1. **Start with tutorials/01_introduction.py** - Learn the basics
2. **Work through examples/** - See practical implementations
3. **Create your own scripts in scripts/** - Apply what you learned

### NEW: Plugin (Menu) Development Tutorial
Want to add a custom top-level menu (e.g., “LGNode”) into Substance Designer?
Follow the step-by-step guide:

- Tutorial: [docs/tutorial_lgnode_menu_plugin.md](docs/tutorial_lgnode_menu_plugin.md)
- Progressive example snapshots:
	- Minimal recognizable plugin: `examples/lgnode_step1_minimal.py`
	- Adds menu only: `examples/lgnode_step2_menu.py`
	- Final with action + logging: `examples/lgnode_step3_final.py`

These examples mirror the learning progression and are safe to copy into your user plugin folder for experimentation.

#### Advanced LGNode Tutorials (B–E)
Build on the basics with practical, production-style tools:

- Tutorial B (Batch Rename Nodes): [docs/tutorial_lgnode_batch_rename.md](docs/tutorial_lgnode_batch_rename.md)
  - Example: `examples/lgnode_batch_rename.py`
- Tutorial C (Node Template Builder): [docs/tutorial_lgnode_node_templates.md](docs/tutorial_lgnode_node_templates.md)
  - Example: `examples/lgnode_node_template.py`
- Tutorial D (Cleanup Unused / Orphan Nodes): [docs/tutorial_lgnode_cleanup_unused.md](docs/tutorial_lgnode_cleanup_unused.md)
  - Example: `examples/lgnode_cleanup.py`
- Tutorial E (Submenus, Icons & Shortcuts): [docs/tutorial_lgnode_submenus_icons.md](docs/tutorial_lgnode_submenus_icons.md)

Each tutorial explains: goals, design decisions, full code, integration snippet, troubleshooting, and extension exercises.

## 🎯 Common Use Cases

- Automating repetitive node setups
- Batch processing multiple substances
- Creating custom material generators
- Exposing/unexposing parameters automatically
- Generating variations of existing materials

## 🔧 Running Scripts

### In Substance Designer:
1. Open Substance Designer
2. Go to Tools > Scripting > Script Editor
3. Load and run your Python scripts

### As External Tools:
Some scripts can be run externally to process .sbs files

## 📚 Resources

- [Substance Designer Python API Documentation](https://substance3d.adobe.com/documentation/sddoc/python-api-184191934.html)
- [Substance Automation Toolkit](https://substance3d.adobe.com/documentation/sddoc/substance-automation-toolkit-187073291.html)

## 🤝 Contributing

Feel free to add your own scripts and improvements to this workspace!

---
Happy scripting! 🎨
