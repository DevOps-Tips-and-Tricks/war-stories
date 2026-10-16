# Episode 01 — Run of show

Working document. Detail lives in `0001-script-df-vs-du.md` (script),
`0001-spoken-lines.md` (verbatim lines), `0001-cheatsheet.md` (mechanism),
`0001-deleted-but-open-simulator.html` (the Beat 2b visual) and `channel-mental-models.md`
(why any of this is structured the way it is).

---

## The spine

Three sentences. If a take goes wrong, come back to these.

1. **A name and a file are not the same thing.** A directory maps names to inodes; the
   inode owns the blocks.
2. **Removing the name is not the same as freeing the blocks.** Two conditions have to
   be true, and `unlink` satisfies only one.
3. **Your rotation config decides which of those happens.**

Everything in the episode is evidence for one of those three.

---

## Structure: cold open, then flashback

The production incident is split. The symptom opens the video; the resolution closes it.

The reason: the differentiator cannot sit at minute ten. Anyone who leaves at minute
three has seen a toy lab and nothing else. Opening with production puts the thing only
you have in the first ninety seconds, and it converts the lab from a lecture into the
answer to a question the viewer is already holding.

```
  Act 3a  the symptom          ← cold open, 90 seconds, no resolution
     ↓
  Act 1   the lab              ← "same bug, sixty megabytes, nothing at stake"
     ↓
  Act 2   the mechanism
     ↓
  Act 3b  the resolution       ← same evidence, readable now
```

---

## Cold open discipline

**This is the part that decides whether the structure works.** The cold open shows the
symptom and stops. Say one word too many and Beat 2 has nothing left to reveal.

**Allowed:**
- One of three PSMDB pods in CrashLoopBackOff; the other two fine
- "I deleted the pod. It came back and crashed again."
- `df -h` → 100%
- `du` → one huge log file
- "I removed it. `df` still said a hundred percent." — **stop there**
- Your first hypothesis, and the sentence where you realised it was wrong

**Never claim `du` showed the volume empty.** It didn't — it found the file. The
mystery in this cold open is a removal that freed nothing, not a disagreement
between tools.

**Not allowed, at any point before Beat 2:**
- inode
- descriptor, file descriptor, fd
- deleted, unlink
- `lsof`
- logrotate

If a sentence makes you want to use one of those words, that sentence belongs in Act 2.

The wrong hypothesis is the most valuable thing in the cold open. Ninety seconds in,
the viewer learns that a senior engineer guessed wrong and said so. That sets the tone
for the channel more than any explanation will.

---

## Run of show

| time | segment | on screen | note |
|---|---|---|---|
| 0:00 | Intro sting | logo animation | `devops-tips-intro.mp4` |
| 0:10 | **Act 3a — the symptom.** One crashing pod of three, pod delete didn't help, df 100%, du finds a huge log, `rm` it, df still 100%. First hypothesis, and why it was wrong. **Stop.** | real terminal, real Grafana | 90s. Obey the word list above |
| 1:40 | **The promise.** df says full, du says empty, neither is broken. | single terminal | from `0001-spoken-lines.md` §1 |
| 2:00 | **Act 1 — the lab.** *"To explain this I need to show it on a machine where nothing is at stake. Same bug, sixty megabytes, no database."* Build it on camera. | tmux, 5 panes | `lab-setup.sh` |
| 4:00 | Start the writer. All four panes agree. Name the agreement out loud. | tmux | — |
| 4:40 | **Beat 1** — first rotation. rename follows the inode. Still looks healthy. | tmux | — |
| 5:10 | **Beat 2a** — second rotation. The panes diverge. Ask the question, then **two seconds of silence.** | tmux | *"Directory's empty. Disk is full. Where's the space?"* |
| 5:40 | **Beat 2b** — the mechanism, step by step. → **Move 1** | `0001-deleted-but-open-simulator.html`, steps 1–4 | the only explainer visual — no inode primer earlier |
| 6:50 | **Callback.** *"That's one of two reasons my `rm` could have freed nothing."* One line, keep moving. | tmux | closes half the loop — never claim it *was* the reason |
| 7:00 | **Beat 3** — find it cold. `lsof +L1` → `grep deleted` → `-a` scoped | tmux | — |
| 8:10 | **Beat 4** — truncate. Then: *what did not change.* → **Move 2** | tmux | run first, talk second |
| 9:10 | **Beat 5** — sparse-file wrinkle (`stat`: size vs blocks) | tmux | only genuinely optional segment |
| 9:50 | **Beat 6** — the real fix: copytruncate vs postrotate. Prove it on the same panes. → **Move 3** | editor + tmux | — |
| 10:50 | **Bridge back.** *"So. Back to that node."* | to camera | — |
| 11:05 | **Act 3b — the resolution.** Stop the bleeding (15Gi → 22Gi, restart), the two candidates for the `rm`, why you'll never know, why it filled, what you'd run before the restart. | to camera + terminal | script §3.1. The payoff is the honesty, not a reveal |
| 13:20 | **Why Kubernetes is worse.** PID namespace, nodefs, eviction cascade. | node terminal | — |
| 14:40 | **What to actually monitor.** Rate of change, inodes, the exporter. | code + PromQL | — |
| 15:20 | **Lessons learned — prevent it.** Six actions: audit rotations, know the reopen path, stdout over files, logs off the data volume, test two rotations, `lsof` before `rm` in the runbook. | tmux + to camera | ≈75s. Actions, not habits — don't pre-empt the close |
| 16:35 | **Close.** The three moves, then next episode. Stop. | to camera | 30s, no montage |

**Total ≈ 17 minutes.** Over the 14–16 min target; Beat 5 is the obvious cut if needed. The open loop runs 1:40 → 11:05. That's long, which is why the
transition line and the 6:50 callback both exist. Don't drop either.

---

## The three moves

Named out loud, at the moment each one pays off. Not before.

**Move 1 — Beat 2b.** *When two tools disagree, neither is broken. They're answering
different questions.*
Point forward: memory metrics, latency percentiles, `rbd du` vs `df`.

**Move 2 — Beat 4.** *When you fix something surgically, verify with what didn't change.*
The fd pane staying identical is the proof the process was never disturbed.

**Move 3 — Beat 6.** *Mitigation is not a fix. Say which one you just did.*
truncate stopped the bleeding; the logrotate config is the fix.

Move 3 from `channel-mental-models.md` — *name your hypothesis out loud* — is
demonstrated in the cold open rather than labelled. Captioning it would make it smaller.

**Closing lines, 30 seconds:**

> "Three things worth taking from this, none of them about log files.
> One: when two tools disagree, neither is broken.
> Two: when you fix something surgically, check what didn't change.
> Three: a workaround is not a fix — know which one you just did."

---

## What each act has to achieve

| act | job | if it fails |
|---|---|---|
| **3a** | Make them need the answer. | They leave at minute three |
| **1** | Earn trust — they must believe they could rebuild this. | Everything after looks like a trick |
| **2** | Teach the mechanism by letting them watch it happen. | One more generic Linux tutorial |
| **3b** | Prove you have actually done this. | The channel has no reason to exist |

---

## Four ways this falls apart

**You resolve the cold open.** The single biggest risk in this structure. Shoot the
cold open last, after Act 2 is cut, so you already know exactly which words to avoid.

**The transition sounds like a detour.** *"Let's cover some Linux basics first"* is
bait-and-switch. The lab is the key to the mystery, not a prerequisite — frame it that
way or the viewer feels tricked.

**You explain Beat 4 before running it.** The `df` bar dropping is the reveal. Run the
command, let it land, then talk.

**Act 3b drifts into what you didn't witness.** The moment you hear yourself say "and
what probably happened was…", stop the take. Either you saw it, or you frame it as
general.

---

## The test before publishing

In one sentence: *what does a senior engineer know after this video that they did not
know before, and could not have got from a model?*

If the answer only describes Act 2, the episode is not finished.
