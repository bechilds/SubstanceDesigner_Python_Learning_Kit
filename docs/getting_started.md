# Getting Started with Substance Designer Python Scripting

Welcome! This guide will help you get started with Python scripting in Adobe Substance Designer, even if you're new to programming.

## 📋 Prerequisites

1. **Adobe Substance Designer** (2019.1 or later)
2. A basic understanding of Substance Designer interface
3. No prior programming experience required!

## 🚀 Quick Start

### Step 1: Open the Script Editor
1. Launch Substance Designer
2. Go to `Tools > Scripting > Script Editor`
3. This opens the Python script editor where you'll run your scripts

### Step 2: Run Your First Script
1. Open `tutorials/01_introduction.py` in the Script Editor
2. Click the "Run" button (or press F5)
3. Watch the output in the console below

### Step 3: Work Through the Tutorials
Follow this learning path:
1. `tutorials/01_introduction.py` - Learn the basics
2. `tutorials/02_working_with_nodes.py` - Understand nodes
3. `tutorials/03_parameters.py` - Master parameters

## 📁 File Structure Explained

```
├── tutorials/          # Learning materials (start here!)
├── examples/           # Practical working scripts
├── utilities/          # Helper functions you can reuse
├── scripts/            # Your custom scripts go here
└── docs/              # Documentation and guides
```

## 🎯 What Can You Do with Python in Substance Designer?

### 1. Automate Repetitive Tasks
- Batch process multiple materials
- Apply the same changes to many nodes
- Generate variations of existing substances

### 2. Parameter Management
- Expose parameters automatically
- Delete unwanted exposed parameters
- Organize parameters into groups

### 3. Node Operations
- Create complex node networks automatically
- Connect nodes based on rules
- Duplicate and modify existing setups

### 4. File Operations
- Process multiple .sbs files
- Export materials in different formats
- Generate reports about your substances

## 🔧 Running Scripts

### Method 1: Script Editor (Recommended for Beginners)
1. Open Substance Designer
2. Load a .sbs file (your material)
3. Open `Tools > Scripting > Script Editor`
4. Copy and paste script code, or load a .py file
5. Click "Run" or press F5

### Method 2: External Python (Advanced)
Some scripts can run externally to process files in batch.

## 💡 Tips for Beginners

### Understanding the Code Structure
```python
# This is a comment - it explains what the code does
import sd  # This imports the Substance Designer module

def main():  # This defines a function
    # Your code goes here
    print("Hello Substance Designer!")  # This prints text

if __name__ == "__main__":  # This runs the main function
    main()
```

### Common Patterns
1. **Always start with imports**
2. **Get the current context** (connection to SD)
3. **Get the current package/graph** (your material)
4. **Do your operations** (the actual work)
5. **Handle errors gracefully** (what if something goes wrong)

### Reading Error Messages
When something goes wrong, the console will show error messages:
- Read the last line first (usually the main error)
- Look for line numbers to find where the problem is
- Common issues: file not loaded, wrong node name, etc.

## 📚 Learning Resources

### Official Documentation
- [Substance Designer Python API](https://substance3d.adobe.com/documentation/sddoc/python-api-184191934.html)
- [Substance Automation Toolkit](https://substance3d.adobe.com/documentation/sddoc/substance-automation-toolkit-187073291.html)

### Key Concepts to Learn
1. **Context** - The connection to Substance Designer
2. **Packages** - Your .sbs files
3. **Graphs** - The material networks inside packages
4. **Nodes** - Individual elements in your material
5. **Properties** - Settings and connections on nodes
6. **Parameters** - Exposed settings you can adjust

## 🛠 Troubleshooting

### "Import sd could not be resolved"
This is normal! The `sd` module only exists inside Substance Designer. Your code will work fine when run in the Script Editor.

### "No packages loaded"
Make sure you have a .sbs file open in Substance Designer before running scripts.

### Script doesn't do anything
Check that you have the right material selected and that it has the nodes/parameters your script expects.

### Permission errors
Make sure your .sbs file isn't read-only and that you have permission to modify it.

## 🎨 Your First Custom Script

Here's a template for your own scripts:

```python
import sd
from sd.api.sdproperty import *

def my_custom_function():
    """
    Describe what your function does here
    """
    try:
        # Connect to Substance Designer
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        
        # Get current package
        packages = package_mgr.getUserPackages()
        if not packages:
            print("No packages loaded!")
            return
        
        current_package = packages[0]
        
        # Get current graph
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        if not graphs:
            print("No graphs found!")
            return
        
        current_graph = graphs[0]
        
        # Your custom code goes here!
        print(f"Working with: {current_graph.getIdentifier()}")
        
    except Exception as e:
        print(f"Error: {e}")

# Run the function
if __name__ == "__main__":
    my_custom_function()
```

## 🤝 Getting Help

1. **Read the error messages carefully**
2. **Start with the tutorial scripts**
3. **Modify existing examples rather than starting from scratch**
4. **Check the official Substance Designer documentation**
5. **Practice with simple materials first**

Happy scripting! 🎉
