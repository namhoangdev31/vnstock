# Project Charter & AI Assistant Boundaries (Master Rules)

## 1. Project Goal & Core Scope
This project is an **Investment Decision-Support, Quantitative Analysis, and Simulation Sandbox** tailored specifically for the Vietnamese Financial Market (VN30F1M index futures and underlying equities).

The platform comprises exactly four functional pillars:
1. **Actionable Signals & Position Recommendations**:
   - Quantitative indicators, algorithmic setups, and technical analysis generating structured trading signals (Entry, Target Take-Profit, Stop-Loss, Risk/Reward Ratio).
2. **Live Market Monitoring**:
   - Real-time quote tracking, order-book depth, candlestick visualization (1-minute, daily, and tick-by-tick) to empower informed human decisions.
3. **Paper Trading & Sandbox Engine**:
   - Virtual order simulation, hypothetical portfolio performance measurement, slippage/fee accounting, and historical strategy backtesting.
4. **Portfolio & Cash Flow Modeling (T+2 Settlement)**:
   - Cash flow and purchasing power modeling compliant with Vietnam's **T+2** settlement cycle (equities buy on day T, settle at 13:00 on day T+2).
   - Risk management rules for margin limits, drawdown thresholds, and capital allocation.

---

## 2. ABSOLUTE PROHIBITIONS (ZERO-TOLERANCE RULES)

> [!CAUTION]
> ### RULE 1: STRICTLY NO REAL-MONEY AUTO-EXECUTION BOTS
> - **DO NOT IMPLEMENT** any automated order execution agent, background daemon, webhook, or cron script that connects to any real brokerage account to execute real trades or deploy real capital.
> - **DO NOT INTEGRATE** with proprietary broker trading APIs (e.g., VPS, SSI FastConnect, TCBS, DNSE, VNDIRECT, HSC, Mirae Asset) for order routing or live trade placement.
> - **DO NOT STORE, ACCEPT, OR PROMPT FOR** live brokerage credentials: login passwords, trading PINs, 2FA/OTP tokens, or session private keys.
> - **MANDATORY HUMAN-IN-THE-LOOP**: All actual market actions and real capital deployments remain 100% human-driven. The system's output stops at visual recommendations and paper simulation.

> [!CAUTION]
> ### RULE 2: STRICT ISOLATION OF SIMULATION FROM REAL CAPITAL
> - All order placement, balance modifications, fills, cancellations, and PnL metrics MUST reside exclusively within the isolated `paper_trading` / `simulation` database schemas and models.
> - Any state that simulates money MUST be explicitly labeled with simulated prefixes (e.g., `simulated_balance`, `paper_portfolio`, `virtual_order`).

---

## 3. VIETNAM MARKET TRADING CONSTRAINTS (DOMAIN LOGIC)

Any quantitative model, simulation, or financial calculation MUST adhere strictly to the rules of the Vietnamese market:

### 3.1 Equities (HOSE, HNX, UPCOM)
- **Settlement Cycle**: **T+2** (Purchased shares become sellable in the afternoon session of T+2; sold cash settles in the afternoon of T+2).
- **Price Limits (Daily Ceilings / Floors)**:
  - **HOSE**: ±7% from reference price.
  - **HNX**: ±10% from reference price.
  - **UPCOM**: ±15% from reference price.
- **Trading Sessions**:
  - ATO (Opening Call Auction): 09:00 - 09:15.
  - Continuous Auction: 09:15 - 11:30 & 13:00 - 14:30.
  - ATC (Closing Call Auction): 14:30 - 14:45.
  - Put-Through (Thỏa thuận): 09:00 - 15:00.

### 3.2 Derivatives (VN30F1M Futures)
- **Settlement**: T+0 (Intraday buy and sell of the same contract is allowed).
- **Daily Price Limit**: ±7% from previous settlement price.
- **Contract Code Format**: Use standard **`VN30F1M`** (1-month rolling contract). Do NOT use non-standard tokens like `VN301M` or `VN30F`.
- **Trading Hours**: 08:45 - 11:30 & 13:00 - 14:45 (derivates market opens 15 minutes before the stock market).

---

## 4. MARKET DATA ACQUISITION & RATE-LIMITING RULES

### 4.1 Data Engine Architecture
- Use `vnstock` v4 (Community Edition) via dedicated adapters:
  ```python
  from vnstock import Quote, Listing, Company, Finance
  ```
- **Primary Source**: `VCI` (Vietcap) / `TCBS`.
- **Fallback Source**: `KBS` (KB Securities) / `MSN`.

### 4.2 Caching & Anti-Ban Safeguards
- **PostgreSQL-First Storage**: Historical data (Daily OHLCV, Company Profiles, Financial Reports) MUST be stored permanently in PostgreSQL and served from DB first. Only backfill from external APIs if DB has missing date ranges.
- **In-Memory TTL Caching**:
  - Realtime 1m/tick prices: TTL **3 to 5 seconds** in memory (never hit external APIs on every single user request).
  - Metadata / Symbol listings: TTL **24 hours**.
- **No Aggressive Web Scraping**: Rate-limit batch data pipelines; insert minimum delays (0.2s - 0.5s) between batch symbol requests to prevent IP blacklisting.

---

## 5. CODEBASE ARCHITECTURAL CONVENTIONS

### 5.1 Backend (FastAPI + SQLModel + PostgreSQL)
- **Authentication**: All `/api/v1/stock/*` and `/api/v1/simulation/*` endpoints MUST be protected with JWT via `CurrentUser` dependency.
- **SQLModel Patterns**:
  - Always use `session.exec(select(Model))` and wrap order columns in `col()` (e.g., `.order_by(col(StockOHLCVDaily.trading_date))`).
  - Use `datetime.now(UTC)` for timestamps (never timezone-naive `datetime.now()`).
- **Code Quality**:
  - Every backend modification MUST pass `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check` with **0 errors**.

### 5.2 Frontend (React + Vite + TanStack Router + TailwindCSS)
- **Type Safety**: No raw `any` types in route loaders, components, or API data mappers.
- **Route Definitions**: Use `createFileRoute` and maintain `@tanstack/router-plugin` generated tree in `routeTree.gen.ts`.
- **Code Quality**: Every frontend change MUST pass `npm run build` cleanly.
