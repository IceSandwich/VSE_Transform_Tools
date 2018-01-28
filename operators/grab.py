import bpy
from mathutils import Vector

from .utils import get_pos_x
from .utils import get_pos_y
from .utils import set_pos_x
from .utils import set_pos_y
from .utils import process_input
from .utils import get_res_factor
from .utils import func_constrain_axis_mmb
from .utils import func_constrain_axis
from .utils import get_group_box
from .utils import mouse_to_res
from .utils import get_preview_offset
from .utils import ensure_transforms
from .utils import get_visible_strips


class Grab(bpy.types.Operator):
    """
    ![Demo](https://i.imgur.com/yQCFI0s.gif)
    """
    bl_idname = "vse_transform_tools.grab"
    bl_label = "Grab"
    bl_description = "Change position of strips in Image Preview Window"
    bl_options = {'REGISTER', 'UNDO'}

    axis_x = True
    axis_y = True
    choose_axis = False

    first_mouse_pos = Vector([0, 0])
    pos_clic = Vector([0, 0])
    mouse_pos = Vector([0, 0])
    center_area = Vector([0, 0])
    vec_act = Vector([0, 0])

    group_width = 0
    group_height = 0

    tab_init = []
    tab = []

    key_val = ''
    key_period = False
    key_period_val = 1

    handle_axes = None

    slow_factor = 10
    pre_slow_vec = Vector([0, 0])
    reduction_vec = Vector([0, 0])
    slow_act_fm = Vector([0, 0])

    horizontal_interests = []
    vertical_interests = []
    
    initially_shifted = False

    @classmethod
    def poll(cls, context):
        scene = context.scene
        if (scene.sequence_editor and
           scene.sequence_editor.active_strip):
            return True
        return False

    def modal(self, context, event):
        
        if self.tab:
            scene = context.scene
            res_x = scene.render.resolution_x
            res_y = scene.render.resolution_y

            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y

            mouse_vec = Vector([mouse_x, mouse_y])
            self.mouse_pos = mouse_to_res(mouse_vec)

            self.vec_act = self.mouse_pos - self.reduction_vec - self.first_mouse_pos


            func_constrain_axis_mmb(self, context, event.type, event.value, 0)
            func_constrain_axis(self, context, event.type, event.value, 0)
            
            process_input(self, event.type, event.value)
            if self.key_val != '':
                try:
                    if self.axis_y and not self.axis_x:
                        self.vec_act = Vector([0, float(self.key_val)])
                    else:
                        self.vec_act = Vector([float(self.key_val), 0])
                except ValueError:
                    pass

            if not self.initially_shifted and 'SHIFT' in event.type and event.value == 'PRESS' and self.key_val == '':
                self.pre_slow_vec = self.mouse_pos

            elif not self.initially_shifted and 'SHIFT' in event.type and event.value == 'RELEASE' and self.key_val == '':
                self.vec_act = (self.pre_slow_vec - self.first_mouse_pos - self.reduction_vec) + self.slow_act_fm
                self.reduction_vec = self.reduction_vec + ((self.mouse_pos - self.pre_slow_vec) * (self.slow_factor - 1)) / self.slow_factor

            elif not self.initially_shifted and event.shift and self.key_val == '':
                self.slow_act_fm = (self.mouse_pos - self.pre_slow_vec) / self.slow_factor
                self.vec_act = (self.pre_slow_vec - self.first_mouse_pos - self.reduction_vec) + self.slow_act_fm
            
            elif 'SHIFT' in event.type and event.value == 'RELEASE':
                self.initially_shifted = False
            
            info_x = round(self.vec_act.x, 5)
            info_y = round(self.vec_act.y, 5)
            if not self.axis_x:
                self.vec_act = Vector((0, self.vec_act.y))
                context.area.header_text_set("D: %.4f along global Y" % info_y)
            if not self.axis_y:
                self.vec_act = Vector((self.vec_act.x, 0))
                context.area.header_text_set("D: %.4f along global X" % info_x)
            if self.axis_x and self.axis_y:
                context.area.header_text_set("Dx: %.4f Dy: %.4f" % (info_x, info_y))

            snap_distance = int(max([res_x, res_y]) / 50)
            
            group_pos_x = self.center_area.x + self.vec_act.x
            group_pos_y = self.center_area.y + self.vec_act.y
            
            current_left = group_pos_x - (self.group_width / 2)
            current_right = group_pos_x + (self.group_width / 2)
            current_bottom = group_pos_y - (self.group_height / 2)
            current_top = group_pos_y + (self.group_height / 2)

            offset_x = 0
            offset_y = 0

            if event.ctrl:
                for line in self.horizontal_interests:
                    if (current_left < line + snap_distance and
                       current_left > line - snap_distance):
                        offset_x = line - current_left
                        break
                    if (current_right > line - snap_distance and
                       current_right < line + snap_distance):
                        offset_x = line - current_right
                        break

                for line in self.vertical_interests:
                    if (current_bottom < line + snap_distance and
                       current_bottom > line - snap_distance):
                        offset_y = line - current_bottom
                        break
                    if (current_top > line - snap_distance and
                       current_top < line + snap_distance):
                        offset_y = line - current_top
                        break

            for strip, init_pos in zip(self.tab, self.tab_init):
                pos_x = init_pos[0] + self.vec_act.x + offset_x
                pos_y = init_pos[1] + self.vec_act.y + offset_y

                strip.translate_start_x = set_pos_x(strip, pos_x)
                strip.translate_start_y = set_pos_y(strip, pos_y)

            if (event.type == 'LEFTMOUSE' or
               event.type == 'RET' or
               event.type == 'NUMPAD_ENTER' or
               not self.tab):
                if self.handle_axes:
                    bpy.types.SpaceSequenceEditor.draw_handler_remove(
                        self.handle_axes, 'PREVIEW')

                if scene.tool_settings.use_keyframe_insert_auto:
                    cf = context.scene.frame_current
                    for strip in self.tab:
                        strip.keyframe_insert(data_path='translate_start_x', frame=cf)
                        strip.keyframe_insert(data_path='translate_start_y', frame=cf)

                context.area.header_text_set()
                return {'FINISHED'}

            if event.type == 'ESC' or event.type == 'RIGHTMOUSE':
                if self.handle_axes:
                    bpy.types.SpaceSequenceEditor.draw_handler_remove(
                        self.handle_axes, 'PREVIEW')
                for strip, init_pos in zip(self.tab, self.tab_init):
                    strip.translate_start_x = set_pos_x(strip, init_pos[0])
                    strip.translate_start_y = set_pos_y(strip, init_pos[1])
                context.area.header_text_set()
                return {'FINISHED'}

            return {'RUNNING_MODAL'}

        return {'FINISHED'}

    def invoke(self, context, event):
        if event.alt:
            for strip in context.selected_sequences:
                if strip.type == 'TRANSFORM':
                    strip.translate_start_x = 0
                    strip.translate_start_y = 0
                return {'FINISHED'}
        else:
            scene = context.scene

            res_x = scene.render.resolution_x
            res_y = scene.render.resolution_y

            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y

            self.key_val = ''

            self.tab = []
            self.tab_init = []
            self.center_area = Vector([0, 0])

            self.group_width = 0
            self.group_height = 0

            self.horizontal_interests = [0, res_x]
            self.vertical_interests = [0, res_y]

            mouse_vec = Vector([mouse_x, mouse_y])
            self.first_mouse_pos = mouse_to_res(mouse_vec)

            fac = get_res_factor()

            self.tab = ensure_transforms()
            visible_strips = get_visible_strips()
            
            for strip in visible_strips:
                if strip not in self.tab:
                    left, right, bottom, top = get_group_box([strip])

                    self.horizontal_interests.append(left)
                    self.horizontal_interests.append(right)

                    self.vertical_interests.append(bottom)
                    self.vertical_interests.append(top)

            for strip in self.tab:
                strip.select = True
                pos_x = get_pos_x(strip)
                pos_y = get_pos_y(strip)
                self.tab_init.append([pos_x, pos_y])

            if self.tab:
                group_box = get_group_box(self.tab)
                min_left, max_right, min_bottom, max_top = group_box

                self.group_width = max_right - min_left
                self.group_height = max_top - min_bottom

                center_x = (min_left + (self.group_width / 2))
                center_y = (min_bottom + (self.group_height / 2))

                self.center_area = Vector([center_x, center_y])

            # Prevents weird behavior if this op is called by 
            # bpy.ops.vse_transform_tools.duplicate()
            if event.shift:
                self.initially_shifted = True
            
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}