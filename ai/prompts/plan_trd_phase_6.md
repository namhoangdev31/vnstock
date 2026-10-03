# Prompt: Comprehensive Implementation Planning for TRD Phase 6 (Frontend Dashboards & Quantitative Trading Cockpit)

Read the following reference documents carefully and in strict order before drafting the plan:
1. `ai/start_task.md` (Mandatory workflow before creating or modifying code)
2. `ai/context.md` (Single source of truth for overall project architecture)
3. `ai/project_map.json` (Module navigation map and file routing)
4. `AGENTS.md` (Master project charter, especially §1 Prime Mission, §2 Tri-Engine Architecture, §5 Absolute Prohibitions, §6 Vietnam Market Trading Constraints, §8.2 Frontend Nuxt 3 & Strict UI Rules)
5. `frontend/data/trd/phase6SpecContent.ts` (Detailed TRD Phase 6 Markdown specification)
6. Key relevant codebase files:
   - `frontend/pages/admin/trd/phase-6.vue` (Existing Phase 6 prototype & test matrix)
   - `frontend/pages/iboard/index.vue` (Existing high-performance trading board)
   - `frontend/layouts/default.vue`
   - `frontend/package.json` (Dependencies: Nuxt 3, Vue 3, @nuxt/ui, TailwindCSS)
   - Backend APIs for integration:
     - `backend/app/domains/quant/presentation/quant_router.py` (Ensemble signals, ATC & T+1 forecasts, Monte Carlo)
     - `backend/app/domains/quant/presentation/forecast_router.py` (Forecast ledger & metrics)
     - `backend/app/domains/quant/presentation/recalibration_router.py` (Model versions & rollback)
     - `backend/app/domains/simulation/presentation/router.py` (Paper trading account, orders, positions)
     - `backend/app/domains/market_data/presentation/router.py` (Quotes, OHLCV, ticks, breadth, flows)

---

## 🎯 Task Goal
Formulate a comprehensive, actionable, step-by-step **Technical Implementation Plan** to fulfill 100% of the requirements in **TRD Phase 6: Frontend Dashboards & Quantitative Trading Cockpit (Realtime Derivatives Command Station, Flow Radar, ATC/T+1 Prediction Scenarios & Paper Trading Terminal)**.

> [!IMPORTANT]
> **Tech Stack Alignment**:
> Although legacy notes in `phase6SpecContent.ts` initially referred to React, the canonical, active frontend stack of this project is **Nuxt 3 + Vue 3 Composition API + @nuxt/ui + TailwindCSS + TypeScript** (as mandated by `AGENTS.md` §8.2). All components, composables, routes, and styling MUST be implemented within this Nuxt 3 architecture.

The system must deliver:
- **Derivatives Live Command Station**: High-performance real-time candlestick charts (`VN30F1M` 1m/5m/15m) using `lightweight-charts` inside `<ClientOnly>`, live tick flow order delta, Basis spread gauge ($P_{\text{F1M}} - I_{\text{VN30}}$), and dynamic SL/TP Ensemble signal cards.
- **Institutional Flow & Breadth Radar**: Visualizing Foreign and Proprietary trading flow, Advance/Decline breadth gauge, T+2 afternoon liquidation pressure meter, and USD/VND / SJC gold macro tickers.
- **ATC & T+1 Prediction Terminal**: Live ATC pre-open imbalance monitor, Monte Carlo probability distribution chart (P10 - P50 - P90 within $\pm 7\%$ limits), and live Forecast Audit Ledger table with Brier score metrics.
- **Paper Trading Cockpit**: Virtual balance overview, virtual order placement form (LO, MP, ATO, ATC, STOP_LOSS with 17% initial margin validation), open positions table with 1-click Quick Close, order history, and Alpha Baskets rebalancing.
- **Zero Real-Money Guarantee & Prominent Warning**: Clear visual badge **`[MÔ PHỎNG / PAPER TRADING 100%]`** on all trading panels.

---

## 🛡️ Absolute Prohibitions (Zero-Tolerance Rules)
1. **RULE 1 - Strictly No Real-Money Execution Bots**: No live brokerage API integration. All trading forms and buttons must route strictly to `/api/v1/simulation/...`.
2. **RULE 2 - Strict Simulation Isolation**: Account balances, PnL, margin, and order status must remain strictly isolated within simulation stores and endpoints.
3. **RULE 3 - Data Integrity & No Fabricated Data**: Market prices, orderflow delta, and predictions must originate from real backend API responses.
4. **RULE 4 - Informational & Educational Only**: Prominently display risk disclaimers across all prediction and signal widgets.
5. **Strict Frontend UI Standards (AGENTS §8.2)**:
   - **Token CSS Only (No Arbitrary Colors)**: All background, text, and border colors must use canonical tokens (e.g., `bg-surface-abyss`, `bg-surface-midnight`, `text-aave-graphite`, `text-aave-iron`, `bg-aave-obsidian`, `border-white/[0.08]`). Arbitrary hex codes like `bg-[#10B981]` are strictly prohibited.
   - **Zero Gradients**: Absolutely no `bg-gradient-to-...` or `linear-gradient(...)`. All card surfaces and buttons must be disciplined flat surfaces.
   - **Zero Emojis in Text**: Never use emojis in labels or headings. Use system `<UIcon>` components instead.
   - **No Parentheses `()` for Explanatory Notes**: Never use `()` in text labels to explain acronyms or terms. Use `<UTooltip text="...">` instead.
6. **Code Quality Gates**:
   - `bun run lint` must pass with 0 errors.
   - `bun run typecheck` must pass with 0 errors.
   - `bun run build` must build cleanly with 0 errors.

---

## 📋 Required Plan Deliverables

The implementation plan presented by AGENTS must include the following sections:

### 1. Gap Analysis
- Audit existing frontend assets vs. Phase 6 specification:
  - Existing `frontend/pages/admin/trd/phase-6.vue` (identifying static mock elements that need real backend integration).
  - Existing `frontend/pages/iboard/index.vue` (identifying reusable chart widgets, order book tables, and stock services).
  - Missing standalone components in `frontend/components/trading/`.
  - Missing reactive composables in `frontend/composables/`.
  - Charting library setup: verifying `lightweight-charts` compatibility with Nuxt 3 SSR (`<ClientOnly>`).

### 2. Architecture & Component Hierarchy (4 Core Tabs)
Deconstruct Phase 6 into 4 cohesive dashboards:

#### Tab 1: Derivatives Command Station (`DerivativesStation.vue`)
- `DerivativesPriceHeader.vue`: Current `VN30F1M` price, change, %, ceiling/floor/reference, and live Basis divergence ($P_{\text{F1M}} - I_{\text{VN30}}$).
- `InteractiveCandleChart.vue`: Responsive TradingView `lightweight-charts` candlestick chart with 1m, 5m, 15m resolution, VWAP line, and dynamic Bollinger Bands.
- `OrderflowDeltaBar.vue`: Aggressive buy volume vs. aggressive sell volume delta ($V_{\text{buy}} - V_{\text{sell}}$) per 1-minute interval.
- `EnsembleSignalCard.vue`: Real-time strategy card displaying `LONG` / `SHORT` / `NEUTRAL`, Confidence Score (%), Entry Zone, Dynamic ATR Stop Loss, Take Profit ($R:R \ge 1:2.0$), and Trailing Stop.

#### Tab 2: Flow & Breadth Radar (`FlowRadar.vue`)
- `InstitutionalFlowChart.vue`: Foreign investors (Khối ngoại) and Proprietary desks (Tự doanh) net buying/selling value on the VN30 basket.
- `MarketBreadthGauge.vue`: HOSE Advance/Decline ratio, ceiling/floor counter, and sector rotation distribution.
- `TPlus2PressureMeter.vue`: Afternoon T+2 liquidity pressure meter estimating profit-taking pressure during 13:00 - 14:15.
- `MacroSummaryTicker.vue`: Realtime USD/VND exchange rate and SJC gold price trends.

#### Tab 3: ATC & T+1 Prediction Terminal (`PredictionTerminal.vue`)
- `AtcImbalanceMonitor.vue`: Expected matched volume, price deviation, and buy/sell delta during the 14:15 - 14:45 pre-ATC/ATC auction.
- `MonteCarloDistributionChart.vue`: Probability distribution of 10,000 simulated price paths, highlighting Median (P50), 80% confidence interval (P10 - P90), and daily $\pm 7\%$ price limits.
- `ForecastLedgerTable.vue`: Historical audit ledger displaying past predictions, realized settlement prices, directional accuracy badges, and Brier scores.

#### Tab 4: Paper Trading Cockpit (`PaperCockpit.vue`)
- `VirtualAccountOverview.vue`: Initial capital, virtual cash balance, margin utilization % (17% initial margin for derivatives), realized and unrealized PnL.
- `OrderPlacementForm.vue`: Virtual order execution form for `VN30F1M` and equities (`LO`, `MP`, `ATO`, `ATC`, `STOP_LOSS`), with margin check and dynamic SL/TP setting.
- `ActivePositionsTable.vue`: Open virtual positions with real-time mark-to-market PnL and 1-click Quick Close.
- `OrderHistoryTable.vue`: Filterable virtual order history (`PENDING`, `FILLED`, `CANCELLED`).
- `AlphaBasketsRebalanceCard.vue`: Recommended Weekly, Monthly, and Quarterly alpha equity baskets with 1-click "Virtual Allocate".

### 3. Reactive State Management & Composables Layer
Specify the composables to create or enhance:
- `useDerivativesLive(symbol: Ref<string>)`:
  - Session-adaptive polling (1s in continuous trading, 5s in intermission/overnight).
  - Web worker or throttle for smooth candle rendering.
- `useFlowBreadthRadar()`: Polling institutional flows, market breadth, and macro indicators.
- `useAtcPrediction()`: Fetching ATC call auction simulation, Monte Carlo paths, and prediction scenarios.
- `usePaperTrading()`: Managing virtual account state, placing orders, closing positions, and resetting balance.
- Network resilience: Reconnecting states, offline handling, and custom error toast integration (`useCustomToast`).

### 4. Step-by-Step Implementation Roadmap
Organize into sequential, reviewable execution steps:
- **Step 1: Charting & Core Libraries Setup**: Install/verify `lightweight-charts` and create SSR-safe Vue 3 wrapper.
- **Step 2: API Client & Composables**: Implement reactive composables interfacing backend endpoints.
- **Step 3: Derivatives Station & Signal Components**: Implement Tab 1 components.
- **Step 4: Flow, Breadth & Macro Radar Components**: Implement Tab 2 components.
- **Step 5: ATC & Monte Carlo Prediction Components**: Implement Tab 3 components.
- **Step 6: Paper Trading Cockpit Components**: Implement Tab 4 components.
- **Step 7: View Integration & Route Wiring**: Integrate all tabs into `frontend/pages/admin/trd/phase-6.vue` (and main navigation).
- **Step 8: Quality Checks & Responsiveness Polish**: Audit CSS design tokens, flat surfaces, zero emojis, tooltips, and verify mobile layout.

### 5. Acceptance Test Matrix (TEST-FE-01 to TEST-FE-08)
Detailed verification scenarios corresponding to TRD Phase 6 criteria:
1. `TEST-FE-01`: Derivatives Station candle chart renders smoothly without full-page flickering on realtime updates.
2. `TEST-FE-02`: Timeframe switching (1m, 5m, 15m) dynamically loads historical candle bars.
3. `TEST-FE-03`: Order form accurately computes required initial margin ($P \times 100{,}000 \times 17\%$).
4. `TEST-FE-04`: Insufficient virtual balance disables order submit button with an informative tooltip.
5. `TEST-FE-05`: Placing a paper order immediately updates open positions and order history reactively.
6. `TEST-FE-06`: Monte Carlo distribution chart clearly displays P10 - P50 - P90 within the $\pm 7\%$ ceiling/floor bounds.
7. `TEST-FE-07`: Mobile layout (< 768px) cleanly stacks widgets vertically without horizontal overflow.
8. `TEST-FE-08`: Temporary network disconnection shows "Offline / Reconnecting" state without crashing the page.

---
**Begin by inspecting the referenced files, performing the frontend gap analysis, and outlining the full Technical Implementation Plan!**
