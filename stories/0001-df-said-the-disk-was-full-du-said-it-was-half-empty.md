---
id: "0001"
title: df said the disk was full, du said it was half empty
concept: A deleted file with an open descriptor still owns its blocks
stack: [linux, kubernetes, mongodb, logrotate]
severity: sev2
detection: alerting
time_to_detect: 30m
time_to_resolve: 2h
root_cause_category: capacity
blast_radius: single-service
contributed_by: "@maintainer"
---

> **Draft — incident sections not yet verified.** Everything above `## Symptom`
> has been run in the lab and is accurate. The incident narrative below is a
> scaffold: the fields marked `TODO(maintainer)` — including `severity`,
> `detection`, and both durations in the front matter — must come from the
> maintainer's own notes before this entry is published. Nothing here may be
> filled in from memory of how such incidents usually go.

## The general problem

A filename is not a file. A directory entry points at an inode, and the inode
owns the data blocks. Deleting a file removes the directory entry and decrements
the link count; the kernel frees the blocks only when the link count reaches
zero **and** the last open file descriptor is closed. Until that second
condition is met the data is unreachable and undeletable at the same time.

That is why two tools that both claim to measure disk usage can disagree by
gigabytes without either being wrong:

- `du` walks the directory tree and adds up what it finds. A file with no
  directory entry is not in any tree, so as far as `du` is concerned it does not
  exist.
- `df` walks nothing. It asks the filesystem how many blocks are allocated, and
  they are still allocated.

The gap between those two answers is created by any long-lived process holding a
descriptor to a file somebody else unlinked — which is exactly what log rotation
does when it renames a file and never tells the writer. The writer keeps the
inode it opened, and every byte it writes lands somewhere no directory listing
will ever show.

`stat` provides the third disagreement: a sparse file reports a large `Size` and
a small `Blocks`, because a file's length and its allocation are different
facts. The recurring question is not "how much space is used" but *what is this
tool actually measuring*.

## Reproduce it

A small loop-mounted filesystem, one writer holding a descriptor, and a
logrotate config that looks entirely reasonable. Root required; nothing touches
the real root filesystem.

```bash
# 1. a 64M filesystem so the fill is watchable
mkdir -p /var/log/demo-app
fallocate -l 64M /root/demo-disk.img
mkfs.ext4 -q -m 0 /root/demo-disk.img
mount -o loop /root/demo-disk.img /var/log/demo-app
findmnt /var/log/demo-app >/dev/null || { echo "FATAL: not a separate mount"; exit 1; }
```

The `findmnt` guard matters: if the mount silently failed, the next step fills
the real root filesystem.

```bash
# 2. a writer that opens the log once and holds the descriptor, like any daemon
cat >/usr/local/sbin/demo-hoarder.sh <<'EOF'
#!/usr/bin/env bash
LOG=/var/log/demo-app/access.log
exec 9>>"$LOG"          # opened ONCE — this is the whole point
PAD=$(head -c 49152 /dev/zero | tr '\0' 'x')
while true; do
  printf '%(%Y-%m-%dT%H:%M:%S%z)T GET /health 200 %s\n' -1 "$PAD" >&9
  sleep 0.02
done
EOF
chmod +x /usr/local/sbin/demo-hoarder.sh
/usr/local/sbin/demo-hoarder.sh & PID=$!
```

`exec 9>>` is the load-bearing line. Written as `printf ... >> "$LOG"` inside
the loop, the shell would reopen the path on every iteration and this entire
class of bug would be invisible. The bug lives in the long-lived descriptor.

```bash
# 3. rotation that renames the file and never tells the writer
cat >/etc/logrotate.d/demo-app <<'EOF'
/var/log/demo-app/access.log {
    size 20M
    rotate 1
    missingok
    create 0644 root root
}
EOF

logrotate -f /etc/logrotate.d/demo-app                    # first rotation
echo "marker" >> /var/log/demo-app/access.log
logrotate -f /etc/logrotate.d/demo-app                    # second rotation deletes the archive
```

Omit `notifempty`, which appears in almost every logrotate config on the
internet. After the first rotation the writer is still on the old inode, so the
new `access.log` sits at zero bytes and `notifempty` refuses to rotate it — the
second rotation never happens and the deleted state never appears.

```bash
# 4. the divergence
ls -alh /var/log/demo-app     # two small files; nothing large
du -sh  /var/log/demo-app     # frozen at 4.0K — nothing to walk to
df -h   /var/log/demo-app     # climbing to 100% and not stopping
ls -l /proc/$PID/fd/          # 9 -> '/var/log/demo-app/access.log.1 (deleted)'
```

A healthy run has `df` and `du` tracking each other. After step 3 they diverge
permanently, and the writer keeps running: when the filesystem fills it takes
`ENOSPC` and loops on, still `active`, writing nothing. A full disk did not kill
anything — it made every write fail quietly, which is how these incidents
survive for hours before anyone notices.

Finding it without knowing the answer, in increasing order of precision:

```bash
lsof +L1                                    # everything with link count 0 — noisy
lsof +L1 | grep deleted                     # what people type at 2am
lsof -a -nP +L1 /var/log/demo-app           # deleted AND on the full filesystem
ls -l /proc/$PID/fd/                        # ground truth; works with no lsof
```

The `-a` is the part worth knowing: `lsof` ORs its selection criteria by
default, so without it the last command means "deleted anywhere" *plus*
"everything on this mount" — a longer list than you started with.

Reclaim the space without restarting the writer, then confirm what did and did
not change:

```bash
truncate -s 0 /proc/$PID/fd/9
df -h /var/log/demo-app       # drops to near-zero immediately
ls -l /proc/$PID/fd/          # UNCHANGED — still 9 -> access.log.1 (deleted)
```

The unchanged descriptor is the success condition, not a stale reading:
`truncate` frees blocks, it does not touch the descriptor. If that entry had
changed, something would have been killed.

```bash
kill $PID; umount /var/log/demo-app
losetup -j /root/demo-disk.img | cut -d: -f1 | xargs -r losetup -d
rm -f /root/demo-disk.img /etc/logrotate.d/demo-app /usr/local/sbin/demo-hoarder.sh
```

## Symptom

A database pod entered `CrashLoopBackOff`. **TODO(maintainer): what the pod
logs said on each restart, what the operator reported, and — the part that
narrows the search fastest — what was still working. Which other pods on the
node were unaffected, whether reads were still being served, whether the node
itself stayed `Ready`.**

## Timeline

**TODO(maintainer): wall-clock or relative `HH:MM` entries from the night, in
the order things actually happened.** At minimum: first alert or first report,
the first thing checked, each hypothesis and when it was abandoned, the moment
the deleted-but-open file was found, mitigation, and full recovery. Keep the
original telling order rather than a tidy reconstruction.

## What we thought it was

**TODO(maintainer): the hypotheses chased and discarded, and why each was
reasonable given what was visible at the time.** This is the section the entry
exists for, and it is the one section that cannot be reconstructed from the
system afterwards — only from memory of the night.

Close with the observation that should have redirected the investigation
sooner. The candidate to check against the notes: `du` on the volume showing far
less than the pod's own `df`, which was visible before anything was restarted.

## Actual root cause

The volume filled with the operator's own logging, not the database's.
**TODO(maintainer): confirm which component held the descriptor after the file
was rotated or deleted, and on which filesystem — the pod's volume or the
node's `nodefs`.**

The mechanism is the one described above: a process holding a descriptor to an
unlinked file, so the space was allocated but invisible to every tool that walks
a directory tree. Kubernetes makes it worse in three specific ways, each worth
verifying against the notes before publication:

- **The PID namespace hides the descriptor.** `kubectl exec` into the container
  and `lsof` is not installed; from the node, the PID differs from the one
  inside the container. Reading `/proc/<host-pid>/fd` directly works, and does
  not need `nsenter` — only path resolution does.
- **`du` inside the container measures the wrong thing.** Depending on volume
  type, the space that matters is on the node's `nodefs`, which is invisible
  from inside the pod.
- **Operators log too, and nobody budgets for it.** The workload's logs get a
  dashboard. The controller's logs sit on a volume nobody watches.

## Fix

**TODO(maintainer): what was actually done on the night, and whether the pod was
restarted or the space reclaimed in place.** Both work; the distinction is the
interesting part. Restarting the writer closes the descriptor and the kernel
frees the blocks, at the cost of a resync or a cold cache. `truncate -s 0
/proc/<pid>/fd/<n>` frees the blocks with the process still running, and is
worth reaching for exactly when the restart costs something.

Durable: rotation must tell the writer it happened — `copytruncate`, which keeps
the inode and loses whatever is written between the copy and the truncate, or a
`postrotate` signal the process understands (`USR1` for nginx, `HUP` for
rsyslog), which has no race and loses nothing.

## What would have prevented it

An alert on deleted-but-open bytes, which almost nobody exports. As a
node_exporter textfile collector, run from cron:

```bash
lsof -nP +L1 2>/dev/null \
  | awk '$4 ~ /^[0-9]+[rwu]/ {sum[$1]+=$7} END {for (c in sum)
      printf "node_deleted_open_bytes{command=\"%s\"} %d\n", c, sum[c]}'
```

The `$4` filter is load-bearing: without it this sums PostgreSQL's shared memory
segments, which are unlinked on purpose and permanently have a link count of
zero, and reports a phantom baseline that alerts immediately and never clears.
Only numbered descriptors (`9w`, `3r`, `12u`) are real open files.

Alongside it, two cheaper checks: alert on the *rate of change* of
`node_filesystem_avail_bytes` rather than a static threshold — 40% to 80% in ten
minutes is an incident, 85% for six months is a Tuesday — and include operator
and sidecar log volumes in the rotation policy, not just the application's.

## Generalizable lesson

When two tools disagree about the same number, neither is broken and the gap is
the finding. Ask what each one measures before deciding which to believe: one is
walking a namespace, the other is reading an allocator, and the difference
between those two answers is where the failure is hiding.

The corollary is that deleting something does not necessarily release it. Any
resource whose release depends on both an unlink and a close — file descriptors,
but also thin-provisioned block devices that need `discard` plumbed through, and
object stores with versioning — can be freed at one layer and still consumed at
another. Fixing the layer you can see is not evidence that the space came back.
