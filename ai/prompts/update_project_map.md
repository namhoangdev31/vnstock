Update `ai/project_map.json` for `vnstock`.

Goal:
Refresh the existing map after structural changes while preserving schema shape and keeping diffs reviewable.

Read first:
- existing `ai/project_map.json`
- existing `ai/context.md`
- changed files
- impacted backend routes / services / models / engines
- impacted frontend components / routes / stores

Always re-check these before updating:
- `AGENTS.md`
- `pyproject.toml`
- `backend/` key routes and services
- `frontend/` key routes and components

Update the map for:
- new or removed important files
- changed route structure
- changed module responsibilities
- changed key dependencies
- changed commands or generation workflow
- new AI-task suggestions per module if needed

Constraints:
- do not rebuild from scratch unless necessary
- keep ordering stable where possible
- remove stale entries
- keep JSON valid
- keep it navigation-first, not inventory-first
