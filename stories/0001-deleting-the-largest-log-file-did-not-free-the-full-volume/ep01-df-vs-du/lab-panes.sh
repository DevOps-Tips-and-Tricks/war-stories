#!/usr/bin/env bash
# lab-panes.sh
set -euo pipefail
S=ep01
MOUNT=/var/log/demo-app
UNIT=demo-hoarder

tmux kill-session -t "$S" 2>/dev/null || true
tmux new-session -d -s "$S" -x 240 -y 60

# tmux >= 3.1 takes -l 60%; older takes -p 60. Check `tmux -V` first.
tmux split-window -h -l 60% -t "$S":0.0     # 0 driver | 1 right column
tmux split-window -v -l 75% -t "$S":0.1     # 1 dir    | 2
tmux split-window -v -l 66% -t "$S":0.2     # 2 fds    | 3
tmux split-window -v -l 50% -t "$S":0.3     # 3 df     | 4 du

tmux set -t "$S" pane-border-status top
tmux set -t "$S" pane-border-format ' #{pane_title} '
tmux select-pane -t "$S":0.0 -T 'driver'
tmux select-pane -t "$S":0.1 -T 'directory contents'
tmux select-pane -t "$S":0.2 -T 'open file descriptors'
tmux select-pane -t "$S":0.3 -T 'df — filesystem'
tmux select-pane -t "$S":0.4 -T 'du — directory tree'

send() { tmux send-keys -t "$S":0."$1" -l "$2"; tmux send-keys -t "$S":0."$1" Enter; }

send 1 "watch -t -n1 -d 'ls -alh $MOUNT'"
send 2 "watch -t -n1 -d 'p=\$(systemctl show -p MainPID --value $UNIT); [ \"\$p\" != 0 ] && ls -l /proc/\$p/fd/ || echo \"(service not running)\"'"
send 3 "watch -t -n1 -d 'df -h $MOUNT'"
send 4 "watch -t -n1 -d 'du -sh $MOUNT'"

tmux select-pane -t "$S":0.0
tmux attach -t "$S"
