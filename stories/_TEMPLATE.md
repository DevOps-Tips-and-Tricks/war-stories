---
id: "0000"
title: Replace with a symptom-first title
concept: Replace with the general problem, stated without this incident
stack: [kubernetes]
severity: sev3
detection: alerting
time_to_detect: 5m
time_to_resolve: 30m
root_cause_category: configuration
blast_radius: namespace
contributed_by: "@your-github-handle"
---

## The general problem

The mechanism, described as a class of failure rather than as an event. No
company, no cluster, no date — someone who has never seen your stack should be
able to read this section alone and recognise the shape of the bug in theirs.

State what two things are being confused, or what assumption the system quietly
breaks. `df` and `du` disagreeing is a mechanism. "Disk filled up" is not.

## Reproduce it

A minimal lab that produces the same mechanism on one machine, in minutes, with
no proprietary parts. Commands in fenced blocks, in the order they are run, with
the output that proves the divergence.

```bash
# setup — smallest thing that shows the behaviour
# trigger — the one command that breaks the invariant
# observe — the two tools that now disagree
```

Say what to look at and what a healthy run looks like, so the reader can tell
the difference. Note any teardown that matters.

## Symptom

What the real incident looked like from the outside, before anyone connected it
to the mechanism above. Include what was still working — that is usually the
most diagnostic detail in the entry.

## Timeline

- `00:00` — First event.
- `00:05` — Detection.
- `00:30` — Resolution.

## What we thought it was

Required. The hypotheses you chased and discarded, and why each one was
reasonable at the time. If you knew the answer immediately, this incident is
probably not worth an entry.

Close with the signal that should have redirected you sooner.

## Actual root cause

The mechanism from the first section, as it actually manifested here. Explain
what turned the general problem into this outage: which component held the
descriptor, which config was read only at startup, which layer hid the truth.

## Fix

What was changed to restore service. Separate the stop-the-bleeding action from
the durable fix if they were different.

## What would have prevented it

A specific check, guardrail, or runbook step — not "better monitoring".

## Generalizable lesson

The part a reader on a completely different stack can still use. It should read
as a stronger version of the general problem, earned by the incident.
