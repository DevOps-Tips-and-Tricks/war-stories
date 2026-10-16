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

> **Draft — incident sections partly verified.** Everything above `## Symptom`
> has been run in the lab and is accurate. The incident sections below are
> rebuilt from Kubernetes object metadata and a read-only inspection of the
> pods, done about two months after the incident. What that evidence cannot
> show is marked `TODO(maintainer)` — including `severity`, `detection` and
> both durations in the front matter — and must come from the maintainer's own
> memory of the incident before this entry is published.

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

A MongoDB pod on a non-production Kubernetes cluster entered
`CrashLoopBackOff`. The database was a three-member replica set run by an
operator, one pod per member, each with its own persistent volume. `df` on the
pod's data volume reported it full.

**TODO(maintainer): what `mongod` logged on each restart (the exact wording, if
any of it survives), whether one member or all three were looping, and — the
part that narrows the search fastest — what was still working: whether the
other members stayed up and kept a primary, whether the applications could
still read and write, whether the node stayed `Ready`.**

## Timeline

Wall-clock UTC. The only timestamps that survived are in Kubernetes object
metadata, and `managedFields` keeps only the last write per writer, so this is
the end of the incident, not its start. Linking these entries to the incident
is an inference: they are the only volume resize on record for the database.
**TODO(maintainer): confirm that this is the right day, and add the first
report, the first thing checked, each hypothesis and when it was dropped, and
the moment the deleted-but-open file was found.**

- `??:??` — **TODO(maintainer):** first alert or report.
- `09:48` — The requested volume size in the database's custom resource is
  raised, and the operator starts to grow the data volume of all three
  members, not only the one that was crashing.
- `09:49` — The kubelet finishes the online filesystem resize on members 0
  and 1.
- `09:52` — The last edit to the custom resource that day. It came from an
  interactive Kubernetes GUI client, not from a pipeline. One second later the
  operator recreates the StatefulSet, which is how it applies a new volume
  claim template.
- `10:10` — The filesystem resize finishes on member 2.
- `??:??` — **TODO(maintainer):** the pod leaves `CrashLoopBackOff`, and what
  was done immediately before it did.

The volumes ended at 22Gi. That odd size suggests a small emergency bump,
probably from 20Gi, but the old size is not recorded anywhere that survived.

## What we thought it was

**TODO(maintainer): the hypotheses chased and discarded, and why each was
reasonable given what was visible at the time.** This is the section the entry
exists for, and it is the one section that cannot be reconstructed from the
system afterwards. The metadata shows what was done, not what anybody believed
while doing it.

Prompts, from what the metadata does show:

- Growing all three volumes treats the problem as the database outgrowing its
  disk. Was that the first theory? What made it look right — and did the resize
  alone stop the crash loop?
- The earlier draft of this entry blamed "the operator's own logging". The
  operator's controller writes nothing to the data volume; the log files there
  belong to sidecar containers in the database pod. Was the operator a theory on
  the day, or only in hindsight?
- When did somebody first run `du` next to `df`, and what made them do it?

Close with the observation that should have redirected the investigation
sooner. The candidate to check against memory: `du` on the volume showing far
less than the pod's own `df`, which was visible before anything was restarted.

## Actual root cause

Space on the data volume was held by a log file that had been rotated and then
deleted while a process still had it open. The general problem above is the
mechanism. What made this pod prone to it was its layout.

Each member pod of the Percona Server for MongoDB operator ran three containers,
and all three mounted the same persistent volume at `/data/db`:

| Container | Role | Writes to |
|---|---|---|
| `mongod` | The database | `/data/db/logs/mongod.log` |
| `logs` | fluent-bit: tails `mongod.log`, writes it to stdout **and** to a second full copy | `/data/db/logs/mongod.full.log` |
| `logrotate` | Runs `logrotate` from a cron-like scheduler | Rotates `/data/db/logs/*.log` |

There was no separate log volume, so logs and data competed for the same disk,
and every log line was stored twice. At inspection, logs made up 1.6–2.5G of the
2.2–3.1G used on each member.

The rotation configuration had four problems, each harmless alone:

- **It ran hourly, not daily.** The config said `daily`, but the scheduler was
  `go-cron "0 0 * * *"`, and `go-cron` takes a seconds field first. `0 0 * * *`
  therefore means minute 0 of every hour. With `maxsize 100M`, any file over
  100 MB was rotated at the next hour.
- **One glob, one signal, two writers.** `/data/db/logs/*.log` matched both
  `mongod.log` and fluent-bit's `mongod.full.log`, with `sharedscripts`. The
  `postrotate` script told `mongod` to reopen its log (`db.adminCommand({
  logRotate: 1 })`) and never told fluent-bit anything.
- **Two rotators on one file.** `mongod` rotates by renaming its own log, so the
  volume held both `mongod.log.2026-…T18-00-00` names from `mongod` and
  `mongod.log.1` names from `logrotate`. The `mongod` side of the `postrotate`
  failed in 2 of 5 recent runs with `MongoServerError: Log rotation failed due
  to one or more errors`, and nothing alerted on it.
- **The cleanup rule matched the wrong file.** `find … -name 'mongod.full.log'
  -mtime +7 -delete` matches the live file, not the rotated
  `mongod.full.log.N` copies.

A writer that was not told about a rename keeps writing to the renamed inode.
When `rotate 10` or the `find` rule later deletes that file, the directory entry
goes and the blocks stay: `df` full, `du` half empty.

**Which process held the file is not established.** Nobody captured `lsof` or
`/proc/*/fd` during the incident, and a scan of all three members two months
later found no deleted-but-open files. The crash loop itself narrows it down.
When `mongod` exits, the kernel closes its descriptors. If `mongod` had been the
only holder, the first crash would have released the space, and the next start
would have found room. A crash loop that keeps going needs a holder that
survives the crash. `CrashLoopBackOff` restarts only the container that failed;
the sidecars in the same pod keep running with their descriptors open. In this
pod, the long-lived process that follows `mongod.log` across rotations is
fluent-bit in the `logs` container. **TODO(maintainer): confirm or correct — did
restarting `mongod` alone ever bring the space back?**

All the images ran floating `:main` development tags, and the rotation
configuration above is the one inside the image at inspection. What ran on the
day may have differed.

Kubernetes made the mechanism harder to see in two ways:

- **A shared volume is not a shared process namespace.** The three containers
  shared `/data/db` but not a PID namespace, so `ls -l /proc/*/fd` run from
  `kubectl exec` into `mongod` cannot see fluent-bit's descriptors. The check
  has to run in every container, or from the node, where every process is
  visible.
- **The crashing container is not necessarily the culprit.** Kubernetes
  restarts the container that exits, which is the one showing the symptom. A
  sidecar that holds the space is never restarted, so the pod can crash-loop
  indefinitely on a disk that one sidecar restart would free.

## Fix

**TODO(maintainer): what was actually done on the day, and in what order.**
The metadata shows that all three volumes were grown and the StatefulSet was
recreated. It does not show whether any pod or container was restarted.

The distinction matters. Growing a volume does not reclaim blocks that a
deleted-but-open file owns. It buys headroom, and the held file keeps growing
into it. Restarting the holder closes the descriptor and frees the blocks at
once. `truncate -s 0 /proc/<pid>/fd/<n>` frees them with the process still
running. If the crash loop stopped at 09:48, the resize did it; if it stopped
later, look for the restart.

Durable, and not yet applied — the configuration inspected two months later
still had all four problems:

- Give each writer its own rotation rule and its own signal. For `mongod`, set
  `systemLog.logRotate: reopen` with `logAppend: true`, so that `logrotate`
  renames and `mongod` only reopens, and there is one rotator, not two. For
  fluent-bit's file output, use `copytruncate`, which keeps the inode and loses
  only what is written between the copy and the truncate.
- Write the schedule as `go-cron`'s six fields: `0 0 0 * * *` for daily.
- Point the cleanup rule at the rotated copies: `-name 'mongod.full.log.*'`.
- Drop the second full copy of the log, or move logs to their own volume so
  that a log problem cannot take the database's disk.

## What would have prevented it

An alert on deleted-but-open bytes, which almost nobody exports. As a
node_exporter textfile collector, run from cron on the node — not inside a pod,
where it would see only one container's processes:

```bash
lsof -nP +L1 2>/dev/null \
  | awk '$4 ~ /^[0-9]+[rwu]/ {sum[$1]+=$7} END {for (c in sum)
      printf "node_deleted_open_bytes{command=\"%s\"} %d\n", c, sum[c]}'
```

The `$4` filter is load-bearing: without it this sums PostgreSQL's shared memory
segments, which are unlinked on purpose and permanently have a link count of
zero, and reports a phantom baseline that alerts immediately and never clears.
Only numbered descriptors (`9w`, `3r`, `12u`) are real open files.

Neither alert would have fired here: no Prometheus scraped this cluster at all.
An alert rule is only as good as the scrape config under it, so the first check
is that the cluster appears as a target.

Three cheaper checks alongside it:

- Alert on the *rate of change* of `node_filesystem_avail_bytes` rather than a
  static threshold — 40% to 80% in ten minutes is an incident, 85% for six
  months is a Tuesday.
- Alert on the rotation job's own failures. `Log rotation failed` was already
  in the `logrotate` container's output, hourly, and nobody read it.
- Review every rotation rule with one question: for each file this glob
  matches, which process writes it, and does `postrotate` tell that process?
  Any file with a writer and no signal fails the review.

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

The second corollary is that the process that fails is not necessarily the
process that holds the resource. A supervisor restarts whatever exits, and the
thing that exits is the one that ran out. When a restart does not clear a
resource problem, stop asking why the crashing process fails and ask who else
is holding what it needs.
