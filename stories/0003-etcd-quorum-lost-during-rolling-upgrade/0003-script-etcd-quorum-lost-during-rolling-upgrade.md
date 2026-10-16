# Video production script — Episode 0003

**Source entry:** `stories/0003-etcd-quorum-lost-during-rolling-upgrade.md`
**Channel:** https://www.youtube.com/@DevOpsTipsAndTricks
**Status:** draft — not recorded
**Target runtime:** 12:00–13:00
**Format:** terminal screencast primary, talking head for the three lesson beats

> This file is local-only. `video-scripts/` is gitignored — nothing here ships
> to the public repository.

---

## 1. Positioning

### The one-sentence pitch

A Kubernetes cluster that is completely frozen — every `kubectl` command times
out — while every user-facing workload keeps serving traffic perfectly, and the
logs say the shutdown was intentional.

### Why this works as an episode

The channel's differentiator is the **What we thought it was** section. Most
Kubernetes incident content publishes the answer, which is the least useful
part. This episode spends nearly half its runtime on two hypotheses that were
*wrong but correct to hold*, which is the thing no other channel in this niche
is doing. Lead with that, in the video and in the description.

The technical hook is genuinely counter-intuitive and survives a change of
stack: **config that is only read at startup is a landmine with a delay fuse,
and the fuse is however long it has been since your last restart.** That
sentence is the video. Everything else is scaffolding around it.

### Audience assumption

Mid-level DevOps/SRE who has run `kubectl` daily but has never had to reason
about etcd quorum under pressure. Do not explain what a pod is. Do explain what
`--initial-advertise-peer-urls` actually does, because most of this audience has
never set it by hand.

---

## 2. Packaging (write this before recording, not after)

Decide the title and thumbnail **first**. If you cannot write a compelling title
for the video, the video's structure is wrong and recording it will not fix
that.

### Title candidates

Ranked. All keep `etcd` early — it is the searchable term and it filters for the
audience that will actually watch to the end.

1. `Our etcd cluster looked healthy. The whole control plane was already dead.`
2. `The Kubernetes outage where nothing broke — except every kubectl command`
3. `etcd quorum loss: the config bug that stays invisible until you restart`
4. `Why our "graceful shutdown" log line cost us 40 minutes`

Rules applied: under 60 characters where possible so it is not truncated in
search; curiosity gap without clickbait (the video pays off every one of these);
no all-caps; no leading emoji.

### Thumbnail

- Three node boxes, two joined by a green line, the third greyed out and
  disconnected, and a large red `NO QUORUM` stamp.
- Maximum **three words** of text at a size readable at 168×94 px. Check it at
  that size before committing — most thumbnails fail on mobile, which is where
  the majority of views come from.
- High contrast, one saturated accent colour, no thin fonts.
- If including a face: genuine concentration or concern, not exaggerated shock.
  This audience is allergic to the shocked-face thumbnail and it measurably
  underperforms with technical viewers.

### Description

First two lines are all that show above the fold — put the hook there, not a
greeting.

```
A three-node control plane, a routine rolling upgrade, and a cluster that went
completely read-only without a single user noticing. Here is the incident, the
two wrong hypotheses we chased first, and the two-minute check that would have
caught it before we touched the first node.

Full written postmortem, in a fixed schema, including the discarded hypotheses:
https://github.com/DevOps-Tips-and-Tricks/war-stories

This is part of a series of anonymised production incidents. Every entry has a
required "What we thought it was" section, because the transferable skill is
chasing fewer wrong hypotheses — not memorising more root causes.

CHAPTERS
00:00 The symptom
00:50 The architecture
02:00 Every kubectl command times out
03:15 Wrong hypothesis 1: the upgrade tooling
04:30 Wrong hypothesis 2: the graceful shutdown
06:00 The signal we should have caught in two minutes
06:45 What actually happened
08:45 The fix
09:45 The check that would have prevented it
10:45 The lesson that outlives Kubernetes
11:45 What is coming next

COMMANDS AND LAB
Everything shown in the terminal, plus a Docker Compose lab that reproduces
quorum loss on your own machine: [link to gist — do NOT link the private
video-scripts directory]

CHAPTERS must start at 00:00 and there must be at least three, or YouTube will
not render them.
```

### Tags / keywords

`etcd`, `etcd quorum`, `kubernetes control plane`, `kubernetes outage`,
`postmortem`, `sre`, `incident response`, `kubespray`, `rolling upgrade`,
`devops`. Put the primary keyword in the **first spoken sentence** too — the
transcript is indexed.

### Pinned comment (post at upload)

> The check that would have prevented this is three lines and runs from inside
> each node, not from your laptop — it is at 09:45. What is the config in your
> stack that is only read at startup? That is your delay fuse.

Ask a question that is cheap to answer. Comments in the first hour matter
disproportionately.

---

## 3. Narration script

Timings are targets, not gospel. Markers: `[CAM]` talking head, `[SCR]` screen
recording, `[GFX]` motion graphic or diagram, `[TEXT]` on-screen text overlay.

Read the whole thing aloud once before recording. Anything you stumble over
twice is written wrong — rewrite it rather than practising it.

---

### COLD OPEN — 0:00–0:25

No intro. No "hey everyone". The first frame is already the problem.

`[SCR]` Terminal, `kubectl get nodes`, cursor blinking. Nothing happens. Let it
hang for a genuinely uncomfortable four seconds, then the timeout error.

> **VO:** Every `kubectl` command against this cluster times out. Every single
> one. Deployments, scaling, rescheduling — the cluster cannot be changed at all.

`[SCR]` Cut to a browser hitting the app. It loads instantly.

> **VO:** And the application is fine. Users are being served, right now, with
> zero errors. Nobody has noticed anything.

`[TEXT]` `SEV1 · 1h35m to resolve · zero customer impact`

> **VO:** This is a sev-one that no customer ever saw. It took us ninety-five
> minutes, and we spent the first forty of them looking in completely the wrong
> place — for reasons that were, at the time, entirely reasonable.

**Note:** the "reasons that were entirely reasonable" promise is the retention
contract for the whole video. Do not cut it.

---

### TITLE — 0:25–0:50

`[GFX]` Channel ident. **Three seconds maximum.** A long animated intro is the
single most reliable way to lose a technical audience.

> **VO:** This is War Stories, where we go through real production incidents in
> a fixed format — including the hypotheses that turned out to be wrong. That
> last part is the whole point of the series, and in this one the wrong
> hypotheses are more instructive than the answer.

No subscribe request here. It is too early and it costs retention at the exact
moment viewers decide whether to stay.

---

### THE ARCHITECTURE — 0:50–2:00

`[GFX]` Build the diagram one element at a time as it is described. Never show a
finished complex diagram — the viewer reads ahead and stops listening.

> **VO:** Three control-plane nodes. Standard stuff: an API server on each one,
> and behind them a three-member etcd cluster, which is where the entire state
> of the cluster actually lives.
>
> Each node has two network interfaces. One is management: SSH, monitoring, the
> network your laptop is on. The other is a separate data network, and that is
> what cluster traffic is supposed to use. If you have ever run bare metal or
> anything on-prem, this is a completely normal layout.

`[GFX]` Highlight the two networks in distinct colours. Keep those colours
consistent for the rest of the video — this is what makes the root cause land
visually later.

> **VO:** Remember quorum: three members means you need two of them talking to
> each other. Lose two, and etcd stops accepting writes. It does not crash — it
> deliberately refuses to serve, so it can never give you stale or split-brain
> data. Hold on to that. It is why the logs lied to us later.

`[TEXT]` `3 members · quorum = 2 · lose 2 = read-only`

---

### THE SYMPTOM — 2:00–3:15

> **VO:** Twenty-one ten. Planned control-plane upgrade, one node at a time. The
> first node goes through cleanly. Comes back, joins, looks perfect.
>
> Twenty-one thirty-eight, second node drains and restarts.
>
> Twenty-one forty-two, every `kubectl` call starts timing out.

`[SCR]` Real terminal. Run these live rather than pasting output:

```bash
kubectl get nodes
kubectl get pods -A
```

Both hang, then time out.

> **VO:** But here is the thing that made this incident strange, and it is the
> single most useful fact in the entire story. The workloads never stopped.

`[SCR]` Split screen: `kubectl` timing out on the left, `curl` against the app
returning `200` in a loop on the right.

> **VO:** Pods that were already running kept running. Services kept routing.
> The ingress kept serving. Not one user-facing request failed for the whole
> ninety-five minutes.
>
> So what is broken is not the network. It is not the kubelets. It is not the
> container runtime. The *only* thing that is broken is our ability to
> **change** anything.

`[TEXT]` `Everything works. Nothing can change.`

---

### WRONG HYPOTHESIS 1 — 3:15–4:30

`[CAM]` Switch to camera here. The wrong-turn sections are the emotional core
and they land better on a face than on a terminal.

> **VO:** First hypothesis: the upgrade tooling.
>
> And be honest about why that is the *right* first guess. A rolling upgrade
> that stalls halfway through is, the overwhelming majority of the time, a
> playbook that failed on some task and left a node half-configured. That is not
> a lazy assumption. That is pattern matching on a genuinely common failure, and
> nine times out of ten it is correct.

`[SCR]` Scroll through clean playbook output. Let it scroll for a beat too long
— the audience should feel the wasted time.

> **VO:** We spent about fifteen minutes reading task output. All of it was
> clean. Every task succeeded. Which, at the time, was just confusing.

`[TEXT]` `~15 minutes · playbook output was clean`

---

### WRONG HYPOTHESIS 2 — 4:30–6:00

> **VO:** Second hypothesis: the API server itself. And this one is the
> interesting one, because the evidence actively pointed the wrong way.

`[SCR]` API server log showing an orderly shutdown sequence. Highlight the
graceful shutdown lines.

> **VO:** The API server log showed a clean, orderly, graceful shutdown. Not a
> crash. Not an OOM kill. Not a panic. A textbook shutdown sequence.
>
> And a graceful shutdown reads as *deliberate*. Something must have told it to
> stop. So we went looking for what told it to stop — systemd, the upgrade
> tooling, a health check, something.

`[CAM]`

> **VO:** The API server was behaving perfectly correctly. It had lost its
> datastore, and it shut itself down rather than serve reads it could not
> guarantee. That log was a healthy component reacting to an unhealthy
> dependency.
>
> We read the evidence of correct behaviour as the problem.

`[TEXT]` `A graceful shutdown is not always a decision. Sometimes it is a symptom.`

**Note:** hold two full beats of silence after that line. It is the most
quotable moment in the video and it needs room. This is also the natural place
for a Shorts clip.

---

### THE REDIRECT — 6:00–6:45

> **VO:** So what should have redirected us, and how fast?
>
> Two minutes. It was there from the very beginning, and it was the thing we
> kept mentioning to each other without hearing it: **the running workloads were
> completely unaffected.**

`[GFX]` Elimination animation. Grey out each layer as it is excluded.

> **VO:** That single fact eliminates the network dataplane. It eliminates the
> kubelets. It eliminates the container runtime. It eliminates the CNI. All of
> those were demonstrably working, because traffic was flowing.
>
> What is left is the control plane's own state store. Nothing else.
>
> So the rule: **when the only thing that is broken is change, look at the
> datastore first.** Not the tooling that was running when it broke. The
> datastore.

`[TEXT]` `Only change is broken → look at the datastore`

`[SCR]` The command that actually found it — run against each member
individually, not through the load balancer:

```bash
etcdctl --endpoints=https://<node1-data-ip>:2379 endpoint status -w table
etcdctl --endpoints=https://<node2-data-ip>:2379 endpoint status -w table
etcdctl --endpoints=https://<node3-data-ip>:2379 endpoint status -w table
```

> **VO:** Twenty-two twenty. Two of the three members are unreachable — but only
> *from each other*. From my laptop, all three answer fine.

---

### ROOT CAUSE — 6:45–8:45

This is the payoff. Slow down. Aim for roughly 15% slower delivery than the
rest of the video.

> **VO:** The inventory had two address fields per node. One for SSH
> connectivity, on the management network. One for etcd peer traffic, on the
> data network.
>
> On two of the three nodes, the peer address had been filled in with the
> management address.

`[GFX]` Show the inventory side by side, correct node versus broken nodes.
Highlight the single wrong field. Use the network colours from earlier — the
viewer should recognise "that is the wrong colour" before you say it.

> **VO:** Now — why did this not break immediately? Why did it not break the
> day it was written?
>
> Because etcd reads its peer URLs **once, at startup**. Members that already
> have established peer connections keep using them, on whatever path those
> connections were originally built on. The configuration is wrong on disk and
> completely invisible in behaviour.

`[TEXT]` `Wrong on disk. Invisible in behaviour.`

> **VO:** It only materialises when a member restarts and re-reads its config.
> At that moment it advertises, and dials, an address the other members cannot
> route to.
>
> And this is the part that genuinely misled us. The first node restarted
> *fine*. Its config was correct. So the first node coming back healthy looked
> like proof the upgrade procedure was safe — and it proved nothing at all,
> because the failure needed a *second* member to leave.
>
> Second restart. Quorum below two. Control plane frozen.

`[GFX]` Animate it: node 1 restarts, rejoins, green. Node 2 restarts, dials the
management address, the line fails to connect. Quorum counter drops 3 → 2 → 1.
Everything goes red *except* the workload layer, which stays green.

---

### THE FIX — 8:45–9:45

> **VO:** Stop the bleeding: correct the peer addresses, then restart the
> affected members **one at a time** — verifying health after each one from
> another member, not from my workstation.

`[SCR]` Correct the config, restart one member, verify from inside a peer:

```bash
./scripts/reset.sh    # restores config, rolls members one at a time,
                      # verifying from ANOTHER member before each one
```

> **VO:** The durable fix is the more interesting one. The two address fields
> were being maintained independently, which means they *can* disagree. So they
> now derive from a single source of truth in the inventory. One value in, both
> fields out. They cannot drift apart, because there is no longer anything to
> drift.

`[TEXT]` `Two fields that must agree = a bug waiting for a restart`

---

### PREVENTION — 9:45–10:45

> **VO:** A pre-upgrade gate. Before touching any node, assert that every etcd
> member can reach every other member on its configured peer URL — executed
> **from inside each node**, not from the operator's machine.

`[SCR]` Show the check, then deliberately run it against the broken config so
it fails loudly on camera. Showing a check pass is boring. Showing it *catch the
actual incident* is the whole point.

```bash
./scripts/gate.sh     # every member -> every peer, on the peer URL that
                      # member will actually use after a restart
```

> **VO:** That is three lines. It would have failed before the first node was
> touched.
>
> And second: **never validate a rolling change against a sample of one.** The
> first node succeeding proved nothing, because the failure mode required a
> second member to leave. If your canary cannot experience the failure, it is
> not a canary.

`[TEXT]` `If your canary can't hit the failure mode, it isn't a canary`

---

### THE LESSON — 10:45–11:45

`[CAM]` Full camera. No terminal. This is the part people quote.

> **VO:** Here is the part that has nothing to do with etcd, or Kubernetes, or
> even distributed systems.
>
> Any configuration that is only consulted at startup is a landmine with a delay
> fuse — and the length of that fuse is however long it has been since your last
> restart.
>
> Your systems are full of these. Connection strings. TLS paths. Bind addresses.
> Feature flags read once into a constant. Every one of them is currently
> unverified, and you will find out whether it is correct at the least
> convenient possible moment: during a restart, which is usually during an
> incident, or during a change.

`[TEXT]` `Config read only at startup = a landmine with a delay fuse`

> **VO:** And the operational habit that follows from it: when you verify
> connectivity, verify it from the perspective of the component that needs it —
> not from yours.
>
> Reachability from your laptop on the management network is not evidence about
> a data network. On multi-homed hosts, those two answers routinely differ. Ours
> differed for weeks before anyone found out.

---

### OUTRO — 11:45–12:15

> **VO:** The full written postmortem is in the repo, in a fixed schema, and it
> includes the wrong hypotheses in writing — link in the description. If you
> have an incident worth writing up, it takes pull requests.
>
> If this was useful, subscribe — this is a series, and the next one is
> [TOPIC].

Ask for the subscribe **once**, at the end, after value has been delivered. End
screen with one video and the subscribe element. Keep talking over the end
screen for a few seconds — silent end screens get clicked away.

---

## 4. Demo environment

### Design goal

Reproduce the *asymmetry* that defines this incident: management addresses that
are reachable **from the operator** but **not between the nodes**. That asymmetry
is what made the incident confusing, and a lab that does not reproduce it will
not demo honestly.

### How the asymmetry is achieved

**Built: GCP + kubespray.** See `lab-0001/README.md` for the full design.

GCP requires each NIC to live in a different VPC, which maps directly onto the
real multi-homed bare-metal layout:

| Network | Members | Purpose |
|---|---|---|
| `mgmt` VPC — `10.10.0.0/24` | cp1-3, w1, ops (nic0) | SSH, operator access, etcd *client* traffic |
| `data` VPC — `10.20.0.0/24` | cp1-3, w1 (nic1) | All Kubernetes and etcd *peer* traffic |

The asymmetry is a **priority-900 deny rule**: nodes cannot reach each other on
the mgmt VPC at all, while the ops box reaches all of them. The ops box has no
data NIC, so "it looks fine from my laptop" is literally true rather than
staged. `assert-asymmetry.sh` proves all four properties and fails the lab if
any of them regress.

### Components

- **3 × `e2-medium` control plane** — kubespray-installed, `etcd_deployment_type:
  host`, so etcd is a systemd unit with its config in `/etc/etcd.env` and the
  bug can be planted in exactly the field kubespray writes from the inventory's
  `ip=` column.
- **1 × `e2-small` worker** — runs the nginx workload that keeps serving while
  the control plane is frozen. On its own node so the split-screen is
  unambiguous.
- **1 × `e2-small` ops** — management network only. The operator's laptop.
- Real `kubectl`, real apiserver, real graceful-shutdown logs. Nothing simulated.

~$0.16/hr running, ~$0.37/day paused. A full recording day is about $1.60.

### Demo beats the lab must support

1. Healthy cluster, correct peer URLs, `endpoint health --cluster` all green.
2. Break the config on nodes 2 and 3 **without restarting** → still fully
   healthy. This is the "invisible on disk" beat and it is essential.
3. Restart node 2 → it cannot rejoin. Quorum holds at 2/3. `kubectl` still
   works. From `ops`, per-endpoint checks still answer.
4. Restart node 3 → quorum lost. `kubectl` times out. API server logs a graceful
   shutdown. **nginx keeps serving.** This is the money shot; get several takes.
5. Run the prevention gate against the broken config → it fails loudly.
6. Fix, rolling restart one at a time, verify from inside a peer each time.

**Fidelity note to state on camera:** the real incident lost quorum on the second
node restart because a member was already effectively out. The lab needs both
node 2 and node 3 to restart before quorum drops. Say this out loud in one
sentence — this audience notices, and being straight about it buys credibility.
Do not quietly fudge the arithmetic.

### Prerequisites on this machine

Verified 2026-08-02:

| Tool | Status |
|---|---|
| Terraform | 1.13.1 ✅ |
| gcloud SDK | 504.0.1 ✅ (project `clgcporg8-045`) |
| Ansible | core 2.21.0 ✅ (runs on the ops box, not here) |
| `kubectl` | present ✅ |
| `jq` | 1.8.1 ✅ |
| `etcdctl` | ❌ not needed — the scripts run it on the nodes |
| `ffmpeg` | ❌ not installed — `brew install ffmpeg` if editing needs it |
| OBS | ❌ not installed |

### The lab

Built and living in `lab-0001/`. Start with `lab-0001/README.md`, then
`lab-0001/RUNBOOK.md` for shot order.

```bash
cd lab-0001
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
$EDITOR terraform/terraform.tfvars      # project_id + operator_cidr
./scripts/00-preflight.sh
./scripts/01-provision.sh               # ~3 min
./scripts/02-install-kubespray.sh       # 20-35 min
```

Design constraints it holds to, and which any future episode lab should:

- **`reset.sh` returns to known-good in under 60 seconds** — config restore plus
  a rolling etcd restart, not a rebuild. You run it twenty-plus times per
  session, so this is the single most important property of the lab.
- **Every on-camera command is in `RUNBOOK.md` verbatim, in shot order.**
  Recording never involves improvising a command.
- **The lab self-checks.** `assert-asymmetry.sh` proves the incident is still
  reproducible; `03-verify-healthy.sh` gates every take. A lab that silently
  stops reproducing the bug is worse than no lab.
- **RFC1918 only**, `10.10.0.0/24` and `10.20.0.0/24`. Never put a routable
  address on screen — the repo's CI rejects them in prose and the same
  discipline applies on camera.
- **Static internal IPs**, so the runbook never needs a lookup mid-take.
- Prompt must be a clean `$ ` with no hostname, no path, no git branch, no
  personal identifiers.

---

## 5. Recording setup

### Terminal

- **Font 20–22 pt minimum.** Most viewers are on a phone. Anything smaller is
  unreadable and they leave. Test by playing back a clip on your own phone.
- Window sized to roughly 100×30, not fullscreen on a 4K display.
- High-contrast dark theme. Avoid low-contrast pastel themes; YouTube's
  compression destroys them.
- Prompt: `PS1='$ '`. Nothing else.
- `export HISTFILE=/dev/null` for the session.
- Disable ligatures — they render oddly after compression.

### Screen and audio

- Record 1080p60 (or 4K downscaled — sharper text after compression).
- **Audio matters more than video.** Viewers forgive a soft picture and leave
  instantly over bad sound. Dynamic mic, close, treated room if possible.
- Record voiceover **separately** from the screen capture. Terminal work and
  clean narration do not coexist; commanding and explaining at the same time
  produces stumbles and dead air.
- Room tone: capture 30 seconds of silence for noise reduction.
- Target −16 LUFS integrated, true peak ≤ −1 dBTP.

### Before you hit record

- [ ] Docker Desktop running, lab reset to known-good
- [ ] Do Not Disturb on; Slack, Mail, calendar alerts quit entirely
- [ ] Every other window closed — no stray tabs in a screen capture
- [ ] No company names, real hostnames, cloud account IDs, or routable IPs
      anywhere on screen, including shell history and tab titles
- [ ] `RUNBOOK.md` open on a second display
- [ ] Phone silenced and face down
- [ ] 30 s of room tone recorded

---

## 6. Editing

- **Cut every pause over ~400 ms.** Dead air is the main reason technical
  videos lose viewers.
- Cut waiting time, but **not the four-second `kubectl` hang in the cold open**
  — that discomfort is doing narrative work. It is the one pause to keep.
- Zoom in on any command or log line being discussed. Do not expect the viewer
  to find it in a full-screen terminal.
- Keyword text overlays on the six `[TEXT]` beats. They are the moments people
  screenshot and share.
- Pattern interrupt roughly every 40 s: cut between camera, terminal, and
  diagram. Never hold one visual for more than ~60 s.
- Music: optional, instrumental, ducked to −25 dB under voice. If it competes
  with the voice at all, drop it entirely — no music beats bad music.
- Captions: upload a corrected `.srt`. Auto-captions mangle `etcd`,
  `kubectl`, and `quorum`, and captions affect both accessibility and search.

### Derivative content

- **Short (< 60 s):** the graceful-shutdown reveal at 4:30–6:00. It is
  self-contained, counter-intuitive, and needs no setup. Best standalone clip in
  the episode.
- **Second Short:** the elimination logic at 6:00–6:45 — "only change is broken,
  look at the datastore."
- The `[TEXT]` lines are ready-made post copy for LinkedIn/X on publish day.

---

## 7. Publish checklist

- [ ] Title matches the thumbnail promise; video pays it off
- [ ] Thumbnail checked at 168×94 px
- [ ] Chapters start at `00:00`, three or more, matching the final cut
- [ ] Description hook in the first two lines
- [ ] Repo link correct and public; **no link to `video-scripts/`**
- [ ] Corrected captions uploaded
- [ ] End screen: one video + subscribe
- [ ] Category "Science & Technology"; "Not made for kids"
- [ ] Watched end to end at 1× before publishing
- [ ] Pinned comment posted
- [ ] Once live: add `video: https://...` to the front matter of
      `stories/0001-...md`, run `python scripts/build_index.py`, and open a PR.
      **This is a maintainer-only field** — do not set it before the episode
      exists.

---

## 8. Post-publish

Check at 48 hours and at 7 days:

- **Retention graph.** Find the first big drop. If it is before 0:30 the hook is
  wrong; if it is in the architecture section it is too slow; if viewers make it
  past 6:00 the format works and the next episode should keep this shape.
- **Click-through rate.** Below ~4% is a packaging problem, not a content
  problem — swap the thumbnail before touching anything else.
- **Comments** describing their own version of this failure are the strongest
  signal that the "generalizable lesson" framing landed. They are also the
  best source of contributed entries for the repo — reply and point them at
  `CONTRIBUTING.md`.
