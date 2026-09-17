# Project Charter & AI Assistant Boundaries (Master Rules)

## 1. Prime Mission & Core Objective
This platform is a **Continuous 24/7 Quantitative Research, Predictive Analytics, and Simulation Engine** dedicated exclusively to the Vietnamese Financial Market (derivatives `VN30F1M` and underlying equities).

### 1.1 Core Mission Statement
- The system operates continuously (**24/7 autonomous background calculation and simulation**) to analyze market dynamics, model scenarios, and generate actionable foresight.
- **Primary Deliverables**:
  1. **ATC Session & Next-Day Forecasting**: High-probability scenario analysis for the ongoing day's ATC call auction (14:30 - 14:45) and directional/volatility forecasts for the following trading day (T+1).
  2. **Optimal Derivatives Positioning (Full-Session Live + 24/7 Paper Trading)**:
     - **Full-Session Active Tracking**: For derivatives (`VN30F1M`), the tracking loop MUST run without interruption through all session phases: **Pre-open (08:45 ATO) -> Morning Continuous (09:00 - 11:30) -> Afternoon Continuous (13:00 - 14:30) -> Closing Call Auction (14:30 - 14:45 ATC)**.
     - Continuous position optimization: Realtime Long/Short triggers, basis arbitrage monitoring, intraday trailing stops, and overnight hedge recommendations.
  3. **Multi-Horizon Equity Portfolios (T+2 Compliant)**: Automated periodic rebalancing and selection of the highest-alpha stock baskets across **Weekly**, **Monthly**, and **Quarterly** horizons.

---

## 2. TRI-ENGINE ANALYTICS ARCHITECTURE (3 ENGINES)

All analytical computations, signal generations, and forecasting pipelines MUST pass through or combine the following **Three Analytical Engines**:

```
+-----------------------------------------------------------------------------------+
|                        24/7 CONTINUOUS RESEARCH PIPELINE                          |
+-------------------------+-------------------------------+-------------------------+
|        ENGINE 1         |           ENGINE 2            |        ENGINE 3         |
|  Technical & Price-Vol  |   Macro, Cashflow & Liquidity | Quantitative ML & Prob  |
+-------------------------+-------------------------------+-------------------------+
| - Multi-timeframe OHLCV | - Foreign flow (Khối ngoại)   | - Volatility modeling   |
| - Order-book & Ticks    | - Proprietary flow (Tự doanh) | - Basis spread model    |
| - Momentum, Breakouts   | - T+2 Cashflow settlement     | - Regime classification |
| - Support/Resistance    | - Market breadth & liquidity  | - Probabilistic outcome |
+-------------------------+-------------------------------+-------------------------+
                          |                               |
                          +---------------+---------------+
                                          |
                                          v
                    +-------------------------------------------+
                    |        ENSEMBLE DECISION & SCENARIO       |
                    | - Full ATO-to-ATC Volatility Response     |
                    | - Current ATC Auction Forecast            |
                    | - Next-Day (T+1) Trend & Price Targets    |
                    | - Optimal VN30F1M Signal (Long/Short/SL)  |
                    | - Periodic Stock Portfolio (Week/Mo/Qtr)  |
                    +-------------------------------------------+
```

### 2.1 Engine 1: Technical & Price-Action Engine
- Multi-timeframe analysis (1-minute, 5-minute, 15-minute, Hourly, Daily).
- Tick-by-tick order matching flow via `Quote.intraday()` (Aggressive Buy vs. Aggressive Sell imbalances).
- Classical indicators (RSI, MACD, Bollinger Bands, ATR, VWAP) combined with Price Action (Liquidity Sweeps, Fair Value Gaps, Key Levels).

### 2.2 Engine 2: Liquidity, Flow & T+2 Cash Flow Engine
- Tracking institutional capital flows: **Foreign Investors (Khối ngoại)** and **Proprietary Desks (Tự doanh)**.
- Market breadth metrics (Advance/Decline lines, New Highs/Lows, Sector rotation).
- Macroeconomic context: Gold prices and exchange rates via `Retail` (USD/VND, SJC gold trends impacting liquidity).
- Strict modeling of the **T+2** equity settlement cycle: purchasing power constraints, margin availability, pending settlement shares, and cash return projections.

### 2.3 Engine 3: Quantitative, Statistical & Machine Learning Engine
- Derivatives-to-Spot Basis spread tracking (`VN30F1M` vs. `VN30` cash index) and arbitrage boundaries.
- Volatility forecasting (HV, GARCH, Implied Volatility proxies) and Monte Carlo scenario simulation.
- Probabilistic classification for session transitions:
  - **ATO Transition (08:45 - 09:00)**: Opening gap distribution and early sentiment bias.
  - **Continuous -> ATC Transition (14:15 - 14:45)**: Closing call auction equilibrium projection.
  - **Post-Market to Next-Day (15:00 - 08:45 T+1)**: Overnight probability landscape.

---

## 3. FULL-SESSION DERIVATIVES PROTOCOL (ATO TO ATC)

To capture volatility and protect positions effectively, the `VN30F1M` pipeline operates across all session regimes:

| Phase | Time Window | System Responsibility |
|---|:---:|---|
| **Pre-ATO / Morning Preparation** | 08:30 - 08:45 | Sync previous settlement prices, compute overnight basis divergence, update key pivots |
| **ATO Call Auction** | 08:45 - 09:00 | Monitor ATO estimated match prices, detect opening gap severity (Bullish/Bearish Gap) |
| **Morning Continuous** | 09:00 - 11:30 | High-frequency 1m & tick processing, VWAP tracking, trend breakouts, intraday paper trades |
| **Midday Intermission** | 11:30 - 13:00 | Background re-computation, basis drift check against VN30 basket, midday scenario updates |
| **Afternoon Continuous** | 13:00 - 14:30 | Institutional flow re-evaluation, liquidity sweep checks, preparation for T+2 settlement impacts |
| **Pre-ATC Setup** | 14:15 - 14:30 | **ATC Prediction Engine Trigger**: Calculate expected rebalancing volume & target closing price |
| **ATC Call Auction** | 14:30 - 14:45 | Full auction monitoring: Track simulated ATC settlement impact, basis closing spread, and finalize day's PnL |
| **Post-Market / Evening (24/7)** | 14:45 - 08:30 | Overnight paper position tuning, scenario simulations, T+1 outlook generation, equity basket rebalancing |

---

## 4. MAXIMUM VNSTOCK CAPABILITY HARNESSING & DOCUMENTATION MAPPING

The system MUST exploit the full capability surface of the `vnstock` v4 ecosystem mapped directly from official documentation ([https://vnstocks.com/docs/vnstock](https://vnstocks.com/docs/vnstock)):

### 4.1 Core Module Hierarchy

```python
# Modern Unified Adapters (Primary Layer)
from vnstock import Quote, Listing, Company, Finance

# High-Level Semantic Explorer Layer (Alternative / Complementary)
from vnstock.ui import Reference, Market, Fundamental, Retail, Broker
```

1. **`Quote` / `Market` (Price, Volatility & Order Matching)**:
   - `Quote.history(interval='1m', count_back=...)`: High-frequency intraday candlestick series.
   - `Quote.history(interval='1D', start=..., end=...)`: Historical bars for training, backtest, and daily baseline.
   - `Quote.intraday(page_size=...)`: Live tick-by-tick order-matching flow (bid/ask aggression, buy/sell volume delta).
   - `Market.quote()`, `Market.futures()`: Cross-asset quote exploration (derivatives, indices, equities).
2. **`Listing` / `Reference` (Universe, Structure & Corporate Metadata)**:
   - `Listing.all_symbols()`: Dynamic ticker universe synchronization across HOSE, HNX, UPCOM, and DERIVATIVES.
   - `Listing.symbols_by_group(group='VN30')`: Component stock weight tracking for basis calculation.
   - `Listing.industries_icb()`: Industry classification for multi-horizon sector rotation models.
   - `Reference.company()`, `Reference.futures()`: Reference data and metadata queries.
3. **`Company` (Corporate Profiles & Ownership)**:
   - `Company.overview()`: Fundamental metadata (shares outstanding, charter capital, market cap).
   - `Company.shareholders()`, `Company.officers()`, `Company.subsidiaries()`: Institutional ownership and governance tracking.
4. **`Finance` / `Fundamental` (Financial Statements & Valuation)**:
   - `Finance.income_statement(period='quarter'|'annual')`: Revenue, operating profit, net income growth.
   - `Finance.balance_sheet()`, `Finance.cash_flow()`, `Finance.ratio()`: Balance sheet health, free cash flow, ROE, ROIC, and debt ratios for Quarterly equity selection.
   - `Fundamental.equity()`: High-level equity valuation and fundamental metrics.
5. **`Retail` (Macro, Commodities & Currency Flows)**:
   - `Retail.gold()`: Domestic and global gold price movement as a macro sentiment / inflation hedge indicator.
   - `Retail.exchange_rate()`: Foreign exchange rates (USD/VND) to gauge institutional liquidity pressure and foreign investor behavior.

### 4.2 Official Documentation Reference Index
To ensure strict alignment with the latest `vnstock` v4 architectural standards, agents should adhere to the following reading order and feature matrix:
- **Introduction & Scope**: [Giới thiệu vnstock](https://vnstocks.com/docs/vnstock/gioi-thieu-vnstock) (Community scope & limits).
- **Architecture**: [Kiến trúc thư viện](https://vnstocks.com/docs/vnstock-data/kien-truc-thu-vien) (Modular structure & data sources).
- **Reference Data**: [Tra cứu Reference](https://vnstocks.com/docs/vnstock/tra-cuu-thong-tin-tham-chieu-reference) (`Reference` class).
- **Market Data**: [Dữ liệu giao dịch Market Data](https://vnstocks.com/docs/vnstock/du-lieu-thi-truong-market-data) (`Market`, `Quote` classes).
- **Fundamental Data**: [Phân tích cơ bản Fundamental](https://vnstocks.com/docs/vnstock/phan-tich-co-ban-fundamental) (`Fundamental`, `Finance` classes).
- **Retail & Commodities**: [Hàng hoá & Bán lẻ Retail](https://vnstocks.com/docs/vnstock/du-lieu-thi-truong-hang-hoa-retail) (`Retail` class for Gold & FX).
- **Visualization**: [Biểu diễn trực quan](https://vnstocks.com/docs/vnstock/bieu-dien-du-lieu) (`vnstock_ezchart`).
- **Alerts & Messaging**: [Gửi tin nhắn Telegram, Lark, Slack](https://vnstocks.com/docs/vnstock/gui-tin-nhan-telegram-slack-larksuite) (Automated signal notification integration).
- **Edition Parity**: [So sánh Free vs Sponsor](https://vnstocks.com/docs/vnstock/so-sanh-free-va-sponsor) (Feature differences & upgrade paths).

---

## 5. ABSOLUTE PROHIBITIONS (ZERO-TOLERANCE RULES)

> [!CAUTION]
> ### RULE 1: STRICTLY NO REAL-MONEY AUTO-EXECUTION BOTS
> - **DO NOT IMPLEMENT** any automated order execution agent, background daemon, webhook, or cron script that connects to any real brokerage account to execute real trades or deploy real capital.
> - **DO NOT INTEGRATE** with proprietary broker trading APIs (e.g., VPS, SSI FastConnect, TCBS, DNSE, VNDIRECT, HSC, Mirae Asset) for live trade placement.
> - **DO NOT STORE, ACCEPT, OR PROMPT FOR** live brokerage credentials: login passwords, trading PINs, 2FA/OTP tokens, or session private keys.
> - **MANDATORY HUMAN-IN-THE-LOOP**: All actual market actions and real capital deployments remain 100% human-driven. The system's output stops at visual recommendations and paper simulation.

> [!CAUTION]
> ### RULE 2: STRICT ISOLATION OF SIMULATION FROM REAL CAPITAL
> - All order placement, balance modifications, fills, cancellations, and PnL metrics MUST reside exclusively within the isolated `paper_trading` / `simulation` database schemas, models, and endpoints.
> - **Context-Level Isolation & Clean Fields**: Clarify simulation context at the Entity/Table/Model level (e.g., `PaperPortfolio`, `PaperOrder`, `SimulationSession`, or `/api/v1/simulation/...`). Internal fields and attributes SHOULD use clean, standard domain terminology (e.g., `balance`, `price`, `volume`, `pnl`, `status`) without requiring redundant prefixes like `simulated_balance` or `virtual_price`.

> [!CAUTION]
> ### RULE 3: DATA INTEGRITY, PERSISTENCE & FORECAST AUDITABILITY
> - **NO FABRICATED DATA**: Never invent, hallucinate, or hardcode market prices, volumes, or financial figures. Every value MUST originate from a verifiable source (a `vnstock` adapter) or a persisted DB row. If data is missing or unavailable, the system MUST surface the gap explicitly — it MUST NOT guess or interpolate silently.
> - **NO LOOK-AHEAD BIAS**: Signals, backtests, and model training MUST only use information available *at the decision timestamp*. Future data must never leak into a historical evaluation.
> - **NO SURVIVORSHIP BIAS**: Universe construction and backtests MUST account for delisted/suspended symbols and historical index constituents — not only today's survivors.
> - **MANDATORY FORECAST LEDGER**: Every forecast/signal emitted MUST be persisted with its prediction (value/direction), timestamp, and contributing engine weights. Once reality resolves, the ledger MUST be back-filled with the actual outcome, error, and score. No forecast may be generated without leaving an auditable trail (see Section 9).

> [!CAUTION]
> ### RULE 4: OUTPUTS ARE INFORMATIONAL, NOT INVESTMENT ADVICE
> - Every forecast, Long/Short trigger, price target, and portfolio suggestion MUST be presented as **informational/educational simulation output**, accompanied by a clear risk disclaimer.
> - The system MUST NOT claim certainty, guarantee returns, or instruct the user to place a specific real order. Final decision authority remains **100% human** (reinforces RULE 1).

---

## 6. VIETNAM MARKET TRADING CONSTRAINTS (DOMAIN LOGIC)

Any quantitative model, simulation, or financial calculation MUST adhere strictly to the rules of the Vietnamese market:

### 6.1 Equities (HOSE, HNX, UPCOM)
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

### 6.2 Derivatives (VN30F1M Futures)
- **Settlement**: T+0 (Intraday buy and sell of the same contract is allowed).
- **Daily Price Limit**: ±7% from previous settlement price.
- **Contract Code Format**: Use standard **`VN30F1M`** (1-month rolling contract). Do NOT use non-standard tokens like `VN301M` or `VN30F`.
- **Trading Hours**: 08:45 - 11:30 & 13:00 - 14:45 (derivatives market opens 15 minutes before the stock market).

---

## 7. MARKET DATA ACQUISITION & RATE-LIMITING RULES

### 7.1 Data Source Orchestration
- **Primary Source**: `VCI` (Vietcap) / `TCBS`.
- **Fallback Source**: `KBS` (KB Securities) / `MSN`.

### 7.2 Caching, Tiered Persistence & Anti-Ban Safeguards
- **Tiered Persistence Policy** (data MUST reach PostgreSQL, but at the right granularity — see Section 9 for the forecast journal):
  | Tier | Data | Retention / Granularity |
  |---|---|---|
  | **Raw tick (`Quote.intraday`)** | Every matched tick | Persist only the **last N days** (configurable, default ~30). Beyond that, keep aggregated/downsampled form. |
  | **1-minute bars** | Intraday OHLCV + buy/sell delta | Aggregate ticks → 1m and persist **indefinitely**; raw ticks may be pruned once aggregated. |
  | **Daily OHLCV / Financials / Profiles** | Historical bars, financial statements, company metadata | Persist **permanently**; serve DB-first. |
  | **Derived data (forecasts, signals, scores)** | Every prediction & realized outcome | Persist **100%, indefinitely** — this is the learning substrate (Section 9). |
- **PostgreSQL-First Storage**: Historical data MUST be served from DB first. Only backfill from external APIs when the DB has missing date ranges (enforces RULE 3 — no fabricated/guessed data).
- **In-Memory TTL Caching** (latency layer on top of persistence, never a substitute for it):
  - Realtime 1m/tick prices: TTL **3 to 5 seconds** in memory (never hit external APIs on every single user request).
  - Metadata / Symbol listings: TTL **24 hours**.
- **No Aggressive Web Scraping**: Rate-limit batch data pipelines; insert minimum delays (0.2s - 0.5s) between batch symbol requests to prevent IP blacklisting.

---

## 8. CODEBASE ARCHITECTURAL CONVENTIONS

### 8.1 Backend (FastAPI + SQLModel + PostgreSQL)
- **Authentication**: All `/api/v1/stock/*` and `/api/v1/simulation/*` endpoints MUST be protected with JWT via `CurrentUser` dependency.
- **SQLModel Patterns**:
  - Always use `session.exec(select(Model))` and wrap order columns in `col()` (e.g., `.order_by(col(StockOHLCVDaily.trading_date))`).
  - Use `datetime.now(UTC)` for timestamps (never timezone-naive `datetime.now()`).
- **Code Quality**:
  - Every backend modification MUST pass `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check` with **0 errors**.

### 8.2 Frontend (React + Vite + TanStack Router + TailwindCSS)
- **Type Safety**: No raw `any` types in route loaders, components, or API data mappers.
- **Route Definitions**: Use `createFileRoute` and maintain `@tanstack/router-plugin` generated tree in `routeTree.gen.ts`.
- **Code Quality**: Every frontend change MUST pass `npm run build` cleanly.

---

## 9. FORECAST JOURNAL & CONTROLLED SELF-LEARNING LOOP

The system MUST learn from its own past mistakes. This is achieved through two layers — a cheap **recording/measurement** layer (mandatory, always on) and a governed **recalibration** layer (heavier, auditable, reversible). The learning loop MUST NOT degenerate into overfitting on noise.

### 9.1 Layer A — Forecast Ledger (Record & Measure)
Every forecast/signal emitted by the Ensemble (Section 2) MUST be written to a persistent ledger at prediction time, then back-filled with the realized outcome.

- **Suggested model — `ForecastJournal`** (SQLModel, lives in the analytics DB):

  | Field | Meaning |
  |---|---|
  | `id` | Unique signal identifier |
  | `asset` / `symbol` | Target instrument (e.g. `VN30F1M`, equity ticker) |
  | `horizon` | ATC / T+1 / Weekly / Monthly / Quarterly |
  | `predicted_at` | UTC timestamp of the prediction (anchors the no-look-ahead guarantee) |
  | `predicted_value` / `predicted_direction` | The forecast itself |
  | `engine_weights` | JSON snapshot of Engine 1/2/3 contributions |
  | `model_version` / `parameter_snapshot` | Which calibration produced it (for traceability & rollback) |
  | `actual_value` / `realized_at` | Back-filled once reality resolves |
  | `error` / `score` | e.g. MAE for value targets, directional accuracy / Brier score for probabilities |
  | `status` | `pending` → `resolved` → `scored` |

- **Scoring metrics**: directional accuracy, Brier score (probabilistic calibration), MAE/RMSE (price targets). Computed automatically once `status = resolved`.

### 9.2 Layer B — Controlled Recalibration Loop (Learn)
The ledger feeds a **governed** feedback loop. It adjusts analytical calibration — it does NOT freely self-modify model code, and it NEVER touches real order execution (RULE 1) or escapes the simulation boundary (RULE 2).

- **What it MAY adjust**: ensemble engine weights, signal thresholds, regime-detection parameters, probability calibration (e.g. Platt/isotonic on the ledger).
- **Hard guardrails**:
  - **Auditable & reversible**: every recalibration MUST write a new `model_version` + `parameter_snapshot`. The previous version MUST remain restorable (rollback).
  - **No live mutation by default**: a recalibration MUST pass a validation/walk-forward gate on the ledger before it becomes active; it is never applied to the live signal path un-reviewed.
  - **Human-in-the-loop for promotion**: promoting a new calibration to the active path is a human-approved action, consistent with the informational-only stance (RULE 4).
  - **Anti-overfit**: validate out-of-sample; refuse recalibrations whose improvement is within noise, and cap how aggressively weights may shift per cycle.

### 9.3 Continuous Loop
```
predict ──► write ForecastJournal (pending)
   │
   ▼ (reality resolves)
back-fill actual ──► score ──► aggregate accuracy by engine/horizon/regime
   │
   ▼ (governed, gated)
recalibrate weights/thresholds ──► new model_version (snapshot)
   │
   ▼ (walk-forward validation + human approval)
promote to active signal path  ◄── rollback always available
```
