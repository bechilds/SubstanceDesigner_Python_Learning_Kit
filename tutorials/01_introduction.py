"""
Substance Designer Python API - Introduction Tutorial
====================================================

This is your first step into Substance Designer Python scripting!

What you'll learn:
- How to connect to Substance Designer
- Basic API structure and concepts
- How to access the current document
- Simple operations with packages and graphs

Requirements:
- Substance Designer must be running
- Run this script in SD's Script Editor (Tools > Scripting > Script Editor)
"""

# Import the necessary Substance Designer modules
import sd
from sd.api.sdproperty import *
from sd.api.sdvaluearray import *
from sd.api.sdvaluecolorrgba import *
from sd.api.sdvaluefloat import *
from sd.api.sdvalueint import *

def main():
    """
    Main function that demonstrates basic SD Python API usage
    """
    print("🎯 Starting Substance Designer Python Tutorial!")
    print("=" * 50)
    
    try:
        # Step 1: Get the current Substance Designer context
        print("📋 Step 1: Connecting to Substance Designer...")
        context = sd.getContext()
        app = context.getSDApplication()
        print("✅ Successfully connected to Substance Designer!")
        
        # Step 2: Get the package manager (handles .sbs files)
        print("\n📦 Step 2: Accessing Package Manager...")
        package_mgr = app.getPackageMgr()
        print("✅ Package Manager ready!")
        
        # Step 3: Get currently loaded packages
        print("\n📚 Step 3: Listing loaded packages...")
        packages = package_mgr.getUserPackages()
        
        if not packages:
            print("⚠️  No packages currently loaded.")
            print("💡 Tip: Open a .sbs file in Substance Designer first!")
            return
        
        print(f"📄 Found {len(packages)} package(s):")
        for i, package in enumerate(packages):
            print(f"   {i+1}. {package.getFilePath()}")
        
        # Step 4: Work with the first package
        if packages:
            print(f"\n🔍 Step 4: Examining first package...")
            current_package = packages[0]
            print(f"📁 Package path: {current_package.getFilePath()}")
            
            # Get all graphs in the package
            graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
            print(f"📊 Found {len(graphs)} graph(s) in package:")
            
            for i, graph in enumerate(graphs):
                print(f"   {i+1}. {graph.getIdentifier()} ({graph.getDefinition().getLabel()})")
        
        print("\n🎉 Tutorial completed successfully!")
        print("💡 Next: Try tutorial 02_working_with_nodes.py")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        print("💡 Make sure Substance Designer is running and you have a package loaded!")

if __name__ == "__main__":
    main()
