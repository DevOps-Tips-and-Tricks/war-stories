#!/usr/bin/env bash
# teardown.sh
tmux kill-session -t ep01 2>/dev/null || true
systemctl stop demo-hoarder 2>/dev/null || true
systemctl reset-failed demo-hoarder 2>/dev/null || true
rm -f /etc/systemd/system/demo-hoarder.service
systemctl daemon-reload
umount /var/log/demo-app 2>/dev/null || true
losetup -j /root/demo-disk.img | cut -d: -f1 | xargs -r losetup -d
rm -f /root/demo-disk.img
rm -f /etc/logrotate.d/demo-app /usr/local/sbin/demo-hoarder.sh
