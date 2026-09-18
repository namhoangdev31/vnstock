export const phase2Markdown = `# Đặc Tả Kỹ Thuật (TRD) Phase 2: Tri-Engine Analytics Core & Ensemble Decision System

Tài liệu này xác định chi tiết **Yêu cầu kỹ thuật (Technical Requirements)**, **Kiến trúc Module (Architecture & Interfaces)**, **Tiêu chuẩn nghiệm thu (Definition of Done - DoD)** và **Ma trận kịch bản kiểm thử (Test Matrix)** cho Phase 2 của hệ sinh thái Quantitative Research & Simulation Engine vnstock.

---

## 1. Mục Tiêu & Tầm Nhìn Phase 2

Xây dựng lõi tính toán định lượng gồm **3 Động cơ Phân tích (Tri-Engine Architecture)** độc lập và **Bộ hợp nhất đa tầng (Ensemble Decision Engine)** theo đúng quy định tại AGENTS.md (Section 2):

\`\`\`
+-----------------------------------------------------------------------------------+
|                        TRI-ENGINE ANALYTICS CORE (PHASE 2)                        |
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
                    | - Dynamic Weight Blending (w1, w2, w3)    |
                    | - Optimal VN30F1M Signal (Long/Short/SL)  |
                    | - Current ATC Auction Forecast            |
                    | - Next-Day (T+1) Trend & Scenario Matrix  |
                    | - Mandatory ForecastJournal Auto-Ledger   |
                    +-------------------------------------------+
\`\`\`

---

## 2. Đặc Tả Chi Tiết 3 Engine Phân Tích

### 2.1 Engine 1: Technical & Price-Action Engine (TechnicalEngine)
* **Mục tiêu**: Phân tích hành động giá đa khung thời gian, dòng lệnh tick chủ động (Orderflow) và cấu trúc thị trường (Market Structure).
* **Đầu vào (Inputs)**:
  - Nến OHLCV đa khung: 1m, 5m, 15m, 1H, 1D từ StockOHLCVDaily và Quote.history().
  - Dòng lệnh khớp liên tục tick-by-tick từ TickFlowAggregated / Quote.intraday().
* **Thuật toán & Chỉ báo (Indicators & Formulas)**:
  1. **Chỉ báo động lượng & xu hướng**:
     - RSI 14 (Relative Strength Index): Quá mua (>70), Quá bán (<30), Phân kỳ đỉnh/đáy.
     - MACD (12, 26, 9): Histogram, Signal line, Golden/Death Cross.
     - Bollinger Bands (20, 2): Squeeze detection, Upper/Lower bands, Bandwidth.
     - ATR 14 (Average True Range): Đo lường biến động cho Stop Loss và Trailing Stop.
     - VWAP (Volume Weighted Average Price): Tích lũy theo phiên:
       VWAP = sum(Typical_Price * Volume) / sum(Volume)
  2. **Dòng lệnh & Áp lực mua/bán (Orderflow / Aggressive Delta)**:
     - Khối lượng mua chủ động (Vol_Buy) vs. Bán chủ động (Vol_Sell).
     - Volume Delta: Delta = Vol_Buy - Vol_Sell.
     - Order Imbalance Ratio:
       Imbalance = (Vol_Buy - Vol_Sell) / (Vol_Buy + Vol_Sell) [-1.0, 1.0]
  3. **Cấu trúc giá (Price Action & Key Levels)**:
     - Camarilla & Classic Pivots: Các ngưỡng R1..R4, S1..S4.
     - Liquidity Sweeps: Quét thanh khoản đỉnh/đáy rồi đảo chiều.
     - Fair Value Gaps (FVG): Khoảng trống giá mất cân bằng 3 nến.
* **Đầu ra (Engine1Signal)**:
  - trend: BULLISH | BEARISH | NEUTRAL
  - score: float (-1.0 đến +1.0)
  - vwap, rsi, macd, atr
  - volume_delta, order_imbalance
  - key_levels (Pivots, FVG)

---

### 2.2 Engine 2: Liquidity, Flow & T+2 Cashflow Engine (FlowLiquidityEngine)
* **Mục tiêu**: Đo lường dòng vốn tổ chức (Khối ngoại, Tự doanh), độ rộng thị trường (Market Breadth), luân chuyển ngành (Sector Rotation) và mô hình hóa ràng buộc chu kỳ thanh toán T+2.
* **Đầu vào (Inputs)**:
  - Bảng InstitutionalFlow (Khối ngoại & Tự doanh mua/bán ròng).
  - Bảng MarketBreadth (Mã tăng, giảm, đứng giá, trần, sàn, thanh khoản).
  - Bảng MacroIndicator (Tỷ giá USD/VND, Giá vàng SJC mua/bán, Giá vàng thế giới).
  - Ngành ICB (Listing.industries_icb()).
* **Thuật toán & Mô hình hóa**:
  1. **Chỉ số Dòng tiền Tổ chức (Institutional Flow Momentum - IFM)**:
     - Tích lũy mua ròng lăn 3d, 5d, 10d của Khối ngoại và Tự doanh:
       IFM = alpha * F_net_norm + (1 - alpha) * P_net_norm (alpha = 0.6)
  2. **Độ rộng thị trường (Market Breadth Index - MBI)**:
     - Advance/Decline Ratio & Breadth Score:
       Breadth_Score = (N_advancers - N_decliners) / N_total [-1.0, 1.0]
  3. **Mô hình hóa chu kỳ thanh toán T+2 (Vietnamese Equity T+2 Cycle)**:
     - Mô hình hàng T+2 về vào 13:00 chiều T+2.
     - Áp lực hàng T+2 về tài khoản (T+2 Selling Pressure Index): Đo lường lượng volume mua bắt đáy đột biến ngày T để ước tính áp lực chốt lời/cắt lỗ tiềm tàng vào đầu phiên chiều T+2.
  4. **Tác động Vĩ mô & Ngoại hối (Macro Sentiment Index)**:
     - Biến động tỷ giá USD/VND và chênh lệch giá vàng phản ánh dòng vốn FII rút ròng hoặc tìm nơi trú ẩn.
* **Đầu ra (Engine2Signal)**:
  - institutional_bias: BULLISH | BEARISH | NEUTRAL
  - score: float (-1.0 đến +1.0)
  - foreign_net_5d, prop_net_5d, market_breadth_score
  - t_plus_2_pressure_index (0.0 đến 1.0)
  - macro_liquidity_pressure (-1.0 đến 1.0)

---

### 2.3 Engine 3: Quantitative, Statistical & ML Engine (QuantMLEngine)
* **Mục tiêu**: Mô hình hóa chênh lệch Basis phái sinh - cơ sở, độ biến động thống kê (Volatility) và xác suất chuyển phiên (ATO, ATC, T+1).
* **Đầu vào (Inputs)**:
  - Chuỗi giá VN30F1M và chỉ số cơ sở VN30.
  - Lịch sử Basis các phiên liền trước.
* **Thuật toán & Thống kê**:
  1. **Mô hình Phân kỳ Basis Spread (Derivatives-to-Spot Basis Model)**:
     - Basis = P_VN30F1M - P_VN30.
     - Z-score = (Basis - Mean_20) / Std_20.
     - Quy tắc Arbitrage Mean-Reversion:
       - Z_basis > +2.0: Tín hiệu Short Bias đảo chiều.
       - Z_basis < -2.0: Tín hiệu Long Bias đảo chiều.
  2. **Dự báo Độ biến động (Volatility Modeling)**:
     - Historical Volatility (HV 20-day annualized).
     - Parkinson Volatility (dựa trên High/Low).
  3. **Xác suất Chuyển Phiên (Probabilistic Transition Classifiers)**:
     - ATO Gap probability P(Gap > 0).
     - ATC Closing Auction Equilibrium Projection: Dự báo Delta P_ATC và xác suất kịch bản đóng cửa lúc 14:45.
     - T+1 Monte Carlo Simulation (1,000 paths trong biên độ +/- 7%).
* **Đầu ra (Engine3Signal)**:
  - basis_current, basis_z_score
  - volatility_hv, volatility_parkinson
  - score: float (-1.0 đến +1.0)
  - atc_forecast (kịch bản giá ATC và xác suất)
  - next_day_forecast (dải giá P_low, P_high, P_close kỳ vọng)

---

### 2.4 Ensemble Decision Engine (EnsembleEngine)
* **Mục tiêu**: Hợp nhất 3 Engine với trọng số động (w1, w2, w3), sinh tín hiệu giao dịch tối ưu VN30F1M và tự động lưu sổ nhật ký ForecastJournal (Rule 3).
* **Hợp nhất Trọng số Động**:
  - Score_Ensemble = w1 * Score_Engine1 + w2 * Score_Engine2 + w3 * Score_Engine3.
  - Tự động chuẩn hóa sum(w) = 1.0.
  - Thích ứng theo phiên: Trong phiên ưu tiên Engine 1; Trước ATC ưu tiên Engine 3.
* **Sinh Tín Hiệu & Quản Trị Rủi Ro**:
  - Score >= +0.35: LONG (Confidence = |Score|).
  - Score <= -0.35: SHORT (Confidence = |Score|).
  - Ngược lại: NEUTRAL.
  - Dynamic Stop Loss (k * ATR_14) & Take Profit (R:R >= 1:2.0).
  - Tự động tạo bản ghi ForecastJournal với trạng thái 'pending' (Không Look-Ahead Bias).

---

## 3. Danh Sách API Endpoints Mới (FastAPI Phase 2)

| Method | Endpoint | Mô tả chức năng |
|---|---|---|
| GET | /api/v1/quant/engine1/technical/{symbol} | Chỉ báo kỹ thuật, VWAP, Orderflow Delta, Liquidity Sweeps |
| GET | /api/v1/quant/engine2/flow-liquidity | Dòng tiền Khối ngoại, Tự doanh, Độ rộng thị trường, Áp lực T+2 |
| GET | /api/v1/quant/engine3/basis-volatility | Chỉ số Basis, Z-score, Volatility và xác suất chuyển phiên |
| POST | /api/v1/quant/ensemble/signal | Tính toán tín hiệu hợp nhất VN30F1M & tự động lưu ForecastJournal |
| GET | /api/v1/quant/ensemble/atc-forecast | Dự báo phiên ATC thời gian thực (14:15 - 14:45) |
| GET | /api/v1/quant/ensemble/next-day-forecast | Dự báo phiên tiếp theo T+1 (Dải giá kỳ vọng và kịch bản) |
| GET | /api/v1/quant/ensemble/weights | Lấy cấu hình trọng số hiện tại của 3 engine |
| PUT | /api/v1/quant/ensemble/weights | Cập nhật cấu hình trọng số w1, w2, w3 |

---

## 4. Tiêu Chuẩn Hoàn Thành (Definition of Done - DoD)

1. Tách biệt 3 Engine độc lập trong backend/app/services/quant/.
2. Tuân thủ tuyệt đối RULE 1 (No Real Orders), RULE 2 (Isolation), RULE 3 (No Fake Data, Forecast Ledger), RULE 4 (Disclaimer).
3. uv run ruff check -> 0 errors; uv run ty check app -> 0 diagnostics.
4. Unit tests đầy đủ với coverage >= 90% trên các quant services.
`;
