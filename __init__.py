import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import IntProperty, BoolProperty, EnumProperty, PointerProperty

bl_info = {
    "name" : "BakeManagerTool",
    "author" : "hyeffect55",
    "description" : "",
    "blender" : (5, 0, 1),
    "version" : (1, 6, 0),
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

    status_filter: EnumProperty(
        name="Physics Type",
        description="Show only objects that use the selected physics type",
        items=(
            ('ALL', "All", "Show all supported physics types"),
            ('CLOTH', "Cloth", "Show Cloth objects"),
            ('SOFT_BODY', "Soft", "Show Soft Body objects"),
            ('PARTICLE_SYSTEM', "Particle", "Show Particle System objects"),
            ('COLLISION', "Collision", "Show Collision objects"),
        ),
        default='ALL'
    )

    all_view_mode: EnumProperty(
        name="All View",
        description="Choose how all physics objects are organized",
        items=(
            ('NAME', "Name", "Show all objects in alphabetical order"),
            ('PHYSICS_GROUP', "Physics Groups", "Group objects by physics type"),
        ),
        default='NAME'
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

        layout.label(text="Filter by Physics Type", icon='FILTER')
        layout.prop(props, "status_filter", expand=True)

        if props.status_filter == 'ALL':
            layout.label(text="All View", icon='SORTALPHA')
            layout.prop(props, "all_view_mode", expand=True)

        layout.separator()

        # Toggle UI for displaying frame numerical values
        layout.prop(props, "show_modifier_frame_range", toggle=True, icon='PREFERENCES')
        layout.separator()

        if (
            props.status_filter == 'ALL'
            and props.all_view_mode == 'PHYSICS_GROUP'
        ):
            objects_info = []
            all_objects_info = self.get_physics_objects_info()
            physics_groups = (
                ('CLOTH', "Cloth"),
                ('SOFT_BODY', "Soft Body"),
                ('PARTICLE_SYSTEM', "Particle"),
                ('COLLISION', "Collision"),
            )
            for physics_type, group_label in physics_groups:
                group_objects = [
                    obj_info
                    for obj_info in all_objects_info
                    if self.matches_physics_filter(obj_info, physics_type)
                ]
                for index, obj_info in enumerate(group_objects):
                    grouped_info = obj_info.copy()
                    grouped_info['display_filter'] = physics_type
                    grouped_info['group_label'] = group_label if index == 0 else ""
                    objects_info.append(grouped_info)
        else:
            objects_info = self.get_physics_objects_info(props.status_filter)

        if objects_info:
            for obj_info in objects_info:
                display_filter = obj_info.get(
                    'display_filter',
                    props.status_filter
                )
                group_label = obj_info.get('group_label')
                if group_label:
                    header = layout.row()
                    header.label(text=group_label, icon='MOD_PHYSICS')

                obj = obj_info['object']
                obj_name = obj.name
                box = layout.box()

                # Object Label & Select Button + Visibility Toggles
                row = box.row(align=True)
                row.label(text=f"Object: {obj_name}", icon='OBJECT_DATA')

                # Viewport visibility toggle
                row.prop(
                    obj,
                    "hide_viewport",
                    text="",
                    toggle=True
                )

                # Render visibility toggle
                row.prop(
                    obj,
                    "hide_render",
                    text="",
                    toggle=True
                )

                # Existing Select Button
                select_op = row.operator("script.select_object", text="", icon='RESTRICT_SELECT_OFF')
                select_op.obj_name = obj_name

                # Collision
                if (
                    obj_info['collision_modifier']
                    and display_filter in {'ALL', 'COLLISION'}
                ):
                    mod = obj_info['collision_modifier']
                    row = box.row(align=True)
                    row.label(text="Collision", icon='MOD_PHYSICS')
                    icon_res = 'CHECKBOX_HLT' if mod.settings.use else 'CHECKBOX_DEHLT'
                    row.prop(mod.settings, "use", text="", icon=icon_res, toggle=True)

                # Cloth
                if (
                    obj_info['cloth_modifier']
                    and display_filter in {'ALL', 'CLOTH'}
                ):
                    mod = obj_info['cloth_modifier']
                    cache = mod.point_cache
                    self.draw_cache_row(
                        box,
                        props,
                        obj_name,
                        mod,
                        cache,
                        "Cloth",
                        'CLOTH'
                    )

                # Soft Body
                if (
                    obj_info['softbody_modifier']
                    and display_filter in {'ALL', 'SOFT_BODY'}
                ):
                    mod = obj_info['softbody_modifier']
                    cache = mod.point_cache
                    self.draw_cache_row(
                        box,
                        props,
                        obj_name,
                        mod,
                        cache,
                        "Soft Body",
                        'SOFT_BODY'
                    )

                # Particle
                particle_modifiers = (
                    obj_info['particle_modifier']
                    if display_filter in {'ALL', 'PARTICLE_SYSTEM'}
                    else []
                )
                for particle_modifier in particle_modifiers:
                    ps = particle_modifier.particle_system
                    cache = ps.point_cache
                    self.draw_cache_row(
                        box,
                        props,
                        obj_name,
                        particle_modifier,
                        cache,
                        ps.name,
                        'PARTICLE_SYSTEM',
                        ps.name
                    )
        else:
            layout.label(text="No matching physics objects found.")

    @staticmethod
    def draw_cache_row(
        box,
        props,
        obj_name,
        modifier,
        cache,
        label,
        modifier_type,
        particle_system_name=""
    ):
        row = box.row(align=True)
        label_text = label
        if props.show_modifier_frame_range:
            label_text += f" ({cache.frame_start}~{cache.frame_end})"
        row.label(
            text=label_text,
            icon='CHECKMARK' if cache.is_baked else 'CANCEL'
        )

        row.prop(modifier, "show_viewport", text="")
        row.prop(modifier, "show_render", text="")

        bake_op = row.operator(
            "script.bake_single_cache",
            text="Bake",
            icon='RENDER_ANIMATION'
        )
        bake_op.obj_name = obj_name
        bake_op.modifier_type = modifier_type
        bake_op.particle_system_name = particle_system_name

        clear_op = row.operator(
            "script.clear_single_cache",
            text="Clear",
            icon='X'
        )
        clear_op.obj_name = obj_name
        clear_op.modifier_type = modifier_type
        clear_op.particle_system_name = particle_system_name

    @staticmethod
    def matches_physics_filter(obj_info, status_filter):
        return (
            (
                status_filter == 'ALL'
                and any((
                    obj_info['cloth_modifier'],
                    obj_info['softbody_modifier'],
                    obj_info['particle_modifier'],
                    obj_info['collision_modifier'],
                ))
            )
            or (
                status_filter == 'CLOTH'
                and obj_info['cloth_modifier']
            )
            or (
                status_filter == 'SOFT_BODY'
                and obj_info['softbody_modifier']
            )
            or (
                status_filter == 'PARTICLE_SYSTEM'
                and obj_info['particle_modifier']
            )
            or (
                status_filter == 'COLLISION'
                and obj_info['collision_modifier']
            )
        )

    def get_physics_objects_info(self, status_filter='ALL'):
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

                obj_info = {
                    'object': obj,
                    'cloth_modifier': cloth_mod,
                    'softbody_modifier': softbody_mod,
                    'collision_modifier': collision_mod,
                    'particle_modifier': particle_mods,
                }
                if self.matches_physics_filter(obj_info, status_filter):
                    physics_objects_info.append(obj_info)
        return sorted(
            physics_objects_info,
            key=lambda obj_info: obj_info['object'].name.casefold()
        )


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
