# Project notes

## Cloudflare Workers

On 11 November 2026, the maintainer asked about hosting the project on
Cloudflare Workers and decided to defer it.

The proposal was a static site served with Workers Static Assets, with
`scripts/build_index.py` also emitting a machine-readable `stories.json`.
GitHub Actions would still run CI, and the Mac would still handle rendering and
voice generation. R2 was discussed as a private backup for production masters
in `video-scripts/`.

The open decision was how to turn the story Markdown into HTML. A JavaScript
toolchain was one option. A Python package would affect the repository's
two-package dependency list. Recheck Cloudflare's limits and prices if the
maintainer reopens the proposal.
