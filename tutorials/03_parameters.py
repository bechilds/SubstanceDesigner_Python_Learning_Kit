"""
Working with Parameters in Substance Designer
=============================================

What you'll learn:
- How to expose and unexpose parameters
- Modifying parameter values
- Creating parameter groups
- Setting parameter ranges and defaults
- Batch parameter operations

This script addresses the specific use case in your DeleteExposeParameters folder!
"""

import sd
from sd.api.sdproperty import *
from sd.api.sdvaluearray import *

def main():
    """
    Demonstrates parameter manipulation in Substance Designer
    """
    print("⚙️  Working with Parameters Tutorial")
    print("=" * 45)
    
    try:
        # Get the current context
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        
        packages = package_mgr.getUserPackages()
        if not packages:
            print("❌ No packages loaded. Please open a .sbs file first!")
            return
        
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if not graphs:
            print("❌ No graphs found!")
            return
        
        current_graph = graphs[0]
        print(f"📊 Working with graph: {current_graph.getIdentifier()}")
        
        # Step 1: List all exposed parameters
        print("\n📋 Step 1: Listing exposed parameters...")
        exposed_params = current_graph.getExposedParameters()
        
        if exposed_params:
            print(f"Found {len(exposed_params)} exposed parameter(s):")
            for i, param in enumerate(exposed_params):
                param_id = param.getId()
                param_label = param.getLabel()
                param_group = param.getGroup()
                print(f"   {i+1}. {param_id} - '{param_label}' (Group: {param_group})")
        else:
            print("   📝 No exposed parameters found.")
        
        # Step 2: Find parameters that can be exposed
        print("\n🔍 Step 2: Finding unexposed parameters...")
        nodes = current_graph.getNodes()
        unexposed_count = 0
        
        for node in nodes:
            # Get input properties that could be exposed
            input_props = node.getProperties(SDPropertyCategory.Input)
            
            for prop in input_props:
                # Check if this property is not already exposed
                if not prop.isConnectedToExposedParameter():
                    unexposed_count += 1
                    # Only show first few to avoid spam
                    if unexposed_count <= 5:
                        print(f"   📌 {node.getIdentifier()}.{prop.getId()} - {prop.getLabel()}")
        
        if unexposed_count > 5:
            print(f"   ... and {unexposed_count - 5} more unexposed parameters")
        
        print(f"📊 Total unexposed parameters: {unexposed_count}")
        
        # Step 3: Example of how to expose a parameter
        print("\n➕ Step 3: How to expose a parameter...")
        print("💡 Code example to expose a parameter:")
        print("""
        # Find the property you want to expose
        target_property = some_node.getPropertyFromId('inputname', SDPropertyCategory.Input)
        
        # Create an exposed parameter
        exposed_param = current_graph.exposeParameter(target_property)
        exposed_param.setLabel('My Custom Parameter')
        exposed_param.setGroup('Custom Group')
        """)
        
        # Step 4: Example of how to delete exposed parameters
        print("\n🗑️  Step 4: How to delete exposed parameters...")
        print("💡 Code example to delete exposed parameters:")
        print("""
        # Get all exposed parameters
        exposed_params = current_graph.getExposedParameters()
        
        # Delete specific parameters
        for param in exposed_params:
            if 'unwanted' in param.getId().lower():
                current_graph.deleteExposedParameter(param)
        
        # Or delete ALL exposed parameters (be careful!)
        # for param in exposed_params:
        #     current_graph.deleteExposedParameter(param)
        """)
        
        # Step 5: Show parameter value manipulation
        if exposed_params:
            print("\n🎛️  Step 5: Parameter value examples...")
            first_param = exposed_params[0]
            print(f"📋 Examining parameter: {first_param.getLabel()}")
            
            # Get the property this parameter is connected to
            connected_props = first_param.getConnectedProperties()
            if connected_props:
                prop = connected_props[0]
                current_value = prop.getValue()
                print(f"   📄 Current value type: {type(current_value)}")
                print(f"   📊 Current value: {current_value}")
        
        print("\n🎯 Practical Example: Delete Expose Parameters Script")
        print("=" * 55)
        print("Based on your folder name, here's a practical script:")
        print("""
def delete_all_exposed_parameters():
    '''Deletes all exposed parameters from the current graph'''
    context = sd.getContext()
    app = context.getSDApplication()
    package_mgr = app.getPackageMgr()
    packages = package_mgr.getUserPackages()
    
    if packages:
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        for graph in graphs:
            exposed_params = graph.getExposedParameters()
            for param in exposed_params:
                graph.deleteExposedParameter(param)
            print(f"Deleted {len(exposed_params)} parameters from {graph.getIdentifier()}")

# Uncomment to run:
# delete_all_exposed_parameters()
        """)
        
        print("\n🎉 Parameters tutorial completed!")
        print("💡 Next: Try the practical examples in the examples/ folder")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Make sure Substance Designer is running with a material loaded!")

if __name__ == "__main__":
    main()
