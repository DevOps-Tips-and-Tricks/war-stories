#!/usr/bin/env bash

LOG=/var/log/demo-app/access.log
exec 9>>"$LOG"

PAD=$(head -c 4096 /dev/zero | tr '\0' 'x')
while true; do
  printf '\n\n%(%Y-%m-%dT%H:%M:%S%z)T GET /health 200 %s\n' -1 "$PAD" >&9
  sleep 0.001
done
