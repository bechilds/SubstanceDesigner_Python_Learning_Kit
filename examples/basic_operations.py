"""
Basic Substance Designer Operations
==================================

This file contains simple examples of common Substance Designer operations.
Perfect for beginners to understand the basic concepts.

Examples included:
- Connecting to Substance Designer
- Working with packages and graphs
- Basic node operations
- Property manipulation
"""

import sd
from sd.api.sdproperty import *

def get_substance_info():
    """
    Get basic information about the current Substance Designer session
    """
    print("🔍 Getting Substance Designer Information...")
    
    try:
        context = sd.getContext()
        app = context.getSDApplication()
        
        print(f"✅ Successfully connected to Substance Designer")
        print(f"📋 Application context ready")
        
        # Get package information
        package_mgr = app.getPackageMgr()
        packages = package_mgr.getUserPackages()
        
        print(f"📦 Loaded packages: {len(packages)}")
        
        for i, package in enumerate(packages):
            print(f"   {i+1}. {package.getFilePath()}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def list_graph_contents():
    """
    List all graphs and their contents in the current package
    """
    print("\n📊 Analyzing Graph Contents...")
    
    try:
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        packages = package_mgr.getUserPackages()
        
        if not packages:
            print("❌ No packages loaded")
            return
        
        for package in packages:
            print(f"\n📁 Package: {package.getFilePath()}")
            
            graphs = package.getChildrenOfType(sd.api.sdgraph.SDGraph)
            print(f"   📊 Graphs: {len(graphs)}")
            
            for graph in graphs:
                print(f"      📈 {graph.getIdentifier()}")
                
                nodes = graph.getNodes()
                print(f"         🔧 Nodes: {len(nodes)}")
                
                exposed_params = graph.getExposedParameters()
                print(f"         ⚙️  Exposed Parameters: {len(exposed_params)}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def count_node_types():
    """
    Count different types of nodes in the current graph
    """
    print("\n🔢 Counting Node Types...")
    
    try:
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        packages = package_mgr.getUserPackages()
        
        if not packages:
            print("❌ No packages loaded")
            return
        
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if not graphs:
            print("❌ No graphs found")
            return
        
        current_graph = graphs[0]
        nodes = current_graph.getNodes()
        
        # Count different node types
        node_types = {}
        
        for node in nodes:
            node_def = node.getDefinition()
            node_type = node_def.getId()
            
            if node_type in node_types:
                node_types[node_type] += 1
            else:
                node_types[node_type] = 1
        
        print(f"📊 Node type distribution in '{current_graph.getIdentifier()}':")
        
        # Sort by count (most common first)
        sorted_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)
        
        for node_type, count in sorted_types:
            # Simplify the node type name for readability
            simple_name = node_type.split('::')[-1] if '::' in node_type else node_type
            print(f"   {simple_name}: {count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def show_node_connections():
    """
    Show how nodes are connected in the current graph
    """
    print("\n🔗 Analyzing Node Connections...")
    
    try:
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        packages = package_mgr.getUserPackages()
        
        if not packages:
            print("❌ No packages loaded")
            return
        
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if not graphs:
            print("❌ No graphs found")
            return
        
        current_graph = graphs[0]
        nodes = current_graph.getNodes()
        
        total_connections = 0
        connected_nodes = 0
        
        for node in nodes:
            node_connections = 0
            
            # Check output connections
            output_props = node.getProperties(SDPropertyCategory.Output)
            for output_prop in output_props:
                connections = output_prop.getConnections()
                node_connections += len(connections)
                total_connections += len(connections)
            
            if node_connections > 0:
                connected_nodes += 1
                print(f"   🔧 {node.getIdentifier()}: {node_connections} output connection(s)")
        
        print(f"\n📊 Connection Summary:")
        print(f"   📈 Total nodes: {len(nodes)}")
        print(f"   🔗 Nodes with outputs: {connected_nodes}")
        print(f"   📊 Total connections: {total_connections}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """
    Run all basic operations examples
    """
    print("🚀 Basic Substance Designer Operations")
    print("=" * 45)
    
    # Run all example functions
    success = get_substance_info()
    
    if success:
        list_graph_contents()
        count_node_types()
        show_node_connections()
        
        print("\n🎉 Basic operations completed successfully!")
        print("💡 Try running other example scripts to learn more!")
    else:
        print("\n❌ Could not connect to Substance Designer")
        print("💡 Make sure Substance Designer is running and has a material loaded")

if __name__ == "__main__":
    main()
