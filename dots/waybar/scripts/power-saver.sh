#!/usr/bin/env bash

# Set power profile to balanced (power-saver behavior)
powerprofilesctl set power-saver

# Notification
notify-send "Power" \
  "Power plan: Power Saver"
