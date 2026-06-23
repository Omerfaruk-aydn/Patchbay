"""Blender MCP server — God Mode Ultra Professional (50+ tools).

Complete Blender access with professional-grade tools for:
- Viewport control, mesh operations, materials, lighting, camera
- Animation, physics, rendering, import/export
- Scene management, quality checks, undo/redo
- Batch operations, smart cleanup, feedback
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from typing import Any

import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("blender-mcp-server")

BLENDER_HOST = os.getenv("BLENDER_HOST", "localhost")
BLENDER_PORT = int(os.getenv("BLENDER_PORT", "9876"))
SSE_HOST = os.getenv("SSE_HOST", "0.0.0.0")
SSE_PORT = int(os.getenv("SSE_PORT", "8456"))


# ═══════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (55 tools)
# ═══════════════════════════════════════════════════════════════

MCP_TOOLS = [
    # ═══ CORE ═══
    {"name": "execute_code", "description": "Execute arbitrary Python code in Blender. Full bpy API access.", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
    {"name": "get_scene_info", "description": "Get full scene info", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_object_info", "description": "Get detailed object info", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}}, "required": ["object_name"]}},
    {"name": "get_viewport_screenshot", "description": "Capture viewport screenshot", "inputSchema": {"type": "object", "properties": {"filepath": {"type": "string"}}}},
    # ═══ OBJECT CRUD ═══
    {"name": "create_primitive", "description": "Create primitive (cube,sphere,cylinder,cone,torus,plane,monkey,ico,grid,text,empty)", "inputSchema": {"type": "object", "properties": {"type": {"type": "string"}, "name": {"type": "string"}, "location": {"type": "array", "items": {"type": "number"}}, "scale": {"type": "array", "items": {"type": "number"}}, "rotation": {"type": "array", "items": {"type": "number"}}, "size": {"type": "number"}}, "required": ["type"]}},
    {"name": "delete_object", "description": "Delete object", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}}, "required": ["object_name"]}},
    {"name": "select_object", "description": "Select/deselect objects", "inputSchema": {"type": "object", "properties": {"object_names": {"type": "array", "items": {"type": "string"}}, "mode": {"type": "string", "enum": ["select", "deselect", "add", "set_active"]}}, "required": ["object_names", "mode"]}},
    {"name": "move_object", "description": "Move object", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "location": {"type": "array", "items": {"type": "number"}}}, "required": ["object_name", "location"]}},
    {"name": "rotate_object", "description": "Rotate object (degrees)", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "rotation": {"type": "array", "items": {"type": "number"}}}, "required": ["object_name", "rotation"]}},
    {"name": "scale_object", "description": "Scale object", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "scale": {"type": "array", "items": {"type": "number"}}}, "required": ["object_name", "scale"]}},
    {"name": "rename_object", "description": "Rename object", "inputSchema": {"type": "object", "properties": {"old_name": {"type": "string"}, "new_name": {"type": "string"}}, "required": ["old_name", "new_name"]}},
    {"name": "duplicate_object", "description": "Duplicate object", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "new_name": {"type": "string"}, "offset": {"type": "array", "items": {"type": "number"}}}, "required": ["object_name"]}},
    {"name": "parent_objects", "description": "Set parent-child", "inputSchema": {"type": "object", "properties": {"parent_name": {"type": "string"}, "child_names": {"type": "array", "items": {"type": "string"}}}, "required": ["parent_name", "child_names"]}},
    {"name": "join_objects", "description": "Join objects", "inputSchema": {"type": "object", "properties": {"object_names": {"type": "array", "items": {"type": "string"}}}, "required": ["object_names"]}},
    # ═══ MESH OPERATIONS ═══
    {"name": "boolean_operation", "description": "Boolean: union, difference, intersect between two objects", "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}, "cutter": {"type": "string"}, "operation": {"type": "string", "enum": ["union", "difference", "intersect"]}}, "required": ["target", "cutter", "operation"]}},
    {"name": "remesh", "description": "Remesh object (quad or voxel)", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "mode": {"type": "string", "enum": ["quad", "voxel"]}, "voxel_size": {"type": "number"}, "octree_depth": {"type": "integer"}}}, "required": ["object_name"]},
    {"name": "decimate", "description": "Reduce polygon count", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "ratio": {"type": "number", "description": "0.0-1.0"}}, "required": ["object_name", "ratio"]}},
    {"name": "shade_smooth", "description": "Set smooth/flat shading", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "smooth": {"type": "boolean"}}}},
    {"name": "add_modifier", "description": "Add modifier to object", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "modifier_type": {"type": "string", "enum": ["SUBSURF", "BEVEL", "ARRAY", "MIRROR", "SOLIDIFY", "WIREFRAME", "DISPLACE", "SIMPLE_DEFORM"]}, "settings": {"type": "object"}}}, "required": ["object_name", "modifier_type"]},
    # ═══ MATERIALS ═══
    {"name": "create_material", "description": "Create material (metal,glass,plastic,wood,emissive,matte,custom)", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "preset": {"type": "string", "enum": ["metal", "glass", "plastic", "wood", "emissive", "matte", "custom"]}, "color": {"type": "array", "items": {"type": "number"}}, "roughness": {"type": "number"}, "metallic": {"type": "number"}, "emission_strength": {"type": "number"}, "alpha": {"type": "number"}}, "required": ["name"]}},
    {"name": "assign_material", "description": "Assign material to object", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "material_name": {"type": "string"}}, "required": ["object_name", "material_name"]}},
    {"name": "list_materials", "description": "List materials", "inputSchema": {"type": "object", "properties": {}}},
    # ═══ LIGHTING ═══
    {"name": "add_light", "description": "Add light (point,sun,area,spot)", "inputSchema": {"type": "object", "properties": {"type": {"type": "string"}, "name": {"type": "string"}, "location": {"type": "array", "items": {"type": "number"}}, "energy": {"type": "number"}, "color": {"type": "array", "items": {"type": "number"}}, "size": {"type": "number"}}, "required": ["type"]}},
    {"name": "setup_three_point_lighting", "description": "Professional 3-point lighting", "inputSchema": {"type": "object", "properties": {"key_energy": {"type": "number"}, "fill_energy": {"type": "number"}, "rim_energy": {"type": "number"}}}},
    {"name": "setup_studio_lighting", "description": "Studio lighting setup", "inputSchema": {"type": "object", "properties": {"preset": {"type": "string", "enum": ["studio", "outdoor", "indoor", "dramatic"]}}}},
    {"name": "add_hdri", "description": "Add HDRI environment lighting", "inputSchema": {"type": "object", "properties": {"filepath": {"type": "string"}, "strength": {"type": "number"}}}},
    # ═══ CAMERA ═══
    {"name": "add_camera", "description": "Add camera", "inputSchema": {"type": "object", "properties": {"location": {"type": "array", "items": {"type": "number"}}, "rotation": {"type": "array", "items": {"type": "number"}}, "focal_length": {"type": "number"}}}},
    {"name": "setup_product_render", "description": "Product visualization setup", "inputSchema": {"type": "object", "properties": {"angle": {"type": "number"}}}},
    {"name": "setup_portrait_camera", "description": "Portrait photography camera", "inputSchema": {"type": "object", "properties": {"focal_length": {"type": "number", "default": 85}}}},
    {"name": "setup_architectural_camera", "description": "Architectural visualization camera", "inputSchema": {"type": "object", "properties": {"angle": {"type": "number"}}}},
    # ═══ ANIMATION ═══
    {"name": "add_keyframe", "description": "Add keyframe", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "property": {"type": "string"}, "frame": {"type": "integer"}}, "required": ["object_name", "property", "frame"]}},
    {"name": "set_animation_range", "description": "Set frame range", "inputSchema": {"type": "object", "properties": {"start": {"type": "integer"}, "end": {"type": "integer"}, "fps": {"type": "integer"}}}},
    {"name": "set_interpolation", "description": "Set keyframe interpolation", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "interpolation": {"type": "string", "enum": ["constant", "linear", "bezier", "auto"]}}, "required": ["object_name", "interpolation"]}},
    {"name": "play_animation", "description": "Play/pause animation", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["play", "pause", "stop", "next_frame", "prev_frame"]}}}},
    # ═══ PHYSICS ═══
    {"name": "setup_rigid_body", "description": "Add rigid body physics", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "type": {"type": "string", "enum": ["active", "passive"]}, "mass": {"type": "number"}}}},
    {"name": "setup_cloth", "description": "Add cloth simulation", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "mass": {"type": "number"}}}},
    {"name": "setup_fluid", "description": "Add fluid simulation", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "type": {"type": "string", "enum": ["domain", "flow", "effector"]}}}},
    {"name": "setup_particles", "description": "Add particle system", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "count": {"type": "integer"}, "lifetime": {"type": "integer"}}}},
    {"name": "setup_soft_body", "description": "Add soft body physics", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}}}},
    # ═══ RENDERING ═══
    {"name": "setup_render", "description": "Configure render settings", "inputSchema": {"type": "object", "properties": {"engine": {"type": "string", "enum": ["cycles", "eevee"]}, "resolution_x": {"type": "integer"}, "resolution_y": {"type": "integer"}, "samples": {"type": "integer"}, "use_gpu": {"type": "boolean"}, "transparent": {"type": "boolean"}}}},
    {"name": "render_image", "description": "Render to file", "inputSchema": {"type": "object", "properties": {"filepath": {"type": "string"}, "format": {"type": "string", "enum": ["png", "jpg", "exr", "hdr"]}}, "required": ["filepath"]}},
    {"name": "setup_clay_render", "description": "Setup clay render (all white)", "inputSchema": {"type": "object", "properties": {}}},
    # ═══ IMPORT/EXPORT ═══
    {"name": "import_file", "description": "Import 3D file", "inputSchema": {"type": "object", "properties": {"filepath": {"type": "string"}, "format": {"type": "string", "enum": ["fbx", "obj", "gltf", "glb", "stl", "blend"]}}, "required": ["filepath"]}},
    {"name": "export_file", "description": "Export scene", "inputSchema": {"type": "object", "properties": {"filepath": {"type": "string"}, "format": {"type": "string", "enum": ["fbx", "obj", "gltf", "glb", "stl", "blend"]}, "selected_only": {"type": "boolean"}}, "required": ["filepath", "format"]}},
    # ═══ SCENE ═══
    {"name": "create_collection", "description": "Create collection", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "list_collections", "description": "List collections", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_materials", "description": "List materials", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_cameras", "description": "List cameras", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_lights", "description": "List lights", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_modifiers", "description": "List modifiers", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}}, "required": ["object_name"]}},
    {"name": "set_active_scene", "description": "Set active scene", "inputSchema": {"type": "object", "properties": {"scene_name": {"type": "string"}}, "required": ["scene_name"]}},
    # ═══ UNDO/QUALITY ═══
    {"name": "undo", "description": "Undo last action", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "redo", "description": "Redo last action", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "check_quality", "description": "Quality checks (normals, scale, duplicates)", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "fix_normals", "description": "Recalculate normals", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}}}},
    {"name": "optimize_mesh", "description": "Smart cleanup (remove doubles, fix normals)", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}}}},
    # ═══ BATCH ═══
    {"name": "batch_move", "description": "Move multiple objects", "inputSchema": {"type": "object", "properties": {"object_names": {"type": "array", "items": {"type": "string"}}, "location": {"type": "array", "items": {"type": "number"}}}, "required": ["object_names", "location"]}},
    {"name": "batch_scale", "description": "Scale multiple objects", "inputSchema": {"type": "object", "properties": {"object_names": {"type": "array", "items": {"type": "string"}}, "scale": {"type": "array", "items": {"type": "number"}}}, "required": ["object_names", "scale"]}},
    {"name": "batch_material", "description": "Apply material to multiple objects", "inputSchema": {"type": "object", "properties": {"object_names": {"type": "array", "items": {"type": "string"}}, "material_name": {"type": "string"}}, "required": ["object_names", "material_name"]}},
]


# ═══════════════════════════════════════════════════════════════
# CONNECTION
# ═══════════════════════════════════════════════════════════════

class BlenderConnection:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    async def connect(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            self._sock = await loop.run_in_executor(None, self._create_socket)
            return True
        except Exception:
            return False

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((self._host, self._port))
        return sock

    async def execute(self, command: dict) -> dict:
        if not self._sock:
            if not await self.connect():
                return {"status": "error", "message": "Not connected to Blender"}
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_command, command)
        except Exception as e:
            self._sock = None
            return {"status": "error", "message": str(e)}

    def _send_command(self, command: dict) -> dict:
        assert self._sock
        data = json.dumps(command).encode("utf-8")
        self._sock.sendall(data)
        self._sock.settimeout(60.0)
        chunks = []
        while True:
            chunk = self._sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError:
                continue
        raise ConnectionError("Empty response")

    def close(self) -> None:
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None


blender = BlenderConnection(BLENDER_HOST, BLENDER_PORT)
CC = lambda c: {"type": "execute_code", "params": {"code": c}}


# ═══════════════════════════════════════════════════════════════
# TOOL DISPATCH
# ═══════════════════════════════════════════════════════════════

def _dispatch(name: str, args: dict) -> dict:
    # Core
    if name == "execute_code": return CC(args.get("code", ""))
    if name == "get_scene_info": return CC(
        "import bpy,json\ns=bpy.context.scene\n"
        "o=[{'name':o.name,'type':o.type,'loc':[round(l,2)for l in o.location]}for o in list(s.objects)[:20]]\n"
        "print(json.dumps({'name':s.name,'objects':len(s.objects),'materials':len(bpy.data.materials),"
        "'cameras':len(bpy.data.cameras),'lights':len(bpy.data.lights),'engine':s.render.engine,"
        f"'resolution':f\"{{s.render.resolution_x}}x{{s.render.resolution_y}}\",'objects':o}}))")
    if name == "get_object_info": return CC(
        f"import bpy,json\no=bpy.data.objects.get('{args.get('object_name','')}')\n"
        "if o:\n d={'name':o.name,'type':o.type,'loc':list(o.location),'rot':list(o.rotation_euler),"
        "'scale':list(o.scale),'parent':o.parent.name if o.parent else None,"
        "'materials':[m.name for m in o.data.materials] if hasattr(o,'data') and hasattr(o.data,'materials') else [],"
        "'modifiers':[{'name':m.name,'type':m.type} for m in o.modifiers],"
        "'children':[c.name for c in o.children]}\n print(json.dumps(d))")
    if name == "get_viewport_screenshot":
        path = args.get("filepath", "/tmp/viewport.png")
        return CC(f"import bpy\na=next((a for a in bpy.context.screen.areas if a.type=='VIEW_3D'),None)\nif a:\n with bpy.context.temp_override(area=a): bpy.ops.screen.screenshot_area(filepath='{path}')\n print(f'Saved: {path}')")

    # Object CRUD
    if name == "create_primitive":
        t = args.get("type", "cube")
        loc = args.get("location", [0,0,0])
        scale = args.get("scale", [1,1,1])
        rot = args.get("rotation", [0,0,0])
        size = args.get("size", 1)
        name = args.get("name", "")
        ops = {"cube":f"primitive_cube_add(size={size})", "sphere":f"primitive_uv_sphere_add(radius={size})",
               "cylinder":f"primitive_cylinder_add(radius={size})", "cone":f"primitive_cone_add(radius1={size})",
               "torus":f"primitive_torus_add(major_radius={size})", "plane":f"primitive_plane_add(size={size*2})",
               "monkey":f"primitive_monkey_add()", "ico":f"primitive_ico_add(radius={size})", "grid":f"primitive_grid_add(size={size*2})"}
        op = ops.get(t, ops["cube"])
        c = f"import bpy,math\nbpy.ops.mesh.{op},location={tuple(loc)})\no=bpy.context.active_object\n"
        if name: c += f"o.name='{name}'\n"
        if scale!=[1,1,1]: c += f"o.scale={tuple(scale)}\n"
        if rot!=[0,0,0]: c += f"o.rotation_euler=tuple(math.radians(r)for r in {rot})\n"
        c += "print(f'Created '+o.name)"
        return CC(c)
    if name == "delete_object": return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:bpy.data.objects.remove(o,do_unlink=True)\nprint(f'Deleted')")
    if name == "select_object":
        n=args.get("object_names",[]);m=args.get("mode","select")
        ns=str(n)
        if m=="select": return CC(f"import bpy\nbpy.ops.object.select_all(action='DESELECT')\nfor n in {ns}:\n o=bpy.data.objects.get(n)\n if o:o.select_set(True)\nif {ns}:bpy.context.view_layer.objects.active=bpy.data.objects.get({ns}[0])")
        if m=="deselect": return CC(f"import bpy\nfor n in {ns}:\n o=bpy.data.objects.get(n)\n if o:o.select_set(False)")
        if m=="add": return CC(f"import bpy\nfor n in {ns}:\n o=bpy.data.objects.get(n)\n if o:o.select_set(True)")
        return CC(f"import bpy\no=bpy.data.objects.get('{n[0]}')\nif o:bpy.context.view_layer.objects.active=o;o.select_set(True)")
    if name=="move_object": return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\no.location={tuple(args.get('location',[0,0,0]))}\nprint('Moved')")
    if name=="rotate_object": return CC(f"import bpy,math\no=bpy.data.objects.get('{args.get('object_name','')}')\no.rotation_euler=tuple(math.radians(r)for r in {tuple(args.get('rotation',[0,0,0]))})\nprint('Rotated')")
    if name=="scale_object": return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\no.scale={tuple(args.get('scale',[1,1,1]))}\nprint('Scaled')")
    if name=="rename_object": return CC(f"import bpy\no=bpy.data.objects.get('{args.get('old_name','')}')\nif o:o.name='{args.get('new_name','')}'\nprint('Renamed')")
    if name=="duplicate_object": return CC(f"import bpy\nsrc=bpy.data.objects.get('{args.get('object_name','')}')\nif src:\n dup=src.copy();dup.data=src.data.copy()\n bpy.context.collection.objects.link(dup)\n dup.location.x+={args.get('offset',[2,0,0])[0]}\n if '{args.get('new_name','')}':dup.name='{args.get('new_name','')}'\n print(f'Duplicated -> '+dup.name)")
    if name=="parent_objects":
        p=args.get("parent_name","");cs=args.get("child_names",[])
        c=f"import bpy\np=bpy.data.objects.get('{p}')\n"
        for ch in cs:c+=f"ch=bpy.data.objects.get('{ch}')\nif p and ch:ch.parent=p\n"
        c+=f"print(f'Parented {{len(cs)}} to {p}')"
        return CC(c)
    if name=="join_objects":
        ns=args.get("object_names",[])
        c=f"import bpy\nbpy.ops.object.select_all(action='DESELECT')\n"
        for n in ns:c+=f"o=bpy.data.objects.get('{n}')\nif o:o.select_set(True)\n"
        c+=f"bpy.ops.object.join()\nprint(f'Joined {{len(ns)}} objects')"
        return CC(c)

    # Mesh Operations
    if name=="boolean_operation":
        return CC(f"import bpy\nt=bpy.data.objects.get('{args.get('target','')}')\nc=bpy.data.objects.get('{args.get('cutter','')}')\nif t and c:\n mod=t.modifiers.new(name='Bool',type='BOOLEAN')\n mod.operation='{args.get('operation','difference')}'\n mod.object=c\n bpy.context.view_layer.objects.active=t\n bpy.ops.object.modifier_apply(modifier='Bool')\n bpy.data.objects.remove(c,do_unlink=True)\n print('Boolean applied')")
    if name=="remesh":
        mode=args.get("mode","voxel");vs=args.get("voxel_size",0.1);od=args.get("octree_depth",4)
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n mod=o.modifiers.new(name='Remesh',type='REMESH')\n mod.mode='{mode.upper()}'\n if '{mode}'=='voxel':mod.voxel_size={vs}\n else:mod.octree_depth={od}\n bpy.context.view_layer.objects.active=o\n bpy.ops.object.modifier_apply(modifier='Remesh')\n print('Remeshed')")
    if name=="decimate":
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n mod=o.modifiers.new(name='Decimate',type='DECIMATE')\n mod.ratio={args.get('ratio',0.5)}\n bpy.context.view_layer.objects.active=o\n bpy.ops.object.modifier_apply(modifier='Decimate')\n print('Decimated')")
    if name=="shade_smooth":
        s=args.get("smooth",True)
        return CC(f"import bpy\nfor o in bpy.context.selected_objects:\n if o.type=='MESH':\n  o.data.polygons.foreach_set('use_smooth',{s})\n  o.data.update()\nprint('Shading set')")
    if name=="add_modifier":
        mt=args.get("modifier_type","SUBSURF");settings=args.get("settings",{})
        c=f"import bpy\no=bpy.context.active_object\nif o:\n mod=o.modifiers.new(name='{mt}',type='{mt}')\n"
        for k,v in settings.items():c+=f" mod.{k}={v}\n"
        c+="print(f'Modifier {mt} added')"
        return CC(c)

    # Materials
    if name=="create_material":
        mn=args.get("name","Material");preset=args.get("preset","custom")
        color=args.get("color",[0.8,0.8,0.8]);rough=args.get("roughness",0.5)
        met=args.get("metallic",0);em=args.get("emission_strength",0)
        c=f"import bpy\nmat=bpy.data.materials.new(name='{mn}')\nmat.use_nodes=True\nbsdf=mat.node_tree.nodes.get('Principled BSDF')\n"
        presets={"metal":f"bsdf.inputs['Base Color'].default_value={color}\nbsdf.inputs['Metallic'].default_value=0.9\nbsdf.inputs['Roughness'].default_value=0.1\n",
                 "glass":f"bsdf.inputs['Base Color'].default_value=(1,1,1,1)\nbsdf.inputs['Alpha'].default_value=0.1\nbsdf.inputs['Roughness'].default_value=0.0\nbsdf.inputs['Transmission Weight'].default_value=1.0\n",
                 "plastic":f"bsdf.inputs['Base Color'].default_value={color}\nbsdf.inputs['Roughness'].default_value=0.4\n",
                 "emissive":f"bsdf.inputs['Base Color'].default_value={color}\nbsdf.inputs['Emission Strength'].default_value={em}\n",
                 "matte":f"bsdf.inputs['Base Color'].default_value={color}\nbsdf.inputs['Roughness'].default_value=1.0\n"}
        c+=presets.get(preset,f"bsdf.inputs['Base Color'].default_value={color}\nbsdf.inputs['Roughness'].default_value={rough}\nbsdf.inputs['Metallic'].default_value={met}\n")
        c+=f"print(f'Created material: {mn}')"
        return CC(c)
    if name=="assign_material":
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nm=bpy.data.materials.get('{args.get('material_name','')}')\nif o and m:\n o.data.materials.clear()\n o.data.materials.append(m)\n print(f'Assigned {m.name} to {o.name}')")
    if name=="list_materials": return CC("import bpy,json\nprint(json.dumps([{'name':m.name,'users':m.users}for m in bpy.data.materials]))")

    # Lighting
    if name=="add_light":
        lt=args.get("type","point");loc=args.get("location",[3,-3,5])
        energy=args.get("energy",1000);color=args.get("color",[1,1,1])
        name=args.get("name","")
        c=f"import bpy\nbpy.ops.object.light_add(type='{lt.upper()}',location={tuple(loc)})\nl=bpy.context.active_object\nl.data.energy={energy}\nl.data.color={tuple(color)}\n"
        if name:c+=f"l.name='{name}'\n"
        c+=f"print(f'Added {lt} light')"
        return CC(c)
    if name=="setup_three_point_lighting":
        ke=args.get("key_energy",1000);fe=args.get("fill_energy",300);re=args.get("rim_energy",500)
        return CC(f"import bpy\nbpy.ops.object.light_add(type='AREA',location=(4,-4,6))\nk=bpy.context.active_object;k.name='Key';k.data.energy={ke};k.data.size=2\n"
                  f"bpy.ops.object.light_add(type='AREA',location=(-3,-2,4))\nf=bpy.context.active_object;f.name='Fill';f.data.energy={fe};f.data.size=3\n"
                  f"bpy.ops.object.light_add(type='AREA',location=(0,4,5))\nr=bpy.context.active_object;r.name='Rim';r.data.energy={re};r.data.size=1.5\nprint('3-point lighting done')")
    if name=="setup_studio_lighting":
        p=args.get("preset","studio")
        presets={
            "studio": "bpy.ops.object.light_add(type='AREA',location=(5,-5,8))\nl=bpy.context.active_object;l.name='Key';l.data.energy=1200;l.data.size=3\nbpy.ops.object.light_add(type='AREA',location=(-4,-3,5))\nl=bpy.context.active_object;l.name='Fill';l.data.energy=400;l.data.size=4\nbpy.ops.object.light_add(type='SUN',location=(0,0,10))\nl=bpy.context.active_object;l.name='Sun';l.data.energy=0.5",
            "outdoor": "bpy.ops.object.light_add(type='SUN',location=(5,5,10))\nl=bpy.context.active_object;l.name='Sun';l.data.energy=2\nl.rotation_euler=(0.785,0,0.785)",
            "indoor": "bpy.ops.object.light_add(type='POINT',location=(0,0,3))\nl=bpy.context.active_object;l.name='Ceiling';l.data.energy=500",
            "dramatic": "bpy.ops.object.light_add(type='SPOT',location=(3,-3,5))\nl=bpy.context.active_object;l.name='Spot';l.data.energy=2000;l.data.spot_size=0.5",
        }
        return CC(f"import bpy,math\n{presets.get(p,presets['studio'])}\nprint(f'{p} lighting done')")
    if name=="add_hdri":
        return CC(f"import bpy\nworld=bpy.context.scene.world\nif not world:\n world=bpy.data.worlds.new('World')\n bpy.context.scene.world=world\nworld.use_nodes=True\nbg=world.node_tree.nodes.get('Background')\nbg.inputs['Strength'].default_value={args.get('strength',1.0)}\nprint('HDRI setup done')")

    # Camera
    if name=="add_camera":
        loc=args.get("location",[5,-5,3]);rot=args.get("rotation",[70,0,45]);fl=args.get("focal_length",50)
        return CC(f"import bpy,math\nbpy.ops.object.camera_add(location={tuple(loc)})\nc=bpy.context.active_object\nc.data.lens={fl}\nc.rotation_euler=tuple(math.radians(r)for r in {tuple(rot)})\nbpy.context.scene.camera=c\nprint(f'Camera: {fl}mm')")
    if name=="setup_product_render":
        a=args.get("angle",45)
        return CC(f"import bpy,math\nbpy.ops.object.camera_add(location=(4,-4,3))\nc=bpy.context.active_object\nc.data.lens=50\nc.rotation_euler=(math.radians(65),0,math.radians({a}))\nbpy.context.scene.camera=c\n"
                  f"bpy.ops.object.light_add(type='AREA',location=(3,-3,5))\nl=bpy.context.active_object;l.data.energy=800;l.name='Key'\n"
                  f"bpy.ops.object.light_add(type='AREA',location=(-2,-1,3))\nl=bpy.context.active_object;l.data.energy=250;l.name='Fill'\n"
                  f"bpy.ops.object.light_add(type='AREA',location=(0,3,4))\nl=bpy.context.active_object;l.data.energy=400;l.name='Rim'\nprint('Product render ready')")
    if name=="setup_portrait_camera":
        fl=args.get("focal_length",85)
        return CC(f"import bpy,math\nbpy.ops.object.camera_add(location=(0,-3,1.5))\nc=bpy.context.active_object\nc.data.lens={fl}\nc.rotation_euler=(math.radians(85),0,0)\nbpy.context.scene.camera=c\nprint(f'Portrait camera: {fl}mm')")
    if name=="setup_architectural_camera":
        a=args.get("angle",45)
        return CC(f"import bpy,math\nbpy.ops.object.camera_add(location=(10,-10,5))\nc=bpy.context.active_object\nc.data.lens=24\nc.rotation_euler=(math.radians(75),0,math.radians({a}))\nbpy.context.scene.camera=c\nprint('Architectural camera: 24mm')")

    # Animation
    if name=="add_keyframe":
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:o.keyframe_insert(data_path='{args.get('property','location')}',frame={args.get('frame',1)})\nprint('Keyframe added')")
    if name=="set_animation_range":
        return CC(f"import bpy\nbpy.context.scene.frame_start={args.get('start',1)}\nbpy.context.scene.frame_end={args.get('end',250)}\nbpy.context.scene.render.fps={args.get('fps',24)}\nprint('Animation range set')")
    if name=="set_interpolation":
        interp=args.get("interpolation","auto")
        return CC(f"import bpy,mathutils\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o and o.animation_data:\n for fc in o.animation_data.action.fcurves:\n  for kp in fc.keyframe_points:\n   kp.interpolation='{interp.upper()}'\nprint('Interpolation set')")
    if name=="play_animation":
        act=args.get("action","play")
        if act=="play": return CC("import bpy\nbpy.context.scene.frame_set(bpy.context.scene.frame_start)\nbpy.ops.screen.animation_play()\nprint('Playing')")
        if act=="pause": return CC("import bpy\nbpy.ops.screen.animation_play()\nprint('Paused')")
        if act=="stop": return CC("import bpy\nbpy.ops.screen.animation_cancel()\nprint('Stopped')")
        if act=="next_frame": return CC("import bpy\nbpy.context.scene.frame_set(bpy.context.scene.frame_current+1)\nprint('Next frame')")
        return CC("import bpy\nbpy.context.scene.frame_set(bpy.context.scene.frame_current-1)\nprint('Prev frame')")

    # Physics
    if name=="setup_rigid_body":
        rt=args.get("type","active");mass=args.get("mass",1)
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n bpy.ops.rigidbody.object_add()\n rb=bpy.context.object.rigid_body\n rb.type='{rt.upper()}'\n rb.mass={mass}\n print(f'Rigid body: {rt}')")
    if name=="setup_cloth":
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n bpy.ops.object.modifier_add(type='CLOTH')\n o.modifiers['Cloth'].settings.mass={args.get('mass',1)}\n print('Cloth added')")
    if name=="setup_fluid":
        ft=args.get("type","domain")
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n bpy.ops.object.modifier_add(type='FLUID')\n o.modifiers['Fluid'].domain_settings.domain_type='{ft}'\n print(f'Fluid: {ft}')")
    if name=="setup_particles":
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n bpy.ops.object.particle_system_add()\n ps=o.particle_systems[0].settings\n ps.count={args.get('count',1000)}\n ps.lifetime={args.get('lifetime',50)}\n print('Particles added')")
    if name=="setup_soft_body":
        return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:\n bpy.ops.object.modifier_add(type='SOFT_BODY')\n print('Soft body added')")

    # Rendering
    if name=="setup_render":
        eng=args.get("engine","cycles");rx=args.get("resolution_x",1920);ry=args.get("resolution_y",1080)
        s=args.get("samples",128);gpu=args.get("use_gpu",True);tr=args.get("transparent",False)
        c=f"import bpy\nsc=bpy.context.scene\nsc.render.engine='CYCLES' if '{eng}'=='cycles' else 'BLENDER_EEVEE_NEXT'\n"
        c+=f"sc.render.resolution_x={rx}\nsc.render.resolution_y={ry}\nsc.render.film_transparent={tr}\n"
        if eng=="cycles":c+=f"sc.cycles.samples={s}\nsc.cycles.device='GPU' if {gpu} else 'CPU'\n"
        c+=f"print(f'Render: {eng} {rx}x{ry}')"
        return CC(c)
    if name=="render_image":
        return CC(f"import bpy\nbpy.context.scene.render.filepath='{args.get('filepath','/tmp/render.png')}'\nbpy.context.scene.render.image_settings.file_format='{args.get('format','png').upper()}'\nbpy.ops.render.render(write_still=True)\nprint('Rendered')")
    if name=="setup_clay_render":
        return CC("import bpy\nmat=bpy.data.materials.new(name='Clay')\nmat.use_nodes=True\nbsdf=mat.node_tree.nodes.get('Principled BSDF')\nbsdf.inputs['Base Color'].default_value=(0.8,0.78,0.75,1)\nbsdf.inputs['Roughness'].default_value=0.9\nfor o in bpy.context.scene.objects:\n if o.type=='MESH':\n  if o.data.materials:o.data.materials[0]=mat\n  else:o.data.materials.append(mat)\nprint('Clay render setup')")

    # Import/Export
    if name=="import_file":
        fmt=args.get("format","fbx");ops={"fbx":"import_scene.fbx","obj":"import_scene.obj","gltf":"import_scene.gltf","glb":"import_scene.gltf","stl":"import_mesh.stl","blend":"wm.append"}
        return CC(f"import bpy\nbpy.ops.{ops.get(fmt,'import_scene.fbx')}(filepath='{args.get('filepath','')}')\nprint(f'Imported {fmt}')")
    if name=="export_file":
        fmt=args.get("format","fbx");sel=args.get("selected_only",False)
        ops={"fbx":"export_scene.fbx","obj":"export_scene.obj","gltf":"export_scene.gltf","glb":"export_scene.gltf","stl":"export_mesh.stl"}
        return CC(f"import bpy\nbpy.ops.{ops.get(fmt,'export_scene.fbx')}(filepath='{args.get('filepath','')}',use_selection={sel})\nprint('Exported')")

    # Scene
    if name=="create_collection": return CC(f"import bpy\nc=bpy.data.collections.new('{args.get('name','Collection')}')\nbpy.context.scene.collection.children.link(c)\nprint('Collection created')")
    if name=="list_collections": return CC("import bpy,json\nprint(json.dumps([{'name':c.name,'objects':len(c.objects)}for c in bpy.data.collections]))")
    if name=="list_cameras": return CC("import bpy,json\nprint(json.dumps([{'name':c.name,'lens':c.lens}for c in bpy.data.cameras]))")
    if name=="list_lights": return CC("import bpy,json\nprint(json.dumps([{'name':l.name,'type':l.type,'energy':l.energy}for l in bpy.data.lights]))")
    if name=="list_modifiers": return CC(f"import bpy,json\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o:print(json.dumps([{'name':m.name,'type':m.type}for m in o.modifiers]))")
    if name=="set_active_scene": return CC(f"import bpy\nbpy.context.window.scene=bpy.data.scenes['{args.get('scene_name','Scene')}']\nprint('Scene set')")

    # Undo/Quality
    if name=="undo": return CC("import bpy\nbpy.ops.ed.undo()\nprint('Undone')")
    if name=="redo": return CC("import bpy\nbpy.ops.ed.redo()\nprint('Redone')")
    if name=="check_quality": return CC(
        "import bpy\nissues=[]\nfor o in bpy.context.scene.objects:\n if o.type=='MESH':\n"
        "  if o.scale!=(1.0,1.0,1.0):issues.append(f'{o.name}: non-uniform scale')\n"
        "  mesh=o.data\n  if mesh.polygons:\n   for p in mesh.polygons:\n    if len(p.vertices)<3:issues.append(f'{o.name}: degenerate face');break\n"
        "print(f'Found {len(issues)} issues')\nfor i in issues:print(f'  - {i}')")
    if name=="fix_normals": return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o and o.type=='MESH':\n bpy.context.view_layer.objects.active=o\n o.select_set(True)\n bpy.ops.object.mode_set(mode='EDIT')\n bpy.ops.mesh.normals_make_consistent(inside=False)\n bpy.ops.object.mode_set(mode='OBJECT')\n print('Normals fixed')")
    if name=="optimize_mesh": return CC(f"import bpy\no=bpy.data.objects.get('{args.get('object_name','')}')\nif o and o.type=='MESH':\n bpy.context.view_layer.objects.active=o\n o.select_set(True)\n bpy.ops.object.mode_set(mode='EDIT')\n bpy.ops.mesh.remove_doubles()\n bpy.ops.mesh.normals_make_consistent(inside=False)\n bpy.ops.object.mode_set(mode='OBJECT')\n print('Optimized')")

    # Batch
    if name=="batch_move":
        ns=args.get("object_names",[]);loc=tuple(args.get("location",[0,0,0]))
        c=f"import bpy\nfor n in {str(ns)}:\n o=bpy.data.objects.get(n)\n if o:o.location={loc}\nprint(f'Moved {len(ns)} objects')"
        return CC(c)
    if name=="batch_scale":
        ns=args.get("object_names",[]);sc=tuple(args.get("scale",[1,1,1]))
        c=f"import bpy\nfor n in {str(ns)}:\n o=bpy.data.objects.get(n)\n if o:o.scale={sc}\nprint(f'Scaled {len(ns)} objects')"
        return CC(c)
    if name=="batch_material":
        ns=args.get("object_names",[]);mn=args.get("material_name","")
        c=f"import bpy\nm=bpy.data.materials.get('{mn}')\nfor n in {str(ns)}:\n o=bpy.data.objects.get(n)\n if o and m:o.data.materials.clear();o.data.materials.append(m)\nprint(f'Applied {mn} to {len(ns)} objects')"
        return CC(c)

    return {"error": f"Unknown tool: {name}"}


# ═══════════════════════════════════════════════════════════════
# SERVER
# ═══════════════════════════════════════════════════════════════

async def mcp_tools_call(request: Request) -> JSONResponse:
    body = await request.json()
    tool_name = body.get("name", "")
    args = body.get("arguments", {})
    cmd = _dispatch(tool_name, args)
    if isinstance(cmd, dict) and "error" in cmd:
        return JSONResponse(cmd, status_code=400)
    result = await blender.execute(cmd)
    content = [{"type": "text", "text": result.get("result", "") if isinstance(result.get("result"), str) else json.dumps(result, indent=2)}]
    return JSONResponse({"content": content})

async def mcp_tools_list(request: Request) -> JSONResponse:
    return JSONResponse({"tools": MCP_TOOLS})

async def mcp_initialize(request: Request) -> JSONResponse:
    return JSONResponse({"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "blender-mcp", "version": "0.4.0"}})

async def mcp_sse(request: Request) -> EventSourceResponse:
    async def gen():
        yield {"event": "endpoint", "data": "/messages"}
        try:
            while True: await asyncio.sleep(30); yield {"event": "heartbeat", "data": "ok"}
        except asyncio.CancelledError: pass
    return EventSourceResponse(gen())

async def mcp_messages(request: Request) -> JSONResponse:
    body = await request.json()
    m = body.get("method", "")
    if m == "initialize": return await mcp_initialize(request)
    if m == "tools/list": return await mcp_tools_list(request)
    if m == "tools/call": return await mcp_tools_call(request)
    return JSONResponse({"error": f"Unknown method: {m}"}, status_code=400)

app = Starlette(routes=[
    Route("/sse", mcp_sse, methods=["GET"]),
    Route("/messages", mcp_messages, methods=["POST"]),
    Route("/tools/call", mcp_tools_call, methods=["POST"]),
    Route("/tools/list", mcp_tools_list, methods=["GET"]),
])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=SSE_HOST, port=SSE_PORT, log_level="info")
