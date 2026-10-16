# Episode 01 — Presenter's Cheat Sheet

Not for the video. This is so that when someone asks a follow-up in the comments, or an
interviewer pulls the thread, you're standing on the mechanism rather than on the demo.

Every claim has a command next to it. Run them once; don't take them on faith.

---

## 1. Files, names, and inodes

**A filename is not a file.** A directory is a table mapping names to inode numbers. The
inode holds metadata (mode, owner, timestamps, size, block pointers) and owns the data
blocks. Names are just references.

```bash
ls -i file                # inode number
stat file                 # inode, links, size, blocks
```

**Link count** is the number of directory entries pointing at that inode. `ln`
increments it, `unlink()` decrements it.

```bash
touch a && ln a b && stat -c '%h %i' a b   # 2 links, same inode
```

**`unlink()` removes the name, not the file.** The kernel frees the inode and its blocks
only when **both** hold:

1. link count == 0, **and**
2. no process holds an open file descriptor to it

That conjunction is the entire episode. Miss either half and the demo makes no sense.

**Where "deleted" lives on ext4:** an inode with zero links but open descriptors goes on
the **orphan inode list** in the superblock. If the machine crashes in that state,
`e2fsck` walks the orphan list at next mount and reclaims the blocks. That's why a hard
reboot "fixes" a disk that a graceful shutdown wouldn't need to.

```bash
sudo dumpe2fs -h /dev/loop0 2>/dev/null | grep -i orphan
```

**`rename()` is a directory operation.** It changes which name points at the inode. It
doesn't touch the inode, so open descriptors are completely unaffected — exactly why
logrotate's `create` mode strands long-lived writers.

---

## 2. File descriptors vs open file descriptions

The distinction most people get wrong, and the one that explains `O_APPEND`.

- **File descriptor** — a small integer, per-process, in the process's fd table
- **Open file description** — a kernel object created by `open()`. Holds the **file
  offset** and the **status flags** (`O_APPEND`, `O_NONBLOCK`, …)
- **Inode** — the file itself

fd → open file description → inode. Many fds can share one description (`dup()`,
`fork()`); many descriptions can point at one inode (two separate `open()` calls).

Consequences:

- `fork()` shares the description, so parent and child share an offset. Two separate
  `open()` calls do not.
- `O_APPEND` is a property of the **description**, not the fd, and can be changed at
  runtime with `fcntl(F_SETFL)`.
- Closing one fd doesn't free the file until *all* descriptions referencing the inode
  are gone.

```bash
cat /proc/<pid>/fdinfo/9
```

```
pos:    41943040
flags:  02101001
mnt_id: 42
```

`flags` is **octal**: `O_APPEND`=`02000`, `O_WRONLY`=`01`, `O_CREAT`=`0100`,
`O_LARGEFILE`=`0100000`. `pos` is the offset — the number that makes sparse files happen.

---

## 3. `/proc/<pid>/fd`

Symlinks, one per open descriptor. For a deleted file the target reads
`/path/to/file (deleted)`. **The ` (deleted)` suffix is appended by the kernel** — it is
not part of the path.

- **They're not ordinary symlinks.** Opening `/proc/<pid>/fd/9` reopens the *inode*, not
  the path. That's why `truncate -s 0 /proc/<pid>/fd/9` reaches a file with no name
  anywhere on the filesystem.
- **It works across mount namespaces.** From the host, `/proc/<hostpid>/fd/N` reaches a
  container's file even though that path doesn't exist in the host's namespace. You do
  **not** need `nsenter` for descriptors — only for commands that resolve paths.
- **Needs privilege** — same UID or `CAP_SYS_PTRACE`. In practice, root.

**What you'll see on a systemd-managed bash script:**

```
0   -> /dev/null                       # StandardInput=null, systemd's default
1,2 -> socket:[397427]                 # both to journald, same socket
255 -> /usr/local/sbin/demo-hoarder.sh # bash's own handle on the script
9   -> /var/log/... (deleted)          # ours
```

fd 255 is bash-specific: it keeps the script open so it can read ahead without holding
the whole file in memory. Worth knowing, because viewers ask.

**The `+` in `lrwx------+`** indicates extended attributes / an ACL on the entry — on
these boxes usually an LSM label rather than a POSIX ACL. `getfacl` on the target will
tell you which; don't assert it on camera without checking.

**Transient descriptors.** `$(...)` command substitution is implemented with a pipe:
bash creates one, forks, the child writes, the parent reads. Run `$(date)` in a tight
loop and a `pipe:[N]` descriptor flickers in and out at the lowest free number (3, if
0–2 and 9 and 255 are taken — `open()` always returns the lowest unused fd).

```bash
for i in $(seq 20); do readlink /proc/<pid>/fd/3 2>/dev/null; sleep 0.1; done
```

Different pipe inode each time, with misses. `printf '%(%F)T' -1` is the built-in
replacement — no fork, no pipe (bash 4.2+).

---

## 4. `df` — what it actually asks

`df` calls `statvfs()`/`statfs()` and reads the filesystem's own counters. It never
looks at files.

- `f_blocks` — total blocks
- `f_bfree` — free blocks, **including** the reserved pool
- `f_bavail` — free blocks available to unprivileged users, **excluding** reserve

`Available` is `f_bavail`. `Use%` is computed against `f_blocks - f_bfree + f_bavail`,
which is why a filesystem can read 100% used while root still writes. ext4 reserves 5%
by default.

```bash
sudo tune2fs -l /dev/loop0 | grep -i 'reserved block'
sudo tune2fs -m 0 /dev/loop0        # change after the fact
stat -f /var/log/demo-app           # statvfs directly
```

**Inodes are a separate exhaustible resource** — `df -i`. A filesystem full of tiny
files runs out of inodes with free bytes remaining, and every byte-based alert stays
green. ext4 fixes the inode count at mkfs time; you cannot grow it later.

---

## 5. `du` — what it actually asks

`du` walks the tree, `stat()`s everything, sums `st_blocks`.

- `st_blocks` is in **512-byte units**, always, regardless of filesystem block size
- Default output is 1KiB blocks (`-h` human, `-B` to set)
- **Hardlinks counted once** per invocation — it tracks inodes already seen. Two
  separate runs each count it.
- `--apparent-size` uses `st_size` instead, which is why it can exceed the disk size on
  sparse files

**The four ways `df` and `du` legitimately disagree.** Know all four — comments will ask:

1. **Deleted-but-open files** — this episode.
2. **Mounts hiding files underneath** — anything written to `/mnt/x` *before* a mount
   landed there is still on the parent filesystem: counted by `df`, invisible to `du`.
3. **Reserved blocks** — `df` counts them used, `du` never sees them.
4. **Filesystem metadata and journal** — the ext4 journal (64–128M typically) is real
   allocated space belonging to no file.

```bash
sudo mount --bind / /mnt/root-check && du -sh /mnt/root-check/mnt/x   # case 2
```

---

## 6. `stat` — Size vs Blocks

```
  Size: 41943040        Blocks: 8          IO Block: 4096   regular file
```

- `Size` = `st_size`, the logical end of file — where a read hits EOF
- `Blocks` = `st_blocks` in 512-byte units — real allocation
- `IO Block` = preferred I/O size, not the allocation unit

`Size > Blocks * 512` means holes. The reverse is also possible — ext4 preallocation.

`stat -L /proc/<pid>/fd/9` dereferences to the inode, which is how you watch a deleted
file's real size change.

---

## 7. Sparse files and why the offset matters

`truncate(2)` / `ftruncate(2)` change `st_size`. They **do not change the file offset**
of any open description.

So: file at 40MB, offset at 40,000,000, truncate to 0. `st_size` is now 0 but `pos` is
still 40,000,000. The next `write()` lands there, `st_size` jumps back to ~40MB, and
everything between 0 and the offset is a hole — allocated to nothing, reading as zeros.

**`O_APPEND` prevents this.** The kernel atomically repositions to end-of-file before
every write, so the stored offset is irrelevant. That atomicity is also why multiple
processes can append to one log without interleaving damage (for writes under
`PIPE_BUF`; larger writes can still tear).

Force the sparse case — your shell writer can't, because `>>` *is* `O_APPEND`:

```bash
python3 - <<'EOF'
import os
fd = os.open('/var/log/demo-app/test.log', os.O_WRONLY | os.O_CREAT)  # no O_APPEND
os.write(fd, b'x' * 10_000_000)
os.ftruncate(fd, 0)          # size -> 0, offset stays at 10,000,000
os.write(fd, b'end')
os.close(fd)
EOF
stat /var/log/demo-app/test.log
filefrag -v /var/log/demo-app/test.log     # extent map shows the gap
```

---

## 8. `lsof`

```bash
lsof +L1                              # link count < 1 — deleted but open
lsof -nP +L1                          # no DNS, no port names: much faster
lsof -a -nP +L1 /var/log/demo-app     # AND: deleted-but-open ON this filesystem
lsof +D /var/log                      # everything under a directory (walks it, slow)
lsof /path/to/file                    # who has this open
```

**`-a` ANDs the selection criteria.** lsof ORs them by default, so `lsof +L1 /mount`
without `-a` returns "deleted anywhere" *plus* "everything on that mount" — a longer
list than `+L1` alone. This catches people who've used lsof for years.

**Columns:** `COMMAND PID USER FD TYPE DEVICE SIZE/OFF NLINK NODE NAME`. `+L1` inserts
the `NLINK` column, which shifts positions. Verify indices before scripting against
them; they also shift when a `USER` can't be resolved.

**The `FD` column is the important filter.** `mem` means memory-mapped, not a numbered
descriptor. Only `9w`, `3r`, `12u` and friends are real open files:

```bash
lsof -nP +L1 | awk 'NR==1 || $4 ~ /^[0-9]+[rwu]/'
```

**Why postgres floods `+L1`:** `/dev/zero` and `/SYSV000bc750` entries are shared memory
— a segment created and immediately unlinked so it lives only while processes are
attached. Link count zero permanently, by design. Device `0,1`, not a disk, so no
storage is involved. Same *lifecycle* as your deleted log, entirely different *problem*.
Any script that sums `+L1` sizes without filtering the FD column reports over a gigabyte
of phantom deleted bytes on any box running postgres.

Alternatives when lsof isn't installed:

```bash
fuser -v /path
sudo ls -l /proc/*/fd 2>/dev/null | grep deleted
```

---

## 9. logrotate

| directive | mechanism | breaks long-lived fds? |
|---|---|---|
| `create` (default) | `rename()` old → new name, create fresh file at old path | **yes** — writer keeps the old inode forever |
| `copytruncate` | copy contents out, then `truncate()` in place | no — inode never changes |
| `postrotate` + signal | rename, then signal the app to reopen | no — app closes and reopens |

**`copytruncate`'s race is real:** anything written between the copy finishing and the
truncate landing is lost, and you need double the space transiently. Fine for access
logs, not for audit trails.

**`postrotate` is correct but app-dependent.** nginx `USR1`, Apache `USR1` (graceful),
rsyslog `HUP`. No reopen signal means you're back to `copytruncate`.

**`notifempty` breaks the deleted-file demo.** After the first rotation the writer is
still on the old inode, so the new file is empty — and `notifempty` refuses to rotate an
empty file. The second rotation never happens. This is a real production trap too: it
silently stops rotating any log whose writer was stranded, which is exactly when you
most need rotation to keep working.

```bash
logrotate -d /etc/logrotate.d/demo-app       # dry run, prints its reasoning
logrotate -f /etc/logrotate.d/demo-app       # force regardless of size/time
cat /var/lib/logrotate/status                # last-rotation state
```

`size` rotates when larger, ignoring schedule. `minsize` rotates on schedule but only if
larger. `maxsize` rotates on schedule *or* early if larger. Confusing these is its own
production bug.

**journald ignores logrotate entirely** — it vacuums via `SystemMaxUse=` in
`journald.conf`.

---

## 10. systemd failures you'll hit while recording

**`203/EXEC`** — systemd's `EXIT_EXEC`. `execve()` failed. In order of likelihood:

- Shebang not at byte 0 → `binfmt_script` doesn't see `0x23 0x21` → `ENOEXEC` (errno 8,
  which is what appears in the journal)
- Not executable → `EACCES`
- Interpreter missing → `ENOENT`
- CRLF line endings → interpreter becomes `bash\r` → `ENOENT`

```bash
head -c2 script | xxd            # expect 2321
file script                      # "ASCII text executable" if the shebang parsed
cat -A script | head -3          # ^M$ means CRLF
sed -i 's/\r$//' script
```

Shebang length is capped by `BINPRM_BUF_SIZE` — 128 bytes historically, 256 on newer
kernels. Long interpreter paths get silently truncated.

**`Start request repeated too quickly`** — the rate limiter. `StartLimitBurst=5` starts
within `StartLimitIntervalSec=10s`. Once tripped the unit latches failed and
`systemctl start` does nothing:

```bash
systemctl reset-failed <unit>
```

Both are `[Unit]` options — they moved from `[Service]` in systemd 229, and old posts
still put them in the wrong section. `StartLimitIntervalSec=0` disables it.

**`systemctl show -p MainPID --value <unit>`** — clean PID, no `pgrep` self-matching.
`systemctl show <unit>` with no `-p` dumps every resolved property, the fastest way to
settle "is this setting actually applied."

---

## 11. Loop devices

```bash
losetup -a                             # what's attached
losetup -j /root/demo-disk.img         # find the device for a file
sudo losetup -d /dev/loop0             # detach
```

`fallocate` allocates real blocks immediately; `truncate -s 64M` would make a sparse
image, so the host would only consume space as the guest fills. For this demo
`fallocate` is right — you want host accounting to be boring.

Loop devices pass through discard when the backing filesystem supports hole punching, so
`fstrim` on the loop mount can shrink a sparse backing file. Same idea as the Ceph
section in Act 3.

**Always verify the mount took before starting the writer** (`findmnt <mount>`). If
`mount` fails, the target is an ordinary directory on the root filesystem and the writer
fills the real disk at several MB/s.

---

## 12. Kubernetes specifics

```bash
crictl ps
crictl inspect <container-id> | jq '.info.pid'
```

Then `/proc/<hostpid>/fd` and `/proc/<hostpid>/fdinfo/N` work directly from the node.
Use `nsenter -t <pid> -m -p -- <cmd>` only when you need path resolution inside the
container's namespaces.

**Which filesystem the kubelet cares about:**

- `nodefs` — kubelet's volumes, logs, emptyDir (usually `/var/lib/kubelet`)
- `imagefs` — the runtime's images and writable layers

**Hard eviction defaults** (configurable, and they've changed across versions — verify):

```
memory.available   < 100Mi
nodefs.available   < 10%
nodefs.inodesFree  < 5%
imagefs.available  < 15%
```

```bash
kubectl get --raw /api/v1/nodes/<node>/proxy/configz | jq '.kubeletconfig.evictionHard'
```

Eviction ranks by QoS class and by how far each pod exceeds its requests — so a
BestEffort pod with nothing to do with the disk growth gets killed. That's the cascade.

**Ephemeral storage is polled, not enforced inline.** The kubelet measures writable
layers and emptyDir periodically (tens of seconds, version dependent). A process can
blow past its `ephemeral-storage` limit between polls. Check the cadence on your version
before quoting a number.

---

## 13. Ceph / RBD

Thin provisioning allocates on first write and **never reclaims on delete** unless
discard reaches it.

```bash
rbd du <pool>/<image>          # provisioned vs actually used
rbd info <pool>/<image>        # features
```

`rbd du` needs `object-map` and `fast-diff` enabled to be accurate and fast; without
them it scans every object.

Two ways to plumb discard through:

- `mountOptions: [discard]` in the StorageClass — inline on every delete. Correct, with
  a throughput cost on delete-heavy workloads.
- Periodic `fstrim` — batched and cheaper, but the pool over-reports between runs.

```bash
fstrim -av
lsblk -D                       # DISC-GRAN / DISC-MAX: is discard supported at all?
```

`df` inside the pod says fixed, `rbd du` says still full. Same confusion as `df` vs
`du`, one layer down.

---

## 14. Prometheus

```promql
# will it fill in the next 4 hours?
predict_linear(node_filesystem_avail_bytes{mountpoint="/var/lib/kubelet"}[6h], 4*3600) < 0

# inode exhaustion — separate alert, or it never fires
node_filesystem_files_free / node_filesystem_files < 0.10

# the gap this episode is about
node_deleted_open_bytes > 1e9
```

`predict_linear` fits an ordinary least-squares line over the range and extrapolates.
Linear, so it overreacts to bursts — pair with a `for:` long enough to filter noise.

**Textfile collector semantics:**

- `--collector.textfile.directory=/var/lib/node_exporter/textfile_collector`
- Files must end `.prom` and be valid exposition format
- **Write to a temp file and `mv`** — rename is atomic within a filesystem, so the
  collector never sees a partial file. A plain redirect will eventually be read
  mid-write.
- A stale file exports forever. Alert on
  `time() - node_textfile_mtime_seconds > 300`, or you'll page on data from a cron job
  that died last month.
- **Filter the FD column** (§8) or postgres shared memory becomes a permanent false
  positive.

---

## 15. Questions you should be able to answer cold

- Why doesn't `rm` free space if a process has the file open?
- What's the difference between a file descriptor and an open file description?
- Where does `O_APPEND` live, and why does that make truncation safe?
- Name four ways `df` and `du` legitimately disagree.
- Why can `df` show 100% while root still writes successfully?
- After `truncate -s 0 /proc/<pid>/fd/9`, why doesn't `/proc/<pid>/fd` change?
- What does `create` do in logrotate, and why does it strand a writer?
- What's the race in `copytruncate`, and when does it matter?
- Why does `notifempty` silently stop rotating a stranded log?
- Why is `st_blocks` in 512-byte units when the filesystem block is 4096?
- Why does `lsof +L1` return postgres shared memory, and how do you exclude it properly?
- What does `-a` do in lsof, and what happens without it?
- Exit code 203 — what failed, and what are the four common causes?
- Why does `pgrep -f` inside a `watch` command match itself?
- How do you read a container's open descriptors from the node?
- Space freed in the pod but `rbd du` unchanged — why?
- Why does a hard reboot sometimes "fix" a full disk when a graceful one doesn't?
