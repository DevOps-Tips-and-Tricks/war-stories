---
name: asd-ste100
description: Write PR/MR descriptions (and other prose asked for "in ASD-STE100" or "Simplified Technical English" / "STE") using the ASD-STE100 discipline — short sentences, one idea per sentence, active voice, imperative instructions, approved-word consistency. Use whenever the user asks for an MR/PR description, release note, or any text "in STE" or "ASD-STE100".
---

# ASD-STE100 (Simplified Technical English)

ASD-STE100 is an aerospace/defence writing standard. It exists to make
technical text readable by non-native English speakers and impossible to
misread. Apply its rules whenever a user asks for text "in ASD-STE100," "in
STE," or "in Simplified Technical English" — most often a PR/MR description
in this repository.

## Writing rules

1. **One idea per sentence.** Split any sentence that describes two changes,
   two conditions, or a change and its reason, into two sentences.
2. **Keep sentences short.** Target 20 words for an instruction, 25 words for
   a description. If a sentence runs longer, split it.
3. **Use active voice.** "The validator rejects an unquoted id," not "An
   unquoted id is rejected by the validator."
4. **Use the imperative for instructions.** "Run `scripts/validate.py`," not
   "You should run" or "It is necessary to run."
5. **Use simple tenses only.** Present simple for facts and instructions,
   past simple for events. Avoid the perfect and continuous tenses ("has been
   added," "is being validated").
6. **Use the same word for the same thing, every time.** Do not vary
   terminology for style. If a change adds a field, call it a "field" in
   every sentence, not "field" once and "property" or "attribute" later.
7. **Use common, simple verbs.** "Use," "add," "remove," "check," "start,"
   "show." Avoid "utilize," "leverage," "facilitate," "initiate."
8. **Use articles.** Do not drop "a," "an," or "the" for brevity — dropped
   articles read as clipped and can be ambiguous.
9. **Avoid noun strings.** No more than two nouns in a row ("index build
   script" is fine; "story front matter field validation logic" is not — say
   "logic that validates front matter fields in a story").
10. **Prefer the positive form.** "Only nine sections are required" reads
    faster than "No more or fewer than nine sections are permitted."
11. **State the change before the reason**, as two sentences, not one
    subordinated clause. "The schema now requires `concept`. This lets the
    index show the general problem beside the title."
12. **Spell out an abbreviation on first use**, then use it consistently:
    "pull request (PR)."
13. **Use a list for three or more related items** instead of a comma-run
    sentence.
14. **No idioms, humour, or hedging.** No "basically," "just," "obviously,"
    "should probably." State the fact.

## Applying this to an MR/PR description in this repository

Structure the description in this order, each as its own short section:

1. **Summary** — one or two sentences: what the change does, in the
   imperative-adjacent present tense used for facts ("This adds...", "This
   renames...").
2. **Changes** — a bulleted list, one bullet per distinct change, each
   bullet a single short sentence.
3. **Validation** — the exact commands run and their result, as fact
   sentences ("`scripts/validate.py` passes. `scripts/build_index.py
   --check` passes.").
4. **Notes** — anything a reviewer must know that does not fit the above
   (a draft entry with placeholder sections, a rename, a follow-up needed).

Do not use this style for the repository's editorial prose (`CLAUDE.md`
voice rules, story bodies) unless the user asks for that too — those follow
their own house style, documented in `CLAUDE.md` under "Voice."
