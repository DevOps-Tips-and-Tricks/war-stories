# YouTube Short — Episode 01: df vs du

**Source entry:** `0001-deleting-the-largest-log-file-did-not-free-the-full-volume.md`
**Length:** 72.6 s as rendered (68.4 s of narration plus a 3.5 s channel end card), vertical 1080×1920
**Voice:** an ElevenLabs instant clone of the maintainer's own voice (`eleven_v4`, stability 0.95,
similarity 0.95, light-Persian-accent delivery tag), generated per beat. Video and captions are
built to the generated audio's timestamps. Tick YouTube's "altered or synthetic content" box when
posting.
**Look:** the episode's design system, taken from `0001-deleted-but-open-simulator.html`
(ground `#0A111D`, panel `#111A2A`, ink `#F5EEE2`, accent `#EC9A46`, danger `#E95460`,
ok `#5BC98B`; JetBrains Mono plus the system sans). Calm motion: fades, rises, gauges and
highlights. No stamps, shake or whooshes; the only sound effect is soft typing under the
terminal.

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

Terminal output is a **reconstruction at the incident's scale**, not a capture: a 15G volume
at 100% and an 11G `mongod.log`, so that "one huge log file" matches the screen. It is
modelled on a real lab run of the same commands (488M volume, 477M log). The terminal title
says "reconstruction, names redacted", and the WiredTiger data-file names in the `du`
listing are blurred as if confidential. The 15G figure is the one the entry already
publishes; nothing else in the listing comes from the incident.

| Beat | On screen |
|---|---|
| 1 | Card `/data/db/logs` with `mongod.log 11G`, struck out on "deleted". A large `df` reading of `100%` stays put; chip "after rm · unchanged" |
| 2 | Pod `database-0` with a `CrashLoopBackOff` chip. Terminal: `df -h` at 100%, `du -ah /data/db \| sort -rh \| head -8` with the 11G `mongod.log` highlighted and the data files blurred, `rm`, `df -h` at 100% again |
| 3 | The simulator's model, animated: directory entry → inode 13 ← process fd 9w. `nlink` drops to 0, open fds stays at 1, "blocks kept". `du`/`df` gauges: `du` falls from 15G to 4.0G, `df` stays at 15G, the call chip flips from AGREE to SPLIT |
| 4 | "Why did rm free nothing?" with the entry's two open explanations and what each would show (fluent-bit's full copy: `df` full, `du` full; a process holding the file: `df` full, `du` empty). The pod restart closes every container's descriptors and both turn to "evidence gone" |
| 5 | Terminal: `lsof +L1`, with `NLINK 0` and `(deleted)` in red and `9w` in orange; chips "name deleted" and "still open for writing". Then the pod's three containers (`mongod`, `logs`/fluent-bit, `logrotate`), each with its own PID 1, on one shared `/data/db`; chip "shared disk · separate PID namespaces" |
| 6 | The two lesson lines as cards, highlighted word by word as they are spoken. Then the channel end card in the style of the long-form intro's closing frame: logo, `DEVOPS` decoding from scrambled glyphs, `TIPS AND TRICKS`, "what broke at 2am — and why", and LIKE / COMMENT / SUBSCRIBE |

Captions are burned in for beats 1–5 in a reserved band above the Shorts UI, with nothing
else drawn there. Up to four words show at a time: upcoming words dim, the current word in
the accent colour. Commands use the on-screen spelling, not the pronunciation. Beat 6 has
no separate captions, because the lesson cards are the words.
