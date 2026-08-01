#!/usr/bin/env python3
"""Validate war story entries.

Checks, in order:
  1. Front matter exists and is parseable YAML.
  2. Front matter validates against schema/war-story.schema.json.
  3. All required H2 sections are present, in order, and non-empty.
  4. The filename matches the id and the slugified title.
  5. Ids are unique across the corpus.
  6. No routable IP addresses leaked into the prose.

Exits non-zero on any failure. Emits GitHub Actions annotations when running
in CI so errors appear inline on the pull request diff.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
STORIES_DIR = ROOT / "stories"
SCHEMA_PATH = ROOT / "schema" / "war-story.schema.json"

REQUIRED_SECTIONS = [
    "Symptom",
    "Timeline",
    "What we thought it was",
    "Actual root cause",
    "Fix",
    "What would have prevented it",
    "Generalizable lesson",
]

FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Addresses that may legitimately appear in a published entry.
DOCUMENTATION_NETS = [
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("233.252.0.0/24"),
]

IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"


class Problem:
    def __init__(self, path: Path, message: str, line: int | None = None):
        self.path = path
        self.message = message
        self.line = line

    def render(self) -> str:
        rel = self.path.relative_to(ROOT)
        if IN_CI:
            where = f"file={rel}"
            if self.line:
                where += f",line={self.line}"
            return f"::error {where}::{self.message}"
        location = f"{rel}:{self.line}" if self.line else str(rel)
        return f"{location}: {self.message}"


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def is_publishable_ip(raw: str) -> bool:
    try:
        addr = ipaddress.ip_address(raw)
    except ValueError:
        # Not a real address (e.g. a version string like 1.2.3.4 that isn't
        # valid); leave it alone rather than raising a false positive.
        return True
    if addr.is_private or addr.is_loopback or addr.is_link_local:
        return True
    if addr.is_unspecified or addr.is_multicast:
        return True
    return any(addr in net for net in DOCUMENTATION_NETS)


def line_of(haystack: str, needle: str) -> int:
    index = haystack.find(needle)
    if index == -1:
        return 1
    return haystack.count("\n", 0, index) + 1


def check_sections(body: str, path: Path, problems: list[Problem]) -> None:
    found = H2_RE.findall(body)
    missing = [s for s in REQUIRED_SECTIONS if s not in found]
    for section in missing:
        problems.append(Problem(path, f"missing required section: ## {section}"))

    present = [s for s in found if s in REQUIRED_SECTIONS]
    expected_order = [s for s in REQUIRED_SECTIONS if s in present]
    if present != expected_order:
        problems.append(
            Problem(
                path,
                "sections are out of order; expected: "
                + " -> ".join(REQUIRED_SECTIONS),
            )
        )

    # Reject sections that exist but were never filled in.
    chunks = re.split(r"^##\s+", body, flags=re.MULTILINE)[1:]
    for chunk in chunks:
        heading, _, content = chunk.partition("\n")
        heading = heading.strip()
        if heading in REQUIRED_SECTIONS and len(content.strip()) < 40:
            problems.append(
                Problem(
                    path,
                    f"section '## {heading}' is empty or too short to be useful",
                    line_of(body, f"## {heading}"),
                )
            )


def check_leaked_ips(text: str, path: Path, problems: list[Problem]) -> None:
    for match in IPV4_RE.finditer(text):
        raw = match.group(0)
        if not is_publishable_ip(raw):
            problems.append(
                Problem(
                    path,
                    f"routable IP address '{raw}' must be replaced with an "
                    "RFC1918 or documentation address (192.0.2.0/24, "
                    "198.51.100.0/24, 203.0.113.0/24)",
                    line_of(text, raw),
                )
            )


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"schema not found at {SCHEMA_PATH}", file=sys.stderr)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    problems: list[Problem] = []
    seen_ids: dict[str, Path] = {}
    entries = sorted(p for p in STORIES_DIR.glob("*.md") if not p.name.startswith("_"))

    if not entries:
        print("no entries found in stories/", file=sys.stderr)
        return 1

    for path in entries:
        text = path.read_text(encoding="utf-8")
        match = FRONT_MATTER_RE.match(text)
        if not match:
            problems.append(
                Problem(path, "no YAML front matter found between --- delimiters")
            )
            continue

        raw_front_matter, body = match.group(1), match.group(2)

        try:
            data = yaml.safe_load(raw_front_matter)
        except yaml.YAMLError as exc:
            problems.append(Problem(path, f"front matter is not valid YAML: {exc}"))
            continue

        if not isinstance(data, dict):
            problems.append(Problem(path, "front matter must be a YAML mapping"))
            continue

        if isinstance(data.get("id"), int):
            problems.append(
                Problem(
                    path,
                    "id must be quoted so the leading zeros survive, e.g. id: \"0042\"",
                )
            )
            continue

        for error in sorted(validator.iter_errors(data), key=lambda e: e.path):
            field = ".".join(str(p) for p in error.path) or "(root)"
            problems.append(Problem(path, f"{field}: {error.message}"))

        entry_id = data.get("id")
        title = data.get("title")

        if isinstance(entry_id, str) and isinstance(title, str):
            expected = f"{entry_id}-{slugify(title)}.md"
            if path.name != expected:
                problems.append(
                    Problem(path, f"filename should be '{expected}'")
                )
            if entry_id in seen_ids:
                other = seen_ids[entry_id].name
                problems.append(
                    Problem(path, f"id '{entry_id}' is already used by {other}")
                )
            else:
                seen_ids[entry_id] = path

        check_sections(body, path, problems)
        check_leaked_ips(text, path, problems)

    for problem in problems:
        print(problem.render())

    if problems:
        print(
            f"\n{len(problems)} problem(s) in {len(entries)} entr(ies).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(entries)} entries validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
