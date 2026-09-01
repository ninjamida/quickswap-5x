QuickSwap is a plugin to speed up color changes on AD5X printers running Z-Mod.

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
- Not yet tested with nopoop (only with slicer-controlled poop)
- Filament runout switchover is not yet tested
- Not yet tested *without* an IFS Jacker
- Not yet tested (and I likely won't test it myself) with Klipper 13
- Use at your own risk



Compatibility requirements:
- Native screen must be disabled. Any alternative is fine.
- Must not be using Bambufy or LessWaste plugins.
- Must use either Nopoop or Slicer-Controlled Poop.

Z-Mod version compatibility:
- [Future version with zmod_ifs.py improvements] - Recommended for best results
- Z-Mod 1.7.3 - Minimum if using Klipper 13
- Z-Mod 1.7.2 - Acceptable for Klipper 12
- Z-Mod 1.7.1 or earlier - Might work, untested
You can use it with older Z-Mod + Klipper 13, but you will need to create the
symlink in the "extras" dir to quickswap.py manually. Z-Mod 1.7.3 changes the
location of this dir, and the install script only supports the new location.

And to avoid doubt:
- YES, automatic switch on runout works, including in multicolor prints
- YES, compatible with IFS Jacker

For best results:
- Set filament_unload_before_cutting to 20
- Set nozzle_cleaning_length to 20
- Set filament_unload_into_tube to 90 (you can try reducing it - the filament
  should end up just barely inside the 4-in-1 adapter after being withdrawn)
- Experiment with filament_extruder_speed and filament_ifs_speed and see if you
  can push them higher for certain material types
- Tune your flush volumes
- Make use of purging to infill / etc to reduce poop or prime tower time

How it works:
The primary way QuickSwap saves time, is by performing the unload-before-cut and
the movement to the cutter at the same time, instead of sequentially. Aside from
this, almost the entire process is controlled by a Python script which cuts out
a lot of the "there for the sake of non-printing loading / unloading" stuff and
optimizes some of the timings. The end result is - especially when using unload
before cut - an optimized color change process.

To hide the console messages, add to user.cfg:
[quickswap]
silent: 2
# If you instead add silent: 1, you will get a message at the start and end of
# color changes, but no info during them.

Debug mode, add to user.cfg as follows. This will cause the generated GCode to
be written to a file, and not executed, with the default filament change gcode
being actually executed instead.
[quickswap]
debug: 1