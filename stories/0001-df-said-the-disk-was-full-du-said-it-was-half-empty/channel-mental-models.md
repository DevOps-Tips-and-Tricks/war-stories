# The thing this channel actually teaches

Channel-level doctrine, not episode-specific. Read before scripting any episode.

---

## Mechanism vs model

A **mechanism** is a fact about one system: deleted-but-open files hold blocks.
Useful once, when the viewer hits that exact problem.

A **model** is a move the viewer can run on a problem you never showed them:
*when two instruments disagree, ask what each one measures.*

Every episode will teach a mechanism, because that is what makes it concrete. The
mechanism is the vehicle. The moves are the cargo.

The test for whether an episode carried cargo: **could a viewer apply something from it
to a problem in a different part of the stack?** If the only takeaway is "now I know
about `lsof +L1`", the episode taught a fact.

---

## The moves already inside episode 01

These are all in the material. None of them are currently said out loud.

| # | the move | where it lives | where else it applies |
|---|---|---|---|
| 1 | **When two instruments disagree, neither is broken. They measure different things.** | Beat 2, df vs du | RSS vs working set, p50 vs p99, nodefs vs pod disk, `rbd du` vs `df` |
| 2 | **The system enters the broken state before any instrument shows it.** | Beat 1 — df and du still agree while the writer is already stranded | any "it was fine until suddenly it wasn't" incident |
| 3 | **Name your hypothesis out loud before you test it.** | Act 3, the wrong first guess | every incident, always |
| 4 | **Narrow with what you already know before you search wider.** | the lsof ladder: `df` already told you which filesystem | log search, trace search, bisecting anything |
| 5 | **Prefer the reversible action — and know what the irreversible one costs.** | truncate vs restart | failover, scaling, cache flush, schema change |
| 6 | **Verify with what did not change.** | the fd pane after truncate | any surgical fix on a live system |
| 7 | **Mitigation is not a fix. Say which one you are doing.** | truncate vs the logrotate config | every incident with a workaround |
| 8 | **Under every tool there is a ground truth. Know where it is.** | `/proc/<pid>/fd` beneath lsof | cgroups beneath `docker stats`, etcd beneath `kubectl` |

**Pick three for episode 01.** Eight labels in one video is a lecture. The three that
fit this episode's spine:

- **Move 1** at Beat 2 — it is the episode's title
- **Move 6** at Beat 4 — the most unusual and the most memorable
- **Move 7** at Beat 6 — it is the difference between stopping the bleeding and fixing
  the cause

Move 3 belongs in Act 3, but demonstrate it rather than label it. Saying the wrong
hypothesis out loud *is* the lesson; captioning it makes it smaller.

The rest accumulate across episodes.

---

## Making a move visible

Three ways, in increasing order of how well they work.

**Weakest: say it.** "This is a general principle you should remember." The viewer
hears a platitude and forgets it.

**Better: name it at the moment it pays off.** Right after the df/du divergence lands —
not before — one short line: *"That's the first general thing here. When two tools
disagree, neither one is broken. They are answering different questions. You'll meet
that again in memory metrics, and in latency percentiles."* Twelve seconds. The
generalisation arrives while the specific case is still on screen.

**Strongest: let the viewer be wrong first.** Before revealing anything at Beat 2, ask
the question and leave two seconds of silence: *"The directory is empty. The disk is
full. Where is the space?"* A viewer who guesses — even wrongly — remembers the answer.
A viewer who is told forgets it.

Use the third one once per episode. It costs two seconds and it is the single highest-
leverage thing in this document.

---

## What calm actually is

Calm during an incident is not temperament. It is structure. Specifically it is four
things, and all four are teachable.

1. **Always having a next question**, so not knowing the answer is never a dead end.
2. **Knowing which actions are reversible**, so acting does not feel like gambling.
3. **Separating "stop the bleeding" from "find the cause"**, so the two do not compete
   for attention.
4. **Expecting the first hypothesis to be wrong**, so being wrong is a step in the
   process rather than a failure.

You cannot tell someone to be calm. You can show them someone who is calm while not
knowing something, and you can show them the structure that makes it possible.

Which leads to the format decision that matters more than everything above.

---

## The unscripted take is the curriculum

The script already says to record Act 2 without solving it first. With this goal, that
stops being a stylistic choice and becomes the method.

**A video in which you are never confused cannot teach anyone how to be un-panicked
while confused.**

Your instinct will be to polish — to retake until you look like you knew all along.
That instinct produces a better-looking video and a worse one for your actual purpose.
Every hesitation you cut is an example of composure under uncertainty that you deleted.

Keep:

- The pause before you decide what to check next
- The command that returns nothing useful, and what you do about it
- "I don't know yet, so here's what I'd rule out first"
- Saying a hypothesis and then disproving your own hypothesis on camera

Cut only: dead air with nothing happening, actual mistakes you correct off-camera, and
anything that discloses an employer's infrastructure.

This is also your moat. A model can generate a confident explanation of anything. It
cannot generate a person being uncertain in a well-structured way, because that comes
from having been there.

---

## Practice, not just teaching

You said teaching **and** practising. Teaching is the video; practising is the repo.

The repo is not a bonus resource. It is the other half of the curriculum, and it should
be framed that way: *"Everything I just did is in the repo. Build it, break it
yourself, and try to find it before you watch the second half."*

What that changes:

- `lab-setup.sh` and `teardown.sh` are deliverables, not conveniences
- Each episode's README states the exercise, not just the commands
- A viewer who runs the lab has practised the move, not just watched it

Over time this is what separates the channel from a playlist of war stories: a viewer
can work through it.

---

## The episode formula this produces

> one real incident + one mechanism + two or three named moves + a reproducible lab

Scales to every episode. The mechanisms vary; the moves accumulate. After ten episodes
the moves are the channel's actual curriculum, and that is a thing people subscribe to
and send to their juniors.

Keep a running list of which move appeared in which episode. When a move recurs, say so
on camera — *"this is the same thing we did with df and du in episode one"* — because
repetition across different mechanisms is what converts a move into a habit.

---

## One revision to earlier advice

I argued against a recap at the end of the episode. That argument was about recapping
the **mechanism** — the viewer has already watched it happen, so replaying it is dead
weight after the emotional peak of Act 3.

Naming the **moves** at the end is a different thing, and it is worth 30 seconds. The
viewer has not heard them as a set, and the set is the part meant to persist. Three
lines, no visuals, straight to camera, then the next-episode line and stop.

> "Three things worth taking from this, none of them about log files.
> One: when two tools disagree, neither is broken.
> Two: when you fix something surgically, check what didn't change.
> Three: a workaround is not a fix — know which one you just did."
