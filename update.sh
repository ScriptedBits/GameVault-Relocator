#!/bin/bash

# Usage: ./update.sh <new_app_path> <target_app_path>
# Example: ./update.sh /tmp/GameVault-Relocator-v2.1.3 /usr/local/bin/GameVault-Relocator

NEW_APP="$1"
TARGET_APP="$2"

if [ -z "$NEW_APP" ] || [ -z "$TARGET_APP" ]; then
  echo "Usage: $0 <new_app_path> <target_app_path>"
  exit 1
fi

APP_NAME=$(basename "$TARGET_APP")

echo "[INFO] Waiting for $APP_NAME to close..."

# Wait until process is gone (max 30s)
for i in {1..30}; do
  if ! pgrep -f "$APP_NAME" > /dev/null; then
    echo "[INFO] $APP_NAME has exited."
    break
  fi
  sleep 1
done

echo "[INFO] Replacing $TARGET_APP with $NEW_APP..."
if [ -f "$TARGET_APP" ]; then
  rm -f "$TARGET_APP" || { echo "[ERROR] Could not remove $TARGET_APP"; exit 1; }
fi

mv "$NEW_APP" "$TARGET_APP" || { echo "[ERROR] Move failed"; exit 1; }
chmod +x "$TARGET_APP"

echo "[INFO] Relaunching $APP_NAME..."
"$TARGET_APP" &

# Optional self-deletion
SCRIPT_PATH="$0"
if [ -f "$SCRIPT_PATH" ]; then
  echo "[INFO] Cleaning up update script..."
  rm -- "$SCRIPT_PATH"
fi

exit 0
