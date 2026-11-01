# YouTube Short — Episode 01: df vs du

**Source entry:** `0001-deleting-the-largest-log-file-did-not-free-the-full-volume.md`
**Length:** 70 s as rendered (calm delivery runs longer than the 56 s word-count estimate), vertical 1080×1920
**Voice:** an ElevenLabs instant clone of the maintainer's own voice (`eleven_v4`, stability 0.95,
similarity 0.95, light-Persian-accent delivery tag), generated per beat. Video and captions are
built to the generated audio's timestamps. Tick YouTube's "altered or synthetic content" box when
posting.

The Short must not claim more than the entry does. The entry leaves open *why*
the `rm` freed nothing (a held descriptor, or fluent-bit's duplicate copy), so
the Short teaches the mechanism as one possible cause and makes the open
question the twist. It does not show `truncate` as what we did: that is from
the lab, and in the incident we grew the volume and restarted the pod.

## Recording notes (if re-recorded by hand)

- Say it as written. Each line is short on purpose.
- Leave a clear half-second pause between beats. The video cuts on those pauses.
- One take for the whole thing is best. If a beat goes wrong, pause, and say that
  beat again from its first line. The bad take is cut out.
- Pronunciation: `df` = "dee-eff", `du` = "dee-you", `rm` = "R M",
  `lsof` = "el-ess-oh-eff", `+L1` = "plus L one".
- Any format the phone records is fine (`.m4a` is typical). Quiet room, phone
  about a hand's width from your mouth.

## Narration

**1 — Hook**

> We deleted the biggest file on a full disk.
> The disk stayed full.

**2 — What happened**

> A database pod was crash-looping.
> `df` said the volume was at a hundred percent.
> `du` found one huge log file. We removed it.
> `df` still said a hundred percent.

**3 — How that can happen**

> `rm` does not delete data. It deletes a name.
> If a process still has the file open, the kernel keeps every block.
> `du` counts names, so for `du` the file is gone.
> `df` asks the filesystem, and the filesystem still sees every block.

**4 — The twist**

> Was that our case? We never found out.
> We restarted the pod. The restart closed every file,
> and it destroyed the evidence.

**5 — Check first**

> So before you restart, run `lsof +L1`.
> It lists files that are deleted but still open.
> In a pod, check every container.
> They share the disk, not the processes.

**6 — Lesson**

> When `df` and `du` disagree, stop deleting.
> Ask who still has the file open.

About 140 words, so roughly 56 s at a calm pace.

## Visuals (built by Claude to the audio)

| Beat | On screen |
|---|---|
| 1 | Big `100%` disk bar. A file icon is deleted; the bar does not move |
| 2 | Terminal: `df -h` → `100%`, `du -h -d 1` → one large `mongod.log`, `rm`, `df -h` → `100%` again |
| 3 | Diagram: name → inode → blocks. `rm` cuts the name link; a process's fd arrow still holds the inode. `du` reads names, `df` reads blocks |
| 4 | A large `?` over the diagram, then a pod restart icon wipes it clean |
| 5 | Terminal: `lsof +L1`, one row ending in `(deleted)`, highlighted. Then three container boxes on one shared disk, each with its own process list |
| 6 | The two lines as text cards, then the channel name |

Word-by-word captions are burned in throughout. Commands in captions use the
spelling on screen, not the pronunciation.
