---
name: report-issue
description: Use when someone found a problem or has an idea while USING a MiraNote app (often a screenshot, a Discord message or a one-line description) and wants it on the team's shared bug list -- dedupes against open issues, reproduces it, and files a Problem / Context / Acceptance criteria GitHub issue like miranote-ios#120.
---

# report-issue

## Overview

The team's shared bug list is GitHub Issues (team meeting, 2026-10-19).
Reference example: [miranote-ios#120](https://github.com/MiraNote-AI/miranote-ios/issues/120).
This skill turns "I saw X" into an issue like that in a few minutes, so anyone
can pick it up. For planned work you are about to build, use **create-ticket**.

## When to use

- A tester reports something from TestFlight or the simulator ("the keyboard
  won't go down", "Add does nothing"), with or without a screenshot.
- A Discord message lists several findings -- file one issue per finding.
- An idea or a "should this work like X?" question about existing behaviour.

## Workflow

1. **Pick the repo** (same table as create-ticket): app behaviour ->
   `miranote-ios`; server results (image generation, chat replies,
   transcription) -> `miranote-api`.
2. **Dedupe first.**
   `gh issue list -R MiraNote-AI/<repo> --state open --search "<keywords>"`.
   If it is already reported, do not open a new issue: comment on the existing
   one with the new evidence (`gh issue comment <n> --body-file <file>`) and
   stop. One problem = one issue.
3. **Reproduce** (if impossible, say so in Context):
   - find the code path (search the accessibility identifier or the label seen
     in the screenshot);
   - drive it on one simulator with a throwaway UI test or by hand; use the
     `-UITEST` mocks and the debug delay hooks for timing problems (see
     `docs/testing/adversarial-harness.md` in miranote-ios);
   - write down the exact steps, device, iOS version and the commit on `dev`
     (`git rev-parse --short origin/dev`). Never commit the throwaway test.
4. **Label** (GitHub defaults only, never invent labels):
   - `bug` -- broken or behaves wrongly;
   - `enhancement` -- works, but should be better;
   - `question` -- the code does what the design says, or a product call is
     needed (Jason / Gloria decide). Combine with `bug`/`enhancement` if both
     apply.
5. **Write the issue** into a temp file, English and ASCII only (Rule 3):

   ```
   ## Problem
   <what the user sees, in user terms, one short paragraph. Then how to
   reproduce: numbered steps, device / iOS / build. Use a small table when
   several places behave differently (place | action | what happens).>

   ## Context
   <relevant code (types, files, identifiers); the cause if known for sure;
   related issues / PRs (#n); what was NOT checked.>

   ## Acceptance criteria
   - [ ] <outcome the user would observe>
   - [ ] <...>
   - [ ] <the test that proves it, failing before the fix>
   ```

   Title: a problem-focused sentence, at most ~80 characters, no `#N`
   (e.g. `Only the Send key lowers the keyboard (Home ask bar, editor fields)`).
   Criteria are observable outcomes, not implementation steps.
6. **File it**:
   `gh issue create -R MiraNote-AI/<repo> --title "<title>" --label <label> --body-file <file>`
   and share the URL.
7. **Screenshots**: the CLI cannot attach images. Ask the reporter to drag the
   screenshot (problem circled in red) into the issue's comment box.
8. **Ownership**: assign nobody unless asked; whoever takes it assigns
   themselves. The fixing PR says `Closes #<n>` (see create-pr), which closes
   the issue on merge.

## Batch mode

Several findings at once: dedupe each, file one issue per problem, then reply
with a short list -- `#n title (label)`.

## Common mistakes

| Mistake | Fix |
|---|---|
| A second issue for a known problem | Comment on the existing issue instead |
| A guess written as the cause | Only state causes you confirmed; otherwise "not checked" |
| Criteria are code changes ("add a focus state") | Rewrite as what the user sees ("a tap outside lowers the keyboard") |
| Two problems in one issue | Split them, cross-link with `#n` |
| No repro steps | Steps + device + build, or say why it could not be reproduced |
