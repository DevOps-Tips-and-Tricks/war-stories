# war-stories

Anonymised production incidents in a fixed schema — each one starting from the
general problem underneath it, and including the hypotheses that turned out to
be wrong.

Every entry is in two halves. It opens with the mechanism as a class of failure
and a lab you can run in five minutes to see it happen on your own machine —
`df` and `du` disagreeing, a config that is only read at startup — and only then
tells the production incident where that mechanism cost somebody a night. The
general problem is what makes the entry useful to a reader on a different stack;
the incident is what makes it true.

Postmortem collections usually publish the answer. That is the least useful
part. What separates a senior engineer from a competent mid-level one is not
knowing more root causes, it is chasing fewer wrong ones, and that skill is
transferable only if somebody writes the wrong turns down. So every entry here
has a required **What we thought it was** section, and an entry without one does
not get merged.

Part of [DevOps Tips and Tricks](https://www.youtube.com/@DevOpsTipsAndTricks).

## The index

<!-- INDEX:START -->

| # | Incident | General problem | Stack | Sev | Root cause | Time to resolve | By |
|---|---|---|---|---|---|---|---|
| 0001 | [df said the disk was full, du said it was half empty](stories/0001-df-said-the-disk-was-full-du-said-it-was-half-empty.md) | A deleted file with an open descriptor still owns its blocks | `linux`, `kubernetes`, `mongodb`, `logrotate` | SEV2 | capacity | 2h | [@maintainer](https://github.com/maintainer) |
| 0003 | [etcd quorum lost during rolling upgrade](stories/0003-etcd-quorum-lost-during-rolling-upgrade.md) | Config read only at startup fails at the next restart, not when it changes | `kubernetes`, `etcd`, `kubespray` | SEV1 | configuration | 1h35m | [@maintainer](https://github.com/maintainer) |

_2 entries: **1** capacity, **1** configuration._

<!-- INDEX:END -->

## Adding an entry

```bash
pip install -r requirements.txt
cp stories/_TEMPLATE.md stories/00XX-your-short-title.md
$EDITOR stories/00XX-your-short-title.md
python scripts/validate.py
python scripts/build_index.py
```

Then open a pull request with that one file plus the regenerated README.

See [CONTRIBUTING.md](https://github.com/DevOps-Tips-and-Tricks/.github/blob/main/CONTRIBUTING.md)
for the worked example. It is worth two minutes — it is the actual
specification, and the rules underneath it are only there to be enforced by CI.

## Anonymisation

Nothing here should identify a real environment. No employer names, customer
names, internal hostnames, or routable IP addresses. Use RFC1918 space or the
documentation ranges `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`.

CI rejects routable IPv4 addresses automatically. It cannot detect a leaked
hostname or company name, so that part is on you and on review. If you are
unsure whether a detail is identifying, remove it — no entry has ever been
weakened by being one detail more generic.

The `date` field is deliberately month-precision only, for the same reason.

## What makes a good entry

- **The general problem stands on its own.** Someone who has never seen your
  stack should be able to read the first section and recognise the shape of the
  bug in theirs. "Disk filled up" is a category; "`df` and `du` measure
  different things" is a mechanism.
- **The reproduction actually runs.** Minimal, no proprietary parts, and it ends
  with the two tools disagreeing on screen. If it cannot be reproduced on one
  machine in a few minutes, say what the smallest honest version is.
- **The symptom is described before the cause.** Write it the way you
  experienced it, not the way you understand it now.
- **Something in it is surprising.** A full disk is not an entry. A full disk
  that presented as an authentication failure is.
- **The lesson survives a change of stack.** If it only applies to one tool at
  one version, it is a bug report, not a war story.
- **Severity is not the bar.** A 20-minute sev3 with a genuinely non-obvious
  cause beats a six-hour sev1 with a boring one.

## Schema

Front matter is validated against
[`schema/war-story.schema.json`](schema/war-story.schema.json) on every pull
request, along with section presence, section order, filename format, id
uniqueness, and leaked addresses.

The nine H2 sections must all be present, non-empty, and in this order:
`## The general problem`, `## Reproduce it`, `## Symptom`, `## Timeline`,
`## What we thought it was`, `## Actual root cause`, `## Fix`,
`## What would have prevented it`, `## Generalizable lesson`. The validator
compares the headings literally, so a reworded one reads as a missing section.

| Field | Notes |
|---|---|
| `id` | Quoted, zero-padded, four digits. Never reused |
| `title` | Symptom-first, sentence case, 10–80 characters |
| `concept` | The general problem, stated without the incident. 10–80 characters |
| `stack` | 1–6 lowercase tags |
| `severity` | `sev1`–`sev4` |
| `detection` | `alerting`, `customer`, `manual`, `chance` |
| `time_to_detect` / `time_to_resolve` | Compound duration: `4m`, `2h30m`, `1d4h` |
| `root_cause_category` | `configuration`, `capacity`, `code`, `dependency`, `process` |
| `blast_radius` | `single-service` … `global` |
| `contributed_by` | Your GitHub handle, with the `@` |
| `video` | Optional. Set by maintainers when an entry becomes an episode |
| `date` | Optional. `YYYY-MM` only |

The categorisation exists so the corpus can be queried once it is large enough
to be interesting — "show me every configuration failure that took over an hour
to detect", or "every entry whose general problem is a caching assumption" — is
a better source of video topics, and of your own team's priorities, than a
folder of prose.

## Licence

Content is CC BY-SA 4.0. Scripts are Apache-2.0. By contributing you agree to
publish under those terms and confirm you have the right to share the material.
