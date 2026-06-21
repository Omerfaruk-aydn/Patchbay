# Patchbay CLI

Professional command-line interface for the Patchbay Universal LLM Gateway.

## Installation

```bash
pip install -e cli/
```

## Commands

### System
- `patchbay status` — Show gateway status, services, and connection health
- `patchbay health` — Quick health check of all services
- `patchbay open` — Open the web dashboard in browser

### Models
- `patchbay models list` — List all registered LLM models
- `patchbay models info <model>` — Show detailed model info

### API Keys
- `patchbay keys list` — List configured API keys
- `patchbay keys add` — Add a new provider API key (interactive)
- `patchbay keys delete <name>` — Delete an API key

### MCP Servers
- `patchbay mcp list` — List connected MCP servers
- `patchbay mcp tools` — List available MCP tools
- `patchbay mcp add` — Register a new MCP server

### Blender Integration
- `patchbay blender info` — Show Blender scene info
- `patchbay blender objects` — List all objects in scene (tree view)
- `patchbay blender create <primitive>` — Create cube, sphere, cylinder, etc.
- `patchbay blender material <object> --color <color>` — Apply material
- `patchbay blender delete <object>` — Delete an object
- `patchbay blender exec "<code>"` — Execute Python code in Blender
- `patchbay blender screenshot` — Capture viewport screenshot

### Chat
- `patchbay chat` — Interactive chat session with any LLM model
- `patchbay chat -m gpt-4o` — Chat with specific model

### Routing
- `patchbay routing list` — List routing strategies

### Configuration
- `patchbay config show` — Show current configuration
- `patchbay config set <key> <value>` — Set a config value
- `patchbay config init` — Interactive configuration setup

## Quick Start

```bash
# Check system status
patchbay status

# Create a sphere in Blender
patchbay blender create sphere --name MySphere --location 0,0,2

# Apply a red material
patchbay blender material MySphere --color red

# List all objects
patchbay blender objects

# Start interactive chat
patchbay chat -m gpt-4o
```
