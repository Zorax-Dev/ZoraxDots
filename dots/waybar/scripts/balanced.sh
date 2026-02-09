#!/usr/bin/env bash

# Set power profile to balanced
powerprofilesctl set balanced


# Notification
notify-send "Power" \
  "Power plan: Balanced"
