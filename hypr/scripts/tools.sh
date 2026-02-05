#!/usr/bin/env bash

if pgrep -x rofi >/dev/null; then
  pkill rofi
  exit 0
fi

VIDEO_DIR="$HOME/Videos"
mkdir -p "$VIDEO_DIR"

DEFAULT_NAME="recording-$(date +%F-%T)"

# Auto-focus Stop if already recording
if pgrep wf-recorder > /dev/null; then
  DEFAULT_ROW=4
else
  DEFAULT_ROW=0
fi

# Define options with icons
options=(
    " 󰄀    Region Screenshot"
    "     Screen Recording (no audio)"
    "     Screen Recording (Desktop sound only)"
    "     Screen Recording (Mic + Desktop sound)"
    " ⏹   Stop recording"
    "     Color Picker"
)

# Show menu
choice=$(printf '%s\n' "${options[@]}" | \
rofi -dmenu \
  -no-config \
  -selected-row "$DEFAULT_ROW" \
  -theme ~/.config/rofi/sl.rasi)

# Exit if no choice is made (e.g., pressing Esc)
[[ -z "$choice" ]] && exit 1

ask_filename() {
  name=$(rofi -dmenu \
    -p "Recording name" \
    -theme ~/.config/rofi/record-input.rasi)

  [ -z "$name" ] && name="recording_$(date +%Y-%m-%d_%H-%M-%S)"
  echo "$VIDEO_DIR/$name.mp4"
}


# Add a small delay to let Rofi disappear
sleep 0.2

# Execute corresponding command
case "$choice" in
    " 󰄀    Region Screenshot")
        grim -g "$(slurp)" - | satty --early-exit --action-on-enter save-to-file --right-click-copy --filename - --output-filename ~/Pictures/screenshots/$(date '+%y-%d:%m-%H:%M').png
        ;;
    "     Screen Recording (no audio)")
         FILE=$(ask_filename)
         pkill wf-recorder
         wf-recorder -f "$FILE" &
         notify-send "Screen Recording" "Recording VIDEO ONLY"
        ;;
    "     Screen Recording (Desktop sound only)")
          FILE=$(ask_filename)
          pkill wf-recorder
          wf-recorder --audio=@DEFAULT_SINK@.monitor -f "$FILE" &
          notify-send "Screen Recording" "Recording DESKTOP AUDIO"
          ;;
    "     Screen Recording (Mic + Desktop sound)")
          FILE=$(ask_filename)
          pkill wf-recorder

          pactl load-module module-null-sink sink_name=RecordMix >/dev/null
          pactl load-module module-loopback source=@DEFAULT_SOURCE@ sink=RecordMix >/dev/null
          pactl load-module module-loopback source=@DEFAULT_SINK@.monitor sink=RecordMix >/dev/null

          wf-recorder --audio=RecordMix.monitor -f "$FILE" &
          notify-send "Screen Recording" "Recording MIC + DESKTOP"
          ;;
    " ⏹   Stop recording")
            pkill wf-recorder
            notify-send "Screen Recording" "Recording stopped"
            ;;
    "     Color Picker")
        hyprpicker -a
        ;;
    *)
        exit 1
        ;;
esac
