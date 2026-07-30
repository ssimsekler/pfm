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

## 4. Conventions
- ADRs are numbered incrementally (see the last number in `docs/DECISIONS.md`).
- Keep `docs/PROGRESS.md` accurate enough that a fresh session can resume from
  it alone.
- Prefer configurable/metadata-driven solutions consistent with existing ADRs.

> Rationale: session memory does not persist reliably between sessions. Encoding
> the rule in the repo (auto-loaded from `.clinerules/`) guarantees continuity.