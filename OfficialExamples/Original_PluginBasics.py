# Plugin entry point. Called by Designer when loading a plugin.
def initializeSDPlugin():
    print("Hello!")

# If this function is present in your plugin,
# it will be called by Designer when unloading the plugin.
def uninitializeSDPlugin():
    print("Bye!")