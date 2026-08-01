# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this repository is

`war-stories` is a curated corpus of anonymised production incidents, published
under the [DevOps Tips and Tricks](https://github.com/DevOps-Tips-and-Tricks)
organisation. Entries are the source material for episodes on the
[YouTube channel](https://www.youtube.com/@DevOpsTipsAndTricks).

Two consequences follow from that, and they drive most of the rules below:

1. **The corpus is queryable, not just readable.** Front matter is structured
   and validated so questions like "every configuration failure that took over
   an hour to detect" can be answered mechanically. Never treat the front matter
   as decoration.
2. **Every entry is a script in waiting.** It is read aloud, on camera, by
   someone who was not in the incident. Prose that only makes sense to the
   person who lived it has failed even if it is accurate.

The defining constraint of the project is the required **What we thought it
was** section. Most postmortem collections publish only the answer. This one
publishes the wrong turns, because the transferable skill is chasing fewer bad
hypotheses, not memorising more root causes. An entry without a real, specific
account of the discarded hypotheses does not get merged, regardless of how good
the rest of it is.

## Layout

| Path | Purpose |
|---|---|
| `stories/` | One Markdown file per incident. `_TEMPLATE.md` is skipped by all tooling (leading underscore) |
| `schema/war-story.schema.json` | Draft 2020-12 schema for front matter. `additionalProperties: false` |
| `scripts/validate.py` | Front matter, section presence/order/length, filename, id uniqueness, leaked IPs |
| `scripts/build_index.py` | Regenerates the README table between the `INDEX:START` / `INDEX:END` markers |
| `.github/workflows/validate.yml` | Runs both scripts on PRs, plus a `lychee` dead-link check |
| `README.md` | Contributor-facing spec. The index block inside it is **generated** |

## Working commands

```bash
pip install -r requirements.txt        # jsonschema, PyYAML

python scripts/validate.py             # must exit 0
python scripts/build_index.py          # rewrite the README index in place
python scripts/build_index.py --check  # what CI runs; fails if the index is stale
```

Run **both** after touching anything in `stories/`. A new entry always produces
a README diff — a PR that adds a story without the regenerated index fails CI.

Never hand-edit the table between `<!-- INDEX:START -->` and
`<!-- INDEX:END -->`; it is overwritten. Everything else in README.md is
hand-written and must be edited by hand.

## Adding an entry

```bash
cp stories/_TEMPLATE.md stories/00XX-your-short-title.md
```

Pick the next unused id. Ids are never reused, even if an entry is deleted.

### Front matter rules that bite

- `id` **must be quoted** (`id: "0042"`). Unquoted, YAML eats the leading zeros
  and `validate.py` rejects it with a dedicated error.
- The filename must be exactly `{id}-{slugify(title)}.md`. Slugification is
  ASCII-fold, lowercase, non-alphanumerics collapsed to `-`. **If you change the
  title, rename the file** — this is the most common validation failure.
- `title` is 10–80 characters, sentence case, symptom-first, no trailing period.
  "etcd quorum lost during rolling upgrade", not "Fixing our etcd inventory bug".
- `stack` is 1–6 lowercase tags matching `^[a-z0-9][a-z0-9.-]*$`.
- `time_to_detect` / `time_to_resolve` are compound durations: `4m`, `2h30m`,
  `1d4h`. Not `90 minutes`, not `1.5h`.
- `date` is optional and **year-month only** (`2025-11`). That imprecision is an
  anonymisation measure — never add a day.
- `video` is optional and set **by maintainers only**, when an entry becomes an
  episode. Do not populate it when drafting.
- No other keys are permitted. The schema is closed.

### Section rules

The seven H2 sections must all be present, non-empty, and **in this order**:

```
## Symptom
## Timeline
## What we thought it was
## Actual root cause
## Fix
## What would have prevented it
## Generalizable lesson
```

Headings must match those strings exactly — the validator compares literals, so
a reworded or re-cased heading reads as a missing section. Each section needs
more than 40 characters of body or it is rejected as a stub. Additional H2s
beyond the seven are allowed but are unusual; prefer folding the material into
an existing section.

## Editorial standards

These are what separates a merged entry from a rejected one. Apply them when
drafting, and enforce them when reviewing.

**Symptom before cause.** Write each section from the epistemic position of the
people in the incident at that moment. The Symptom section must not contain the
answer, or even hint at it. Reveal in order.

**Say what was still working.** In the reference entry (`stories/0001-…`), "the
workloads stayed up" is the single most diagnostic fact, and it is what
should have redirected the responders in two minutes. Negative space narrows the
search faster than symptoms do. Ask for it explicitly if a draft omits it.

**"What we thought it was" must be sympathetic to the wrong hypothesis.**
Explain why each discarded theory was *reasonable given what was visible*, not
why it was dumb. An entry that makes past-you look foolish teaches nothing; an
entry that shows a competent engineer being misled by a real signal teaches the
signal. Close the section with the observation that should have redirected the
investigation sooner.

**Mechanism, not label.** "Actual root cause" explains why the system behaved as
it did. "Misconfiguration" is a category, not a cause. The reader should be able
to predict the same failure in a system they have never seen.

**Separate the stop-the-bleeding fix from the durable one** whenever they
differ. They usually differ, and conflating them hides the interesting part.

**"What would have prevented it" must be executable.** A named check, gate, or
runbook step. "Better monitoring" and "more testing" are non-answers and should
be pushed back on.

**The lesson must survive a change of stack.** If it only applies to one tool at
one version, it is a bug report. The generalizable lesson is what the video is
actually about.

**Severity is not the bar.** A 20-minute sev3 with a non-obvious cause is a
better entry — and a better episode — than a six-hour sev1 with a boring one.
Something in the entry must be surprising. A full disk is not an entry; a full
disk that presented as an authentication failure is.

### Voice

Plain, past tense, first person plural for the responding team. No marketing
register, no "it turns out", no exclamation marks, no emoji. Do not open a
section by restating its heading. Prefer British spelling for consistency with
the existing prose (`anonymised`, `licence`, `categorisation`) — except the
literal heading `## Generalizable lesson`, which is fixed by the validator.

Backtick all commands, fields, paths, and log excerpts. Timeline entries use
`` `HH:MM` `` timestamps, relative or wall-clock, consistently within an entry.

## Anonymisation — treat as a hard gate

Nothing may identify a real environment: no employer or customer names, no
internal hostnames or DNS suffixes, no routable IP addresses, no ticket ids, no
Slack channel names, no dashboard URLs, no team member names or handles other
than `contributed_by`.

`validate.py` rejects routable IPv4 automatically. RFC1918, loopback,
link-local, multicast and the documentation ranges `192.0.2.0/24`,
`198.51.100.0/24`, `203.0.113.0/24` pass. **CI cannot detect a leaked hostname
or company name** — that is a review responsibility, and yours when drafting or
editing.

When you notice a detail that might be identifying, remove or generalise it and
say so in your summary to the user. No entry has ever been weakened by being one
detail more generic. If a user supplies material that appears to come from a
real employer, flag the identifying details explicitly before committing rather
than silently laundering them.

## Reviewing a contributed entry

Check in this order and report failures with file:line:

1. `python scripts/validate.py` and `python scripts/build_index.py --check`.
2. Anonymisation sweep — the part CI cannot do.
3. Is "What we thought it was" real? A single sentence, or hypotheses invented
   after the fact to satisfy the section, is the failure mode to watch for.
4. Is anything in it surprising, and does the lesson survive a change of stack?
5. Does the Symptom section leak the answer?

## Working conventions

- The user is the maintainer of this repository and the channel. Content
  judgement calls (which incidents are worth an entry, what becomes an episode)
  are theirs — surface the trade-off rather than deciding silently.
- Prefer one entry per PR, plus the regenerated README.
- Scripts are Apache-2.0; content is CC BY-SA 4.0. Keep that split intact if
  adding files.
- Python 3.12 in CI. Avoid syntax newer than that in `scripts/`.
- Do not add dependencies to `requirements.txt` without asking; the toolchain is
  deliberately two packages.
