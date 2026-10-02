# Required workflow before making changes in vnstock

Use this file as the required workflow before making changes in `vnstock`.

Follow `ai/context.md` as the source of truth for project conventions.
Use `ai/project_map.json` to navigate the repository before editing.
Use this file to reduce common LLM coding mistakes before, during, and after implementation.

---

## Read first

Before writing or changing code, read these in order:

1. `ai/context.md`
2. `ai/project_map.json`
3. `AGENTS.md` (Master Project Rules & Boundaries)
4. the nearest real files in the target area

---

## Core behavior rules

### Think before coding
- State assumptions explicitly.
- Surface tradeoffs or simpler approaches before writing complex code.
- If something is ambiguous, inspect local code patterns first before making minimal, reversible choices.

### Surgical edits only
- Touch only code directly related to the task.
- Do not refactor unbroken modules or change existing code style unnecessarily.
- Match local code formatting and idioms.

### Absolute prohibitions (Zero-Tolerance Rules)
- **STRICTLY NO REAL-MONEY AUTO-EXECUTION BOTS**: No real brokerage API execution (VPS, SSI, TCBS, etc.).
- **STRICT ISOLATION OF SIMULATION**: Paper trading and simulation must remain strictly isolated in simulation models/schemas.
- **NO FABRICATED DATA / LOOK-AHEAD BIAS**: Real data must come from verifiable `vnstock` source. Persist signals into `ForecastJournal`.
- **INFORMATIONAL ONLY**: Outputs are educational simulation data, not financial advice.

### Verification & Quality Gates
- **Backend Quality**: Every backend modification MUST pass `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check` with 0 errors.
- **Frontend Quality**: Every frontend modification MUST pass `npm run build` cleanly without TypeScript or routing errors.
