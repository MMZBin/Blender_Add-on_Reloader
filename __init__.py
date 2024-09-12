# pyright: reportInvalidTypeForm = false
# pyright: reportUnknownVariableType = false
# pyright: reportUnknownMemberType = false

from typing import Callable

from os.path import dirname, join, exists
from pathlib import Path

import bpy

from bpy.types import Operator, Panel, AddonPreferences, Context

from bpy.props import StringProperty
from bpy.app import timers

bl_info = {
    "name": "AddonReloader",
    "author": "MOMIZI",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "support": "RELEASE",
    "category": "Development",
    "location": "View3D > Sidebar > Tool Tab",
}

class AddonReloader:
    @staticmethod
    def get_addon_folder_path() -> str:
        return dirname(dirname(__file__))
    @classmethod
    def get_targeted_addon_folder_path(cls) -> str:
        addon_name = bpy.context.preferences.addons[__name__].preferences.addon_folder_name
        if not addon_name:
            addon_name = bpy.context.preferences.addons[__name__].preferences.addon_name
        if not addon_name:
            return ""

        return join(cls.get_addon_folder_path(), addon_name) # type: ignore

class DEV_OT_AddonReloader(Operator):
    bl_idname = "development.addon_reloader"
    bl_label = "Addon reloader"
    bl_description = "Reloads the specified add-on periodically."

    __INTERVAL: float = 1.0
    __timer = None

    @classmethod
    def is_timer_running(cls) -> bool: return cls.__timer is not None

    def execute(self, context: Context) -> set[str]:
        if self.is_timer_running():
            try:
                self.__unregister_timer()
            except ValueError:
                pass
        else:
            self.__register_timer()

        return {"FINISHED"}

    def __register_timer(self) -> None:
        self.__class__.__timer = self.__on_timer(
            bpy.context.preferences.addons[__name__].preferences.addon_name, # type: ignore
            Path(AddonReloader.get_targeted_addon_folder_path())
        )

        timers.register(self.__class__.__timer)

    def __unregister_timer(self) -> None:
        timers.unregister(self.__class__.__timer)
        self.__class__.__timer = None

    def __on_timer(self, addon_name: str, addon_path: Path) -> Callable[[], float]:
        import time

        is_running = False
        INTERVAL = self.__INTERVAL
        last_update_time: float = time.time()

        def _on_timer() -> float:
            nonlocal is_running, last_update_time

            if is_running: return INTERVAL
            is_running = True

            latest_update_time = max(
                addon_path.glob('**/*'),
                key=lambda f: f.stat().st_mtime if f.is_file() and not str(f) in '__pycache__' else 0
            ).stat().st_mtime

            if latest_update_time > last_update_time:
                last_update_time = latest_update_time

                #if not AddonReloader.is_modal_operator_running(): bpy.ops.script.reload()
                # try:
                #     bpy.ops.script.reload()
                # except RuntimeError as e:
                #     print(f"エラーは{e}")

                bpy.ops.preferences.addon_disable(module=addon_name) # type: ignore
                bpy.ops.preferences.addon_enable(module=addon_name) # type: ignore

            is_running = False

            return INTERVAL

        return _on_timer

class DEV_PT_AddonReloaderPanel(Panel):
    bl_idname = "DEV_PT_AddonReloaderPanel"
    bl_label = "Addon Reloader"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context: Context):
        layout = self.layout

        icon = 'PLAY'
        text = "Start Monitoring"
        if DEV_OT_AddonReloader.is_timer_running():
            icon = 'PAUSE'
            text = "Stop Monitoring"

        layout.label(text=f"Target Add-on:{bpy.context.preferences.addons[__name__].preferences.addon_name}")

        switch = layout.row()

        if not exists(AddonReloader.get_targeted_addon_folder_path()):
            switch.label(text="Add-ons folder not found, please check your Blender settings.", icon="ERROR")
        else:
            switch.operator(DEV_OT_AddonReloader.bl_idname, icon=icon, text=text)

class DEV_PT_AddonReloaderPreferences(AddonPreferences):
    bl_idname = __name__

    addon_name: StringProperty(
        name="Addon name",
        description="Targeted add-on name.",
        subtype='DIR_PATH',
        default=""
    )

    addon_folder_name: StringProperty(
        name="Addon folder name",
        description="The folder name of the target add-on (if not specified, it will be the same as the add-on name).",
        subtype='DIR_PATH',
        default=""
    )

    def draw(self, context: Context) -> None:
        layout = self.layout

        layout.enabled = not DEV_OT_AddonReloader.is_timer_running()

        layout.prop(self, "addon_name")

        folder_name_field = layout.row()

        if not self.addon_name:
            folder_name_field.enabled = False
            layout.label(text="Specify the add-on name.", icon='ERROR')

        folder_name_field.prop(self, "addon_folder_name")

        target_path = AddonReloader.get_targeted_addon_folder_path()

        if exists(target_path):
            if self.addon_name:
                layout.label(text=f'Files under the "{target_path}" will be monitored.', icon='INFO')
        else:
            layout.label(text=f'"{target_path}" does not exist.', icon='ERROR')

classes = (
    DEV_OT_AddonReloader,
    DEV_PT_AddonReloaderPanel,
    DEV_PT_AddonReloaderPreferences
)

def register() -> None:
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

def unregister() -> None:
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
