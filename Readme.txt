QuickSwap is a plugin to speed up color changes on AD5X printers running Z-Mod.

Requirements:
- Z-Mod
- Nopoop or the Slicer-Controlled Poop profile
- NOT compatible with native screen
- NOT compatible with Bambufy / LessWaste

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

IFS Jacker compatibility:
QuickSwap is compatible with, and has been tested with, an IFS Jacker running
two IFSes. It works correctly for color swaps from one IFS to the other just as
it does with color swaps on the same IFS. QuickSwap does not, however, have any
special functionality to take advantage of the presence of multiple IFSes - like
core Z-Mod itself, it just treats the jacker as a single, large IFS.