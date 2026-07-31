# Project rule: documentation continuity (READ AND FOLLOW EVERY SESSION)

This rule is loaded automatically at the start of every task. It is mandatory
for all changes to this repository, by any contributor or AI assistant, in this
and all future sessions — no reminder required.

## 1. Before making any change (docs-first read)
Read, in this order, to reload project context:
1. `docs/PROGRESS.md`  — current phase, what's done, exact next step.
2. `docs/PLAN.md`      — scope and phases.
3. `docs/DECISIONS.md` — architecture decision records (ADRs).
4. `docs/ERD.md`       — field-level data model.

## 2. With every change (update docs in the SAME change)
A change is **not complete** until the affected docs are updated alongside the
code. Before finishing a task, update whichever of these apply:

- **`docs/PROGRESS.md`** — update "Current status", the "Next step", and the
  phase checklist to reflect what was just done.
- **`docs/DECISIONS.md`** — add a new numbered ADR for any new architectural or
  cross-cutting decision (keep the incrementing ADR numbers).
- **`docs/ERD.md`** — reflect any data-model change (new/changed tables,
  columns, constraints) and any new persistence-affecting endpoints.
- **`docs/PLAN.md`** — reflect any scope/phase change (e.g., a new phase).

## 3. Definition of done
- Code + docs are updated **together**.
- **After every pass of changes, git commit and push to the remote** (mandatory):
  stage everything, commit with a clear message, and `git push`. If the push fails
  (e.g. no network/credentials), keep committing locally and retry the push next time
  (ADR #22). This applies to all interactions and all future sessions.

## 3a. Git invocation on Windows/PowerShell (avoid false "errors" / getting stuck)
`git` writes normal progress to **stderr** (e.g. `To https://…`, `abc..def main -> main`)
even on success. In PowerShell, combining streams with `2>&1` and piping to
`Select-Object`/`Out-*` makes PowerShell wrap those lines as `NativeCommandError` /
`RemoteException` (red text), which looks like a failure and can leave the run
ambiguous ("stuck"). To prevent this:
- **Do NOT** pipe git through `2>&1 | Select-Object …`. Run git as plain commands.
- **Run each git command as its OWN separate tool call** — do **not** chain
  `git add -A; git commit …` (or with `&&`) in a single PowerShell invocation.
  Chaining is the usual cause of the run appearing to "get stuck": PowerShell may
  wrap git's stderr progress as errors, and a chained `commit` with nothing to
  commit returns a non-zero exit that stalls the combined command. Sequence:
  1. `git add -A`  (its own call)
  2. `git commit -m "…"`  (its own call; if it prints "nothing to commit", that's fine — continue)
  3. `cmd /c "git push origin main 2>&1"`  (its own call — plain text, no PowerShell error-wrapping)
- Keep commit messages **short and single-line** (no newlines, no special chars that
  PowerShell must escape) to avoid quoting problems that hang the shell.
- After pushing, confirm success cleanly with `git rev-parse HEAD` and `git status -sb`
  (each its own call) rather than parsing the push output. `## main...origin/main`
  with no "ahead" means the push landed.

## 4. Conventions
- ADRs are numbered incrementally (see the last number in `docs/DECISIONS.md`).
- Keep `docs/PROGRESS.md` accurate enough that a fresh session can resume from
  it alone.
- Prefer configurable/metadata-driven solutions consistent with existing ADRs.
- **Batch prefix per session:** at the start of each work session, pick **one
  random 3-digit number** and use it as the shared prefix for every batch in that
  session (e.g. `815-Batch 1`, `815-Batch 2`, …). This makes changes from
  different sessions distinguishable in commits, PROGRESS.md, and ADRs. Record the
  chosen prefix in `docs/PROGRESS.md` "Current status".

> Rationale: session memory does not persist reliably between sessions. Encoding
> the rule in the repo (auto-loaded from `.clinerules/`) guarantees continuity.