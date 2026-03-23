import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import IntProperty, BoolProperty, PointerProperty

bl_info = {
    "name" : "BakeManagerTool",
    "author" : "",
    "description" : "",
    "blender" : (5, 0, 1),
    "version" : (1, 1, 0),
    "location" : "View3D > Sidebar > BakeManagerTool",
    "warning" : "",
    "category" : "Baking"
}


# ─────────────────────────────────────────────
#  Property Group
# ─────────────────────────────────────────────

class BakeManagerToolProperties(PropertyGroup):
    # 1. Addon-defined custom frame range
    custom_frame_start: IntProperty(
        name="Start Frame",
        description="Bake start frame (addon custom value)",
        default=1,
        min=0
    )
    custom_frame_end: IntProperty(
        name="End Frame",
        description="Bake end frame (addon custom value)",
        default=250,
        min=0
    )

    # 3. Checkbox to choose whether to use the scene frame range
    use_scene_frame_range: BoolProperty(
        name="Use Scene Frame Range",
        description="When enabled, bakes using the current scene Start/End Frame values",
        default=True
    )

    # 5. Select which cache types to clear (multiple selection supported)
    clear_cloth: BoolProperty(name="Cloth", default=True)
    clear_softbody: BoolProperty(name="Soft Body", default=True)
    clear_particle: BoolProperty(name="Particle", default=True)


# ─────────────────────────────────────────────
#  Panel Base
# ─────────────────────────────────────────────

class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BakeManagerTool"


# ─────────────────────────────────────────────
#  Panel : Bake Controls
# ─────────────────────────────────────────────

class VIEW3D_PT_CacheBakeButton(MainPanel, Panel):
    bl_label = "Cache Bake Controls"
    bl_idname = "VIEW3D_PT_cache_bake_button"

    def draw(self, context):
        layout = self.layout
        props = context.scene.bake_help_tool

        # ── Frame Range Settings ───────────────────────
        box = layout.box()
        box.label(text="Frame Range", icon='TIME')

        # 3. Checkbox: use scene frame range or addon custom values
        box.prop(props, "use_scene_frame_range")

        if props.use_scene_frame_range:
            # Show scene values as read-only
            row = box.row()
            row.enabled = False
            row.prop(context.scene, "frame_start", text="Start")
            row.prop(context.scene, "frame_end", text="End")
        else:
            # 1. Input addon custom frame range values
            row = box.row()
            row.prop(props, "custom_frame_start", text="Start")
            row.prop(props, "custom_frame_end", text="End")

        # 2. Button to fetch frame range from current scene
        row = box.row()
        row.operator("script.fetch_scene_frame_range", icon='IMPORT')

        # ── Bake Buttons ──────────────────────────────
        layout.separator()
        layout.operator('ptcache.bake_all', text="Bake All", icon='RENDER_ANIMATION').bake = True
        layout.operator("script.bake_frame_synchronization", icon='UV_SYNC_SELECT')

        # ── Clear All Cache ────────────────────────────
        layout.separator()
        box2 = layout.box()
        box2.label(text="Clear All Cache", icon='TRASH')

        # 5. Select cache types to clear
        row = box2.row(align=True)
        row.prop(props, "clear_cloth", toggle=True)
        row.prop(props, "clear_softbody", toggle=True)
        row.prop(props, "clear_particle", toggle=True)

        box2.operator("script.clear_all_cloth_softbody_cache", icon='X')


# ─────────────────────────────────────────────
#  Panel : Bake Status
# ─────────────────────────────────────────────

class VIEW3D_PT_CacheBakeStatusPanel(MainPanel, Panel):
    bl_label = "Cache Bake Status"
    bl_idname = "VIEW3D_PT_cache_bake_status"

    def draw(self, context):
        layout = self.layout
        cloth_softbody_objects_info = self.get_cloth_softbody_objects_info()

        bakeText = "O"
        notBakeText = "X"

        if cloth_softbody_objects_info:
            for obj_info in cloth_softbody_objects_info:
                obj_name = obj_info['object'].name
                box = layout.box()
                box.label(text=f"Object: {obj_name}", icon='OBJECT_DATA')

                # Cloth
                if obj_info['cloth_modifier']:
                    mod = obj_info['cloth_modifier']
                    is_baked = mod.point_cache.is_baked
                    row = box.row(align=True)
                    row.label(text=f"Cloth: {'O' if is_baked else 'X'}")
                    # 4. Individual Clear button
                    op = row.operator("script.clear_single_cache", text="Clear", icon='X')
                    op.obj_name = obj_name
                    op.modifier_type = 'CLOTH'
                    op.particle_system_name = ""

                # Soft Body
                if obj_info['softbody_modifier']:
                    mod = obj_info['softbody_modifier']
                    is_baked = mod.point_cache.is_baked
                    row = box.row(align=True)
                    row.label(text=f"Soft Body: {'O' if is_baked else 'X'}")
                    # 4. Individual Clear button
                    op = row.operator("script.clear_single_cache", text="Clear", icon='X')
                    op.obj_name = obj_name
                    op.modifier_type = 'SOFT_BODY'
                    op.particle_system_name = ""

                # Particle
                for particle_modifier in obj_info['particle_modifier']:
                    ps = particle_modifier.particle_system
                    is_baked = ps.point_cache.is_baked
                    row = box.row(align=True)
                    row.label(text=f"{ps.name}: {'O' if is_baked else 'X'}")
                    # 4. Individual Clear button
                    op = row.operator("script.clear_single_cache", text="Clear", icon='X')
                    op.obj_name = obj_name
                    op.modifier_type = 'PARTICLE_SYSTEM'
                    op.particle_system_name = ps.name
        else:
            layout.label(text="No Cloth / Soft Body / Particle objects found.")

    def get_cloth_softbody_objects_info(self):
        cloth_softbody_objects_info = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data:
                cloth_modifier = None
                softbody_modifier = None
                particle_modifier = []
                for modifier in obj.modifiers:
                    if modifier.type == 'CLOTH':
                        cloth_modifier = modifier
                    elif modifier.type == 'SOFT_BODY':
                        softbody_modifier = modifier
                    elif modifier.type == 'PARTICLE_SYSTEM':
                        particle_modifier.append(modifier)
                if cloth_modifier or softbody_modifier or particle_modifier:
                    cloth_softbody_objects_info.append({
                        'object': obj,
                        'cloth_modifier': cloth_modifier,
                        'softbody_modifier': softbody_modifier,
                        'particle_modifier': particle_modifier,
                    })
        return cloth_softbody_objects_info


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

def get_frame_range(context):
    """Returns the frame_start / frame_end to use based on addon props settings"""
    props = context.scene.bake_help_tool
    if props.use_scene_frame_range:
        return context.scene.frame_start, context.scene.frame_end
    else:
        return props.custom_frame_start, props.custom_frame_end


class SCRIPT_OT_FetchSceneFrameRange(Operator):
    """Copies the current scene's Start/End Frame values into the addon custom fields"""
    bl_idname = "script.fetch_scene_frame_range"
    bl_label = "Fetch from Scene"

    def execute(self, context):
        props = context.scene.bake_help_tool
        props.custom_frame_start = context.scene.frame_start
        props.custom_frame_end = context.scene.frame_end
        self.report({'INFO'}, f"Frame range fetched: {props.custom_frame_start} ~ {props.custom_frame_end}")
        return {'FINISHED'}


class SCRIPT_OT_BakeFrameSynchronization(Operator):
    """Synchronizes the cache frame range of all Cloth / Soft Body modifiers"""
    bl_idname = "script.bake_frame_synchronization"
    bl_label = "Bake Frame Synchronization"

    def execute(self, context):
        frame_start, frame_end = get_frame_range(context)
        for obj in bpy.data.objects:
            for modifier in obj.modifiers:
                if modifier.type in {'CLOTH', 'SOFT_BODY'}:
                    modifier.point_cache.frame_start = frame_start
                    modifier.point_cache.frame_end = frame_end
        self.report({'INFO'}, f"Synchronized: {frame_start} ~ {frame_end}")
        return {'FINISHED'}


class SCRIPT_OT_ClearAllClothSoftbodyCache(Operator):
    """Clears all caches of the selected types"""
    bl_idname = "script.clear_all_cloth_softbody_cache"
    bl_label = "Clear Selected Cache"

    def execute(self, context):
        props = context.scene.bake_help_tool
        target_types = set()
        if props.clear_cloth:
            target_types.add('CLOTH')
        if props.clear_softbody:
            target_types.add('SOFT_BODY')
        if props.clear_particle:
            target_types.add('PARTICLE_SYSTEM')

        if not target_types:
            self.report({'WARNING'}, "Please select at least one cache type to clear.")
            return {'CANCELLED'}

        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for modifier in obj.modifiers:
                if modifier.type not in target_types:
                    continue

                if modifier.type == 'PARTICLE_SYSTEM':
                    point_cache = modifier.particle_system.point_cache
                else:
                    point_cache = modifier.point_cache

                override = context.copy()
                override['active_object'] = obj
                override['point_cache'] = point_cache
                with context.temp_override(**override):
                    bpy.ops.ptcache.free_bake()

        cleared = ", ".join(sorted(target_types))
        self.report({'INFO'}, f"Cache cleared: {cleared}")
        return {'FINISHED'}


class SCRIPT_OT_ClearSingleCache(Operator):
    """Clears the cache of a specific modifier on a specific object"""
    bl_idname = "script.clear_single_cache"
    bl_label = "Clear Cache"

    obj_name: bpy.props.StringProperty()
    modifier_type: bpy.props.StringProperty()  # 'CLOTH', 'SOFT_BODY', 'PARTICLE_SYSTEM'
    particle_system_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        obj = bpy.data.objects.get(self.obj_name)
        if not obj:
            self.report({'WARNING'}, f"Object '{self.obj_name}' not found.")
            return {'CANCELLED'}

        for modifier in obj.modifiers:
            if modifier.type != self.modifier_type:
                continue

            if self.modifier_type == 'PARTICLE_SYSTEM':
                if modifier.particle_system.name != self.particle_system_name:
                    continue
                point_cache = modifier.particle_system.point_cache
            else:
                point_cache = modifier.point_cache

            # Clear the cache
            override = context.copy()
            override['active_object'] = obj
            override['point_cache'] = point_cache
            with context.temp_override(**override):
                bpy.ops.ptcache.free_bake()

            self.report({'INFO'}, f"'{self.obj_name}' - {self.modifier_type} cache cleared.")
            return {'FINISHED'}

        self.report({'WARNING'}, "Modifier not found.")
        return {'CANCELLED'}


# ─────────────────────────────────────────────
#  Register
# ─────────────────────────────────────────────

classes = [
    BakeManagerToolProperties,
    VIEW3D_PT_CacheBakeButton,
    VIEW3D_PT_CacheBakeStatusPanel,
    SCRIPT_OT_FetchSceneFrameRange,
    SCRIPT_OT_BakeFrameSynchronization,
    SCRIPT_OT_ClearAllClothSoftbodyCache,
    SCRIPT_OT_ClearSingleCache,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bake_help_tool = PointerProperty(type=BakeManagerToolProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.bake_help_tool


if __name__ == "__main__":
    register()
