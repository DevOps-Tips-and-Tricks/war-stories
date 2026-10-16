#!/usr/bin/env bash
# lab-setup.sh
set -euo pipefail
MOUNT=/var/log/demo-app
IMG=/root/demo-disk.img

mkdir -p "$MOUNT"
fallocate -l 64M "$IMG"
mkfs.ext4 -q -m 0 "$IMG"
mount -o loop "$IMG" "$MOUNT"

# [gotcha] hard stop if the mount didn't take — otherwise the writer fills the
# real root filesystem at ~5MB/s and this stops being a demo.
findmnt "$MOUNT" >/dev/null || { echo "FATAL: $MOUNT is not a separate mount"; exit 1; }
df -h "$MOUNT"
