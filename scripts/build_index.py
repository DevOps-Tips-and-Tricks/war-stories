#!/usr/bin/env python3
"""Regenerate the entry index in README.md from story front matter.

Usage:
    python scripts/build_index.py            # rewrite README.md in place
    python scripts/build_index.py --check    # fail if README.md is stale (CI)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STORIES_DIR = ROOT / "stories"
README = ROOT / "README.md"

START = "<!-- INDEX:START -->"
END = "<!-- INDEX:END -->"

FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

SEVERITY_ORDER = {"sev1": 0, "sev2": 1, "sev3": 2, "sev4": 3}


def load_entries() -> list[dict]:
    entries = []
    for path in sorted(STORIES_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        match = FRONT_MATTER_RE.match(path.read_text(encoding="utf-8"))
        if not match:
            continue
        data = yaml.safe_load(match.group(1)) or {}
        data["_path"] = f"stories/{path.name}"
        entries.append(data)
    return entries


def render_table(entries: list[dict]) -> str:
    rows = [
        "| # | Incident | Stack | Sev | Root cause | Time to resolve | By |",
        "|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(entries, key=lambda e: str(e.get("id", "")))
    for entry in ordered:
        stack = ", ".join(f"`{s}`" for s in entry.get("stack", []))
        handle = str(entry.get("contributed_by", "")).lstrip("@")
        by = f"[@{handle}](https://github.com/{handle})" if handle else ""
        rows.append(
            "| {id} | [{title}]({path}) | {stack} | {sev} | {cause} | {ttr} | {by} |".format(
                id=entry.get("id", ""),
                title=entry.get("title", ""),
                path=entry["_path"],
                stack=stack,
                sev=str(entry.get("severity", "")).upper(),
                cause=entry.get("root_cause_category", ""),
                ttr=entry.get("time_to_resolve", ""),
                by=by,
            )
        )
    return "\n".join(rows)


def render_stats(entries: list[dict]) -> str:
    if not entries:
        return ""
    by_category: dict[str, int] = {}
    for entry in entries:
        key = entry.get("root_cause_category", "unknown")
        by_category[key] = by_category.get(key, 0) + 1
    total = len(entries)
    parts = [
        f"**{count}** {name}"
        for name, count in sorted(by_category.items(), key=lambda kv: -kv[1])
    ]
    return f"\n\n_{total} entries: " + ", ".join(parts) + "._"


def build_block(entries: list[dict]) -> str:
    return f"{START}\n\n{render_table(entries)}{render_stats(entries)}\n\n{END}"


def main() -> int:
    check_only = "--check" in sys.argv

    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(
            f"README.md is missing the {START} / {END} markers.",
            file=sys.stderr,
        )
        return 2

    entries = load_entries()
    block = build_block(entries)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    updated = pattern.sub(lambda _: block, text)

    if updated == text:
        print("Index already up to date.")
        return 0

    if check_only:
        print(
            "::error file=README.md::index is stale; run "
            "'python scripts/build_index.py' and commit the result"
        )
        return 1

    README.write_text(updated, encoding="utf-8")
    print(f"Index rewritten with {len(entries)} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
