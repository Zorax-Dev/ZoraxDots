#!/usr/bin/env bash

TARGET="$1"
ICON="$2"

DAEMON_MODE="$(powerprofilesctl get 2>/dev/null)"
CLASS=""

case "$TARGET" in
  performance)
    [ "$DAEMON_MODE" = "performance" ] && CLASS="active"
    ;;
  balanced)
    [ "$DAEMON_MODE" = "balanced" ] && CLASS="active"
    ;;
  powersaver)
    [ "$DAEMON_MODE" = "power-saver" ] && CLASS="active"
    ;;
esac

printf '{"text":"%s","class":"%s"}\n' "$ICON" "$CLASS"
