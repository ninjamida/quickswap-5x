# QuickSwap

https://github.com/ninjamida/quickswap-5x

## Introduction
Quickswap is a plugin for Z-Mod on the Flashforge AD5X, for the purpose of achieving faster color / material changes.

QuickSwap uses multiple methods to achieve this:
1. QuickSwap provides macros to calibrate your IFS speed and unload distances, in order to spend less time inserting or withdrawing filament.
1. QuickSwap replaces Z-Mod's standard color change routine with a more efficient custom one, that in particular, performs some actions in parallel instead of sequentially where practical.

Under ideal circumstances, and excluding purge / priming, the combined effect of these calibrations and QuickSwap's can mean color changes taking as little as 30 seconds. Not bad for a single-nozzle printer!

## Compatibility Requirements
- Native screen disabled. Any alternative (Helix, Guppy, etc) is fine.
- Nopoop **or** Slicer-Controlled Poop.
- **NOT** compatible with Bambufy / LessWaste.
- Z-Mod 1.7.3-79 or higher recommended.
- Klipper 12 recommended; Quickswap has not been tested with Klipper 13.
- **Compatible** with IFS Jacker.

**WARNING:** After updating QuickSwap, you must reboot the printer (`REBOOT` macro, or power cycle).

## Recommended Z-Mod Settings
### user.cfg
*Do not use this setting on Z-Mod 1.7.3-78 or below.*
```
[zmod_ifs]
next_cmd_delay: 0.02
```
### filament.json, "default" section
- `filament_unload_before_cutting`: Setting to 20 recommended. (Not tested with flexible filaments.)
- `nozzle_cleaning_length`: Generally, this should be set to 23, minus your value for `filament_unload_after_cutting`. QuickSwap always uses a 1mm unload-after-cutting, then uses the total actual value of `filament_unload_after_cutting` and `nozzle_cleaning_length` to determine the combined extruder+IFS unload. If you find this value is not ideal, there is a calibration available.
- `filament_unload_into_tube`: This setting depends on which type of 4-way adapter you have, or any customizations to your tubing. Using the calibration is recommended.
- `filament_unload_after_drop`: If using Nopoop and you find that, after a switchover where the old filament has run out on the IFS (but not the extruder) you get blobbing on the prime tower, try increasing this value slightly. This will **not** help if such blobbing is occuring on *every* color switch; see the QuickSwap Settings section below for a fix for that.

## filament.json, filament-specific sections
- `filament_ifs_speed`: Use the calibration to determine an appropriate value. Significantly lower values will be necessary for flexible filaments.
- `filament_extruder_speed`: Calibrate (if you haven't already) your max volumetric speed in mm³ via OrcaSlicer's calibration, then multiply the value by 24.95 and round it to the nearest integer.

## QuickSwap Settings
Generally, the default settings should be sufficient. However, if for any reason you need to change them, the following configuration options (default values listed) are available via user.cfg:
```
[quickswap]
silent: 0
purge_step_length: 15
purge_finish_length: 15
ifs_flag_delay: 1.0
insert_base_distance: 17.0
slow_after_unload_length: True
```
- `silent`: Determines the level of console text output. `0` to display all output; `1` for start / finish messages only; `2` to hide all messages. This does not hide messages that come from Z-Mod / Klipper macros called during the course of QuickSwap's actions.
- `purge_step_length`: When a filament change occurs, and the old filament has run out at the IFS but not yet at the print head, so the remaining filament is purged; this determines how much filament is purged between checking if the filament runout sensor has been tripped yet.
- `purge_finish_length`: For aforementioned purges, this determines the extra purge length extruded once the filament runout sensor has been tripped.
- `ifs_flag_delay`: Sets the minimum time between sending an asynchronous IFS command, and accepting a response. Higher values may be needed if using Z-Mod 1.7.3-78 or earlier.
- `insert_base_distance`: Before accounting for `filament_unload_before_cutting`, this is the distance to insert new filament into the extruder after the head sensor is tripped during insert. Generally not important in Slicer-Controlled Poop mode, but needs to be accurately set for Nopoop mode. Increase it if the initial prime tower lines are thin / absent, decrease it if blobs are occurring on the prime tower.
- `slow_after_unload_length`: When enabled, filament insertions insert for `filament_unload_into_tube` length at full speed, then drop to `filament_extruder_speed` for the remaining distance. This can result in slower loading times the first time a given color is loaded during a print, but makes higher loading speeds much safer to use because they are operating for a fixed length instead of relying on sensors.

## Calibrations
QuickSwap includes several macros for calibrating some filament.json parameters, to help increase the speed of color changes. These can make a significant difference to your color change times.

QuickSwap does not automatically save the results of these calibrations. It will display them to you on the console, and it is up to you to enter them into filament.json.

Be advised that at some points during these tests, the filament's position when in/near the print head may be adjusted in small incremental steps instead of smooth movements. This is normal.

**Note:** If you use an IFS Jacker, it is recommended to disconnect it while performing the calibrations, and use a directly-connected IFS instead.

### IFS speed calibration (`filament_ifs_speed`)
**This test should be performed for each filament; or at least performed seperately for rigid and flexible filaments.**

The macro `QS_IFS_CALIBRATION_SPEED` tests inserting and removing a filament at increasingly fast speeds. The purpose of this is to determine how high you can set `filament_ifs_speed` without risk of losing accuracy on the insert / withdraw distances.

Please note that I have only personally tested speeds up to 3000. Using PLA filament, such speeds work without issue. It is likely that the IFS can go faster, but I have chosen not to push mine any further than that.

Before performing this test, ensure that:
- The extruder is not loaded.
- The filament you are intending to calibrate for is loaded in the IFS.

Parameters:
- `channel`: Which IFS channel to use for the test. Must be set.
- `min_speed`: The starting speed to test, in mm/min. Default is 300.
- `max_speed`: The maximum speed to test, in mm/min. Default is 3000.
- `speed_step`: How much to increase the speed between test runs. Default is 300.
- `test_length`: How far to unload and reload the filament in each test run, in mm. Default is 100.
- `tolerance`: How much deviation from the expected movement to accept, in mm. Default is 2.
- `tube_flex`: How much IFS movement is expected to simply result in flexing the filament tube, instead of actually moving the filament. If set at -1, QuickSwap will attempt to autodetect this. Default is -1.

Generally, only the `channel` parameter will need to be changed.

### Combined unload calibration (`nozzle_cleaning_length`)
**This test only needs to be performed once, and will cover all filament types. It may need to be redone if you replace your extruder, especially if switching between different versions of the extruder.**

The macro `QS_IFS_CALIBRATION_COMBINED_UNLOAD` tests how far a filament must be unloaded before the filament presence sensor will no longer detect it. In other words, it tests the distance needed for the combined extruder+IFS unload during a color change.

It is unlikely you will actually need to use this test; generally, `23 - filament_unload_after_cutting` should be a reliable value. However, it is here if you want it.

Before performing this test, ensure that:
- A **rigid** filament is loaded in the extruder.
- Your nozzle is at ambient temperature.
- Your chamber (if enclosed) is at room temperature, or at least **well** below your filament's softening point.

Parameters:
- `initial`: Will withdraw this distance in a single motion at the start. Default is 14. This should be set well below the expected value.
- `max`: The maximum value to test. Default is 25. The calibration is considered to have failed if the filament sensor is still detecting the filament after this length of withdrawal.
- `step`: How much to withdraw the filament between each check of the filament sensor. Default is 1.
- *All parameters are restricted to integer values only.*

Upon completing the calibration, new values will be suggested for both `nozzle_cleaning_length` and `filament_unload_into_tube`. This is calculated so that any reduction in `nozzle_cleaning_length` is offset by a corresponding increase in `filament_unload_into_tube`, in order to maintain the same total withdraw distance. The suggested value for `nozzle_cleaning_length` will take into account any `filament_unload_after_cutting` you have set; you do not need to manually adjust for that.

### Tube unload calibration (`filament_unload_into_tube`)
**This test only needs to be performed once, and will cover all filament types. It will need to be redone if you switch from the older 4-in-1 adapter to the newer one or vice versa, or add or modify a custom filament splitter setup.**

The macro `QS_IFS_CALIBRATION_TUBE_UNLOAD` tests how far a filament must be withdrawn from the print head into the tube, in order for another filament to be able to be loaded. In other words, it tests the distance needed for the IFS-alone unload during a color change. This is tested by inserting one filament ("Filament A"), withdrawing it a certain distance, then attempting to insert another filament ("Filament B"). If filament B is unable to insert, the test is repeated with increasing withdraw distances for filament A, until filament B can be inserted (or the maximum test length is reached).

This calibration test measures from the point at which the filament is no longer detected by the print head sensor - or in other words, it assumes that you will be using the value for `nozzle_cleaning_length` determined by the Combined Unload Calibration. If your `nozzle_cleaning_length` value is higher or lower than said calibration suggests, you will need to adjust the outcome of this calibration accordingly.

Before performing this test, ensure that:
- Two **rigid and non-abrasive** filaments are loaded in the IFS. It is recommended to unload all other IFS channels.
- No filament is loaded in the extruder.
- Your chamber (if enclosed) is at room temperature, or at least **well** below your filament's softening point.
- If your setup involves filament passing through multiple adapters (for example, an 8-way setup involving four 2-way adapters connected to the tubes of the stock 4-way adapter), make sure to use the two IFS channels that will "collide" at the earliest point. Using the same example, for such a setup, use two channels that go through the same 2-way adapter.
- If you are performing one or both of the other calibrations as well, do this one last.

The test will always use the first two non-empty channels on the IFS. The first non-empty channel will become filament A (ie: the one that is inserted as the block) and the second will become filament B (ie: the one that gets inserted to test if the path is still blocked).

Parameters:
- `initial`: How far to withdraw filament A on the first attempt.
- `max`: The maximum length to test withdrawing filament A.
- `step`: How much to increase filament A's withdrawal length on each subsequent attempt.
- *All parameters are restricted to integer values only.*

This test will generally be run twice. On the first run, use the default `step` value. If you are using a stock 4-way adapter, also use the default values for the other parameters. If not, adjust `initial` and `max` so that they are slightly either side of a known good value, or just set a large range.

When the first run is complete, the results will include suggested parameter values for a second test run.

I recommend not using the calculated value directly, but rather adding a small margin of error to it, on the order of 3 to 5 mm. Some custom multi-way adapters may benefit from a larger margin of error.

## Print speed comparisons
These test runs were performed on a relatively early version of QuickSwap (0.1.0), without performing the calibrations, instead just using my pre-existing filament.json values. Recommended settings that did not rely on calibrations (eg. `filament_unload_before_cutting`, `[zmod_ifs] -> next_cmd_delay`) were applied.

The print in question is included in both 3mf and gcode format in the "tests" subfolder. The test consists of a 25x25x3mm cube in one color, with a middle section consisting of a 15x15x3 cylinder in a second color; printed at 0.25mm layer heights, resulting in 11 color changes.

All reasonable efforts were made to keep the starting conditions the same, eg. chamber temperature, print head and bed position, motor status, pre-loaded filament, etc.

These values are intended to show the benefit of QuickSwap's custom color change process compared to Z-Mod's stock one, while using identical filament.json parameters. Running the various calibrations and adjusting filament.json accordingly will result in **very significant** further improvement to color change times.

### Slicer-Controlled Poop
- Without QuickSwap: 28m 15s
- With QuickSwap: 26m 53s
- Time saved: 1m 22s (~7.5s per color change)

### Nopoop
- Without QuickSwap: 28m 8s
- With QuickSwap: 26m 15s
- Time saved: 1m 53s (~10.3s per color change)

## Adding to Z-Mod's update manager
At the time of writing this, QuickSwap is not yet included in Z-Mod's plugin list. You can manually add it by copy-pasting the following into `mod_data/user.moonraker.conf':
```
[update_manager quickswap]
type: git_repo
channel: dev
path: /root/printer_data/config/mod_data/plugins/quickswap
origin: https://github.com/ninjamida/quickswap-5x.git
is_system_service: False
primary_branch: master
```