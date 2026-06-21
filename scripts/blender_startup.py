import bpy
import sys
import time

# Enable addon
bpy.ops.preferences.addon_enable(module='blender_mcp')
print("BlenderMCP addon enabled")

# Start server
bpy.ops.blendermcp.start_server()
print("BlenderMCP server started on port 9876")

# Keep alive with a persistent timer
def keep_alive():
    return 1.0

bpy.app.timers.register(keep_alive, first_interval=1.0)
print("Timer registered, server is running...")
