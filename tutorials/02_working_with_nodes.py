"""
Working with Nodes in Substance Designer
========================================

What you'll learn:
- How to access nodes in a graph
- Creating new nodes
- Connecting nodes together
- Modifying node properties
- Basic node manipulation operations

Prerequisites:
- Complete 01_introduction.py first
- Have a Substance material (.sbs) open in Substance Designer
"""

import sd
from sd.api.sdnode import *
from sd.api.sdconnection import *
from sd.api.sdproperty import *

def main():
    """
    Demonstrates working with nodes in Substance Designer
    """
    print("🔧 Working with Nodes Tutorial")
    print("=" * 40)
    
    try:
        # Get the current context and application
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        
        # Get the current package
        packages = package_mgr.getUserPackages()
        if not packages:
            print("❌ No packages loaded. Please open a .sbs file first!")
            return
        
        current_package = packages[0]
        print(f"📦 Working with package: {current_package.getFilePath()}")
        
        # Get the first graph (usually the main material graph)
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        if not graphs:
            print("❌ No graphs found in package!")
            return
        
        current_graph = graphs[0]
        print(f"📊 Working with graph: {current_graph.getIdentifier()}")
        
        # Step 1: List all nodes in the graph
        print("\n🔍 Step 1: Listing all nodes...")
        nodes = current_graph.getNodes()
        print(f"Found {len(nodes)} nodes:")
        
        for i, node in enumerate(nodes):
            node_def = node.getDefinition()
            print(f"   {i+1}. {node.getIdentifier()} ({node_def.getLabel()})")
        
        # Step 2: Find specific node types
        print("\n🎯 Step 2: Finding specific node types...")
        
        # Look for common node types
        uniform_nodes = []
        noise_nodes = []
        blend_nodes = []
        
        for node in nodes:
            node_id = node.getDefinition().getId()
            if "uniform" in node_id.lower():
                uniform_nodes.append(node)
            elif "noise" in node_id.lower():
                noise_nodes.append(node)
            elif "blend" in node_id.lower():
                blend_nodes.append(node)
        
        print(f"   📐 Uniform Color nodes: {len(uniform_nodes)}")
        print(f"   🌊 Noise nodes: {len(noise_nodes)}")
        print(f"   🎨 Blend nodes: {len(blend_nodes)}")
        
        # Step 3: Examine node properties
        if nodes:
            print(f"\n🔧 Step 3: Examining properties of first node...")
            first_node = nodes[0]
            print(f"📋 Node: {first_node.getIdentifier()}")
            
            # Get node properties
            properties = first_node.getProperties(SDPropertyCategory.Input)
            print(f"   📥 Input properties: {len(properties)}")
            
            for prop in properties:
                prop_id = prop.getId()
                prop_label = prop.getLabel()
                print(f"      - {prop_id}: {prop_label}")
        
        # Step 4: Create a new node (example)
        print(f"\n➕ Step 4: How to create a new node...")
        print("💡 To create a new node, you would use:")
        print("   new_node = current_graph.newNode('sbs::compositing::uniform')")
        print("   new_node.setPosition(float2(100, 100))")
        
        # Note: We're not actually creating a node to avoid modifying the user's work
        print("   (Not creating actual node to preserve your current work)")
        
        # Step 5: Show how to access node connections
        print(f"\n🔗 Step 5: Examining node connections...")
        connection_count = 0
        
        for node in nodes:
            # Get output properties (what this node can connect to)
            output_props = node.getProperties(SDPropertyCategory.Output)
            
            for output_prop in output_props:
                # Check if this output is connected to anything
                connections = output_prop.getConnections()
                connection_count += len(connections)
                
                if connections:
                    print(f"   🔗 {node.getIdentifier()}.{output_prop.getId()} → connected to {len(connections)} input(s)")
        
        print(f"📊 Total connections found: {connection_count}")
        
        print("\n🎉 Node tutorial completed!")
        print("💡 Next: Try tutorial 03_parameters.py")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Make sure you have a Substance material open!")

if __name__ == "__main__":
    main()
