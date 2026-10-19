# Episode 01 — "df is lying (or is it du?)"

**Source entry:** `0001-deleting-the-largest-log-file-did-not-free-the-full-volume.md`
**Target length:** 14–16 min
**Format:** tmux, five panes, live, not pre-solved. One cut between Act 2 and Act 3.
**Lab files:** `ep01-df-vs-du/` next to this script — extracted from the blocks below. Edit both together.
**Explainer visual:** `0001-deleted-but-open-simulator.html` — Beat 2 only. No separate primer video.

> Everything below has been through the lab. Where something bit during rehearsal
> it's marked **[gotcha]** — those are the parts that look fine on paper and fail on
> camera.

---

## Layout

One concern per pane. Combining `du` and `ls` into a single pane made both harder to
read and made it ambiguous which tool was reporting what.

```
┌──────────────────────────┬─────────────────────────────────┐
│                          │  directory contents             │
│                          ├─────────────────────────────────┤
│  DRIVER                  │  open file descriptors          │
│  (where I type)          ├─────────────────────────────────┤
│                          │  df — the filesystem's answer   │
│                          ├─────────────────────────────────┤
│                          │  du — the directory's answer    │
└──────────────────────────┴─────────────────────────────────┘
```

```bash
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
```

**`watch -t` plus tmux pane titles, not `watch`'s own header.** In a narrow pane the
header truncates to `Every 2.0s: ls -...`, which labels nothing. `-t` drops it and the
tmux title carries the label at full width.

**[gotcha] `send-keys -l` for the command, then `Enter` separately.** Without `-l`,
tmux tries to parse each space-separated token as a key name and mangles the line.

**[gotcha] The fd command must be single-quoted so `$(...)` runs inside `watch`.**
This one is silent when you get it wrong. Written unquoted:

```bash
watch -d -n1 ls -alh /proc/$(systemctl show -p MainPID --value demo-hoarder)/fd/
```

your shell expands the substitution *once*, before `watch` ever starts, and bakes that
PID into the string. The pane keeps updating, keeps looking alive, and points at a
`/proc/<dead-pid>/` that stopped existing at the first restart. Confirm with
`ps aux | grep watch` — a literal number in the path means your shell ate it.

**[gotcha] `systemctl show -p MainPID`, never `pgrep -f demo-hoarder.sh`.** `pgrep -f`
matches full command lines, and the `sh -c` that `watch` spawns *contains the string*
`demo-hoarder.sh`. It matches itself, returns two PIDs, the pane breaks. (`pgrep -f
'[d]emo-hoarder'` also dodges it if you prefer.)

**Check `watch --help` on the box.** Newer procps wants `-d=permanent` for sticky
highlighting, older builds want `-d cumulative`. One errors out. Permanent is better
for Act 2 — changes accumulate instead of flashing once.

---

## The one-sentence promise (first 20 seconds)

> `df` says the disk is full. `du` says it's half empty. Neither is broken — they're
> answering two different questions, and the gap between them is where production
> outages live.

Do **not** open with "hi guys, welcome back to the channel."

---

## Act 1 — The lab (0:00–2:30)

Run `lab-panes.sh` first. The monitors are live and empty before anything exists, so
they fill up as you build — that's the visual, and it costs no extra screen time.

```bash
#!/usr/bin/env bash
# lab-setup.sh
set -euo pipefail
MOUNT=/var/log/demo-app
IMG=/root/demo-disk.img

mkdir -p "$MOUNT"
fallocate -l 128M "$IMG"
mkfs.ext4 -q -m 0 "$IMG"
mount -o loop "$IMG" "$MOUNT"

# [gotcha] hard stop if the mount didn't take — otherwise the writer fills the
# real root filesystem at ~5MB/s and this stops being a demo.
findmnt "$MOUNT" >/dev/null || { echo "FATAL: $MOUNT is not a separate mount"; exit 1; }
df -h "$MOUNT"
```

128M on purpose, so the fill is watchable. `-m 0` drops ext4's 5% root reserve so the
on-screen numbers add up the way viewers expect.

Point at the `df` pane — it just went from "No such file or directory" to 128M, 100%
free. You didn't run anything to show that.

The writer, standing in for any long-lived service that logs to a file:

```bash
#!/usr/bin/env bash
# demo-hoarder.sh — shebang MUST be byte 0, see below
LOG=/var/log/demo-app/access.log
exec 9>>"$LOG"          # open ONCE, hold the fd — this is the whole point

PAD=$(head -c 49152 /dev/zero | tr '\0' 'x')   # built once, not per iteration
while true; do
  printf '%(%Y-%m-%dT%H:%M:%S%z)T GET /health 200 %s\n' -1 "$PAD" >&9
  sleep 0.02
done
```

> **Say this out loud:** `exec 9>>` opens the file one time and keeps the descriptor
> for the life of the process. That is what every real daemon does. If you wrote
> `printf ... >> "$LOG"` inside the loop, the shell would reopen the path every
> iteration and this entire class of bug would be invisible. The bug lives in the
> long-lived descriptor.

**[gotcha] `printf '%(...)T'` instead of `$(date -Is)`.** Command substitution is
implemented with a pipe: bash forks, the child writes to it, the parent reads. So
`$(date)` makes fd 3 appear and disappear about fifty times a second, and it shows up
in your fd pane as a flickering `3 -> 'pipe:[1144486]'`. Distracting exactly when
you're pointing at fd 9. Bash's built-in time format needs no subprocess, so the pane
shows five stable descriptors and nothing else. Bash 4.2+.

Removing the fork also makes the loop much faster — retime the fill after switching.
`sleep 0.02` is a starting point; adjust until 128M takes 25–30 seconds.

**[gotcha] Shebang at byte 0.** If anything precedes `#!` — even a comment naming the
file — the kernel's script handler doesn't find `0x23 0x21`, refuses the exec, and
systemd reports `203/EXEC` with `Exec format error` (errno 8). Verify:

```bash
head -c2 /usr/local/sbin/demo-hoarder.sh | xxd    # expect 2321
chmod +x /usr/local/sbin/demo-hoarder.sh
```

```ini
# /etc/systemd/system/demo-hoarder.service
[Unit]
# I start/stop this a lot while recording. systemd has no inline comments:
# a comment after the value makes the line invalid and the default limit stays.
StartLimitIntervalSec=0

[Service]
ExecStart=/usr/local/sbin/demo-hoarder.sh
Restart=always
```

**[gotcha] `StartLimitIntervalSec=0`.** Default is 5 starts in 10 seconds, after which
systemd latches the unit failed and `systemctl start` silently does nothing until
`systemctl reset-failed`. Guaranteed to happen mid-take otherwise. Note it's a
`[Unit]` option — it moved from `[Service]` in systemd 229, and half the blog posts
still put it in the wrong section.

```bash
sudo systemctl daemon-reload && sudo systemctl start demo-hoarder
```

All four monitors come alive at once: the directory shows `access.log` growing, the fd
pane shows `9 -> access.log`, `df` climbs, `du` matches it. Let the audience see
`df` and `du` agreeing. **That agreement is what you're about to break.**

And the culprit, which looks entirely reasonable:

```
# /etc/logrotate.d/demo-app
/var/log/demo-app/access.log {
    size 20M
    rotate 1
    missingok
    create 0644 root root
}
```

*"Keep an eye on `create`. We'll come back to it."*

**[gotcha] No `notifempty`.** It's in every logrotate config on the internet and it
breaks this demo specifically. After the first rotation the writer is still on the old
inode, so the *new* `access.log` sits at zero bytes — and `notifempty` then refuses to
rotate it. The second rotation never happens, and the deleted state you're building
toward never appears. `logrotate -d -f <config>` does a dry run and prints its
reasoning if you want to show why.

---

## Act 2 — Break it and diagnose (2:30–9:00)

Structured by what the panes do, not by what you type.

### Beat 1 — first rotation: everything still looks fine

```bash
sudo logrotate -f /etc/logrotate.d/demo-app
```

**Directory pane:** `access.log` becomes `access.log.1`, a fresh empty `access.log`
appears, both highlighted. **fd pane:** descriptor 9 now points at `access.log.1` —
the process followed the rename without noticing, because it never had the name. It
had the inode.

`df` and `du` still agree. Say that out loud. This is the state most people would call
healthy, and it is already broken.

### Beat 2 — second rotation: the divergence

```bash
echo "$(date -Is) post-rotation marker" >> /var/log/demo-app/access.log
sudo logrotate -f /etc/logrotate.d/demo-app
```

The `echo` gives the new file a byte so the rotation is a real rotation rather than a
rotation of nothing. `rotate 1` keeps one archive, so `access.log.1` is deleted.

Four panes now disagree, all highlighted at once:

| pane | shows | why |
|---|---|---|
| directory | two small files, nothing large | the big one has no name |
| fd | `9 -> '.../access.log.1 (deleted)'` | descriptor still open, still writing |
| `df` | climbing, doesn't stop | blocks still allocated |
| `du` | frozen at 4.0K | nothing to walk to |

**This is the frame the episode exists for.** Point at each pane in turn. Then explain,
once, while the numbers keep moving:

> A filename is not a file. A filename is a directory entry pointing at an inode, and
> the inode owns the data blocks.
>
> `du` walks the tree and adds up what it finds. This file is in no directory, so as
> far as `du` is concerned it doesn't exist.
>
> `df` doesn't walk anything — it asks the filesystem how many blocks are allocated.
> They're still allocated.
>
> The kernel frees an inode when two things are both true: the link count hits zero
> **and** the last open descriptor closes. `unlink` did the first. The process is
> still holding the second. So the data is unreachable and undeletable at the same
> time.

Switch to `0001-deleted-but-open-simulator.html` for this explanation. It replaces the
inode primer video, so this is the first time the viewer sees *directory entry → inode →
data blocks*. The panes carry the motion; the simulator carries the concept.

- Open it full screen and press `P` before recording — presenter mode hides the step
  chips, buttons and brand line. Space or `→` advances, `←` goes back, `R` resets to
  step 1.
- Walk steps 1–4 (`start`, `rotate 1`, `ls -l`, `rotate 2`). They replay what the lab
  just did, slowly, with `nlink` and `open fds` visible — the two conditions the
  explanation above is about. Pause on step 4: `nlink 0`, `open fds 1`, orphan list
  active, `df` and `du` split.
- Steps 5–7 (`lsof +L1`, `truncate`, `stop`) are optional. Use step 6 in Beat 4 only if
  the live `df` pane doesn't read clearly on camera; the live terminal is the stronger
  proof.
- **[gotcha]** The simulator's numbers come from an earlier lab run (`/dev/loop5`,
  PID `474462`, `56M`). Your live panes will show a different loop device and PID. Don't
  point at those values in the simulator; point at `nlink`, `open fds` and the gauges.

Then switch back to tmux.

Then stop talking and let `df` reach 100%. It gets there on its own.

**When it does, the writer takes `ENOSPC` and keeps looping.** The service stays
`active (running)`, the descriptor stays open, all four panes hold their positions.
Worth one line: a full disk didn't kill anything here, it just made every write fail
silently — which is how these incidents survive for hours before anyone notices.

### Beat 3 — find it cold

The panes gave the answer away, so say so and show how you'd find it without them.
Three steps, each better than the last. **The refinement is the lesson — don't skip
to the good command.**

```bash
sudo lsof +L1
```

On a real box this is twenty lines of noise. Postgres shows up with `/dev/zero` and
`/SYSV000bc750` entries — shared memory segments, created and immediately unlinked on
purpose, so link count zero is their permanent normal state. `+L1` is working
correctly. **It found the pattern; the pattern isn't always the problem.**

```bash
sudo lsof +L1 | grep deleted
```

One line. This works because lsof only appends `(deleted)` to entries that still have
a path — shared memory doesn't get it. Show this one *because* it's what people
actually type at 2am. Then puncture it: you're grepping for a label lsof invented, not
for a property of the file. A file legitimately named `deleted.log` matches too.

```bash
sudo lsof -a -nP +L1 /var/log/demo-app
```

`df` already told you which filesystem is full, so scope the question to it. Postgres
is gone — not filtered out, just never asked about.

**The `-a` is the part worth teaching.** lsof ORs its selection criteria by default, so
without it you'd get "deleted files anywhere" *plus* "everything on this mount" — a
longer list than you started with. `-a` ANDs them. This surprises people who've used
lsof for years. `-nP` skips DNS and port-name lookups; on a busy box it's a large
speedup.

Reads as a sentence: *what's deleted-but-open, on the filesystem that's full.*

Then the fallback that always exists, even in a container with no lsof:

```bash
PID=$(systemctl show -p MainPID --value demo-hoarder)
sudo ls -l /proc/$PID/fd/
```

`/proc/<pid>/fd` is ground truth. Every tool for this is a wrapper around it. Remember
it — in Act 3 it's the only one left.

### Beat 4 — reclaim without dropping the service

```bash
sudo truncate -s 0 /proc/$PID/fd/9
```

**[gotcha] Include the `/9`.** `: > /proc/$PID/fd/` with a trailing slash and no
descriptor globs the directory and prints `0 1 2 255 9`. Harmless, but on camera it
looks like a command that did something.

**Don't narrate before running it.** Run it, then stop. The `df` pane drops from 100%
to near-zero in one highlighted tick and the `du` pane doesn't move. Let that land.

*Then* explain: that path resolves to the inode itself, so you truncated the real file
through the descriptor.

**Now point at the fd pane, which did not change.** This is the most important beat in
Act 2 and it looks like a bug:

> Descriptor 9 still says `access.log.1 (deleted)`. Nothing there moved. That's not
> the pane failing to update — that's the proof this worked.
>
> `truncate` frees blocks. It doesn't touch the descriptor. The fd still exists, still
> points at the same inode, and that inode still has zero links. The only thing that
> changed is the block count, and `/proc/<pid>/fd` doesn't display block counts —
> `df` does, which is why `df` moved and this didn't.
>
> If this entry *had* changed, I'd have killed something. An unchanged fd pane is the
> success condition.

That's the whole argument for `truncate` over a restart, and the pane makes it for you.

If you want the reclaim visible in that pane too, follow the descriptor to the inode:

```bash
watch -t -n1 -d 'p=$(systemctl show -p MainPID --value demo-hoarder); \
  ls -l /proc/$p/fd/; echo; stat -L /proc/$p/fd/9 | head -2'
```

`stat -L` dereferences, so you get `Size` and `Blocks` collapsing and then climbing
again as the writer resumes. Same pane, both facts: identity unchanged, contents reset.

Shorter form, which is what you'd actually type:

```bash
: > /proc/$PID/fd/9        # same effect; fails under `set -C`
```

**Don't skip the alternative.** Restarting the service also works, and in most shops
that's what gets done. The reason to reach for `truncate` is when a restart costs
something — replica resync, cache warm-up, in-flight requests. That distinction is the
difference between a trick and a judgment call.

### Beat 5 — the sparse-file wrinkle

Our fd was opened `>>` — `O_APPEND` — so the kernel seeks to end before every write and
truncation is clean.

Without `O_APPEND` the file offset survives the truncate. The next write lands at the
old offset and creates a hole. `stat` puts the contradiction on adjacent lines:

```bash
stat /var/log/demo-app/access.log
```

```
  Size: 41943040        Blocks: 8          IO Block: 4096   regular file
```

Forty megabytes, eight blocks. A third tool now disagrees with the other two. Same root
question every time: *what are you actually measuring?*

Your shell writer can't demonstrate this — `>>` is `O_APPEND` by definition. The Python
snippet in the cheat sheet (§7) forces it. If you'd rather not switch languages
mid-episode, state it as a known behaviour and move on; don't fake it.

### Beat 6 — the permanent fix

`create` tells logrotate to rename the old file and make a new one. Any process holding
a descriptor keeps writing to the renamed inode forever. It never learns a new file
exists.

1. **`copytruncate`** — copy contents out, truncate the original in place. The inode
   never changes, so the descriptor stays valid. Cost: anything written between the
   copy and the truncate is lost, and you briefly need double the space. Fine for
   access logs, not for anything you'd audit.

2. **`postrotate` + signal** — correct when the app supports it. nginx reopens on
   `USR1`, rsyslog on `HUP`. No race, no loss.

```
postrotate
    /bin/kill -USR1 $(cat /run/nginx.pid) 2>/dev/null || true
endscript
```

Fix the config, rerun the rotation twice, and let the panes show `df` and `du` tracking
each other through both. Proving the fix on the same instruments that showed the bug
closes the loop.

> **Line to land on:** if your rotation strategy doesn't tell the process it happened,
> you haven't rotated anything. You've renamed a file and lied to yourself.

---

## Act 3 — Production (9:00–15:00)

> Straight to camera: *"That's the toy version. Here's what this looked like on a
> cluster I run, where it took one member of a database replica set down."*

**Collapse to a single pane here** — `Ctrl-b z` zooms the driver pane, press again to
restore. The split screen is a teaching instrument for a controlled lab. Act 3 is a war
story, and a tidy dashboard makes it look rehearsed.

**This act is the reason the episode exists.** Act 2 is available from a hundred
channels. Act 3 is not available anywhere.

> **Sourcing rule — non-negotiable.** Everything in 3.1 comes from your own memory of
> the night. If a detail didn't happen, it doesn't go in. Anything true in general but
> not personally witnessed gets framed as "this can happen," never "I saw." One viewer
> who runs this stack and catches an invented detail costs you the only asset the
> channel has.

### 3.1 — The incident

Keep the original telling order. Don't reorganise it into a tidy narrative — the mess
is the value. Everything below is confirmed from your own account; anything you
can't remember, say so on camera rather than filling it in.

1. **What broke.** One of three PSMDB member pods in `CrashLoopBackOff`. The other two
   stayed up and kept a primary. Degraded, not down — say that, it's the negative space.
2. **First move: delete the pod.** Reasonable — most crash loops are bad state inside
   the container. Didn't help: *"The pod is disposable. The volume isn't. The
   StatefulSet handed the new pod the same full disk."*
3. **`df` inside the pod: 100%.** 15Gi volume.
4. **`du -h -d 1`** over the data directory — normal. Over the logs directory — one
   huge `mongod.log`.
5. **The wrong belief:** *"I thought: this is Kubernetes, nothing rotates files on a
   volume, so the log just grew."* Wrong — the pod had a `logrotate` sidecar, and
   mongod rotates its own log. Say why it seemed right: in Kubernetes, logs normally
   go to stdout and the kubelet rotates them.
6. **`rm mongod.log`. `df` still said 100%.** This is the callback moment — the viewer
   now knows two reasons that can happen.
7. **Stop the bleeding.** Grew the PVC from 15Gi to 22Gi, restarted the pod. Fixed.
8. **What you never found out.** Why the `rm` freed nothing. Two candidates:
   - fluent-bit's full copy of the same log was still on the volume — `df` and `du`
     would both say full;
   - fluent-bit, a sidecar that tails `mongod.log`, still had the deleted file open —
     Act 2 exactly.

   *"The restart that fixed it closed every file in the pod, so it erased the answer
   too. I'll never know which one it was."* Don't pick one. The honesty is the point.
9. **Why it filled.** You had raised mongod's log verbosity. fluent-bit stored every
   line twice. The rotation sidecar checks `maxsize 100M` only when it runs — once a
   day — so a burst between runs has no ceiling. And logs shared the 15Gi volume with
   the data.
10. **What you'd do differently.** Before the restart: `du` again, then
    `ls -l /proc/*/fd | grep deleted` in **every** container — one `kubectl exec` per
    container, because they don't share a PID namespace. One minute, and it would have
    answered point 8.

**Things you must not say:** that `du` showed the volume half empty (it didn't — `du`
found the file), that the sidecar held the file (unproven), or that the operator's
controller filled the volume (it writes nothing there; the sidecars do).

### 3.2 — Why Kubernetes makes this strictly worse

**The PID namespace hides the descriptor.** `kubectl exec` in and `lsof` isn't
installed. From the node the PID differs from the one inside the container. Get the
host PID (`crictl inspect | jq '.info.pid'`) and read `/proc/<hostpid>/fd` directly —
you don't need `nsenter` to read descriptors, only to resolve paths. That surprises
people.

**`du` inside the container measures the wrong thing anyway.** Depending on volume
type, the space that matters is on the node's `nodefs`, invisible from inside.

**Eviction turns one full disk into a cascade.** Cross `nodefs.available` and the
kubelet evicts pods on that node — including pods with nothing to do with the log
growth. One noisy writer becomes a multi-tenant incident. Pull the real thresholds on
screen.

**Sidecars log too, and nobody budgets for it.** The workload's logs get dashboards.
A sidecar's second copy sits on the data volume and doubles the bill.

**Ceph-backed PVCs add a second floor** — *not part of this incident (the volumes were
OpenEBS LVM local PVs), so 20 seconds as "worth knowing" at most.* Freeing space inside the filesystem
doesn't return blocks to the pool. RBD images don't shrink, and unless discard is
plumbed through (`discard` mount option, or periodic `fstrim`) the pool still counts
them. Node level looks fixed; cluster level isn't. Same shape as `df` vs `du`, one
layer down — worth drawing that parallel explicitly.

### 3.3 — What to actually monitor

- **Rate of change**, not static thresholds. 40% to 80% in ten minutes is an incident;
  85% for six months is a Tuesday. `predict_linear` on `node_filesystem_avail_bytes`.
- **Inodes separately** — `df -i`. Same failure class, and the free-bytes alert never
  fires.
- **Export deleted-but-open bytes.** Nobody has this one:

```bash
# /usr/local/bin/deleted-open-bytes.sh — cron, every minute
OUT=/var/lib/node_exporter/textfile_collector/deleted_open.prom
{
  echo "# HELP node_deleted_open_bytes Bytes held by deleted-but-open files."
  echo "# TYPE node_deleted_open_bytes gauge"
  lsof -nP +L1 2>/dev/null \
    | awk '$4 ~ /^[0-9]+[rwu]/ {sum[$1]+=$7} END {for (c in sum)
        printf "node_deleted_open_bytes{command=\"%s\"} %d\n", c, sum[c]}'
} > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
```

  **[gotcha] The `$4` filter is load-bearing.** Without it this sums postgres's shared
  memory segments and reports a permanent ~1.3GB of phantom deleted bytes on any box
  running postgres — an alert that fires immediately and never clears. Only numbered
  descriptors (`9w`, `3r`, `12u`) are real open files; `mem` means memory-mapped.
  Verify column positions on your distro before trusting the `awk`; they move.

  Write-then-`mv` because the collector can otherwise read a half-written file.

- **Operator and sidecar logs** in the rotation policy, not just the app.

---

## Lessons learned — prevent it on your own systems (≈75s)

3.3 is about *noticing* faster. This segment is about not getting here at all. Every
item is something a viewer can run on Monday morning. If a line can't be turned into a
command or a config change, it doesn't belong on screen.

Back to the split screen for this — the lab is now the test rig.

**1. Find every rotation that renames without telling anyone.**

```bash
grep -L -E 'copytruncate|postrotate' /etc/logrotate.d/*
```

Lists config files that have neither. Each one is either rotating for a process that
reopens per write, or it's this bug waiting for a long-lived writer. **[gotcha]** The
absence of `create` doesn't mean it's off — `/etc/logrotate.conf` usually sets `create`
globally, so every file on that list inherits it.

**2. For every long-running process, know how it reopens its log.** Signal (`USR1`,
`HUP`), an admin command, or nothing. If the answer is nothing, the rotation must be
`copytruncate` — or the process shouldn't own a log file at all.

**3. Prefer stdout over a log file.** Write to stdout/stderr and let journald or the
container runtime own the file. The app holds no descriptor to a rotated path, so this
whole class disappears. On Kubernetes the kubelet rotates container logs
(`containerLogMaxSize`, `containerLogMaxFiles`) — check those are set, not assumed.

**4. Logs don't share a filesystem with data.** A separate volume or mount for logs
means a runaway writer fills its own disk and fails its own writes. It doesn't take the
database down with it.

**5. Test the rotation, not just the config.** The lab is the test. In staging, start
the real service, force two rotations, and assert nothing deleted is still held on that
mount:

```bash
sudo logrotate -f /etc/logrotate.d/<app>
sudo logrotate -f /etc/logrotate.d/<app>
sudo lsof -a -nP +L1 /var/log/<app> && echo "FAIL: deleted-but-open files" || echo "ok"
```

`lsof` exits non-zero when it finds nothing, so an empty result prints `ok`. Two
rotations, not one — Beat 1 showed that a single rotation looks healthy.

**6. Put the first command in the runbook.** "Disk full" runbooks usually start with
`du` and stop there. Add one line: *if `df` and `du` disagree, run `lsof -a -nP +L1
<mount>` before deleting anything.* Deleting more files on a disk in this state frees
nothing and destroys evidence.

> **Spoken version, to camera:**
> "If you take one checklist from this: find every rotation that renames without
> signalling. Know how each process reopens its log — or stop giving it a file. Keep
> logs off the data volume. Test rotation twice, not once. And when `df` and `du`
> disagree, the first command is `lsof`, not `rm`."

**Don't repeat the three moves here.** These are actions; the close is habits. If this
segment starts saying "neither tool is broken", it's eaten the closing line.

---

## Closing

One line, no montage:

> Next episode: _[the etcd outage — an inventory field pointing at the wrong network]_

Then stop.

---

## Teardown

```bash
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
```

---

## Pre-record checklist

**Layout**
- [ ] `tmux -V` checked — `-l 60%` vs `-p 60` confirmed
- [ ] `watch --help` checked — `-d=permanent` vs `-d cumulative` confirmed
- [ ] fd pane command is single-quoted; `ps aux | grep watch` shows `$(...)` unexpanded
- [ ] fd pane survives `systemctl restart demo-hoarder`
- [ ] All five panes readable on a phone at 1080p (test on the phone)
- [ ] Simulator opens full screen in presenter mode (`P`), fonts loaded, readable on a phone
- [ ] Pane titles visible; `watch -t` suppressing the truncated header
- [ ] Colour contrast checked — dark red/blue on black vanish under compression

**Lab**
- [ ] `head -c2 demo-hoarder.sh | xxd` → `2321`; `chmod +x` applied
- [ ] `findmnt` guard present in `lab-setup.sh`
- [ ] `StartLimitIntervalSec=0` in `[Unit]`
- [ ] `notifempty` absent from the logrotate config
- [ ] `printf '%(...)T'` in the writer — no `pipe:` fd flickering in the pane
- [ ] Fill rate retimed after the `printf` change — 128M in 25–30s
- [ ] Full rehearsal: both rotations produce `(deleted)` on fd 9
- [ ] `teardown.sh` tested end to end

**Content**
- [ ] Only free SadServers scenarios referenced; SadServers credited and linked
- [ ] Real hostnames, IPs, internal domains scrubbed — including the prompt in every
      pane and the tmux status line
- [ ] `history -c`; nothing in scrollback that pre-solves it
- [ ] Every Act 3 claim personally witnessed, or explicitly framed as general
- [ ] Act 3 details cleared for disclosure
- [ ] Recorded **without** solving it beforehand. If you get stuck, keep rolling.
