import bpy
import time
import sys

# Enable addon
bpy.ops.preferences.addon_enable(module='blender_mcp')
print("BlenderMCP addon enabled")

# Start the MCP server
bpy.ops.blendermcp.start_server()
print("BlenderMCP server started on localhost:9876")
print("BlenderMCP is ready!")
print("Press Ctrl+C to stop")

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    bpy.ops.blendermcp.stop_server()
    print("Server stopped")
