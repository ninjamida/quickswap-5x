QuickSwap is a plugin to speed up color changes on AD5X printers running Z-Mod.

Compatibility requirements:
- Native screen must be disabled. Any alternative is fine.
- Must not be using Bambufy or LessWaste plugins.
- Must use either Nopoop or Slicer-Controlled Poop.
- To avoid doubt; compatible with IFS Jacker.

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

Caveats:
If a filament runs out mid-print such that there is still filament in the tube,
but the end of it has passed through the IFS, then Z-Mod has a behavior to purge
the rest of the filament at the next color change (to avoid blocking the tube).
In this situation, QuickSwap will not activate for that color change, and the
printer will instead fall back to Z-Mod's standard color change routine.

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