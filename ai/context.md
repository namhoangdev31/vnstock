# AI Project Context - vnstock Platform

## Project Overview

`vnstock` platform is a Continuous Quantitative Research, Predictive Analytics, and Simulation Engine dedicated to the Vietnamese Financial Market (derivatives `VN30F1M` and underlying equities).

### Main Tech Stack
- **Backend**: Python 3.11+ / FastAPI / SQLModel / PostgreSQL / AsyncIO / `uv`
- **Frontend**: React / Vite / TanStack Router / TailwindCSS / TypeScript / `bun` or `npm`
- **Data & Quants Core**: `vnstock` v4 (Quote, Listing, Company, Finance, Reference, Market, Retail), Pandas, NumPy, SciPy
- **Architecture**: Tri-Engine Quants Engine (Technical & Price-Action, Macro/Liquidity/T+2 Cash Flow, Statistical ML & Volatility) + Forecast Journal & Paper Trading Engine

---

## Directory Structure

- `backend/`
  - FastAPI application backend containing API routers, SQLModel models, quant engines, background tasks, and paper trading services.
- `frontend/`
  - Single-page web application built with React, Vite, and TanStack Router for interactive visualization, simulation dashboard, and position tracking.
- `packages/`
  - Internal python/ts packages or shared libraries.
- `apps/`
  - Modular sub-applications or microservices if applicable.
- `scripts/`
  - Maintenance, backfill, migration, and automation helper scripts.
- `AGENTS.md`
  - Master project charter, security rules, domain constraints, and tri-engine specification.

---

## Key Architecture & Domain Rules

1. **Tri-Engine Analytics Architecture**:
   - Engine 1: Technical & Price-Vol (`Quote.history`, `Quote.intraday`, order flow delta, indicators).
   - Engine 2: Macro, Cashflow & Liquidity (Foreign flow, proprietary flow, USD/VND, gold, T+2 settlement model).
   - Engine 3: Quantitative ML & Probabilistic Basis (`VN30F1M` vs. `VN30` basis spread, GARCH/HV volatility, probability models).

2. **Derivatives Protocol (`VN30F1M`)**:
   - 08:45 ATO setup -> Continuous Morning -> Midday -> Afternoon -> 14:15-14:45 ATC prediction & closing.

3. **Forecast Ledger & Auditability**:
   - Every emitted signal/forecast MUST be recorded into `ForecastJournal` at prediction time and backfilled with actual outcomes when resolved.

4. **Vietnam Market Constraints**:
   - Equities: T+2 settlement cycle, HOSE ±7%, HNX ±10%, UPCOM ±15%.
   - Derivatives: T+0, standard contract symbol `VN30F1M`.

5. **Strict Prohibitions**:
   - NO real money broker execution.
   - Paper trading isolated to simulation endpoints & models.
   - NO fabricated/hallucinated market data.
