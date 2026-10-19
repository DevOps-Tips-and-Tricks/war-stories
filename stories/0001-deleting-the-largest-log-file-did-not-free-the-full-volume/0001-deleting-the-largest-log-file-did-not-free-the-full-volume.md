---
id: "0001"
title: Deleting the largest log file did not free the full volume
concept: A deleted file with an open descriptor still owns its blocks
stack: [linux, kubernetes, mongodb, logrotate]
severity: sev3
detection: manual
time_to_detect: 15m
time_to_resolve: 50m
root_cause_category: capacity
blast_radius: single-service
contributed_by: "@maintainer"
date: "2026-08"
---

> **Sources.** Everything above the Symptom section has been run in the lab.
> The incident sections combine the maintainer's account of the incident with
> Kubernetes object metadata and a read-only inspection of the pods two months
> later. Exact times of the responders' actions were not recorded.

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
# 1. a 128M filesystem so the fill is watchable
mkdir -p /var/log/demo-app
fallocate -l 128M /root/demo-disk.img
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

One of the three pods of a MongoDB replica set entered `CrashLoopBackOff`. The
replica set ran on a non-production Kubernetes cluster under the Percona Server
for MongoDB operator, one pod per member, each member with its own 15Gi
persistent volume.

The other two members stayed up and kept a primary. The cluster was degraded,
not down, and the applications kept working. That narrowed the problem to one
pod and whatever belonged to it alone — its node, its container, or its volume.

`df` inside the pod reported the data volume at 100%.

## Timeline

Wall-clock UTC where a timestamp survived in Kubernetes object metadata.
The responders' own actions were not timed; they are marked `--:--` and listed
in the order they happened.

- `--:--` — One member pod enters `CrashLoopBackOff`. The other two stay up.
- `--:--` — We delete the pod. The StatefulSet recreates it on the same volume,
  and the crash loop resumes.
- `--:--` — `df` inside the pod shows the data volume at 100%.
- `--:--` — `du -h -d 1` over the data directory looks normal. The same over the
  log directory finds one very large file, `mongod.log`.
- `--:--` — We delete `mongod.log` with `rm`. `df` still reports 100%.
- `09:48` — To stop the bleeding, we raise the requested volume size in the
  database's custom resource from 15Gi to 22Gi. The operator grows the data
  volume of all three members, not only the crashing one.
- `09:49` — The kubelet finishes the online filesystem resize on members 0
  and 1.
- `09:52` — The last edit to the custom resource that day, from an interactive
  Kubernetes GUI client. One second later the operator recreates the
  StatefulSet, which is how it applies a new volume claim template.
- `10:10` — The filesystem resize finishes on member 2.
- `--:--` — We restart the crashing pod. It comes up and rejoins the replica set.

## What we thought it was

**A pod restart would clear it.** A crash loop usually means bad state inside
the container — a stuck lock file, a corrupt cache, a failed start — and
deleting the pod throws that state away. It is the cheapest thing to try and
it often works. Here it could not: the pod is disposable, the volume is not.
The StatefulSet gave the new pod the same full volume, and it crashed the same
way. A full disk is exactly the kind of state a pod restart does not touch.

**There was no log rotation, so the log simply grew.** In Kubernetes,
applications normally write to stdout and the kubelet rotates container logs.
A 15Gi-filling log file on a persistent volume looked like something nobody had
set up rotation for. That was wrong. The pod had a `logrotate` sidecar container,
and `mongod` rotates its own log on command. The belief mattered because it
pointed the investigation at "nobody rotates this" instead of "rotation exists
and still let one file grow this large", which is the question with the answer.

**Deleting the biggest file would give the space back.** `du` named the file, it
was the largest thing on the volume, and removing it is the obvious move. `df`
did not move. At that point we stopped investigating and started mitigating:
grow the volume, restart the pod. The pod came back, so we never learned why
the deletion freed nothing.

That unchanged `df` was the observation that should have stopped us. A file
removal that does not change `df` means either something else on the volume is
just as large, or a process still holds the removed file open. Both are
checkable in a minute — `du` again, then `ls -l /proc/*/fd | grep deleted` in
every container of the pod — and both answers are destroyed by the restart that
fixes the outage.

## Actual root cause

The volume filled because the pod's logs and its data shared one 15Gi disk,
and the logs grew faster than anything checked them.

Each member pod of the operator ran three containers, all mounting the same
persistent volume at `/data/db`:

| Container | Role | Writes to |
|---|---|---|
| `mongod` | The database | `/data/db/logs/mongod.log` |
| `logs` | fluent-bit: tails `mongod.log`, writes it to stdout **and** to a second full copy | `/data/db/logs/mongod.full.log` |
| `logrotate` | Runs `logrotate` from a cron scheduler | Rotates the log files in `/data/db/logs` |

Four things combined:

- **We had raised `mongod`'s log verbosity.** At higher verbosity `mongod` logs
  per operation, not per event. For scale, the same member at default verbosity
  writes about 260 MB of `mongod.log` a day.
- **Every line was stored twice.** fluent-bit wrote a full copy of `mongod.log`
  next to it on the same volume.
- **Size was checked only when the rotation job ran.** The rotation rule had a
  `maxsize 100M`, but `logrotate` evaluates it only when the scheduler runs it —
  once a day in the image inspected later. Between runs a log can grow without
  limit. A size cap is a rate limit only if it is checked faster than the log
  can grow.
- **Logs and data shared the volume.** When the logs filled it, `mongod` could
  no longer write its data files, exited, and was restarted into the same full
  disk.

The logs path in the custom resource was a trap of its own. It set
`systemLog.path: /var/log/mongodb/mongod.log`, but that directory did not exist
in the container: the operator's entrypoint overrode the path to
`/data/db/logs/mongod.log`. The configuration a responder reads is not the one
the process runs.

Why the `rm` freed nothing is **not established**. Two explanations fit, and
nobody captured the evidence that would separate them:

- **The duplicate.** fluent-bit's full copy of the same log was still on the
  volume, roughly as large. `df` and `du` would both have shown the volume
  nearly full.
- **A process still held the deleted file.** fluent-bit tails `mongod.log`, so
  it had the file open. `CrashLoopBackOff` restarts only the container that
  fails; the sidecars keep running with their descriptors. If fluent-bit had
  not yet released the deleted file, its blocks stayed allocated — the general
  problem above — and `df` would have stayed at 100% while `du` dropped.

Kubernetes made the second case harder to see in two ways:

- **A shared volume is not a shared process namespace.** The three containers
  shared `/data/db` but not a PID namespace, so `ls -l /proc/*/fd` from
  `kubectl exec` into one container cannot see another container's
  descriptors. The check has to run in every container, or from the node.
- **The crashing container is not necessarily the holder.** Kubernetes restarts
  whatever exits. A sidecar that holds space is never restarted, so a pod can
  keep crashing on a disk that one sidecar restart would free.

All images ran floating `:main` development tags. The rotation configuration
changed after the incident: an inspection in September found one rule covering
`/data/db/logs/*.log` that renamed both files, and one in October found
`copytruncate` for fluent-bit's copy and `mongod.log` left to `mongod`'s own
rotation. The old rule also collided with `mongod`: it renamed `mongod.log`, then
asked `mongod` to rotate a file that was no longer there, which `mongod` logged
as `FileRenameFailed` and recovered from by creating a new one.

## Fix

**Stop the bleeding.** We grew the volumes from 15Gi to 22Gi and restarted the
crashing pod. That worked, and it is also why the root cause above has an
open question: restarting the pod closed every descriptor in every container,
so it would have freed a held file too. The fix removed the evidence along with
the problem.

**Durable**, in order of how much they reduce risk:

- **Treat verbosity as a capacity decision.** Raise it at runtime with
  `db.adminCommand({ setParameter: 1, logComponentVerbosity: … })`, which a
  restart resets, rather than in the configuration file, and set a time to
  revert it. The startup options inspected later no longer raise verbosity.
- **Give logs their own volume, or stop storing them twice.** Either a log
  problem cannot take the database's disk, or it fills it half as fast.
- **Check size more often than the log can outgrow the check.** Run the rotation
  job hourly with `maxsize`, so the cap bounds an hour of growth instead of a
  day.
- **One rotator per file.** Leave `mongod.log` to `mongod`'s own `logRotate`, and
  rotate fluent-bit's copy with `copytruncate`, which keeps the inode so a
  writer that is never told about the rotation keeps writing to the right file.
  The image inspected in October already does this.

## What would have prevented it

- **A free-space check before raising verbosity.** A runbook step: take the
  current log bytes per day from `ls -l` over the log directory, multiply by
  the expected verbosity factor and by the number of copies, and compare it
  with `df` free space over the time the setting will stay on. If it does not
  fit, raise it for a bounded window or move the logs first.
- **An alert on the rate of change of free space on the volume**, not a static
  threshold. `predict_linear(kubelet_volume_stats_available_bytes[1h], 4*3600) < 0`
  fires while there is still time to act. 40% to 80% in ten minutes is an
  incident; 85% for six months is a Tuesday.
- **A runbook step before any `rm` on a full volume:** record `df`, delete, record
  `df` again. If it did not move, run `ls -l /proc/*/fd | grep deleted` in every
  container of the pod — or `lsof -nP +L1` on the node — **before** restarting
  anything. The restart is the fix and also the end of the evidence.
- **An exported metric for deleted-but-open bytes**, run from cron on the node,
  where every container's processes are visible:

```bash
lsof -nP +L1 2>/dev/null \
  | awk '$4 ~ /^[0-9]+[rwu]/ {sum[$1]+=$7} END {for (c in sum)
      printf "node_deleted_open_bytes{command=\"%s\"} %d\n", c, sum[c]}'
```

The `$4` filter is load-bearing: without it this sums PostgreSQL's shared memory
segments, which are unlinked on purpose and permanently have a link count of
zero, and reports a phantom baseline that alerts immediately and never clears.
Only numbered descriptors (`9w`, `3r`, `12u`) are real open files.

## Generalizable lesson

When two tools disagree about the same number, neither is broken and the gap is
the finding. Ask what each one measures before deciding which to believe: one is
walking a namespace, the other is reading an allocator, and the difference
between those two answers is where the failure is hiding.

The corollary is that deleting something does not necessarily release it. Any
resource whose release depends on both an unlink and a close — file descriptors,
but also thin-provisioned block devices that need `discard` plumbed through, and
object stores with versioning — can be freed at one layer and still consumed at
another. A deletion that does not change the number you were trying to change is
not a dead end; it is the most specific clue you will get.

The second corollary is that the stop-the-bleeding step usually destroys the
evidence. A restart closes every descriptor, clears every cache and resets every
counter, which is why it works and why it explains nothing. Spend the minute
before it writing down the state the restart is about to erase.
