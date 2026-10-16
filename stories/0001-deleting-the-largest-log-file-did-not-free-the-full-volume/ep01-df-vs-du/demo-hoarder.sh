#!/usr/bin/env bash
# demo-hoarder.sh — shebang MUST be byte 0, see below
LOG=/var/log/demo-app/access.log
exec 9>>"$LOG"          # open ONCE, hold the fd — this is the whole point

PAD=$(head -c 49152 /dev/zero | tr '\0' 'x')   # built once, not per iteration
while true; do
  printf '%(%Y-%m-%dT%H:%M:%S%z)T GET /health 200 %s\n' -1 "$PAD" >&9
  sleep 0.02
done
