import{h as B,u as I,c as v,a as n,b as s,w,d as p,F as G,B as O,p as e,t as o,C as T,E,I as _,A as x,k as q,r as m,e as U,o as f,m as H,z as S}from"./WPUU6VfZ.js";import{_ as K,a as W}from"./Dd-5l10-.js";import{_ as Q}from"./Cl_avYTq.js";import"./D7qHZAIq.js";const j=`# Đặc Tả Kỹ Thuật (TRD) Phase 2: Tri-Engine Analytics Core & Ensemble Decision System

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
`,Z={class:"space-y-6"},J={class:"flex flex-col sm:flex-row sm:items-center justify-between gap-4"},X={class:"flex items-center gap-2 text-xs text-slate-400 font-mono mb-1"},z={class:"text-2xl font-bold tracking-tight text-white flex items-center gap-2"},Y={class:"flex items-center gap-2"},$={class:"px-3 py-1 rounded-full text-xs font-mono font-bold bg-teal-500/10 text-teal-400 border border-teal-500/20 flex items-center gap-1.5"},nn={class:"flex border-b border-slate-800 gap-4"},tn=["onClick"],en={key:0},sn={key:1},on={key:2,class:"space-y-6"},an={class:"p-6 rounded-2xl bg-surface-abyss border border-white/[0.08] shadow-2xl space-y-6"},ln={class:"flex items-center justify-between"},rn={class:"text-base font-bold text-white flex items-center gap-2"},cn={class:"grid grid-cols-1 md:grid-cols-3 gap-6"},hn={class:"p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4"},un={class:"flex items-center justify-between"},dn={class:"text-xs font-mono font-bold text-slate-300"},gn={class:"space-y-3"},pn={class:"text-[11px] text-slate-400 flex justify-between"},mn={class:"font-mono text-emerald-400"},Tn={class:"text-[11px] text-slate-400 flex justify-between"},En={class:"flex items-center gap-1"},_n={class:"p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4"},xn={class:"flex items-center justify-between"},bn={class:"text-xs font-mono font-bold text-slate-300"},vn={class:"space-y-3"},fn={class:"text-[11px] text-slate-400 flex justify-between"},Sn={class:"font-mono text-blue-400"},yn={class:"text-[11px] text-slate-400 flex justify-between"},wn={class:"flex items-center gap-1"},An={class:"p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4"},kn={class:"flex items-center justify-between"},Dn={class:"text-xs font-mono font-bold text-slate-300"},Cn={class:"space-y-3"},Nn={class:"text-[11px] text-slate-400 flex justify-between"},Mn={class:"font-mono text-purple-400"},Pn={class:"text-[11px] text-slate-400 flex justify-between"},Ln={class:"flex items-center gap-1"},Vn={class:"space-y-1"},Rn={class:"text-3xl font-extrabold font-mono flex items-center gap-3"},Fn={class:"text-sm font-normal text-slate-400"},Bn={class:"text-right font-mono text-xs text-slate-400 space-y-1"},In={class:"text-white"},Wn=B({__name:"phase-2",setup(Gn){I({title:"TRD Phase 2: Tri-Engine Architecture - Vnstock Quants"});const b=m("spec"),C=[{id:"spec",label:"Tài liệu đặc tả",icon:"i-heroicons-document-text"},{id:"tests",label:"Ma trận kiểm thử",icon:"i-heroicons-check-badge"},{id:"simulator",label:"Mô phỏng Tri-Engine",icon:"i-heroicons-cpu-chip"}],a=m(.4),c=m(45),l=m(.35),h=m(30),r=m(.25),u=m(-15),N=()=>{a.value=.4,c.value=45,l.value=.35,h.value=30,r.value=.25,u.value=-15},y=S(()=>a.value+l.value+r.value),d=S(()=>{const D=a.value/y.value,t=l.value/y.value,A=r.value/y.value;return D*c.value+t*h.value+A*u.value}),M=S(()=>d.value>=25?"TRIGGER: LONG VN30F1M":d.value<=-25?"TRIGGER: SHORT VN30F1M":"TÍN HIỆU: NEUTRAL (QUAN SÁT)"),P=S(()=>d.value>=25?"text-emerald-400":d.value<=-25?"text-rose-400":"text-slate-300"),L=S(()=>d.value>=25?"bg-emerald-500/10 border-emerald-500/30":d.value<=-25?"bg-rose-500/10 border-rose-500/30":"bg-surface-midnight border-white/[0.08]"),V=[{id:"TEST-E1-01",group:"Engine 1 (Technical)",scenario:"Xử lý chuỗi nến đa khung thời gian (1m, 5m, 15m, 1D) đồng bộ",expectation:"Tính toán đúng chỉ số RSI(14), MACD(12,26,9), VWAP nội phiên không bị lag",status:"PASS"},{id:"TEST-E1-02",group:"Engine 1 (Technical)",scenario:"Phân tích luồng khớp lệnh Quote.intraday() dòng tiền chủ động",expectation:"Bóc tách chính xác Buy Delta vs Sell Delta; phát hiện đột biến khối lượng chủ động",status:"PASS"},{id:"TEST-E2-01",group:"Engine 2 (Flow & Liquidity)",scenario:"Theo dõi dòng tiền Khối ngoại và Tự doanh rổ VN30",expectation:"Ghi nhận chuẩn xác giá trị mua/bán ròng, tương quan tỷ lệ đỡ giá chỉ số VN30",status:"PASS"},{id:"TEST-E2-02",group:"Engine 2 (Flow & Liquidity)",scenario:"Cập nhật bối cảnh vĩ mô giá vàng SJC & tỷ giá USD/VND qua Retail",expectation:"Cảnh báo áp lực rút ròng ngoại tệ khi USD/VND vượt ngưỡng biến động 1.5%",status:"PASS"},{id:"TEST-E3-01",group:"Engine 3 (Quant ML)",scenario:"Theo dõi độ lệch Basis spread (VN30F1M - VN30) theo thời gian thực",expectation:"Xác định vùng lệch chuẩn quá mức (Over-stretched Basis) để đón bắt đảo chiều hội tụ",status:"PASS"},{id:"TEST-ENS-01",group:"Ensemble Decision",scenario:"Kết hợp 3 Engine tạo kịch bản dự báo phiên ATC (14:15 - 14:30)",expectation:"Tạo xác suất dự báo bước giá đóng cửa ATC và khuyến nghị vị thế hợp đồng tối ưu",status:"PASS"}];return(D,t)=>{const A=U,g=H,R=K,F=W,k=Q;return f(),v("div",Z,[n("div",J,[n("div",null,[n("div",X,[s(A,{to:"/admin",class:"hover:text-emerald-400"},{default:w(()=>[...t[6]||(t[6]=[p("Dashboard",-1)])]),_:1}),t[7]||(t[7]=n("span",null,"/",-1)),t[8]||(t[8]=n("span",{class:"text-emerald-400"},"TRD Phase 2",-1))]),n("h1",z,[s(g,{name:"i-heroicons-cpu-chip",class:"w-7 h-7 text-teal-400"}),t[9]||(t[9]=p(" Phase 2: Tri-Engine Architecture ",-1))]),t[10]||(t[10]=n("p",{class:"text-xs sm:text-sm text-slate-400 mt-1"}," Tích hợp 3 Engine: Kỹ thuật Price Action, Dòng tiền khối ngoại & Tự doanh, và Machine Learning xác suất. ",-1))]),n("div",Y,[n("span",$,[s(g,{name:"i-heroicons-check-circle",class:"w-4 h-4"}),t[11]||(t[11]=p(" DoD Tri-Engine: 100% ",-1))])])]),n("div",nn,[(f(),v(G,null,O(C,i=>n("button",{key:i.id,type:"button",class:x(["pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2",e(b)===i.id?"border-teal-400 text-teal-400":"border-transparent text-slate-400 hover:text-slate-200"]),onClick:On=>b.value=i.id},[s(g,{name:i.icon,class:"w-4 h-4"},null,8,["name"]),p(" "+o(i.label),1)],10,tn)),64))]),e(b)==="spec"?(f(),v("div",en,[s(R,{content:e(j),filename:"trd-phase-2-tri-engine.md"},null,8,["content"])])):e(b)==="tests"?(f(),v("div",sn,[s(F,{tests:V})])):e(b)==="simulator"?(f(),v("div",on,[n("div",an,[n("div",ln,[n("div",null,[n("h3",rn,[s(g,{name:"i-heroicons-adjustments-horizontal",class:"w-5 h-5 text-teal-400"}),t[12]||(t[12]=p(" Mô phỏng phối hợp Ensemble Tri-Engine ",-1))]),t[13]||(t[13]=n("p",{class:"text-xs text-slate-400"}," Điều chỉnh trọng số (Weights) và điểm số (Scores) của 3 Engine để tính toán tín hiệu vị thế VN30F1M ",-1))]),n("button",{type:"button",class:"text-xs text-slate-400 hover:text-teal-400 font-mono underline",onClick:N}," Khôi phục mặc định ")]),n("div",cn,[n("div",hn,[n("div",un,[t[14]||(t[14]=n("span",{class:"text-xs font-bold uppercase tracking-wider text-emerald-400"},"Engine 1: Technical",-1)),n("span",dn,"W: "+o((e(a)*100).toFixed(0))+"%",1)]),n("div",gn,[n("div",null,[n("label",pn,[t[15]||(t[15]=n("span",null,"Trọng số",-1)),n("span",mn,o(e(a)),1)]),T(n("input",{"onUpdate:modelValue":t[0]||(t[0]=i=>_(a)?a.value=i:null),type:"range",min:"0.1",max:"0.8",step:"0.05",class:"w-full accent-emerald-500"},null,512),[[E,e(a),void 0,{number:!0}]])]),n("div",null,[n("label",Tn,[n("div",En,[t[16]||(t[16]=n("span",null,"Điểm tín hiệu",-1)),s(k,{text:"Thang đo -100 đến +100"},{default:w(()=>[s(g,{name:"i-heroicons-information-circle",class:"w-3.5 h-3.5 text-aave-graphite cursor-help"})]),_:1})]),n("span",{class:x(["font-mono font-bold",e(c)>=0?"text-emerald-400":"text-rose-400"])},o(e(c)),3)]),T(n("input",{"onUpdate:modelValue":t[1]||(t[1]=i=>_(c)?c.value=i:null),type:"range",min:"-100",max:"100",step:"5",class:"w-full accent-emerald-500"},null,512),[[E,e(c),void 0,{number:!0}]])])]),t[17]||(t[17]=n("p",{class:"text-[11px] text-slate-400"}," RSI, MACD, VWAP, Order matching aggression & tick delta. ",-1))]),n("div",_n,[n("div",xn,[t[18]||(t[18]=n("span",{class:"text-xs font-bold uppercase tracking-wider text-blue-400"},"Engine 2: Flow & Liquidity",-1)),n("span",bn,"W: "+o((e(l)*100).toFixed(0))+"%",1)]),n("div",vn,[n("div",null,[n("label",fn,[t[19]||(t[19]=n("span",null,"Trọng số",-1)),n("span",Sn,o(e(l)),1)]),T(n("input",{"onUpdate:modelValue":t[2]||(t[2]=i=>_(l)?l.value=i:null),type:"range",min:"0.1",max:"0.8",step:"0.05",class:"w-full accent-blue-500"},null,512),[[E,e(l),void 0,{number:!0}]])]),n("div",null,[n("label",yn,[n("div",wn,[t[20]||(t[20]=n("span",null,"Điểm tín hiệu",-1)),s(k,{text:"Thang đo -100 đến +100"},{default:w(()=>[s(g,{name:"i-heroicons-information-circle",class:"w-3.5 h-3.5 text-aave-graphite cursor-help"})]),_:1})]),n("span",{class:x(["font-mono font-bold",e(h)>=0?"text-blue-400":"text-rose-400"])},o(e(h)),3)]),T(n("input",{"onUpdate:modelValue":t[3]||(t[3]=i=>_(h)?h.value=i:null),type:"range",min:"-100",max:"100",step:"5",class:"w-full accent-blue-500"},null,512),[[E,e(h),void 0,{number:!0}]])])]),t[21]||(t[21]=n("p",{class:"text-[11px] text-slate-400"}," Khối ngoại (Foreign net buy/sell), Tự doanh và áp lực thanh khoản T+2. ",-1))]),n("div",An,[n("div",kn,[t[22]||(t[22]=n("span",{class:"text-xs font-bold uppercase tracking-wider text-purple-400"},"Engine 3: Quant ML",-1)),n("span",Dn,"W: "+o((e(r)*100).toFixed(0))+"%",1)]),n("div",Cn,[n("div",null,[n("label",Nn,[t[23]||(t[23]=n("span",null,"Trọng số",-1)),n("span",Mn,o(e(r)),1)]),T(n("input",{"onUpdate:modelValue":t[4]||(t[4]=i=>_(r)?r.value=i:null),type:"range",min:"0.1",max:"0.8",step:"0.05",class:"w-full accent-purple-500"},null,512),[[E,e(r),void 0,{number:!0}]])]),n("div",null,[n("label",Pn,[n("div",Ln,[t[24]||(t[24]=n("span",null,"Điểm tín hiệu",-1)),s(k,{text:"Thang đo -100 đến +100"},{default:w(()=>[s(g,{name:"i-heroicons-information-circle",class:"w-3.5 h-3.5 text-aave-graphite cursor-help"})]),_:1})]),n("span",{class:x(["font-mono font-bold",e(u)>=0?"text-purple-400":"text-rose-400"])},o(e(u)),3)]),T(n("input",{"onUpdate:modelValue":t[5]||(t[5]=i=>_(u)?u.value=i:null),type:"range",min:"-100",max:"100",step:"5",class:"w-full accent-purple-500"},null,512),[[E,e(u),void 0,{number:!0}]])])]),t[25]||(t[25]=n("p",{class:"text-[11px] text-slate-400"}," Basis spread arbitrage, độ lệch VN30F1M vs VN30 và xác suất regime. ",-1))])]),n("div",{class:x(["p-6 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4",e(L)])},[n("div",Vn,[t[26]||(t[26]=n("span",{class:"text-[11px] uppercase tracking-wider font-mono font-bold text-slate-400"}," Kết quả hợp nhất (Ensemble Decision) ",-1)),n("div",Rn,[n("span",{class:x(e(P))},o(e(M)),3),n("span",Fn," (Score: "+o(e(d).toFixed(1))+" / 100) ",1)]),t[27]||(t[27]=n("p",{class:"text-xs text-slate-300"}," Ngưỡng kích hoạt: Score ≥ +25 (Mở vị thế LONG), Score ≤ -25 (Mở vị thế SHORT), Còn lại: NEUTRAL / ĐỨNG NGOÀI. ",-1))]),n("div",Bn,[n("div",null,[t[28]||(t[28]=p("Tổng trọng số: ",-1)),n("span",In,o(e(y).toFixed(2)),1)]),t[29]||(t[29]=n("div",null,[p("Tỉ lệ chuẩn hóa: "),n("span",{class:"text-emerald-400"},"100% OK")],-1))])],2)])])):q("",!0)])}}});export{Wn as default};
