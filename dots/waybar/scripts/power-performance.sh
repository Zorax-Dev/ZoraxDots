#!/usr/bin/env bash


# Set power profile to performance
powerprofilesctl set performance

# Notification
notify-send "Power" \
  "Power plan: Performance"
