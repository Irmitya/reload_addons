import bpy
import importlib
import os
import addon_utils
import sys
from traceback import print_exc as error
is28 = bool(bpy.app.version >= (2, 80, 0))
is27 = bool(bpy.app.version < (2, 80, 0))
prev = ""

bl_info = {
    'name'			: "Reload Addon",
    # 'description'	:	"",
    # 'author'		:	"Your Name",
    # 'version'		:	(0,	9,	0),
    'blender'		: (2, 80, 0),
    # 'location'		: "Everywhere",
    # 'warning'		: "This addon is still in development.",
    # 'wiki_url'		:	"",
    'category'		: " Custom",
    }

bprops = [
    'BoolProperty',
    'BoolVectorProperty',
    'IntProperty',
    'IntVectorProperty',
    'FloatProperty',
    'FloatVectorProperty',
    'StringProperty',
    'EnumProperty',
    'PointerProperty',
    'CollectionProperty',
    'RemoveProperty',
    ]
bprops = [eval('bpy.props.%s' % b) for b in bprops]


class Get:
    def addons(self, context):
        pref = (context.preferences if is28 else context.user_preferences)
        list = []

        list.append((__name__, bl_info['name'], "", 'FILE_REFRESH', 2))
        mine = [__name__, prev]

        for (i, a) in enumerate(sorted(pref.addons.keys())):
            if a in mine:
                continue
            id = pref.addons[a].module

            bl_def = type('m', (), {'bl_info': {'name': id}})
            bl = (addon_utils.addons_fake_modules.get(id, bl_def).bl_info
                  if addon_utils.addons_fake_modules else sys.modules[id].bl_info)
            name = bl['name']
            desc = bl.get('description', id)

            list.append((id, name, desc, 'NONE', i + 20))

        list.append((prev, prev, "Previously Refreshed Addon", 'FILE_REFRESH', 99))

        return list

    def ops(op):
        """Validate whether or not an operator (string) is in bpy.ops"""
        (main, sub) = op.split('.')
        return sub in dir(eval(f'bpy.ops.{main}'))


def disable(module):
    if Get.ops('wm.addon_disable'):
        bpy.ops.wm.addon_disable(module=module)
    elif Get.ops('preferences.addon_disable'):
        bpy.ops.preferences.addon_disable(module=module)
    else:
        addon_utils.disable(module_name=module)


def refresh(module):
    if Get.ops('wm.addon_refresh'):
        bpy.ops.wm.addon_refresh()
    elif Get.ops('preferences.addon_refresh'):
        bpy.ops.preferences.addon_refresh()
    else:
        importlib.reload(module)


def enable(module):
    if Get.ops('wm.addon_enable'):
        bpy.ops.wm.addon_enable(module=module)
    elif Get.ops('preferences.addon_enable'):
        bpy.ops.preferences.addon_enable(module=module)
    else:
        addon_utils.enable(module_name=module)


def reload(self, context, modules):
    global prev
    addons = addon_utils.addons_fake_modules

    os.system('cls')
    try:
        for addon_name in modules:
            disable(addon_name)
            addon_utils.disable(module_name=addon_name)
            os.system("cls")
    except:
        os.system("cls")
        self.report({'INFO'}, f"Error: Addon['{modules}'] failed to disable")
        error()

    for addon_name in modules:
        try:
            addon = sys.modules.get(addon_name)
            if addon is None:
                self.report({'INFO'}, f"Error: could not find addon['{addon_name}'] in sys.modules")
                print(f"Error reloading {addon_name}, not found in sys.modules")
                continue

            if len(modules) == 1 or addon_name == modules[0]:
                print(f"Reloading {addon_name}")
                if addon_name != prev:  # Print filepath when selecting a new addon
                    print(f"\t{addon.__file__}")

            for sub_name in sys.modules:
                if not sub_name.startswith(f"{addon_name}."):
                    continue
                try:
                    importlib.reload(sys.modules[sub_name])
                except:
                    self.report({'INFO'}, f"Error: Sub Module['{sub_name}'] failed to reload")
                    error()
            importlib.reload(addon)

            enable(addon_name)
        except:
            self.report({'INFO'}, f"Error: Addon['{addon_name}'] failed to reload")
            error()

    prev = modules[0]


class SYSTEM_OT_reload_addon(bpy.types.Operator):
    bl_description = "Click to reload previous addon.\nShift/Ctrl/Alt + Click to select an addon to reload"
    bl_idname = 'wm.reload_addon'
    bl_label = "Reload Addons"
    # bl_options = set({'REGISTER'})
    bl_undo_group = ""

    @classmethod
    def poll(self, context):
        return True

    bl_property = "addon"
    addon = bpy.props.EnumProperty(
        items=Get.addons,
        name="",
        description="",
        default=None,  # ('string' or {'set'})  from items
        )

    def invoke(self, context, event):
        global prev
        if (not prev) or any((event.shift, event.ctrl, event.alt)):
            wm = context.window_manager
            wm.invoke_search_popup(self)
            return {'FINISHED'}
        else:
            self.addon = prev
            return self.execute(context)

    def execute(self, context):
        modules = [self.addon]
        reload(self, context, modules)

        return {'FINISHED'}


class SYSTEM_HT_reload_addon(bpy.types.Header):
    bl_space_type = ('TOPBAR', 'INFO')[is27]

    def draw(self, context):
        if is28:
            if context.region.alignment != 'RIGHT':
                return
        layout = self.layout
        layout.operator('wm.reload_addon')


classes = (
    SYSTEM_OT_reload_addon,
    SYSTEM_HT_reload_addon,
    )


def annotate(cls):
    bl_description = "Converts class fields to annotations if running with Blender 2.8"
    if is27:
        return cls
    bl_props = {name: value for name, value in cls.__dict__.items()
                if (value and isinstance(value, tuple) and value[0] in bprops)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for name, value in bl_props.items():
            annotations[name] = value
            delattr(cls, name)
    return cls


def register():
    for cls in classes:
        annotate(cls)
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
