import bpy

class PREV_OT_mute(bpy.types.Operator):
    """
    Mute/Unmute selected
    """
    bl_idname = "vse_transform_tools.mute"
    bl_label = "Mute"
    bl_description = "Mute/Unmute selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        scene = context.scene
        if (scene.sequence_editor and
           scene.sequence_editor.active_strip):
            return True
        return False

    def invoke(self, context, event):
        if event.alt: # alt+h demute all
            # TODO: implement
            return {"FINISHED"}
        elif context.selected_sequences:
            bpy.ops.sequencer.mute(unselected=False)
            bpy.ops.sequencer.select_all(action='DESELECT')
        return {"FINISHED"}
