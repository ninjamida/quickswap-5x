QuickSwap is a plugin to speed up color changes on AD5X printers running Z-Mod.
It can be used with either Slicer-Controlled Poop or Nopoop. Nopoop is faster.


As it is still an early work-in-progress, QuickSwap has not yet been submitted
to Z-Mod's plugin list. You will need to add it manually to user.moonraker.conf
(in mod_data):

[update_manager quickswap]
type: git_repo
channel: dev
path: /root/printer_data/config/mod_data/plugins/quickswap
origin: https://github.com/ninjamida/quickswap-5x.git
is_system_service: False
primary_branch: master



WARNINGS:
- Filament runout switchover is not yet tested at all
- Only tested with Klipper 12
- Use at your own risk



Compatibility requirements:
- Native screen must be disabled. Any alternative is fine.
- Must not be using Bambufy or LessWaste plugins.
- Must use either Nopoop or Slicer-Controlled Poop.
- Z-Mod 1.7.3-79 or higher recommended.
- Klipper 12 recommended.

And to avoid doubt:
- YES, automatic switch on runout should work (untested), including in
  multicolor prints
- YES, compatible (tested) with IFS Jacker



How it works:
The main ways QuickSwap saves time on filament changes are:

a) Any unload-before-cut is performed in parallel with moving the print head to
   the cutter, instead of first doing the unload and then doing the movement
b) Where it makes sense to do so, IFS actions are also performed in parallel.
   In particular, the initial clamping of the old filament channel, and the
   release of the new filament channel at the end of the process.
c) Less unnecessary delays between actions.



For best results:

** In user.cfg **  (Z-Mod 1.7.3-79 or higher only!)
[zmod_ifs]
next_cmd_delay: 0.02

** In filament.json **  (All versions)
filament_unload_before_cutting: 20
nozzle_cleaning_length: 25 - [filament_unload_after_cutting]
filament_unload_into_tube: Depends on 4-in-1-adapter version. Set it so that the
                           filament when unloaded, sits just barely outside of
                           the adapter



Settings:
Add in user.cfg. Default values shown below.

[quickswap]
silent: 0                   # Change to 1 to hide most output text, or 2 to hide
                            # all output text except for errors.
purge_step_length: 15       # When purging a near-empty filament, purges this
                            # length between "is that everything?" checks.
purge_finish_length: 15     # When purging a near-empty filament, purges this
                            # length more after the head sensor reports empty.
ifs_flag_delay: 1.0         # Time after sending an async IFS command, before
                            # the command is assumed to have been received. No
                            # point setting it lower as the command won't
                            # physically complete fast enough for that to make a
                            # difference; but you may need to set it higher on
                            # Z-Mod 1.7.3-78 or below.
insert_base_distance: 15.0  # Base length to insert filament into the extruder,
                            # before filament_unload_before_cutting adjustment
                            # is applied. Only needs to be "perfect" if using
                            # nopoop.



Print speed comparisons:
I printed a 25x25x3mm cube, with a 15x15cm cylinder section in a second color.
The bed was pre-heated before starting the print, while the nozzle was not.
Starting conditions were kept identical (loaded filament, print head position,
etc) or at least within the same ballpark (chamber temperature).

This was printed with 0.25mm layer height, giving 11 color changes.

Tested with Z-Mod 1.7.3-78, but with the -79 version of zmod_ifs.py, and the
next_cmd_delay set to 0.02. This applies to the QuickSwap AND non-QuickSwap
tests.

The only slicer difference between the tests was the prime tower type and the
"Purge into prime tower" setting. Otherwise, the settings and model were the
same. In the case of the QuickSwap vs non-QuickSwap tests for the same settings,
the exact same gcode file was used.

-Slicer-Controlled Poop-
Print time without QuickSwap: 28m 15s
Print time with QuickSwap: 26m 53s
Time saved: 1m 22s (~7.5s per color change)

-Nopoop-
Print time without QuickSwap: 28m 8s
Print time with QuickSwap: 26m 15s
Time saved: 1m 53s (~10.3s per color change)