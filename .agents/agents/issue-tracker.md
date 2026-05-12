# Issue Tracker: Local Markdown

Issues are tracked as local markdown files within this repository.

## Convention

- **Root**: `.scratch/`
- **Path**: `.scratch/<feature>/<issue-id>.md`
- **Format**: Markdown with YAML frontmatter for metadata (status, labels, etc.)

## Triage Workflow

Agents and humans interact with these files directly. The `triage` skill updates the frontmatter to move issues through the state machine.
