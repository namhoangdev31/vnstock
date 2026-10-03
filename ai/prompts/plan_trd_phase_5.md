# Prompt: Comprehensive Implementation Planning for TRD Phase 5 (Forecast Journal & Controlled Self-Learning Loop)

Read the following reference documents carefully and in strict order before drafting the plan:
1. `ai/start_task.md` (Mandatory workflow before creating or modifying code)
2. `ai/context.md` (Single source of truth for overall project architecture)
3. `ai/project_map.json` (Module navigation map and file routing)
4. `AGENTS.md` (Master project charter, especially §1 Prime Mission, §2 Tri-Engine Architecture, §5 Absolute Prohibitions, §8 Code Conventions, §9 Forecast Journal & Self-Learning Loop)
5. `frontend/data/trd/phase5SpecContent.ts` (Detailed TRD Phase 5 Markdown specification)
6. Relevant existing codebase files:
   - `backend/app/domains/quant/domain/models.py`
   - `backend/app/domains/quant/application/forecast_journal_service.py`
   - `backend/app/domains/quant/application/engines/ensemble_engine.py`
   - `backend/app/domains/quant/application/daemon/scheduled_hooks.py`
   - `backend/app/domains/quant/presentation/forecast_router.py`
   - `backend/app/worker.py`
   - `frontend/pages/admin/trd/phase-5.vue`

---

## 🎯 Task Goal
Formulate a comprehensive, actionable, step-by-step **Technical Implementation Plan** to fulfill 100% of the requirements in **TRD Phase 5: Forecast Journal & Controlled Self-Learning Loop (Autonomous Walk-Forward Gate & Auto-Promote)**.

The system must ensure:
- **100% Signal Traceability & Auditability**: Strictly no look-ahead bias, anchored by an immutable `predicted_at` timestamp.
- **Automated Post-Market Reconciliation & Scoring**: Real-world closing/settlement price evaluation computing Brier Score, Directional Accuracy (DA), MAE, and RMSE.
- **Controlled Self-Learning Loop (Autonomous Walk-Forward Gate & Auto-Promote)**: Rolling 30-day softmax rebalancing across the 3 Engines, automatically promoting new model version snapshots (`is_active = True`) without requiring manual Admin approval if the candidate passes the Walk-Forward Validation Gate.
- **Robust Safeguards & Circuit Breaker**: Bounded weight shifts within $\pm 5\%$ per cycle, engine weight floor/ceiling bounded in $[0.15, 0.60]$, autonomous circuit breaker tripping on 3 consecutive session failures or simulated drawdown $> 3\%$ (reverting to defensive baseline `0.33, 0.33, 0.34`), alongside 1-click manual rollback authority for Admins.
- **Production Audit & Monitoring Frontend UI**: Connect live backend APIs to replace hardcoded mock data in `frontend/pages/admin/trd/phase-5.vue`.

---

## 🛡️ Absolute Prohibitions (Zero-Tolerance Rules)
1. **RULE 1 - Strictly No Real-Money Execution Bots**: Do not connect or integrate with any live brokerage trading API (VPS, SSI, TCBS, etc.). System boundaries stop at the audit ledger and paper trading simulation.
2. **RULE 2 - Strict Simulation Isolation**: All order tracking, scoring, and PnL calculations must reside exclusively within simulation/quant analytics models and endpoints.
3. **RULE 3 - Data Integrity & No Look-Ahead Bias**:
   - `predicted_at` must be recorded at prediction time with timezone `VN_TZ` and must remain strictly immutable.
   - Never overwrite or mutate initial predictions during post-market reconciliation.
   - Never invent, fabricate, or silently interpolate missing market data.
4. **RULE 4 - Informational & Educational Only**: All outputs are quantitative research and simulation metrics, never direct investment advice.
5. **Strict Frontend UI Standards**:
   - Strictly use design tokens defined in CSS/Tailwind (`bg-surface-abyss`, `text-aave-graphite`, etc.); no arbitrary hex colors.
   - Zero Gradients (flat, disciplined surfaces only; no `bg-gradient-to-...`).
   - Zero Emojis in text (use system `<UIcon>` components instead).
   - Never use parentheses `()` for inline explanations in labels/text (use `<UTooltip>` instead).
6. **Code Quality Gates**:
   - Backend: `uv run ruff check`, `uv run ruff format --check`, `uv run ty check` must pass with **0 errors**.
   - Frontend: `bun run lint`, `bun run typecheck`, `bun run build` must pass with **0 errors**.

---

## 📋 Required Plan Deliverables

The implementation plan presented by AGENTS must include the following sections:

### 1. Gap Analysis
- Audit current state vs. Phase 5 requirements:
  - Existing `ForecastJournal` in `models.py` (which fields are missing from Phase 5 specification?).
  - Missing `ModelVersionSnapshot` table.
  - Existing `ForecastJournalService` methods (`record`, `resolve`, `score`, `aggregate`), identifying missing capabilities:
    - Standard probabilistic Brier score.
    - 30-day rolling softmax rebalancing logic.
    - Walk-Forward Validation Gate evaluator.
    - Auto-Promote Engine.
    - Circuit Breaker tripping and emergency rollback mechanism.
  - Missing `evaluator.py` worker and scheduled hook during daemon `POST_MARKET_EVAL` (14:45 - 15:30).
  - Missing API endpoints for model version management, rollback, and circuit breaker reset.
  - Current `phase-5.vue` frontend using mock static data rather than live API calls.

### 2. Architectural Design & Detailed Specifications
- **Database Schema & Alembic Migration**:
  - Add missing fields to `ForecastJournal`: `predicted_probability`, `predicted_price_low`, `predicted_price_high`, `directional_correct`, `brier_score`, `absolute_error`.
  - Define new `ModelVersionSnapshot` table: `version_tag`, `parameters_snapshot`, `is_active`, `rolling_30d_accuracy`, `rolling_30d_brier_score`, `auto_promoted`, `circuit_breaker_triggered`, `promoted_at`, `rollback_from`.
  - Specific Alembic migration commands and steps.
- **Application Logic & Mathematical Scoring**:
  - Scoring formulas: Directional Accuracy ($DA$), Brier Score ($BS = \frac{1}{N} \sum (p_i - o_i)^2$), MAE, RMSE.
  - Rolling Softmax Rebalancing across 30 days: $S_k = \alpha \cdot DA_k + (1-\alpha) \cdot (1-BS_k)$ with temperature $\tau = 0.5$.
  - Weight shift clipping ($\pm 5\%$) and boundary limits $[0.15, 0.60]$.
  - Walk-Forward Validation Gate comparing candidate weights against baseline out-of-sample metrics.
  - Autonomous Auto-Promote & Circuit Breaker: fallback to `0.33, 0.33, 0.34` defensive baseline on 3 consecutive session failures or Drawdown $> 3\%$.
- **Hooks & Worker Integration**:
  - Automatic logging hook in `EnsembleEngine.generate_signal()`.
  - Automated post-market reconciliation worker `evaluator.py` executed during `POST_MARKET_EVAL` (14:45 - 15:30).
- **API Endpoints**:
  - `/api/v1/forecast` (GET filter & pagination, POST record, POST {id}/resolve, POST {id}/score, GET aggregate).
  - `/api/v1/quant/recalibrate/auto-run` (POST trigger self-learning & auto-promote loop).
  - `/api/v1/quant/versions` (GET list of model version snapshots).
  - `/api/v1/quant/versions/{version_tag}/rollback` (POST 1-click rollback).
  - `/api/v1/quant/circuit-breaker/reset` (POST reset circuit breaker).
- **Frontend Integration (`phase-5.vue`)**:
  - Replace mock arrays with reactive composables consuming real backend endpoints.
  - Live Forecast Audit Ledger table with status filters (`PENDING`, `RESOLVED`, `SCORED`).
  - Metric summary cards (Directional Accuracy %, Brier Score, MAE, Winrate).
  - Model Version timeline, Auto-Promote badges, and 1-click rollback modal.
  - Circuit Breaker status badge and emergency reset button.

### 3. Step-by-Step Implementation Roadmap
Decompose the implementation into clean, sequential steps. For each step, define:
- **Target Files**: Exact absolute file paths to create or modify.
- **Implementation Scope**: Precise code changes and design decisions.
- **Verification Commands**: Concrete test and quality verification commands.

### 4. Acceptance Test Matrix
Plan unit and integration tests covering all 10 acceptance criteria (`TEST-JOURNAL-01` through `TEST-JOURNAL-10`):
1. `TEST-JOURNAL-01`: Ensemble emits signal -> creates PENDING row in `ForecastJournal` with immutable timezone-aware `predicted_at`.
2. `TEST-JOURNAL-02`: Rejection/prevention of mutating `predicted_target_price` or `predicted_at` after initial creation.
3. `TEST-JOURNAL-03`: ATC scoring: Bullish prediction ($P=0.8$), actual price rises -> `directional_correct = True`, `brier_score = 0.04`.
4. `TEST-JOURNAL-04`: ATC scoring: Bullish prediction ($P=0.7$), actual price drops -> `directional_correct = False`, `brier_score = 0.49`.
5. `TEST-JOURNAL-05`: MAE computation for predicted target 1310 vs actual 1305 -> `absolute_error = 5.0`.
6. `TEST-JOURNAL-06`: Proposed weight delta of +12% -> clipped to max +5.0% within $[0.15, 0.60]$.
7. `TEST-JOURNAL-07`: Passes Walk-Forward Validation Gate -> automatically promotes new snapshot with `is_active = True`.
8. `TEST-JOURNAL-08`: Drawdown exceeds -3% or 3 consecutive failed sessions -> Circuit Breaker trips, resets weights to `0.33, 0.33, 0.34`.
9. `TEST-JOURNAL-09`: Admin triggers `/rollback` API -> immediately restores previous active version.
10. `TEST-JOURNAL-10`: 30-day aggregate statistics report computes correct Winrate, Directional Accuracy, and Brier Score.

---
**Begin by inspecting the reference files, performing the gap analysis, and outlining the full Technical Implementation Plan!**
