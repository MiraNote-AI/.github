# MiraNote Harness Engineering — Day-0 Verification Infrastructure

**Date**: 2026-05-19
**Status**: Approved design, awaiting implementation plan.
**Scope**: One sub-project (B + A) of the broader MiraNote harness engineering effort: the verification infrastructure (Rule-2 meta-rule machinery) plus the first batch of 7 enforced rules.
**Out of scope**: Branch protection (sub-project F), per-stack harness customisation (D), shared org-level Claude skills/memory (E), local pre-commit hooks.
**Source of truth**: `MiraNote-AI/.github` repo.

---

## 1. Background and motivation

MiraNote ships as 5 sibling repos under the `MiraNote-AI` GitHub org: `miranote-web`, `miranote-api`, `miranote-ios`, `mirabot`, and `.github` (org-profile + canonical source for shared assets).

The harness engineering note (`Obsidian/Work/0-Inbox/AI Harness Engineering — Field Overview and DASGPT Lessons.md`, 2026-05-18) establishes the **Rule-2 meta-rule** as the hidden multiplier:

> Every documented rule must have a verification script or it degrades to wall-art.

DASGPT has already validated this principle in production via its `all_rules_have_checks.py` and the CJK-violation incident (note sections 9.2, 9.6).

This spec defines the **day-0 infrastructure** that makes the meta-rule self-enforcing on MiraNote, plus 7 initial rules registered against it.

## 2. Goals and non-goals

### Goals
- Self-enforcing meta-rule: cannot land a documented rule without a matching verification script.
- 7 concrete rules enforced on every PR across all 5 repos.
- Single source of truth (`MiraNote-AI/.github`) for both docs and checks.
- Centralised checks via a GitHub Actions **reusable workflow**; documentation propagated to each target via the existing `sync-ai-docs.yml` workflow.
- Local-runnable checks for tight iteration loops.

### Explicit non-goals (deferred to other sub-projects)
- Branch protection rules, CODEOWNERS, hard enforcement against malicious actors → **sub-project F**.
- Per-stack harness configuration (linter/test setup, settings.json hooks, MCP wiring per repo) → **sub-project D**.
- Org-level shared Claude Code skills or memory → **sub-project E**.
- Local pre-commit hook mirror of CI checks → nice-to-have, post-day-0.
- More than 7 rules → followed via the documented "4-step add-a-rule" procedure (§4.4).

## 3. Architecture

### 3.1 Directory layout — `MiraNote-AI/.github` (source)

```
.github/
├── CLAUDE.md                              # short entry point (≤ 80 lines)
├── CONTRIBUTING.md                        # canonical rule registry (γ parses; α verifies)
├── docs/ai/
│   ├── README.md                          # navigation; already exists
│   └── skills.md                          # Skill/MCP registry (ε parses)
├── checks/                                # Python verification scripts (stdlib only)
│   ├── __init__.py
│   ├── _meta/
│   │   ├── __init__.py
│   │   └── all_rules_have_checks.py       # α
│   ├── contributing_format.py             # γ
│   ├── no_cjk_or_emoji.py                 # β
│   ├── claude_md_size.py                  # δ
│   ├── skills_registry.py                 # ε
│   ├── pr_has_reference.py                # ζ
│   └── protected_paths.py                 # η
├── .github/workflows/
│   ├── sync-ai-docs.yml                   # exists, will expand sync scope
│   ├── checks.yml                         # NEW: reusable, on: workflow_call
│   └── self-check.yml                     # NEW: calls checks.yml in source mode
├── templates/
│   └── target-workflow.yml                # synced to each target's .github/workflows/checks.yml
├── bin/
│   └── sync-ai-docs.sh                    # exists, will expand sync scope
└── pyproject.toml                         # provides `python -m checks.*` import root
```

### 3.2 Directory layout — each target repo

```
miranote-{web,api,ios,mirabot}/
├── CLAUDE.md                              # synced from .github
├── CONTRIBUTING.md                        # synced from .github
├── docs/ai/                               # synced from .github
└── .github/workflows/
    └── checks.yml                         # synced from .github/templates/target-workflow.yml
```

The target's `checks.yml` stub is 6 lines:

```yaml
name: Checks
on:
  pull_request:
  push: { branches: [main] }
jobs:
  checks:
    uses: MiraNote-AI/.github/.github/workflows/checks.yml@main
    with: { mode: target }
```

### 3.3 What syncs vs. what lives centrally

| Asset | Lives in `.github` | Synced to each target |
|---|:---:|:---:|
| `CLAUDE.md` | yes | yes |
| `CONTRIBUTING.md` | yes | yes |
| `docs/ai/**` | yes | yes |
| `.github/workflows/checks.yml` (target stub) | yes (as `templates/target-workflow.yml`) | yes |
| `checks/**` (Python scripts) | yes | **no** — called via reusable workflow |
| `.github/workflows/checks.yml` (reusable) | yes | **no** — called via `uses: ...@main` |
| `.github/workflows/self-check.yml` | yes | **no** — only `.github` self-checks |
| `templates/target-workflow.yml` (the template itself) | yes | **no** — only the rendered copy ships |

The existing `sync-ai-docs.yml` workflow (commit `f223ec8`, not yet pushed) covers `CLAUDE.md` and `docs/ai/`. Phase 0 expands it to also cover `CONTRIBUTING.md` and the rendered target-workflow stub.

## 4. Rule registry contract

CONTRIBUTING.md is the single authoritative registry. γ validates its structure; α verifies the doc-to-script mapping.

### 4.1 Required CONTRIBUTING.md format

```markdown
# Contributing

(any prose)

## Rules

### Rule 1: <short title>

<prose explanation: what the rule means, what violates it>

**Rationale:** <one sentence>
**Enforced by:** `checks/<script>.py`

### Rule 2: <short title>

...
**Enforced by:** `checks/<a>.py`, `checks/<b>.py`   # comma-separated for multiple
```

### 4.2 γ (`contributing_format.py`) validates

1. A `## Rules` top-level section exists.
2. Every heading matching `^### Rule (\d+): .+$` directly under `## Rules` is a rule entry.
3. Rule numbers (`N`) are **unique** (gaps are allowed; renumbering on delete is disallowed for stable IDs).
4. Each rule section contains **exactly one** `**Rationale:**` line.
5. Each rule section contains **exactly one** `**Enforced by:**` line. After stripping the `**Enforced by:**` prefix, the remainder is split on `,` and each token is stripped of surrounding whitespace and backticks. Each token must be a non-empty relative path string (POSIX-style).
6. **In `mode=source` only**: every path token (after the strip in §4.2.5) resolves to an existing file relative to the repo root. (Skipped in `mode=target` because the paths point to scripts that live in `.github`, not in the target.)

### 4.3 α (`_meta/all_rules_have_checks.py`) verifies

Runs only after γ passes. Only meaningful in `mode=source` (the only place `checks/` exists).

1. Parse CONTRIBUTING.md into a `{rule_id: [check_paths]}` mapping.
2. **Forward check**: every referenced `check_path` exists.
3. **Reverse / orphan check**: every Python file under `checks/` (excluding `_meta/` and `__init__.py`) appears in at least one rule's `Enforced by:` line.

### 4.4 Adding a new rule (standard 4-step procedure)

1. Write the check script at `checks/<name>.py`.
2. Append `### Rule N: …` to CONTRIBUTING.md with the required `Rationale:` and `Enforced by:` lines.
3. Locally run: `PYTHONPATH=. python -m checks.contributing_format . && PYTHONPATH=. python -m checks._meta.all_rules_have_checks .`
4. PR into `MiraNote-AI/.github`. On merge, `sync-ai-docs.yml` propagates the doc to all targets; the reusable workflow picks up the new check automatically.

### 4.5 Hard constraints

- No "manual review only" / "no script" rules. If a rule cannot be checked programmatically, it does not belong in CONTRIBUTING.md.
- Orphan checks (no rule references them) fail α — every script must be tied to a documented rule.
- Rule IDs do not renumber on deletion (stable for git-history references).

## 5. The 7 rules

| ID | Name | Check script | mode-`source` | mode-`target` | Trigger |
|---|---|---|:---:|:---:|---|
| Rule 1 (α) | Every rule has an enforcement mechanism | `_meta/all_rules_have_checks.py` | ✓ | — | push, PR |
| Rule 2 (γ) | CONTRIBUTING.md follows canonical structure | `contributing_format.py` | ✓ (full) | ✓ (syntax only) | push, PR |
| Rule 3 (β) | No CJK characters or emoji in committed files | `no_cjk_or_emoji.py` | ✓ | ✓ | push, PR |
| Rule 4 (δ) | CLAUDE.md is at most 80 lines | `claude_md_size.py --max 80` | ✓ | ✓ | push, PR |
| Rule 5 (ε) | Skills and MCP servers are registered in `docs/ai/skills.md` | `skills_registry.py` | ✓ | ✓ | push, PR |
| Rule 6 (ζ) | PR description references an issue, spec, or URL | `pr_has_reference.py` | ✓ | ✓ | PR only |
| Rule 7 (η) | Protected paths cannot be modified outside the sync flow | `protected_paths.py` | — | ✓ | PR only |

### 5.1 Rule 1 — Meta-rule (α)

Spec: §4.3. Failure mode: someone documents a rule but forgets to write the script, or writes a script without registering it.

### 5.2 Rule 2 — CONTRIBUTING.md structure (γ)

Spec: §4.2. The structural validation is split: full validation (including path existence) in `mode=source`; syntactic validation only in `mode=target` (because target repos do not host the check scripts).

### 5.3 Rule 3 — No CJK or emoji (β)

**Why**: DASGPT 9.2 caught a real bug from input-method residue.

**Scope**: All files returned by `git ls-files --cached --others --exclude-standard`. DASGPT's earlier version omitted `--others`; locally-staged-but-not-committed files slipped through and CI caught them after push. We use the inclusive form so local matches CI.

**Detection**: a code point triggers a violation if it is:
- In any of the Unicode blocks `Hiragana` (U+3040..U+309F), `Katakana` (U+30A0..U+30FF), `CJK Unified Ideographs` (U+4E00..U+9FFF), `CJK Symbols and Punctuation` (U+3000..U+303F), `Halfwidth and Fullwidth Forms` (U+FF00..U+FFEF), OR
- Has the Unicode property `Emoji_Presentation=Yes` (resolved via `unicodedata` + an embedded data table generated from the Python `unicodedata` module at script bundle time).

Decoding: files are read as UTF-8 with `errors="replace"`; replacement characters are themselves a violation (signals non-UTF-8 file content that should not be committed as text).

**Allowlist**: An in-script `ALLOWLIST_PATTERNS` glob list (initially empty). Allowlist lives in code, not config, because moving it to a doc would itself need a check (infinite regress).

### 5.4 Rule 4 — CLAUDE.md size (δ)

**Threshold**: 80 lines. Chosen between HumanLayer's 60 (too tight given MiraNote's complexity) and Anthropic's ≤100 guideline (too loose for an entry point whose detail belongs in `docs/ai/`).

**Check**: line count of `CLAUDE.md` at repo root.

### 5.5 Rule 5 — Skill / MCP registry (ε)

**Why**: Counters the "50 MCP servers running" anti-pattern (note §5 #3).

**Day-0 implementation (narrow)**: verifies `docs/ai/skills.md` exists, is non-empty, and contains a `## Skills` header and a `## MCP Servers` header.

**Future ratchet**: When a target repo introduces repo-level skill/MCP configuration (e.g., `.claude/settings.json` with `mcpServers` keys), extend ε to diff the configured set against the documented registry.

### 5.6 Rule 6 — PR references something (ζ)

**Trigger**: only on `pull_request` events; skipped on `push`.

**Pass criteria** (any one suffices): PR body contains a `#<integer>` issue/PR reference, OR any URL (`https?://...`), OR one of the keywords `spec:`, `design:`, `adr:`, `rfc:` followed by a token.

**Bot exemption**: PRs whose head branch matches `chore/sync-ai-docs-*` (the pattern produced by `sync-ai-docs.yml`) are automatically exempted. In practice these PRs include a source-commit link, so they would pass anyway.

### 5.7 Rule 7 — Protected paths (η)

**Protected list (target-side)**: `CLAUDE.md`, `CONTRIBUTING.md`, `docs/ai/**`, `.github/workflows/checks.yml`.

**Pass criteria**: take the PR diff's changed-files list (via `git diff --name-only $BASE_SHA $HEAD_SHA`), intersect with the protected list. The protected list itself is matched via `fnmatch.fnmatchcase` against each changed path (so `docs/ai/**` uses `fnmatch` semantics, not pure-glob). If the intersection is non-empty AND the PR head branch name does not `fnmatch` `chore/sync-ai-docs-*` → FAIL with a message instructing the contributor to edit `MiraNote-AI/.github` instead.

**Soft-enforcement limitation** (explicit and accepted): the branch-name signal is spoofable. Real enforcement requires CODEOWNERS plus branch protection (sub-project F). This check defends against accidental drift, not deliberate evasion.

### 5.8 Rule selection rationale

The Ratchet pattern (note §4) says: only add rules after observed failures. A strict reading would limit day-0 to α + γ + β (the minimum self-consistent set + the only rule with a documented prior failure).

User chose (2026-05-19) to additionally include δ, ε, ζ, η as preventive rules — prioritising day-0 lockdown over Ratchet strictness. Risk: thresholds may be miscalibrated without real failure data. Mitigation: every threshold is configurable (δ's `--max`, η's protected list, ε's required-header set), and rules can be removed if they generate sustained false positives.

## 6. CI integration

### 6.1 Reusable workflow (`.github/workflows/checks.yml`)

```yaml
name: Checks
on:
  workflow_call:
    inputs:
      mode:
        type: string
        default: target          # 'source' for .github self-check
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code under test
        uses: actions/checkout@v4
        with: { path: code, fetch-depth: 0 }   # β needs git ls-files; η needs PR diff

      - name: Checkout tools (.github @main)
        uses: actions/checkout@v4
        with:
          repository: MiraNote-AI/.github
          ref: main
          path: tools

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      - name: γ — CONTRIBUTING.md format
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.contributing_format $GITHUB_WORKSPACE/code --mode ${{ inputs.mode }}

      - name: α — Meta-rule
        if: ${{ !cancelled() && inputs.mode == 'source' }}
        working-directory: tools
        run: python -m checks._meta.all_rules_have_checks $GITHUB_WORKSPACE/code

      - name: β — No CJK/emoji
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.no_cjk_or_emoji $GITHUB_WORKSPACE/code

      - name: δ — CLAUDE.md ≤ 80
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.claude_md_size $GITHUB_WORKSPACE/code --max 80

      - name: ε — Skills/MCP registry
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.skills_registry $GITHUB_WORKSPACE/code

      - name: ζ — PR has reference
        if: ${{ !cancelled() && github.event_name == 'pull_request' }}
        working-directory: tools
        env:
          PR_BODY: ${{ github.event.pull_request.body }}
          PR_BRANCH: ${{ github.event.pull_request.head.ref }}
        run: python -m checks.pr_has_reference

      - name: η — Protected paths
        if: ${{ !cancelled() && inputs.mode == 'target' && github.event_name == 'pull_request' }}
        working-directory: tools
        env:
          PR_BRANCH: ${{ github.event.pull_request.head.ref }}
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: python -m checks.protected_paths $GITHUB_WORKSPACE/code
```

### 6.2 `.github` self-check (`.github/workflows/self-check.yml`)

```yaml
name: Self-check
on:
  pull_request:
  push:
    branches: [main]
    paths: ['CLAUDE.md', 'CONTRIBUTING.md', 'docs/ai/**', 'checks/**', 'templates/**']
jobs:
  checks:
    uses: ./.github/workflows/checks.yml
    with: { mode: source }
```

### 6.3 Target stub (`templates/target-workflow.yml`, rendered into each target)

```yaml
name: Checks
on:
  pull_request:
  push: { branches: [main] }
jobs:
  checks:
    uses: MiraNote-AI/.github/.github/workflows/checks.yml@main
    with: { mode: target }
```

### 6.4 Key CI design decisions and trade-offs

| Decision | Rationale | Trade-off accepted |
|---|---|---|
| One job, sequential steps, `if: !cancelled()` per check | PR authors see all failures in one push, not one per round-trip | Less clean than matrix UI; runner stays warm |
| `uses: ...@main` (not pinned tag) | Day-0 simplicity; instant propagation of fixes | A broken commit in `.github` immediately breaks 4 repos' CI |
| `stdlib`-only checks, no pip install | No dependency lock file; fast cold start | Slightly more verbose regex / unicode code |
| `mode=source` vs `mode=target` | α, full-γ, ε's future extension only valid where their inputs exist | One extra input parameter |
| `fetch-depth: 0` | β needs `git ls-files`, η needs diff between BASE_SHA and HEAD_SHA | Slower checkout on very large histories (acceptable here) |
| Python 3.12 | Current stable, available on `ubuntu-latest` | Pinning a version means a future runner image change could surface compatibility issues; revisit annually |

### 6.5 Trigger and propagation timeline

```
.github PR opened
  └─> self-check.yml (mode=source) — must pass to merge

.github main updated
  ├─> self-check.yml (push, gate against direct-to-main mistakes)
  └─> sync-ai-docs.yml — opens a PR in each of 4 targets

Target PR opened (sync-bot or human)
  └─> checks.yml (mode=target) — must pass to merge

Target main updated
  └─> checks.yml (mode=target, push) — sanity gate
```

## 7. Bootstrap order

### Phase 0 — Implementation in local `.github` clone

Produce the file manifest in §3.1. Modifies the existing `sync-ai-docs.yml` and `bin/sync-ai-docs.sh` to expand sync coverage to `CONTRIBUTING.md` and the rendered target stub.

### Phase 1 — Local self-check loop

Run every check against the local `.github` clone until all pass:

```bash
cd /Users/mengjia/MiraNote/.github
PYTHONPATH=. python -m checks.contributing_format . --mode source
PYTHONPATH=. python -m checks._meta.all_rules_have_checks .
PYTHONPATH=. python -m checks.no_cjk_or_emoji .
PYTHONPATH=. python -m checks.claude_md_size . --max 80
PYTHONPATH=. python -m checks.skills_registry .
```

(ζ and η are PR-event-only and have no local-only mode; their first verification is in Phase 5.)

### Phase 2 — One-time GitHub configuration (user, manual)

1. Create a fine-grained PAT with resource owner `MiraNote-AI`, scoped to the 4 code repos, granting `Contents: write` + `Pull requests: write`.
2. Add the PAT as secret `SYNC_TOKEN` on `MiraNote-AI/.github`:
   ```bash
   gh secret set SYNC_TOKEN -R MiraNote-AI/.github
   ```
3. Enable Actions PR creation in each target repo:
   ```bash
   for r in miranote-web miranote-api miranote-ios mirabot; do
     gh api -X PUT "repos/MiraNote-AI/$r/actions/permissions/workflow" \
       -F can_approve_pull_request_reviews=true \
       -F default_workflow_permissions=write
   done
   ```

### Phase 3 — Bootstrap 4 target repos

```bash
/Users/mengjia/MiraNote/.github/bin/sync-ai-docs.sh direct
```

Each target receives an initial `main` containing `CLAUDE.md`, `CONTRIBUTING.md`, `docs/ai/`, and `.github/workflows/checks.yml` (the synced stub).

**Known transient failure**: the targets' first workflow run after Phase 3 will fail with 404 because `MiraNote-AI/.github`'s `main` does not yet exist (we haven't pushed). This is acceptable; the next workflow run after Phase 4 succeeds. The alternative ordering (push `.github` first, then bootstrap) is worse: `sync-ai-docs.yml` would fire and try to open PRs against non-existent target `main` branches.

### Phase 4 — Push `.github` to GitHub

```bash
cd /Users/mengjia/MiraNote/.github && git push -u origin main
```

Triggers:
- `self-check.yml` (push event) — should pass because Phase 1 passed locally.
- `sync-ai-docs.yml` (push event) — diffs each target against the (now-pushed) source; finds no diff because Phase 3 already mirrored content; all 4 matrix jobs log "no changes, skipping".

### Phase 5 — Smoke test

In `miranote-web`, open a no-op PR:

```bash
cd /Users/mengjia/MiraNote/miranote-web
git checkout -b smoke/checks-bootstrap
echo "" >> README.md
git commit -am "smoke: verify checks pipeline (refs #0, design: bootstrap)"
git push -u origin smoke/checks-bootstrap
gh pr create --title "smoke: verify checks pipeline" \
  --body "Bootstrap smoke test. refs: #0, design: docs/superpowers/specs/2026-05-19-harness-engineering-day0-design.md"
```

Expected: ζ passes (PR body contains both `#0` and a path-style reference); other applicable target-mode checks run and pass; PR can be closed without merging.

### Phase 6 — Deferred

Out of scope for this spec, to be brainstormed separately:

- **Sub-project F**: branch protection rules + CODEOWNERS to harden η.
- **Sub-project D**: per-stack harness (web/api/ios/mirabot linter, tests, settings.json hooks).
- **Sub-project E**: shared org-level Claude skills and memory conventions.
- **Local pre-commit hook**: optional convenience mirror of CI checks.
- **New rule additions**: via the standard 4-step procedure (§4.4).

## 8. Risks and open questions

| Risk | Likelihood | Mitigation |
|---|---|---|
| δ threshold of 80 lines is wrong | Medium | Configurable via `--max`; revisit after first few CLAUDE.md iterations |
| ε is too narrow on day-0 (only checks file existence) | High (intentional) | Extend when MCP/skill config is actually present (Ratchet) |
| η spoofable via branch-name | Accepted | Pair with sub-project F (CODEOWNERS) when ready |
| `uses: ...@main` breaks 4 repos on a bad commit | Medium | Phase 1 (local self-check) gates this; revisit pinning when iteration slows |
| First target workflow run after Phase 3 will 404 | Certain, transient | Documented in Phase 3 |

## 9. Success criteria

- All 5 repos have green CI on day-0 baseline content.
- Attempting to add a documented rule without a check produces a CI failure (α).
- Attempting to add a check without registering the rule produces a CI failure (α orphan detection).
- Attempting to modify a synced file from inside a target repo (outside the sync bot branch pattern) produces a CI failure (η).
- Phase 5 smoke-test PR passes all applicable checks.

## 10. Deliverables checklist (Phase 0)

New files in `MiraNote-AI/.github`:
- [ ] `CONTRIBUTING.md` (with all 7 rules registered)
- [ ] `docs/ai/skills.md` (with `## Skills` and `## MCP Servers` sections; required by ε)
- [ ] `checks/__init__.py`, `checks/_meta/__init__.py`
- [ ] `checks/_meta/all_rules_have_checks.py` (α)
- [ ] `checks/contributing_format.py` (γ)
- [ ] `checks/no_cjk_or_emoji.py` (β)
- [ ] `checks/claude_md_size.py` (δ)
- [ ] `checks/skills_registry.py` (ε)
- [ ] `checks/pr_has_reference.py` (ζ)
- [ ] `checks/protected_paths.py` (η)
- [ ] `.github/workflows/checks.yml` (reusable)
- [ ] `.github/workflows/self-check.yml`
- [ ] `templates/target-workflow.yml`
- [ ] `pyproject.toml`

Modified files in `MiraNote-AI/.github`:
- [ ] `CLAUDE.md` (replace placeholder with real day-0 rules entry; must satisfy δ ≤ 80 lines)
- [ ] `docs/ai/README.md` (point to new docs)
- [ ] `.github/workflows/sync-ai-docs.yml` (extend sync scope)
- [ ] `bin/sync-ai-docs.sh` (extend sync scope to match)
