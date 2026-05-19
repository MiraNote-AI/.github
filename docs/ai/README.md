# MiraNote AI Engineering Docs

Canonical rules and playbooks for AI-assisted development across `MiraNote-AI/*` repos.

> **Source of truth:** `MiraNote-AI/.github`.
> All other repos receive these files via the `sync-ai-docs.yml` workflow.

## Status

Scaffolding only — the actual rule content is **TBD** pending a brainstorm session.
Treat the planned structure below as a strawman; expect changes.

## Planned structure

- `product.md` — what MiraNote is, who uses it, what we're optimizing for
- `architecture.md` — how the 5 repos fit together, request flow, data flow
- `coding-standards.md` — naming, structure, comments, tests
- `workflow.md` — branches, commits, PR conventions
- `playbooks/` — step-by-step task recipes (add feature, fix bug, refactor)
- `decisions/` — ADRs (architecture decision records)

## How to edit

1. PR into `MiraNote-AI/.github` (this repo)
2. On merge to `main`, the sync workflow opens a PR in each of the 4 code repos
3. Reviewers in each code repo merge their auto-PR
