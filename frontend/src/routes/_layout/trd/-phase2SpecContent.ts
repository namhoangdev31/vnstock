export const phase2Markdown = `# Đặc Tả Kỹ Thuật (TRD) Phase 2: Tri-Engine Analytics Core & Ensemble Decision System

Tài liệu này xác định chi tiết **Yêu cầu kỹ thuật (Technical Requirements)**, **Kiến trúc Workflow & Thuật toán (Architectural Workflow & Algorithms)**, **Sơ đồ luồng xử lý (Dataflow Diagram)**, **Mô hình Cơ sở Dữ liệu (Database Models)**, **Tiêu chuẩn nghiệm thu (Definition of Done - DoD)** và **Ma trận kịch bản kiểm thử (Test Matrix)** cho Phase 2 của hệ sinh thái Quantitative Research & Simulation Engine vnstock.

---

## 1. Mục Tiêu & Kiến Trúc Tổng Quan Phase 2

Phase 2 tập trung xây dựng lõi tính toán định lượng gồm **3 Động cơ Phân tích độc lập (Tri-Engine Architecture)** và **Bộ hợp nhất đa tầng (Ensemble Decision Engine)** theo quy định tại AGENTS.md (Section 2).

### 1.1 Sơ Đồ Luồng Xử Lý Dữ Liệu Tổng Quan (End-to-End Workflow Diagram)

\`\`\`
                                  [ MARKET DATA LAYER ]
  vnstock Adapters (Quote, Listing, Retail) / PostgreSQL DB (StockOHLCVDaily, InstitutionalFlow, MacroIndicator)
                                            │
                                            ▼
                             [ FEATURE EXTRACTION PIPELINE ]
      Chuẩn hóa chuỗi thời gian, lọc dữ liệu rác, tính toán biến động nến & orderflow tick
                                            │
              ┌─────────────────────────────┼─────────────────────────────┐
              │                             │                             │
              ▼                             ▼                             ▼
   [ ENGINE 1: TECHNICAL ]       [ ENGINE 2: LIQUIDITY ]        [ ENGINE 3: QUANT ML ]
   - Multi-TF OHLCV (1m->1D)     - Institutional Flow (FII/Prop)- Basis Spread Z-score
   - RSI, MACD, BB, ATR, VWAP    - Market Breadth (ADR/Volume)  - Volatility (HV/Parkinson)
   - Tick Orderflow Delta        - T+2 Settlement Constraints   - ATO/ATC Transition Models
   - Liquidity Sweeps & FVG      - Macro FX & Gold Sentiment    - Monte Carlo T+1 Projection
              │                             │                             │
              └─────────────────────────────┼─────────────────────────────┘
                                            │
                                            ▼
                           [ ENSEMBLE DECISION ENGINE ]
   1. Dynamic Weight Blending: w1(t)*Engine1 + w2(t)*Engine2 + w3(t)*Engine3
   2. Time-of-Day Weight Adjustment (ATO -> Continuous -> Pre-ATC -> ATC -> Post-Market)
   3. Conflict Resolution (Xử lý khi Engine 1 & Engine 3 mâu thuẫn)
   4. Signal Thresholding: Score >= +0.35 (LONG), Score <= -0.35 (SHORT), Else (NEUTRAL)
   5. Dynamic SL/TP Calculation (ATR-based + Key Pivot Levels) & Position Sizing
                                            │
                                            ▼
                           [ FORECAST JOURNAL (RULE 3 AUDIT) ]
   Lưu vết 100% dự báo vào DB (\`forecast_journal\`) với state='pending', timestamp, model_version
                                            │
                                            ▼
                             [ FASTAPI REST API LAYER ]
               \`/api/v1/quant/*\` Endpoints (Protected by JWT Authentication)
\`\`\`

---

## 2. Đặc Tả Chi Tiết Thuật Toán & Workflow Của 3 Engine Phân Tích

---

### 2.1 Engine 1: Technical & Price-Action Engine (TechnicalEngine)

#### Workflow Chi Tiết:
1. **Nạp dữ liệu**: Tải dữ liệu nến 1m, 5m, 15m, 1h, 1D và dữ liệu tick Quote.intraday().
2. **Tính chỉ báo kỹ thuật cơ bản**:
   - **RSI (14)**:
     RS = EMA(Gain, 14) / EMA(Loss, 14), RSI = 100 - (100 / (1 + RS))
   - **MACD (12, 26, 9)**:
     DIF = EMA(P, 12) - EMA(P, 26), DEA = EMA(DIF, 9), Hist = (DIF - DEA) * 2
   - **Bollinger Bands (20, 2)**:
     MB = MA(P, 20), UB = MB + 2*std, LB = MB - 2*std
   - **ATR (14)**:
     TR = max(High - Low, |High - Close_prev|, |Low - Close_prev|), ATR = EMA(TR, 14)
   - **VWAP (Intraday)**:
     VWAP = sum(Typical_Price * Volume) / sum(Volume)

3. **Tính Dòng lệnh & Imbalance (Orderflow Delta)**:
   - Gom nhóm các lệnh khớp chủ động mua (Vol_Buy) và bán (Vol_Sell) trong khung 1m / 5m.
   - Volume Delta: Delta_Vol = Vol_Buy - Vol_Sell.
   - Order Imbalance Ratio:
     Imbalance = (Vol_Buy - Vol_Sell) / (Vol_Buy + Vol_Sell + 1e-9) [-1.0 -> +1.0]

4. **Nhận diện Cấu trúc Thị trường & Key Levels**:
   - **Camarilla Pivots**:
     R4 = C + (H - L) * 1.1 / 2, R3 = C + (H - L) * 1.1 / 4
     S3 = C - (H - L) * 1.1 / 4, S4 = C - (H - L) * 1.1 / 2
   - **Fair Value Gap (FVG)**:
     - Bullish FVG: Low_nến3 > High_nến1 => Biên FVG = [High_nến1, Low_nến3]
     - Bearish FVG: High_nến3 < Low_nến1 => Biên FVG = [High_nến3, Low_nến1]
   - **Liquidity Sweep (Quét thanh khoản)**:
     - Quét đỉnh (Bearish Sweep): High_nến > SwingHigh_20 nhưng Close_nến < SwingHigh_20.
     - Quét đáy (Bullish Sweep): Low_nến < SwingLow_20 nhưng Close_nến > SwingLow_20.

5. **Tổng hợp Điểm Số Engine 1 (Score_E1 in [-1.0, +1.0])**:
   - Cấu phần Kỹ thuật (Trend + RSI + MACD + VWAP position): Tỷ trọng 50%.
   - Cấu phần Orderflow (Volume Delta + Imbalance): Tỷ trọng 30%.
   - Cấu phần Price Action (Sweep + FVG): Tỷ trọng 20%.

---

### 2.2 Engine 2: Liquidity, Flow & T+2 Cashflow Engine (FlowLiquidityEngine)

#### Workflow Chi Tiết:
1. **Nạp dữ liệu dòng vốn & độ rộng**:
   - InstitutionalFlow: Giá trị mua/bán của Khối ngoại (F_buy, F_sell) và Tự doanh (P_buy, P_sell).
   - MarketBreadth: Số mã tăng (N_adv), số mã giảm (N_dec), số mã đứng giá (N_flat).
   - MacroIndicator: Tỷ giá USD/VND, Giá vàng SJC, Giá vàng TG.

2. **Chỉ số Dòng tiền Tổ chức (Institutional Flow Momentum - IFM)**:
   - Tính dòng tiền ròng lăn 5 phiên của Khối ngoại NetF_5D và Tự doanh NetP_5D.
   - Chuẩn hóa Z-score hoặc Min-Max scaling về dải [-1.0, +1.0]:
     IFM = 0.6 * norm(NetF_5D) + 0.4 * norm(NetP_5D)

3. **Chỉ số Độ rộng Thị trường (Market Breadth Index - MBI)**:
   - Advance/Decline Ratio (ADR):
     ADR = (N_adv - N_dec) / (N_adv + N_dec + N_flat)
   - Tỷ lệ cổ phiếu nằm trên MA20 / MA50: Ratio_MA20 in [0.0, 1.0].
   - MBI = 0.7 * ADR + 0.3 * (2 * Ratio_MA20 - 1.0).

4. **Mô hình Chu kỳ Thanh toán T+2 (Vietnamese Equity T+2 Settlement Cycle)**:
   - Lịch thanh toán tại Việt Nam: Giao dịch mua ngày T => Cổ phiếu về tài khoản và có thể bán từ 13:00 ngày T+2 (bỏ qua T7, CN và Ngày lễ Quốc gia).
   - **T+2 Pressure Index**: Nếu ngày T-2 có khối lượng giao dịch mua bùng nổ vượt +2std trung bình 20 phiên, vào đầu phiên chiều ngày T (13:00 - 13:30) sẽ xuất hiện áp lực chốt lời/cắt lỗ gia tăng.
   - Công thức tính Chỉ số Áp lực T+2:
     Pressure_T2 = min(1.0, Vol_T2 / (MA(Vol_20) * 1.5))

5. **Chỉ số Vĩ mô & Tỷ giá (Macro Sentiment Score)**:
   - Tỷ giá USD/VND biến động tăng mạnh > +0.5% trong ngày => Tín hiệu tiêu cực cho dòng vốn FII.
   - Chênh lệch giá vàng nội/ngoại gia tăng đột biến => Dòng tiền rút khỏi chứng khoán gửi vào tài sản trú ẩn.

6. **Tổng hợp Điểm Số Engine 2 (Score_E2 in [-1.0, +1.0])**:
   Score_E2 = 0.45 * IFM + 0.35 * MBI - 0.20 * Pressure_T2 + 0.10 * Score_Macro

---

### 2.3 Engine 3: Quantitative, Statistical & Machine Learning Engine (QuantMLEngine)

#### Workflow Chi Tiết:
1. **Mô hình Chênh lệch Giá Phái sinh - Cơ sở (Basis Spread Model)**:
   - Basis tức thời giữa Hợp đồng tương lai VN30F1M và chỉ số VN30:
     Basis_t = P_VN30F1M - P_VN30
   - Rolling Mean mu_basis_20 và Standard Deviation sigma_basis_20.
   - Z-score Basis:
     Z_basis = (Basis_t - mu_basis_20) / sigma_basis_20
   - **Quy tắc Mean-Reversion Arbitrage**:
     - Khi Z_basis > +2.0: Phái sinh quá đắt => Tín hiệu Short Bias (Score -0.8).
     - Khi Z_basis < -2.0: Phái sinh chiết khấu quá sâu => Tín hiệu Long Bias (Score +0.8).

2. **Mô hình Độ biến động (Volatility Engine)**:
   - Historical Volatility (HV 20-day annualized):
     HV = sqrt(252) * std(ln(P_t / P_{t-1}))
   - Parkinson Volatility (dựa trên dải High-Low):
     sigma_parkinson = sqrt( (252 / (4 * ln(2) * N)) * sum( (ln(High_i / Low_i))^2 ) )

3. **Mô hình Phân loại Xác suất Chuyển phiên (Session Transition Classifier)**:
   - **Phiên Pre-ATO (08:30 - 09:00)**: Dự báo Gap mở cửa dựa trên Basis overnight và tin tức vĩ mô.
   - **Phiên Pre-ATC (14:15 - 14:30)**: Dự báo mức dịch chuyển giá khớp lệnh định kỳ đóng cửa ATC (Delta_P_ATC = P_ATC - P_14:30).
   - **Mô phỏng Monte Carlo T+1 (Next-Day Price Path Simulation)**:
     - Thực hiện 1,000 mô phỏng ngẫu nhiên theo mô hình Geometric Brownian Motion (GBM) với biên độ giới hạn +-7% trần/sàn.
     - Trích xuất dải phân phối kỳ vọng: P05 (đáy kỳ vọng), P50 (trung vị), P95 (đỉnh kỳ vọng).

4. **Tổng hợp Điểm Số Engine 3 (Score_E3 in [-1.0, +1.0])**:
   Score_E3 = 0.50 * (-1 * sign(Z_basis) * min(1.0, |Z_basis| / 2.5)) + 0.50 * Score_Transition

---

### 2.4 Ensemble Decision System (EnsembleEngine)

#### Dynamic Weight Blending According to Time-of-Day Schedule:
- **Pre-ATO (08:30 - 09:00)**: w1=0.20, w2=0.30, w3=0.50 (Ưu tiên Basis overnight & Gap)
- **Morning Continuous (09:00 - 11:30)**: w1=0.55, w2=0.25, w3=0.20 (Ưu tiên Orderflow & Technical)
- **Midday Intermission (11:30 - 13:00)**: w1=0.30, w2=0.40, w3=0.30 (Cân bằng & T+2 setup)
- **Afternoon Continuous (13:00 - 14:15)**: w1=0.50, w2=0.30, w3=0.20 (Áp lực hàng T+2 về)
- **Pre-ATC Setup (14:15 - 14:30)**: w1=0.25, w2=0.25, w3=0.50 (Hội tụ giá đóng cửa ATC)
- **ATC Call Auction (14:30 - 14:45)**: w1=0.15, w2=0.20, w3=0.65 (Khớp lệnh định kỳ ATC)
- **Post-Market / Evening (14:45 - 08:30 T+1)**: w1=0.20, w2=0.35, w3=0.45 (Monte Carlo T+1 & Rebalance)

#### Thuật Toán Hợp Nhất & Xử Lý Xung Đột Tín Hiệu:
1. Score_Ensemble = w1*Score_E1 + w2*Score_E2 + w3*Score_E3
2. **Xử lý xung đột**: Nếu Score_E1 > +0.5 (Cực Bullish) nhưng Score_E3 < -0.5 (Cực Bearish) => Đưa tín hiệu về NEUTRAL với Confidence 50%.
3. **Phân loại Tín hiệu**:
   - Score_Ensemble >= +0.35 => **LONG**
   - Score_Ensemble <= -0.35 => **SHORT**
   - Else => **NEUTRAL**
4. **Tính Stop Loss (SL) & Take Profit (TP) Động**:
   - Tỷ lệ Risk:Reward tối thiểu 1:2.0 dựa trên k*ATR14 và Pivot Camarilla R3/S3.
5. **Ghi Nhật Ký Auto-Ledger (RULE 3)**: Tự động chèn 1 bản ghi vào bảng \`forecast_journal\` với status = 'pending'.

---

## 3. Mô Hình Dữ Liệu SQLModel (ForecastJournal)

\`\`\`python
class ForecastJournal(SQLModel, table=True):
    __tablename__ = "forecast_journal"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(index=True, max_length=20)  # e.g., "VN30F1M"
    horizon: str = Field(max_length=20)  # "INTRADAY", "ATC", "T+1", "WEEKLY"
    
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ), index=True)
    realized_at: Optional[datetime] = Field(default=None)

    predicted_direction: str = Field(max_length=10)  # "LONG", "SHORT", "NEUTRAL"
    predicted_score: float  # -1.0 to +1.0
    confidence: float  # 0.0 to 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    engine_weights: dict = Field(default_factory=dict, sa_column=Column(JSON))
    engine1_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    engine2_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    engine3_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))

    actual_direction: Optional[str] = Field(default=None, max_length=10)
    actual_price: Optional[float] = Field(default=None)
    error_mae: Optional[float] = Field(default=None)
    status: str = Field(default="pending", index=True)  # "pending", "resolved", "scored"
    model_version: str = Field(default="v2.0.0", max_length=20)
\`\`\`

---

## 4. Hướng Dẫn Từng Bước Cho Developer (Step-by-Step Implementation Steps)

1. **Bước 1**: Tạo \`backend/app/domains/quant/domain/models.py\` chứa SQLModel \`ForecastJournal\`, \`TickFlowAggregated\`, \`InstitutionalFlow\`, \`MarketBreadth\`, \`MacroIndicator\` & schemas trong \`backend/app/domains/quant/application/schemas.py\`.
2. **Bước 2**: Triển khai \`backend/app/domains/quant/application/engines/technical_engine.py\` (Engine 1).
3. **Bước 3**: Triển khai \`backend/app/domains/quant/application/engines/flow_engine.py\` (Engine 2).
4. **Bước 4**: Triển khai \`backend/app/domains/quant/application/engines/quant_ml_engine.py\` (Engine 3).
5. **Bước 5**: Triển khai \`backend/app/domains/quant/application/engines/ensemble_engine.py\` (Ensemble Engine & Auto-Ledger).
6. **Bước 6**: Tạo FastAPI Router \`backend/app/domains/quant/presentation/quant_router.py\` & \`forecast_router.py\` đăng ký vào \`backend/app/api/main.py\`.
7. **Bước 7**: Viết Unit Tests trong \`backend/tests/test_quant_engines.py\`, \`backend/tests/test_forecast_journal.py\`, \`backend/tests/api/routes/test_quant.py\` & kiểm tra \`uv run ruff check\`, \`uv run ty check\`.

---

## 5. Danh Sách API Endpoints Phase 2 (FastAPI)

### 5.1 Quant Analytics Endpoints (\`/api/v1/quant/...\`)
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/v1/quant/engine1/technical/{symbol} | Chỉ báo kỹ thuật, VWAP & Orderflow Delta của Engine 1 |
| GET | /api/v1/quant/engine2/flow-liquidity | Dòng tiền Khối ngoại, Tự doanh & Áp lực T+2 |
| GET | /api/v1/quant/engine3/basis-volatility | Basis Z-score, Volatility & Monte Carlo T+1 |
| POST | /api/v1/quant/ensemble/signal | Tính tín hiệu hợp nhất VN30F1M & lưu ForecastJournal |
| GET | /api/v1/quant/ensemble/atc-forecast | Dự báo kịch bản phiên ATC hôm nay |
| GET | /api/v1/quant/ensemble/next-day-forecast | Dự báo kịch bản T+1 (Dải giá High/Low/Close) |
| GET | /api/v1/quant/ensemble/weights | Lấy cấu hình trọng số động hiện tại |
| PUT | /api/v1/quant/ensemble/weights | Cập nhật trọng số w1, w2, w3 (Admin only) |

### 5.2 Forecast Audit Ledger Endpoints (\`/api/v1/forecast/...\` - RULE 3)
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/v1/forecast | Ghi nhận bản ghi dự phóng mới (status=pending, RULE 3) |
| GET | /api/v1/forecast | Danh sách nhật ký dự phóng với bộ lọc symbol, horizon, status |
| GET | /api/v1/forecast/{id} | Chi tiết 1 bản ghi dự phóng kèm snapshot tham số |
| POST | /api/v1/forecast/{id}/resolve | Chốt giá thực tế sau khi phiên kết thúc (status=resolved) |
| POST | /api/v1/forecast/{id}/score | Tự động chấm điểm sai số MAE & chiều hướng (status=scored) |
| GET | /api/v1/forecast/aggregate | Thống kê MAE & tỷ lệ dự báo chính xác (Directional Accuracy) |

---

## 6. Tiêu Chuẩn Hoàn Thành (Definition of Done - DoD)

1. **Kiến trúc Độc Lập**: 3 Engine & Ensemble nằm trong \`backend/app/domains/quant/\` theo chuẩn Domain-Driven Design (DDD) độc lập hoàn toàn, 0 circular imports.
2. **Tuân thủ Tuyệt đối 4 Master Rules**:
   - **RULE 1 & 2**: Zero broker execution, zero real money. Chỉ phục vụ simulation.
   - **RULE 3**: 100% tín hiệu được ghi vào DB \`forecast_journal\` với trạng thái \`pending\`.
   - **RULE 4**: Phản hồi API luôn chứa thông điệp cảnh báo rủi ro \`disclaimer\`.
3. **Chất lượng Mã Nguồn**:
   - \`uv run ruff check\` => **0 errors**.
   - \`uv run ruff format --check\` => **0 issues**.
   - \`uv run ty check app\` => **0 diagnostics**.
4. **Coverage Kiểm Thử**: Unit test pytest đạt coverage >= 90% cho toàn bộ các module trong \`backend/app/domains/quant/\` (39/39 tests PASS).

---

## 7. Ma Trận Kịch Bản Kiểm Thử (Test Matrix - 27 Kịch Bản)

### Nhóm 1: Engine 1 (Technical & Orderflow) - 8 Tests
- **TEST-E1-01**: RSI & MACD calculation (Kiểm tra độ chính xác chỉ báo)
- **TEST-E1-02**: Intraday VWAP đa khung thời gian kết hợp 1m, 5m, 15m
- **TEST-E1-03**: Intraday VWAP với volume zero (Tránh ZeroDivisionError)
- **TEST-E1-04**: Orderflow Delta mua/bán hỗn hợp từ Quote.intraday()
- **TEST-E1-05**: Order Imbalance 100% Mua chủ động (Trả về Imbalance +1.0)
- **TEST-E1-06**: Nhận diện Fair Value Gap FVG (Kiểm tra khoảng trống 3 nến)
- **TEST-E1-07**: Nhận diện Liquidity Sweep (Kiểm tra quét đỉnh/đáy rút râu)
- **TEST-E1-08**: Parkinson Volatility với nến Doji (Xử lý an toàn log-ratio)

### Nhóm 2: Engine 2 (Liquidity & T+2) - 6 Tests
- **TEST-E2-01**: Thiếu dữ liệu Tự doanh (Chuẩn hóa điểm theo Khối ngoại tuân thủ RULE 3)
- **TEST-E2-02**: Độ rộng thị trường 100% giảm (Breadth score -1.0)
- **TEST-E2-03**: Lịch thanh toán T+2 lệnh mua thứ 6 (Cổ phiếu về 13:00 thứ 3)
- **TEST-E2-04**: Áp lực xả hàng T+2 volume nổ x3 (Chỉ số áp lực tiệm cận 1.0)
- **TEST-E2-05**: Tỷ giá USD/VND tăng mạnh >0.5% (Macro score phản ánh tiêu cực)
- **TEST-E2-06**: Dynamic Reweighting khi market_breadth là None

### Nhóm 3: Engine 3 (Basis, Volatility & Monte Carlo) - 7 Tests
- **TEST-E3-01**: VN30F1M cao hơn VN30 cash (Basis dương, Z-score chuẩn)
- **TEST-E3-02**: Basis Z-score > +2.0 (Tín hiệu Short Bias Mean-reversion)
- **TEST-E3-03**: Basis Z-score < -2.0 (Tín hiệu Long Bias Mean-reversion)
- **TEST-E3-04**: Dự báo phiên ATC (Kịch bản giá hội tụ & delta)
- **TEST-E3-05**: Phân loại độ lệch ATO Opening Gap lúc 08:45
- **TEST-E3-06**: Monte Carlo T+1 1,000 runs (Dải giá trong trần/sàn +-7%)
- **TEST-E3-07**: Bọc biên độ trần/sàn phản xạ không tạo kịch bản phi thực tế

### Nhóm 4: Ensemble & Forecast Ledger - 6 Tests
- **TEST-ENS-01**: Tự động chuẩn hóa trọng số w1+w2+w3=1.0
- **TEST-ENS-02**: Xung đột Engine 1 Bullish & Engine 3 Bearish (Trả về NEUTRAL)
- **TEST-ENS-03**: Tự động lưu ForecastJournal (Thêm row status='pending' - RULE 3)
- **TEST-ENS-04**: Phân loại xu hướng ngưỡng >= +0.35 LONG, <= -0.35 SHORT
- **TEST-ENS-05**: Tính Stop Loss / Take Profit theo ATR (Đảm bảo R:R >= 1:2.0)
- **TEST-ENS-06**: Phản hồi bắt buộc có thông điệp cảnh báo rủi ro (RULE 4)
`
