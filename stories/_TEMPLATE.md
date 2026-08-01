---
id: "0000"
title: Replace with a symptom-first title
stack: [kubernetes]
severity: sev3
detection: alerting
time_to_detect: 5m
time_to_resolve: 30m
root_cause_category: configuration
blast_radius: namespace
contributed_by: "@your-github-handle"
---

## Symptom

What it looked like from the outside, before anyone knew the cause. Include what
was still working — that is usually the most diagnostic detail in the entry.

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

The mechanism, not just the label. Explain why the system behaved the way it did.

## Fix

What was changed to restore service. Separate the stop-the-bleeding action from
the durable fix if they were different.

## What would have prevented it

A specific check, guardrail, or runbook step — not "better monitoring".

## Generalizable lesson

The part a reader on a completely different stack can still use.
