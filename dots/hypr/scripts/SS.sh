#!/usr/bin/env bash

DIR="$HOME/Pictures/Screenshots"
TMP="/tmp/satty-$(date +%s).png"
OUT="$DIR/$(date +%Y-%m-%d_%H-%M-%S).png"

mkdir -p "$DIR"

# Take screenshot to temp file
grim -g "$(slurp)" "$TMP" || exit 1

# Open satty with real clipboard support
satty \
  --filename "$TMP" \
  --output-filename "$OUT" \
  --copy-command "wl-copy --type image/png" \
  --right-click-copy \
  --early-exit
