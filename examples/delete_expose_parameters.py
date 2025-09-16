"""
Delete Expose Parameters - Practical Script
==========================================

This script provides a safe and user-friendly way to delete exposed parameters
from your Substance Designer materials.

Features:
- List all exposed parameters before deletion
- Option to delete specific parameters or all parameters
- Backup functionality (saves parameter info before deletion)
- Undo-friendly operations
- Safety confirmations

How to use:
1. Open your .sbs file in Substance Designer
2. Run this script in the Script Editor
3. Follow the prompts to safely delete parameters
"""

import sd
from sd.api.sdproperty import *
import json
from datetime import datetime

class ParameterManager:
    """
    A helper class to manage exposed parameters safely
    """
    
    def __init__(self):
        self.context = sd.getContext()
        self.app = self.context.getSDApplication()
        self.package_mgr = self.app.getPackageMgr()
    
    def get_current_graph(self):
        """Get the currently active graph"""
        packages = self.package_mgr.getUserPackages()
        if not packages:
            raise Exception("No packages loaded. Please open a .sbs file first!")
        
        current_package = packages[0]
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if not graphs:
            raise Exception("No graphs found in the current package!")
        
        return graphs[0]  # Return the first graph (usually the main material)
    
    def list_exposed_parameters(self, graph):
        """List all exposed parameters in the graph"""
        exposed_params = graph.getExposedParameters()
        
        if not exposed_params:
            print("📝 No exposed parameters found in this graph.")
            return []
        
        print(f"📋 Found {len(exposed_params)} exposed parameter(s):")
        print("-" * 60)
        
        param_info = []
        for i, param in enumerate(exposed_params):
            param_id = param.getId()
            param_label = param.getLabel()
            param_group = param.getGroup()
            
            # Get connected properties info
            connected_props = param.getConnectedProperties()
            connected_info = []
            for prop in connected_props:
                node_id = prop.getNode().getIdentifier()
                prop_id = prop.getId()
                connected_info.append(f"{node_id}.{prop_id}")
            
            info = {
                'index': i + 1,
                'id': param_id,
                'label': param_label,
                'group': param_group,
                'connected_to': connected_info
            }
            param_info.append(info)
            
            print(f"{i+1:2d}. ID: {param_id}")
            print(f"    Label: '{param_label}'")
            print(f"    Group: {param_group}")
            print(f"    Connected to: {', '.join(connected_info) if connected_info else 'None'}")
            print()
        
        return param_info
    
    def backup_parameters(self, param_info, graph_name):
        """Save parameter information to a JSON file for backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exposed_params_backup_{graph_name}_{timestamp}.json"
        
        backup_data = {
            'graph_name': graph_name,
            'backup_time': timestamp,
            'parameters': param_info
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(backup_data, f, indent=2)
            print(f"💾 Backup saved to: {filename}")
            return filename
        except Exception as e:
            print(f"⚠️  Warning: Could not save backup file: {e}")
            return None
    
    def delete_parameter_by_index(self, graph, param_index):
        """Delete a specific parameter by its index"""
        exposed_params = graph.getExposedParameters()
        
        if param_index < 1 or param_index > len(exposed_params):
            print(f"❌ Invalid parameter index. Please choose between 1 and {len(exposed_params)}")
            return False
        
        param_to_delete = exposed_params[param_index - 1]
        param_label = param_to_delete.getLabel()
        
        try:
            graph.deleteExposedParameter(param_to_delete)
            print(f"✅ Deleted parameter: '{param_label}'")
            return True
        except Exception as e:
            print(f"❌ Error deleting parameter '{param_label}': {e}")
            return False
    
    def delete_all_parameters(self, graph):
        """Delete all exposed parameters from the graph"""
        exposed_params = graph.getExposedParameters()
        
        if not exposed_params:
            print("📝 No parameters to delete.")
            return 0
        
        deleted_count = 0
        failed_count = 0
        
        # Create a copy of the list since we'll be modifying it
        params_to_delete = list(exposed_params)
        
        for param in params_to_delete:
            param_label = param.getLabel()
            try:
                graph.deleteExposedParameter(param)
                print(f"✅ Deleted: '{param_label}'")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete '{param_label}': {e}")
                failed_count += 1
        
        print(f"\n📊 Summary: {deleted_count} deleted, {failed_count} failed")
        return deleted_count

def main():
    """
    Main function - provides interactive menu for parameter deletion
    """
    print("🗑️  Delete Exposed Parameters Tool")
    print("=" * 40)
    
    try:
        manager = ParameterManager()
        graph = manager.get_current_graph()
        graph_name = graph.getIdentifier()
        
        print(f"📊 Working with graph: {graph_name}")
        print()
        
        # List current parameters
        param_info = manager.list_exposed_parameters(graph)
        
        if not param_info:
            print("🎉 No parameters to delete. You're all set!")
            return
        
        # Interactive menu
        while True:
            print("\n🔧 What would you like to do?")
            print("1. Delete a specific parameter")
            print("2. Delete ALL parameters (with backup)")
            print("3. Just create backup and exit")
            print("4. Exit without changes")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                try:
                    param_num = int(input(f"Enter parameter number (1-{len(param_info)}): "))
                    manager.delete_parameter_by_index(graph, param_num)
                    # Refresh the parameter list
                    param_info = manager.list_exposed_parameters(graph)
                    if not param_info:
                        print("🎉 All parameters deleted!")
                        break
                except ValueError:
                    print("❌ Please enter a valid number")
                
            elif choice == '2':
                print("\n⚠️  WARNING: This will delete ALL exposed parameters!")
                confirm = input("Type 'DELETE ALL' to confirm: ").strip()
                
                if confirm == 'DELETE ALL':
                    # Create backup first
                    backup_file = manager.backup_parameters(param_info, graph_name)
                    if backup_file:
                        print("📁 Backup created, proceeding with deletion...")
                    
                    deleted_count = manager.delete_all_parameters(graph)
                    if deleted_count > 0:
                        print(f"🎉 Successfully deleted all {deleted_count} parameters!")
                    break
                else:
                    print("❌ Deletion cancelled.")
                
            elif choice == '3':
                backup_file = manager.backup_parameters(param_info, graph_name)
                if backup_file:
                    print("🎉 Backup created successfully!")
                break
                
            elif choice == '4':
                print("👋 Exiting without changes.")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\n💡 Troubleshooting tips:")
        print("   - Make sure Substance Designer is running")
        print("   - Open a .sbs file before running this script")
        print("   - Check that the file is not read-only")

if __name__ == "__main__":
    main()
