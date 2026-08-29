import math
import json
import traceback

# Silent:
#  0 - Display all messages
#  1 - Display start and end message only
#  2 - Do not display any messages

# Debug:
#  0 - Non-debug mode
#  1 - Extra debug info output (if Silent = 0)
#  2 - Save generated gcode to file and execute it (+ extra info)
#  3 - Save generated gcode to file, execute stock change (+ extra info)
#  4 - Save generated gcode to file, execute nothing (For internal use)

IFS_IDLE_STATE_VALUE = 5

SILENT_LEVEL_ALL = 0
SILENT_LEVEL_PRIORITY = 1
SILENT_LEVEL_NONE = 2

DEBUG_LEVEL_NONE = 0
DEBUG_LEVEL_SAVE_AND_EXECUTE = 1
DEBUG_LEVEL_SAVE_AND_FALLBACK = 2
DEBUG_LEVEL_INTERNAL = 3

class QuickSwap:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.lookup_object('gcode_move')

        self.zmod_ifs = None # Filled during _handle_ready
        self.save_variables = None # Filled during _handle_ready
        self.print_stats = None # Filled during _handle_ready
        self.toolhead = None # Filled during _handle_ready

        self.silent = config.getint('silent', SILENT_LEVEL_ALL)
        self.debug = config.getint('debug', DEBUG_LEVEL_NONE)

        self.printer.register_event_handler("klippy:ready", self._handle_ready)

        self.gcode.register_command('_QS_CHANGE_FILAMENT', self.cmd_QS_CHANGE_FILAMENT)
        self.gcode.register_command('_QS_WAIT_IFS_IDLE', self.cmd_QS_WAIT_IFS_IDLE)
        self.gcode.register_command('_QS_GENERATE_TEST', self.cmd_QS_GENERATE_TEST)

        # Fill with defaults for now. Load user's actual values in _handle_ready.
        max_z_velocity = 25.0

        self.x_left = 0.0
        self.x_right = 220.0
        self.y_front = 0.0
        self.y_back = 220.0
        self.z_max = 220.0

        self.cut_x = -2.5
        self.cut_prepare_x = 20.0
        self.cut_prepare_y = -7.5

        self.swap_z_movement = 5.0

        self.trash_x = 52.5
        self.trash_y = 229.0

        self.travel_move_speed = 30000
        self.z_travel_move_speed = 1500
        self.cut_prepare_y_travel_move_speed = 1800
        self.cut_move_speed = 600
        self.enter_trash_move_speed = 3000

        self.x_center = (self.x_left + self.x_right) / 2
        self.y_center = (self.y_front + self.y_back) / 2

    def _handle_ready(self):
        self.zmod_ifs = self.printer.lookup_object('zmod_ifs')
        self.save_variables = self.printer.lookup_object('save_variables')
        self.print_stats = self.printer.lookup_object('print_stats')
        self.toolhead = self.printer.lookup_object('toolhead')
        self._set_vars()
        self._rename_macro('_A_CHANGE_FILAMENT', '_QS_ORIG_A_CHANGE_FILAMENT')
        self._rename_macro('_QS_A_CHANGE_FILAMENT', '_A_CHANGE_FILAMENT')

    def _set_vars(self):
        eventtime = self.reactor.monotonic()
        client_vars = self.printer.lookup_object('gcode_macro _CLIENT_VARIABLE').get_status(eventtime)
        cut_vars = self.printer.lookup_object('gcode_macro _CUT_PRUTOK').get_status(eventtime)

        self.x_left = client_vars.get('min_x', 0.0)
        self.x_right = client_vars.get('max_x', 220.0)
        self.y_front = client_vars.get('min_y', 0.0)
        self.y_back = client_vars.get('max_y', 220.0)
        self.z_max = 220.0 # Hardcoded

        self.cut_x = cut_vars.get('x_cut', -2.5)
        self.cut_prepare_x = 20.0 # Hardcoded
        self.cut_prepare_y = cut_vars.get('y_cut', -7.5)

        self.swap_z_movement = 5.0 # Hardcoded

        self.trash_x = client_vars.get('custom_park_x', 52.5)
        self.trash_y = client_vars.get('custom_park_y', 229.0)

        self.travel_move_speed = 30000 # Validated against max at runtime
        self.z_travel_move_speed = 1500 # Validated against max at runtime
        self.cut_prepare_y_travel_move_speed = 1800 # Hardcoded
        self.cut_move_speed = 600 # Hardcoded
        self.enter_trash_move_speed = 3000 # Hardcoded

        self.x_center = (self.x_left + self.x_right) / 2
        self.y_center = (self.y_front + self.y_back) / 2

    def _rename_macro(self, orig_name, new_name):
        original_handler = self.gcode.gcode_handlers.pop(orig_name)

        if original_handler is None:
            raise self.printer.config_error(
                f"Target command {orig_name} not found to override!"
            )

        self.gcode.register_command(
            new_name,
            original_handler
        )

    def cmd_QS_GENERATE_TEST(self, gcmd):
        channel = gcmd.get_int('CHANNEL', 0)
        old_debug = self.debug
        self.debug = DEBUG_LEVEL_INTERNAL
        try:
            self.gcode.run_script_from_command(f'_QS_CHANGE_FILAMENT CHANNEL={channel}')
        finally:
            self.debug = old_debug

    def cmd_QS_WAIT_IFS_IDLE(self, gcmd):
        if self.zmod_ifs.ifs:
            if self.zmod_ifs.ifs_data.State != IFS_IDLE_STATE_VALUE:
                if self.silent == SILENT_LEVEL_ALL:
                    self.gcode.respond_info('QuickSwap: Waiting for IFS to be idle')
                self.zmod_ifs.wait_for_state(FFS_state=IFS_IDLE_STATE_VALUE)

    def cmd_QS_CHANGE_FILAMENT(self, gcmd):
        try:
            cmds = []
            channel = gcmd.get_int('CHANNEL', 0)
            self._generate_quickswap_filament_gcode(channel, cmds)
            
            if self.debug >= DEBUG_LEVEL_SAVE_AND_EXECUTE:
                with open('/usr/data/config/mod_data/quickswap_debug.txt', 'w') as f:
                    f.write('\n'.join(cmds))
            
            if self.debug <= DEBUG_LEVEL_SAVE_AND_EXECUTE:
                self.gcode.run_script_from_command('\n'.join(cmds))
                
            if self.debug == DEBUG_LEVEL_SAVE_AND_FALLBACK:
                self.gcode.run_script_from_command(f'_QS_ORIG_A_CHANGE_FILAMENT CHANNEL={channel} RESTORE_POSITION=1 RESTORE_TEMP=1')
        except Exception as e:
            msg = f"!! (QuickSwap) Filament change error: {str(e)}\nPausing print"
            gcmd.respond_raw(f"{msg}")
            gcmd.respond_raw(f"tgalarm_photo {msg}")
            if self.debug <= DEBUG_LEVEL_SAVE_AND_EXECUTE:
                try:
                    self.gcode.run_script_from_command("IFS_F112")
                    self.gcode.run_script_from_command("IFS_F18")
                except:
                    pass
                pause_resume = self.printer.lookup_object('pause_resume')
                pause_resume.send_pause_command()
                self.gcode.run_script_from_command("PAUSE\nM400\n")
            if self.debug >= DEBUG_LEVEL_SAVE_AND_EXECUTE:
                try:
                    cmds += ['# Interrupted by error']
                    e_filename, e_line, e_func, e_text = traceback.extract_tb(e.__traceback__)[-1]
                    cmds += [f'# {e_filename}, function {e_func} at line {e_line}']
                    cmds += [f'# Message: {e_text}']
                    with open('/usr/data/config/mod_data/quickswap_debug.txt', 'w') as f:
                        f.write('\n'.join(cmds))
                except:
                    pass

    def info(self, msg, cmds, level=0):
        if self.silent <= level:
            cmds += [f"RESPOND MSG='QuickSwap: {msg}'"]
            
    def log(self, msg, cmds):
        if self.debug > DEBUG_LEVEL_NONE:
            cmds += [f'# {msg}']

    def _generate_quickswap_filament_gcode(self, unmapped_target_channel, cmds):
        # TODO: Handle situation of target channel being empty
        status = self.gcode_move.get_status(self.reactor.monotonic())
        old_channel = self.zmod_ifs.get_current_channel_from_config()
        target_channel = self._qs_get_filament_mapping(unmapped_target_channel)

        self.info(f'Changing filament to T{unmapped_target_channel} (physical channel {target_channel})', cmds, SILENT_LEVEL_PRIORITY)

        nopoop = self.save_variables.allVariables.get('use_trash_on_print') == 0
        layer_num = self.print_stats.get_status(self.reactor.monotonic()).get('info', {}).get('current_layer', 1)

        initial_pos = status.get('gcode_position')

        old_filament_info = self.zmod_ifs.get_prutok_config(old_channel)
        new_filament_info = self.zmod_ifs.get_prutok_config(target_channel)

        if old_filament_info is None:
            old_filament_info = new_filament_info

        cmds += ["SAVE_GCODE_STATE NAME=qs_change_filament"]
        cmds += ["_DISABLE_SENSOR"]
        cmds += ["G90"] # Absolute
        cmds += ["M83"] # Relative extruder

        self._qsf_move_to_cutter(status, initial_pos, old_channel, old_filament_info, cmds)

        cmds += [f"G1 X{self.cut_x} F{self.cut_move_speed}"]

        if nopoop and layer_num > 1:
            self._qsf_return_to_print(initial_pos, cmds)
        else:
            self._qsf_move_from_cutter_to_trash(cmds)

        cmds += ["M400"]
        cmds += ["_QS_WAIT_IFS_IDLE"]

        self._qsf_unload_old_filament(old_channel, old_filament_info, cmds)

        self._qsf_load_new_filament(old_filament_info, target_channel, new_filament_info, cmds)

        if nopoop:
            if layer_num > 1:
                self._qsf_nopoop_wipe(cmds)
            else:
                cmds += ["_SBROS_TRASH"]
                cmds += ["_CLEAR_REZINA"]
                cmds += [f"G1 X{initial_pos[0]} Y{initial_pos[1]} F{self.travel_move_speed}"]
                cmds += [f"G1 Z{initial_pos[2]} F{self.z_travel_move_speed}"]

        cmds += ["RESTORE_GCODE_STATE NAME=qs_change_filament MOVE=0"]
        cmds += ["SDCARD_CLEAR_REFUELLING"]
        cmds += ["_ENABLE_SENSOR"]
        cmds += ["IFS_MOTION_ON"]
        cmds += ["IFS_SWITCH_ON"]
        cmds += ["_QS_WAIT_IFS_IDLE"]
        cmds += ["IFS_F18 WAIT=0"]
        self.info(f'Filament change complete', cmds, SILENT_LEVEL_PRIORITY)


    def _qsf_move_to_cutter(self, status, initial_pos, old_channel, old_filament_info, cmds):
        # Move to cutter while simultaneously performing unload before cut
        self.info(f'Moving to cutter', cmds)

        moves_to_cutter = self._get_moves_to_cutter(initial_pos)
        total_duration = sum(move[-1] for move in moves_to_cutter)

        unload_before_cut = old_filament_info['filament_unload_before_cutting']
        extruder_speed = old_filament_info['filament_extruder_speed']

        withdraw_duration = unload_before_cut / (extruder_speed / 60)

        remaining_withdraw_duration = withdraw_duration
        internal_pos = initial_pos
        done_ifs_grab = False
        for move in moves_to_cutter:
            # X, Y, Z, speed mm/min, duration sec
            new_x = internal_pos[0]
            new_y = internal_pos[1]
            new_z = internal_pos[2]
            if move[0] is not None:
                new_x = move[0]
            if move[1] is not None:
                new_y = move[1]
            if move[2] is not None:
                new_z = move[2]

            if remaining_withdraw_duration <= 0:
                extruder_move = 0
                extruder_move_time = 0
                if not done_ifs_grab:
                    cmds += [f"IFS_F24 PRUTOK={old_channel} WAIT=0"]
                    done_ifs_grab = True
            elif remaining_withdraw_duration >= move[4]:
                extruder_move = move[4] * (extruder_speed / 60)
                extruder_move_time = move[4]
            else:
                extruder_move = remaining_withdraw_duration * (extruder_speed / 60)
                extruder_move_time = remaining_withdraw_duration

            if extruder_move_time <= 0:
                cmds += [f"G1 X{new_x} Y{new_y} Z{new_z} F{move[3]}"]
            elif extruder_move_time == move[4]:
                cmds += [f"G1 X{new_x} Y{new_y} Z{new_z} E{-extruder_move} F{move[3]}"]
            else:
                split_point = self._get_move_split_point(initial_pos, [new_x, new_y, new_z], move[4], extruder_move_time)
                cmds += [f"G1 X{split_point[0]} Y{split_point[1]} Z{split_point[2]} E{-extruder_move} F{move[3]}"]
                cmds += [f"IFS_F24 PRUTOK={old_channel} WAIT=0"]
                cmds += [f"G1 X{new_x} Y{new_y} Z{new_z} F{move[3]}"]
                done_ifs_grab = True

            internal_pos = [new_x, new_y, new_z]

        if remaining_withdraw_duration > 0:
            extruder_move = remaining_withdraw_duration * (extruder_speed / 60)
            cmds += [f"G1 E{-extruder_move} F{extruder_speed}"]

        if not done_ifs_grab:
            cmds += [f"IFS_F24 PRUTOK={old_channel} WAIT=0"]

    def _get_move_split_point(self, initial_pos, new_pos, move_duration, split_duration):
        factor = split_duration / move_duration
        result = []
        for i in range(3):
            result += [initial_pos[i] + ((new_pos[i] - initial_pos[i]) * split_duration / move_duration)]
        return result

    def _get_moves_to_cutter(self, current_pos):
        result = []
        relative_to_center_x = current_pos[0] - self.x_center
        relative_to_center_y = current_pos[1] - self.y_center
        closer_on_x = abs(relative_to_center_x) > abs(relative_to_center_y)

        kinematics = self.toolhead.get_kinematics()

        z_travel_speed = min(kinematics.max_z_velocity, self.z_travel_move_speed)

        if current_pos.z < self.z_max:
            result += [[None, None, min(current_pos.z + self.swap_z_movement, max(current_pos.z, self.z_max)), z_travel_speed]]

        travel_speed = self.toolhead.max_velocity

        if closer_on_x or relative_to_center_y > 0:
            if not closer_on_x:
                result += [[None, self.y_back, None, travel_speed]]
            if relative_to_center_x > 0:
                result += [[self.x_right, None, None, travel_speed]]
            else:
                result += [[self.x_left, None, None, travel_speed]]

        result += [[None, self.y_front, None, travel_speed]]
        result += [[self.cut_prepare_x, None, None, travel_speed]]
        result += [[None, self.cut_prepare_y, None, min(self.cut_prepare_y_travel_move_speed, travel_speed)]]

        return self._calculate_move_durations(current_pos, result)

    def _calculate_move_durations(self, current_pos, moveset):
        result = []
        for move in moveset:
            new_pos = current_pos
            distance_sqr = 0
            for i in range(3):
                if move[i] is not None:
                    distance_sqr += (current_pos[i] - move[i]) ** 2
                    current_pos = move[i]
            distance = math.sqrt(distance_sqr)
            result += [move + [distance / (move[3] / 60)]]
            current_pos = new_pos
        return result

    def _qsf_move_from_cutter_to_trash(self, cmds):
        # We don't need to adjust speed here, we can just let Klipper cap it as we aren't synchronizing it to anything.
        self.info(f'Moving to trash chute', cmds)
        cmds += [f"G1 X{self.cut_prepare_x} F{self.cut_move_speed}"]
        cmds += [f"G1 Y{self.y_front} F{self.travel_move_speed}"]
        cmds += [f"G1 X{self.x_left} F{self.travel_move_speed}"]
        cmds += [f"G1 Y{self.y_back} F{self.travel_move_speed}"]
        cmds += [f"G1 X{self.trash_x} F{self.travel_move_speed}"]
        cmds += [f"G1 Y{self.trash_y} F{self.enter_trash_move_speed}"]

    def _qsf_return_to_print(self, initial_pos, cmds):
        # Ditto.
        self.info(f'Returning to print', cmds)
        relative_to_center_x = current_pos[0] - self.x_center
        relative_to_center_y = current_pos[1] - self.y_center
        closer_on_x = abs(relative_to_center_x) > abs(relative_to_center_y)

        cmds += [f"G1 X{self.cut_prepare_x} F{self.cut_move_speed}"]
        cmds += [f"G1 Y{self.y_front} F{self.travel_move_speed}"]

        if closer_on_x or relative_to_center_y > 0:
            if relative_to_center_x <= 0:
                cmds += ["G1 X{self.x_left} F{self.travel_move_speed}"]
            else:
                cmds += ["G1 X{self.x_right} F{self.travel_move_speed}"]

            if closer_on_x:
                cmds += ["G1 Y{initial_pos[1]} F{self.travel_move_speed}"]
            else:
                cmds += ["G1 Y{self.y_back} F{self.travel_move_speed}"]

        cmds += ["G1 X{initial_pos[0]} F{self.travel_move_speed}"]

        if not closer_on_x:
            cmds += ["G1 Y{initial_pos[1]} F{self.travel_move_speed}"]

        cmds += ["G1 Z{initial_pos[2]} F{self.z_travel_move_speed}"]


    def _qsf_unload_old_filament(self, old_channel, old_filament_info, cmds):
        self.info(f'Unloading channel {old_channel}', cmds)

        unload_distance = old_filament_info['filament_unload_after_cutting'] + old_filament_info['nozzle_cleaning_length']

        speed_factor = float(self.gcode_move.get_status(self.reactor.monotonic()).get('speed_factor', 1.0))

        cmds += [f"G1 E{-unload_distance} F{old_filament_info['filament_extruder_speed']}"]
        cmds += [f"IFS_F11 PRUTOK={old_channel} LEN={unload_distance} SPEED={old_filament_info['filament_extruder_speed'] * speed_factor} WAIT=0"]
        cmds += ["_QS_WAIT_IFS_IDLE"]

        cmds += [f"IFS_F11 PRUTOK={old_channel} LEN={old_filament_info['filament_unload_into_tube']} SPEED={old_filament_info['filament_ifs_speed'] * speed_factor}"]

    def _qsf_load_new_filament(self, old_filament_info, new_channel, new_filament_info, cmds):
        self.info(f'Loading channel {new_channel}', cmds)

        speed_factor = float(self.gcode_move.get_status(self.reactor.monotonic()).get('speed_factor', 1.0))

        cmds += [f"IFS_F24 PRUTOK={new_channel} WAIT=1"]
        cmds += [f"IFS_F10 PRUTOK={new_channel} LEN={new_filament_info['filament_tube_length']} SPEED={new_filament_info['filament_ifs_speed'] * speed_factor} CHECK=1"]
        cmds += ["M400"]

        cmds += [f"M104 S{new_filament_info['temp']}"]

        insert_length = 12 + old_filament_info['filament_unload_before_cutting']
        cmds += [f"IFS_F10 PRUTOK={new_channel} LEN={insert_length} SPEED={new_filament_info['filament_extruder_speed'] * speed_factor} WAIT=0 CHECK=0"]
        cmds += [f"G1 E{insert_length} F{new_filament_info['filament_extruder_speed']}"]
        cmds += ["M400"]

        cmds += ["_QS_WAIT_IFS_IDLE"]
        cmds += [f"IFS_F39 PRUTOK={new_channel} WAIT=0"]
        cmds += [f"_SET_EXTRUDER_SLOT SLOT={new_channel}"]
        cmds += [f"SDCARD_SET_CHANNEL CHANNEL={new_channel}"]
        cmds += ["SDCARD_ENABLE_FFM ENABLE=1"]
        cmds += ["M400"]

    def _qsf_nopoop_wipe(self, cmds):
        self.info(f'Performing nopoop wipe', cmds)
        cmds += ["SAVE_GCODE_STATE NAME=nopoop_flatten"]
        cmds += ["G91"]
        cmds += ["G1 X0.75 Y0.75 F600"]
        cmds += ["G1 X-0.75 Y0.75"]
        cmds += ["G1 X-1.5 Y-1.5"]
        cmds += ["G1 X1.5 Y-1.5"]
        cmds += ["G1 X1.5 Y1.5"]
        cmds += ["G1 X-1.5 Y1.5"]
        cmds += ["G1 X-1.5 Y-1.5"]
        cmds += ["G1 X0.75 Y-0.75"]
        cmds += ["G1 X0.75 Y0.75"]
        cmds += ["RESTORE_GCODE_STATE NAME=nopoop_flatten"]

    def _qs_get_filament_mapping(self, channel):
        with open('/usr/data/config/mod_data/file.json', 'r') as f:
            mapping = json.load(f)

        if channel >= len(mapping):
            raise self.printer.command_error(f"Error: CHANNEL {channel} is out of range (max {len(mapping)-1})")
            return

        return mapping[channel]

def load_config(config):
    return QuickSwap(config)