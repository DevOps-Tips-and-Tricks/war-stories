#!/usr/bin/env bash
# install.sh — puts the writer, its unit and the logrotate rule in place.
# Run after lab-setup.sh. Does not start the writer: that happens on camera,
# and only ever with `systemctl start demo-hoarder`, never ./demo-hoarder.sh,
# because the fd pane reads systemd's MainPID.
set -euo pipefail
cd "$(dirname "$0")"

install -m 0755 demo-hoarder.sh /usr/local/sbin/demo-hoarder.sh
[ "$(head -c2 /usr/local/sbin/demo-hoarder.sh | od -An -tx1 | tr -d " \n")" = 2321 ] \
  || { echo "FATAL: shebang is not at byte 0"; exit 1; }

install -m 0644 demo-hoarder.service /etc/systemd/system/demo-hoarder.service
systemctl daemon-reload

# logrotate skips a rule file that is group- or world-writable.
install -m 0644 -o root -g root logrotate-demo-app /etc/logrotate.d/demo-app
grep -q notifempty /etc/logrotate.d/demo-app && { echo "FATAL: remove notifempty"; exit 1; }

# Say which rule is live. Re-running this script puts the broken one back,
# which is easy to miss after installing logrotate-demo-app.fixed by hand.
if grep -q copytruncate /etc/logrotate.d/demo-app; then
  echo "logrotate: copytruncate (the fix) — writer keeps writing to access.log"
else
  echo "logrotate: create (the bug) — after rotation the writer follows its inode to access.log.1"
fi

echo "Installed. On camera: sudo systemctl start demo-hoarder"
