# Blender Python API — God Mode Reference

## Core Concepts
```python
import bpy
import mathutils
from mathutils import Vector, Matrix, Euler
import math
```

## Object Creation
```python
# Mesh primitives
bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(0,0,0))
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=2, location=(0,0,0))
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, radius2=0, depth=2, location=(0,0,0))
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.25, location=(0,0,0))
bpy.ops.mesh.primitive_plane_add(size=2, location=(0,0,0))
bpy.ops.mesh.primitive_monkey_add(location=(0,0,0))
bpy.ops.mesh.primitive_ico_add(subdivisions=2, radius=1, location=(0,0,0))
bpy.ops.mesh.primitive_grid_add(x_segments=10, y_segments=10, size=2, location=(0,0,0))

# Text
bpy.ops.object.text_add(location=(0,0,0))
text = bpy.context.active_object
text.data.body = "Hello World"
text.data.size = 1.0
text.data.extrude = 0.1

# Empty
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
```

## Object Properties
```python
obj = bpy.context.active_object
obj.name = "MyObject"
obj.location = (x, y, z)           # or Vector((x, y, z))
obj.rotation_euler = (rx, ry, rz)  # Euler angles in radians
obj.scale = (sx, sy, sz)
obj.hide_viewport = False
obj.hide_render = False
obj.display_type = 'TEXTURED'      # TEXTURED, SOLID, WIRE, etc.
obj.lock_location = (False, False, False)
obj.lock_rotation = (False, False, False)
obj.lock_scale = (False, False, False)
```

## Materials
```python
mat = bpy.data.materials.new(name="MyMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Principled BSDF
bsdf = nodes.get("Principled BSDF")
bsdf.inputs['Base Color'].default_value = (r, g, b, 1)  # RGBA 0-1
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Roughness'].default_value = 0.5
bsdf.inputs['Emission Strength'].default_value = 0.0
bsdf.inputs['Alpha'].default_value = 1.0

# Assign material
obj.data.materials.append(mat)

# Remove all materials
obj.data.materials.clear()

# Glass material
bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)
bsdf.inputs['Alpha'].default_value = 0.1
bsdf.inputs['Roughness'].default_value = 0.0
bsdf.inputs['Transmission Weight'].default_value = 1.0
mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None

# Emissive material
bsdf.inputs['Base Color'].default_value = (1, 0.5, 0, 1)
bsdf.inputs['Emission Strength'].default_value = 5.0

# Node-based materials
tex_node = nodes.new('ShaderNodeTexImage')
tex_node.image = bpy.data.images.load("/path/to/texture.png")
links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

# Color ramp
ramp = nodes.new('ShaderNodeValToColor')
ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
```

## Lighting
```python
# Point light
bpy.ops.object.light_add(type='POINT', location=(x, y, z))
light = bpy.context.active_object
light.data.energy = 1000  # Watts
light.data.color = (1, 1, 1)
light.data.shadow_soft_size = 0.25

# Sun light
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
light = bpy.context.active_object
light.data.energy = 1.0
light.rotation_euler = (math.radians(45), 0, math.radians(45))

# Area light
bpy.ops.object.light_add(type='AREA', location=(0, 0, 3))
light = bpy.context.active_object
light.data.energy = 100
light.data.size = 2.0
light.data.shape = 'RECTANGLE'  # SQUARE, RECTANGLE, ELLIPSE, DISK

# Spot light
bpy.ops.object.light_add(type='SPOT', location=(0, 0, 5))
light = bpy.context.active_object
light.data.energy = 1000
light.data.spot_size = math.radians(45)
light.data.spot_blend = 0.5
```

## Camera
```python
bpy.ops.object.camera_add(location=(0, -5, 2))
cam = bpy.context.active_object
cam.data.lens = 50  # Focal length in mm
cam.data.sensor_width = 36
cam.data.clip_start = 0.1
cam.data.clip_end = 1000
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 2.8
cam.data.dof.focus_distance = 5.0
cam.rotation_euler = (math.radians(80), 0, 0)
bpy.context.scene.camera = cam

# Track to constraint
constraint = cam.constraints.new(type='TRACK_TO')
constraint.target = bpy.data.objects['Target']
constraint.track_axis = 'NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
```

## Mesh Editing
```python
obj = bpy.context.active_object
mesh = obj.data

# Edit mode operations
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 1)})
bpy.ops.mesh.dissolve_faces()
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')

# Direct vertex manipulation
for v in mesh.vertices:
    v.co.z += 0.5

# Subdivide
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=3)
bpy.ops.object.mode_set(mode='OBJECT')

# Extrude individual
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.extrude_individual()
bpy.ops.transform.translate(value=(0, 0, 1))
bpy.ops.object.mode_set(mode='OBJECT')
```

## Modifiers
```python
obj = bpy.context.active_object

# Subdivision Surface
mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
mod.levels = 2
mod.render_levels = 3
mod.subdivision_type = 'CATMULL_CLARK'

# Bevel
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.1
mod.segments = 3
mod.limit_method = 'ANGLE'
mod.angle_limit = math.radians(30)

# Array
mod = obj.modifiers.new(name="Array", type='ARRAY')
mod.count = 5
mod.use_relative_offset = True
mod.relative_offset_displace = (1, 0, 0)

# Mirror
mod = obj.modifiers.new(name="Mirror", type='MIRROR')
mod.use_axis = (True, False, False)
mod.use_mirror_merge = True

# Solidify
mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod.thickness = 0.1

# Boolean
mod = obj.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = bpy.data.objects['Cutter']

# Wireframe
mod = obj.modifiers.new(name="Wireframe", type='WIREFRAME')
mod.thickness = 0.02

# Displacement
mod = obj.modifiers.new(name="Displace", type='DISPLACE')
mod.strength = 0.5
```

## Constraints
```python
obj = bpy.context.active_object

# Track To
con = obj.constraints.new(type='TRACK_TO')
con.target = bpy.data.objects['Target']
con.track_axis = 'NEGATIVE_Z'
con.up_axis = 'UP_Y'

# Copy Location
con = obj.constraints.new(type='COPY_LOCATION')
con.target = bpy.data.objects['Source']

# Copy Rotation
con = obj.constraints.new(type='COPY_ROTATION')
con.target = bpy.data.objects['Source']

# IK (Inverse Kinematics)
con = obj.constraints.new(type='IK')
con.target = bpy.data.objects['Target']
con.chain_count = 4

# Child Of
con = obj.constraints.new(type='CHILD_OF')
con.target = bpy.data.objects['Parent']

# Limit Distance
con = obj.constraints.new(type='LIMIT_DISTANCE')
con.target = bpy.data.objects['Target']
con.distance = 2.0
```

## Animation
```python
obj = bpy.context.active_object

# Set keyframe
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)
obj.location = (5, 0, 0)
obj.keyframe_insert(data_path="location", frame=60)

# Set interpolation
for fcurve in obj.animation_data.action.fcurves:
    for kfp in fcurve.keyframe_points:
        kfp.interpolation = 'BEZIER'
        kfp.handle_right_type = 'AUTO'

# Set frame range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 250
bpy.context.scene.frame_set(1)

# Drivers
obj = bpy.context.active_object
driver = obj.driver_add('rotation_euler', 2).driver
driver.type = 'SCRIPTED'
var = driver.variables.new()
var.name = 'x'
var.type = 'SINGLE_PROP'
var.targets[0].id = bpy.data.objects['Controller']
driver.expression = 'var * 2'
```

## Physics
```python
# Rigid Body
bpy.ops.rigidbody.object_add()
rb = bpy.rigid_body
rb.type = 'ACTIVE'  # ACTIVE or PASSIVE
rb.mass = 1.0
rb.friction = 0.5
rb.restitution = 0.5

# Cloth
bpy.ops.object.modifier_add(type='CLOTH')
cloth = obj.modifiers['Cloth']
cloth.settings.mass = 1.0
cloth.settings.tension_stiffness = 15
cloth.settings.compression_stiffness = 15
cloth.settings.bending_stiffness = 0.5
cloth.collision_settings.use_collision = True
cloth.collision_settings.distance_min = 0.01

# Particle System
bpy.ops.object.particle_system_add()
ps = obj.particle_systems[0].settings
ps.type = 'EMITTER'
ps.count = 1000
ps.lifetime = 50
ps.frame_start = 1
ps.frame_end = 100
ps.emit_from = 'FACE'
```

## Render Settings
```python
scene = bpy.context.scene

# Render engine
scene.render.engine = 'CYCLES'  # or 'BLENDER_EEVEE_NEXT'
scene.cycles.device = 'GPU'
scene.cycles.samples = 128
scene.cycles.use_denoising = True

# Resolution
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = True

# Output
scene.render.filepath = "/tmp/render.png"
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)

# World (background)
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (0.05, 0.05, 0.1, 1)
bg.inputs['Strength'].default_value = 0.5
```

## Collections
```python
# Create collection
col = bpy.data.collections.new("MyCollection")
bpy.context.scene.collection.children.link(col)

# Move object to collection
col.objects.link(obj)

# Unlink from scene collection
bpy.context.scene.collection.objects.unlink(obj)

# Collection hierarchy
parent_col = bpy.data.collections.new("Parent")
child_col = bpy.data.collections.new("Child")
bpy.context.scene.collection.children.link(parent_col)
parent_col.children.link(child_col)
```

## Import/Export
```python
# Import FBX
bpy.ops.import_scene.fbx(filepath="/path/to/model.fbx")

# Import OBJ
bpy.ops.import_scene.obj(filepath="/path/to/model.obj")

# Import GLTF/GLB
bpy.ops.import_scene.gltf(filepath="/path/to/model.glb")

# Import STL
bpy.ops.import_mesh.stl(filepath="/path/to/model.stl")

# Export FBX
bpy.ops.export_scene.fbx(filepath="/path/to/export.fbx")

# Export OBJ
bpy.ops.export_scene.obj(filepath="/path/to/export.obj")

# Export GLTF/GLB
bpy.ops.export_scene.gltf(filepath="/path/to/export.glb")
```

## Geometry Nodes
```python
obj = bpy.context.active_object
mod = obj.modifiers.new(name="GeoNodes", type='NODES')
node_group = mod.node_group

# Access nodes
for node in node_group.nodes:
    print(node.name, node.type)

# Create new node
new_node = node_group.nodes.new(type='ShaderNodeMath')
new_node.operation = 'ADD'
```

## Scene Management
```python
# Create new scene
new_scene = bpy.data.scenes.new("NewScene")
bpy.context.window.scene = new_scene

# Set active scene
bpy.context.window.scene = bpy.data.scenes["Scene"]

# Delete object
bpy.data.objects.remove(obj, do_unlink=True)

# Select all
bpy.ops.object.select_all(action='SELECT')

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Set active object
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Join objects
bpy.ops.object.select_all(action='DESELECT')
for obj in objects_to_join:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects_to_join[0]
bpy.ops.object.join()
```
