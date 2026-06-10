# docs/

## Responsibility

Project documentation root. Contains architecture decisions, agent engineering conventions, and feature plans. No flat documentation files remain — the source code (`AGENTS.md`) and source code itself are the canonical references.

## History

The following files were intentionally removed to eliminate redundancy:
- `README.md` — content covered by root `AGENTS.md`
- `architecture.md`, `ai-pipeline.md`, `database.md`, `modules.md` — overlapped each other and `AGENTS.md`
- `srs/` — stub outline, chapter files never materialized
- `.obsidian/` — local editor config, gitignored

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `adr/` | Architecture Decision Records |
| `agents/` | AI agent engineering conventions (domain, issues, triage) |
| `plans/` | Feature plans — active (staging) + archive (completed) |
| `project-report/` | Project report drafting, outlines, and content |

For details, read each directory's `codemap.md`.
