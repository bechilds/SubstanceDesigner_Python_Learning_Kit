"""
Substance Designer Helper Functions
==================================

This module contains commonly used helper functions for Substance Designer Python scripting.
Import this module in your scripts to access these utilities.

Usage:
    from utilities.sd_helpers import *
    
    # Connect to SD
    context, app, package_mgr = connect_to_substance()
    
    # Get current graph
    graph = get_active_graph(package_mgr)
"""

import sd
from sd.api.sdproperty import *

def connect_to_substance():
    """
    Connect to Substance Designer and return basic objects
    
    Returns:
        tuple: (context, app, package_mgr) or (None, None, None) if failed
    """
    try:
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        return context, app, package_mgr
    except Exception as e:
        print(f"❌ Failed to connect to Substance Designer: {e}")
        return None, None, None

def get_active_graph(package_mgr):
    """
    Get the currently active graph
    
    Args:
        package_mgr: Package manager from connect_to_substance()
        
    Returns:
        SDGraph: The active graph or None if not found
    """
    try:
        packages = package_mgr.getUserPackages()
        if not packages:
            print("❌ No packages loaded")
            return None
        
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if not graphs:
            print("❌ No graphs found in package")
            return None
        
        return graphs[0]  # Return first graph
        
    except Exception as e:
        print(f"❌ Error getting active graph: {e}")
        return None

def safe_execute(func, *args, **kwargs):
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        tuple: (success: bool, result: any)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        print(f"❌ Error executing {func.__name__}: {e}")
        return False, None

def get_nodes_by_type(graph, node_type_filter=None):
    """
    Get nodes from a graph, optionally filtered by type
    
    Args:
        graph: SDGraph object
        node_type_filter: String to filter node types (case-insensitive)
        
    Returns:
        list: List of matching nodes
    """
    try:
        all_nodes = graph.getNodes()
        
        if not node_type_filter:
            return all_nodes
        
        filtered_nodes = []
        filter_lower = node_type_filter.lower()
        
        for node in all_nodes:
            node_type = node.getDefinition().getId().lower()
            if filter_lower in node_type:
                filtered_nodes.append(node)
        
        return filtered_nodes
        
    except Exception as e:
        print(f"❌ Error filtering nodes: {e}")
        return []

def get_node_info(node):
    """
    Get detailed information about a node
    
    Args:
        node: SDNode object
        
    Returns:
        dict: Node information
    """
    try:
        node_def = node.getDefinition()
        
        info = {
            'identifier': node.getIdentifier(),
            'type': node_def.getId(),
            'label': node_def.getLabel(),
            'position': node.getPosition(),
            'input_count': len(node.getProperties(SDPropertyCategory.Input)),
            'output_count': len(node.getProperties(SDPropertyCategory.Output))
        }
        
        return info
        
    except Exception as e:
        print(f"❌ Error getting node info: {e}")
        return {}

def list_exposed_parameters_simple(graph):
    """
    Get a simple list of exposed parameters
    
    Args:
        graph: SDGraph object
        
    Returns:
        list: List of parameter info dictionaries
    """
    try:
        exposed_params = graph.getExposedParameters()
        param_list = []
        
        for param in exposed_params:
            param_info = {
                'id': param.getId(),
                'label': param.getLabel(),
                'group': param.getGroup(),
                'parameter_obj': param
            }
            param_list.append(param_info)
        
        return param_list
        
    except Exception as e:
        print(f"❌ Error listing parameters: {e}")
        return []

def delete_parameter_safe(graph, parameter):
    """
    Safely delete an exposed parameter with error handling
    
    Args:
        graph: SDGraph object
        parameter: SDProperty parameter to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        graph.deleteExposedParameter(parameter)
        return True
    except Exception as e:
        print(f"❌ Error deleting parameter: {e}")
        return False

def create_simple_node(graph, node_type, position=(0, 0)):
    """
    Create a new node in the graph
    
    Args:
        graph: SDGraph object
        node_type: String node type (e.g., 'sbs::compositing::uniform')
        position: Tuple (x, y) for node position
        
    Returns:
        SDNode: Created node or None if failed
    """
    try:
        new_node = graph.newNode(node_type)
        if new_node:
            # Set position if provided
            if position != (0, 0):
                pos = sd.api.sdbasetypes.float2(position[0], position[1])
                new_node.setPosition(pos)
        return new_node
    except Exception as e:
        print(f"❌ Error creating node: {e}")
        return None

def print_graph_summary(graph):
    """
    Print a nice summary of the graph contents
    
    Args:
        graph: SDGraph object
    """
    try:
        nodes = graph.getNodes()
        exposed_params = graph.getExposedParameters()
        
        print(f"📊 Graph: {graph.getIdentifier()}")
        print(f"   🔧 Nodes: {len(nodes)}")
        print(f"   ⚙️  Exposed Parameters: {len(exposed_params)}")
        
        # Count node types
        node_types = {}
        for node in nodes:
            node_type = node.getDefinition().getId()
            simple_type = node_type.split('::')[-1] if '::' in node_type else node_type
            node_types[simple_type] = node_types.get(simple_type, 0) + 1
        
        if node_types:
            print("   📈 Node Types:")
            for node_type, count in sorted(node_types.items()):
                print(f"      {node_type}: {count}")
        
    except Exception as e:
        print(f"❌ Error printing graph summary: {e}")

# Convenience function for quick setup
def quick_setup():
    """
    Quick setup function that connects to SD and gets the active graph
    
    Returns:
        tuple: (graph, context, app) or (None, None, None) if failed
    """
    context, app, package_mgr = connect_to_substance()
    
    if not context:
        return None, None, None
    
    graph = get_active_graph(package_mgr)
    
    if not graph:
        return None, None, None
    
    return graph, context, app

# Example usage function
def example_usage():
    """
    Example of how to use these helper functions
    """
    print("🔧 SD Helpers Example Usage")
    print("=" * 30)
    
    # Quick setup
    graph, context, app = quick_setup()
    
    if not graph:
        print("❌ Could not set up Substance Designer connection")
        return
    
    # Print graph summary
    print_graph_summary(graph)
    
    # List exposed parameters
    params = list_exposed_parameters_simple(graph)
    if params:
        print(f"\n📋 Exposed Parameters:")
        for param in params:
            print(f"   {param['label']} ({param['id']})")
    
    print("\n✅ Example completed!")

if __name__ == "__main__":
    example_usage()
