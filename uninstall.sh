#!/bin/sh

source /opt/config/mod/.shell/0.sh

SOURCE_DIR="${MOD_CONF}/mod_data/plugins/quickswap"
TARGET_DIRS="/usr/data/zmod/klipper/klippy/extras ${KLIPPER_DIR}/klippy/extras"

for file in "$SOURCE_DIR"/*.py; do
    [ -e "$file" ] || continue
    
    filename=$(basename "$file")

    for target in $TARGET_DIRS; do
        target_path="$target/$filename"

        if [ -L "$target_path" ]; then
            rm "$target_path"
        fi
    done
done

echo "QuickSwap plugin uninstalled"
echo "REBOOT" >/tmp/printer
