#!/bin/bash

SESSION="$TMUX"
SESSION_NAME=$(tmux display-message -p '#S')
SOCKET_PATH="/run/tmux-event.sock"

if [ -S "$SOCKET_PATH" ]; then
  echo "$SESSION_NAME" | socat - UNIX-CONNECT:$SOCKET_PATH
fi
