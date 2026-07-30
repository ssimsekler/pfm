<!-- See CONTRIBUTING.md and .clinerules/docs-continuity.md -->

## Summary

<!-- What does this change do and why? -->

## Docs continuity (required)

A change is not complete until code **and** docs are updated together. Tick all that apply:

- [ ] `docs/PROGRESS.md` updated (current status, next step, phase checklist)
- [ ] `docs/DECISIONS.md` updated (new ADR for any architectural/cross-cutting decision)
- [ ] `docs/ERD.md` updated (data-model or persistence-affecting endpoint changes)
- [ ] `docs/PLAN.md` updated (scope/phase changes)
- [ ] N/A — this change does not affect any of the above

## Checks

- [ ] Backend tests pass (`docker compose run --rm backend sh -c "pip install -r requirements-dev.txt && pytest"`)
- [ ] App builds and runs (`cd infra && docker compose up -d --build`)
- [ ] State-changing UI actions still confirm before executing (ADR #32)