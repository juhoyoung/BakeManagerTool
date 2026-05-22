import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import IntProperty, BoolProperty, PointerProperty

bl_info = {
    "name" : "BakeManagerTool",
    "author" : "happy Blender 😒",
    "description" : "",
    "blender" : (5, 0, 1),
    "version" : (1, 5, 0),
    "location" : "View3D > Sidebar > BakeManagerTool",
    "warning" : "",
    "category" : "Physics"
}

# ─────────────────────────────────────────────
#  Property Group
# ─────────────────────────────────────────────

class BakeManagerToolProperties(PropertyGroup):
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

    use_scene_frame_range: BoolProperty(
        name="Use Scene Frame Range",
        description="When enabled, bakes using the current scene Start/End Frame values",
        default=True
    )

    clear_cloth: BoolProperty(name="Cloth", default=True)
    clear_softbody: BoolProperty(name="Soft Body", default=True)
    clear_particle: BoolProperty(name="Particle", default=True)

    # Toggle option for displaying frame range details
    show_modifier_frame_range: BoolProperty(
        name="Show Frame Range Details",
        description="Toggle display of start/end frames for each physics modifier",
        default=False
    )


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

        box.prop(props, "use_scene_frame_range")

        if props.use_scene_frame_range:
            row = box.row()
            row.enabled = False
            row.prop(context.scene, "frame_start", text="Start")
            row.prop(context.scene, "frame_end", text="End")
        else:
            row = box.row()
            row.prop(props, "custom_frame_start", text="Start")
            row.prop(props, "custom_frame_end", text="End")

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
        props = context.scene.bake_help_tool
        objects_info = self.get_physics_objects_info()

        # Toggle UI for displaying frame numerical values
        layout.prop(props, "show_modifier_frame_range", toggle=True, icon='PREFERENCES')
        layout.separator()

        if objects_info:
            for obj_info in objects_info:
                obj = obj_info['object']
                obj_name = obj.name
                box = layout.box()

                # Object Label & Select Button + Visibility Toggles
                row = box.row(align=True)
                row.label(text=f"Object: {obj_name}", icon='OBJECT_DATA')

                # --- Added Viewport/Render Toggle Icons ---
                # Viewport visibility toggle
                icon_view = 'HIDE_OFF' if not obj.hide_viewport else 'HIDE_ON'
                row.prop(obj, "hide_viewport", text="", toggle=True)

                # Render visibility toggle
                icon_render = 'RESTRICT_RENDER_OFF' if not obj.hide_render else 'RESTRICT_RENDER_ON'
                row.prop(obj, "hide_render", text="", toggle=True)

                # Existing Select Button
                select_op = row.operator("script.select_object", text="", icon='RESTRICT_SELECT_OFF')
                select_op.obj_name = obj_name

                # Collision
                if obj_info['collision_modifier']:
                    mod = obj_info['collision_modifier']
                    row = box.row(align=True)
                    row.label(text="Collision", icon='MOD_PHYSICS')
                    icon_res = 'CHECKBOX_HLT' if mod.settings.use else 'CHECKBOX_DEHLT'
                    row.prop(mod.settings, "use", text="", icon=icon_res, toggle=True)

                # Cloth
                if obj_info['cloth_modifier']:
                    mod = obj_info['cloth_modifier']
                    cache = mod.point_cache
                    is_baked = cache.is_baked
                    row = box.row(align=True)

                    label_text = "Cloth"
                    if props.show_modifier_frame_range:
                        label_text += f" ({cache.frame_start}~{cache.frame_end})"
                    row.label(text=label_text, icon='CHECKMARK' if is_baked else 'CANCEL')

                    row.prop(mod, "show_viewport", text="")
                    row.prop(mod, "show_render", text="")

                    bake_op = row.operator("script.bake_single_cache", text="Bake", icon='RENDER_ANIMATION')
                    bake_op.obj_name = obj_name
                    bake_op.modifier_type = 'CLOTH'

                    clear_op = row.operator("script.clear_single_cache", text="Clear", icon='X')
                    clear_op.obj_name = obj_name
                    clear_op.modifier_type = 'CLOTH'

                # Soft Body
                if obj_info['softbody_modifier']:
                    mod = obj_info['softbody_modifier']
                    cache = mod.point_cache
                    is_baked = cache.is_baked
                    row = box.row(align=True)

                    label_text = "Soft Body"
                    if props.show_modifier_frame_range:
                        label_text += f" ({cache.frame_start}~{cache.frame_end})"
                    row.label(text=label_text, icon='CHECKMARK' if is_baked else 'CANCEL')

                    row.prop(mod, "show_viewport", text="")
                    row.prop(mod, "show_render", text="")

                    bake_op = row.operator("script.bake_single_cache", text="Bake", icon='RENDER_ANIMATION')
                    bake_op.obj_name = obj_name
                    bake_op.modifier_type = 'SOFT_BODY'

                    clear_op = row.operator("script.clear_single_cache", text="Clear", icon='X')
                    clear_op.obj_name = obj_name
                    clear_op.modifier_type = 'SOFT_BODY'

                # Particle
                for particle_modifier in obj_info['particle_modifier']:
                    ps = particle_modifier.particle_system
                    cache = ps.point_cache
                    is_baked = cache.is_baked
                    row = box.row(align=True)

                    label_text = ps.name
                    if props.show_modifier_frame_range:
                        label_text += f" ({cache.frame_start}~{cache.frame_end})"
                    row.label(text=label_text, icon='CHECKMARK' if is_baked else 'CANCEL')

                    row.prop(particle_modifier, "show_viewport", text="")
                    row.prop(particle_modifier, "show_render", text="")

                    bake_op = row.operator("script.bake_single_cache", text="Bake", icon='RENDER_ANIMATION')
                    bake_op.obj_name = obj_name
                    bake_op.modifier_type = 'PARTICLE_SYSTEM'
                    bake_op.particle_system_name = ps.name

                    clear_op = row.operator("script.clear_single_cache", text="Clear", icon='X')
                    clear_op.obj_name = obj_name
                    clear_op.modifier_type = 'PARTICLE_SYSTEM'
                    clear_op.particle_system_name = ps.name
        else:
            layout.label(text="No Physics objects found.")

    def get_physics_objects_info(self):
        physics_objects_info = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data:
                cloth_mod = None
                softbody_mod = None
                collision_mod = None
                particle_mods = []

                for modifier in obj.modifiers:
                    if modifier.type == 'CLOTH':
                        cloth_mod = modifier
                    elif modifier.type == 'SOFT_BODY':
                        softbody_mod = modifier
                    elif modifier.type == 'PARTICLE_SYSTEM':
                        particle_mods.append(modifier)
                    elif modifier.type == 'COLLISION':
                        collision_mod = modifier

                if any([cloth_mod, softbody_mod, collision_mod, particle_mods]):
                    physics_objects_info.append({
                        'object': obj,
                        'cloth_modifier': cloth_mod,
                        'softbody_modifier': softbody_mod,
                        'collision_modifier': collision_mod,
                        'particle_modifier': particle_mods,
                    })
        return physics_objects_info


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

def get_frame_range(context):
    props = context.scene.bake_help_tool
    if props.use_scene_frame_range:
        return context.scene.frame_start, context.scene.frame_end
    else:
        return props.custom_frame_start, props.custom_frame_end


class SCRIPT_OT_SelectObject(Operator):
    bl_idname = "script.select_object"
    bl_label = "Select Object"

    obj_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.obj_name)
        if obj:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            return {'FINISHED'}

        self.report({'WARNING'}, f"Object '{self.obj_name}' not found.")
        return {'CANCELLED'}


class SCRIPT_OT_FetchSceneFrameRange(Operator):
    bl_idname = "script.fetch_scene_frame_range"
    bl_label = "Fetch from Scene"

    def execute(self, context):
        props = context.scene.bake_help_tool
        props.custom_frame_start = context.scene.frame_start
        props.custom_frame_end = context.scene.frame_end
        self.report({'INFO'}, f"Frame range fetched: {props.custom_frame_start} ~ {props.custom_frame_end}")
        return {'FINISHED'}


class SCRIPT_OT_BakeFrameSynchronization(Operator):
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


class SCRIPT_OT_BakeSingleCache(Operator):
    bl_idname = "script.bake_single_cache"
    bl_label = "Bake Cache"

    obj_name: bpy.props.StringProperty()
    modifier_type: bpy.props.StringProperty()
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

            override = context.copy()
            override['active_object'] = obj
            override['point_cache'] = point_cache
            with context.temp_override(**override):
                bpy.ops.ptcache.bake(bake=True)

            self.report({'INFO'}, f"'{self.obj_name}' - {self.modifier_type} cache baked.")
            return {'FINISHED'}

        self.report({'WARNING'}, "Modifier not found.")
        return {'CANCELLED'}


class SCRIPT_OT_ClearSingleCache(Operator):
    bl_idname = "script.clear_single_cache"
    bl_label = "Clear Cache"

    obj_name: bpy.props.StringProperty()
    modifier_type: bpy.props.StringProperty()
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
    SCRIPT_OT_SelectObject,
    SCRIPT_OT_FetchSceneFrameRange,
    SCRIPT_OT_BakeFrameSynchronization,
    SCRIPT_OT_ClearAllClothSoftbodyCache,
    SCRIPT_OT_BakeSingleCache,
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