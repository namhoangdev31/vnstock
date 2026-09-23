export const phase4Markdown = `# TRD Phase 4: Paper Trading Engine & Multi-Horizon Equity Portfolio
## Hệ Thống Giả Lập Giao Dịch Phái Sinh & Sàng Lọc Cổ Phiếu Đa Khung Thời Gian (T+2)

> **Tài liệu đặc tả kỹ thuật chi tiết dành cho kỹ sư phát triển backend (Self-Implementation Blueprint)**  
> *Phiên bản: 1.0.0 | Mục tiêu: Xây dựng sàn giao dịch mô phỏng phái sinh VN30F1M chuẩn xác từng tick và bộ lọc danh mục cổ phiếu cơ sở tuân thủ nghiêm ngặt chu kỳ thanh toán T+2.*

---

## 1. NGUYÊN TẮC CỐT LÕI & RÀO CHẮN AN TOÀN (SAFETY GUARDRAILS)

1. **Cô Lập Tuyệt Đối (Master Rule 2 - Strict Isolation)**:
   - Toàn bộ tài khoản mô phỏng, số dư tiền ảo, vị thế và lịch sử giao dịch nằm riêng biệt trong schema \`paper_trading\`.
   - Sử dụng các tên trường chuẩn mực: \`balance\`, \`price\`, \`volume\`, \`pnl\`, \`status\` trên các bảng có tiền tố rõ ràng (\`PaperPortfolio\`, \`PaperOrder\`, \`PaperPosition\`).
2. **Không Khớp Lệnh Ảo Tưởng (Realistic Execution Simulation)**:
   - Lệnh ảo KHÔNG ĐƯỢC khớp ngay lập tức một cách bừa bãi.
   - Việc khớp lệnh phải căn cứ vào **dòng lệnh khớp thực tế từ \`Quote.intraday()\`**: Lệnh Mua chỉ được khớp khi có giao dịch thực tế xảy ra ở mức giá <= giá đặt; Lệnh Bán chỉ khớp khi có giao dịch thực tế ở mức giá >= giá đặt; và khối lượng khớp ảo không được vượt quá thanh khoản thực của thị trường tại thời điểm đó.
3. **Mô Hình Hóa Chu Kỳ T+2 Chuẩn Thị Trường Việt Nam**:
   - Cổ phiếu cơ sở mua vào phiên ngày $T$ **chỉ trở thành khả dụng để bán vào lúc 13:00 phiên chiều ngày $T+2$**.
   - Tiền bán cổ phiếu ngày $T$ chỉ thực sự về tài khoản vào 13:00 phiên chiều ngày $T+2$.

---

## 2. PAPER TRADING ENGINE CHO PHÁI SINH (VN30F1M)

### 2.1 Các Loại Lệnh Hỗ Trợ
- \`LO\` (Limit Order - Lệnh giới hạn): Khớp khi giá thị trường chạm hoặc vượt mức giá đặt.
- \`MP\` / \`MTL\` (Market Order - Lệnh thị trường): Khớp ngay lập tức theo giá khớp gần nhất kèm theo độ trượt giá (slippage).
- \`ATO\` / \`ATC\`: Tham gia đợt khớp lệnh định kỳ mở cửa (08:45 - 09:00) hoặc đóng cửa (14:30 - 14:45).
- \`STOP_LOSS\` (Cắt lỗ kích hoạt): Tự động sinh lệnh thị trường khi giá vi phạm ngưỡng cắt lỗ.
- \`TRAILING_STOP\`: Ngưỡng kích hoạt trượt theo giá đỉnh/đáy mới nhất với khoảng cách $D_{\\text{trail}} = k \\times \\text{ATR}_{14}$.

### 2.2 Công Thức Ký Quỹ & Quản Trị Rủi Ro (Margin Requirements)
Theo quy chuẩn VSDC (Tổng công ty Lưu ký và Bù trừ Chứng khoán Việt Nam):
- **Tỷ lệ ký quỹ ban đầu (Initial Margin - IM)**: $17\\%$
- **Tỷ lệ ký quỹ duy trì (Maintenance Margin - MM)**: $13\\%$
- **Hệ số nhân hợp đồng phái sinh**: $100{,}000 \\text{ VND/điểm}$

#### Công thức tính tiền ký quỹ yêu cầu:
$$\\text{Required Margin} = N_{\\text{contracts}} \\times P_{\\text{entry}} \\times 100{,}000 \\times 17\\%$$

#### Công thức tính PnL tạm tính (Unrealized Mark-to-Market PnL):
- **Vị thế Long**:
  $$\\text{PnL}_{\\text{Long}} = N_{\\text{contracts}} \\times (P_{\\text{current}} - P_{\\text{entry}}) \\times 100{,}000 - \\text{Fees}$$
- **Vị thế Short**:
  $$\\text{PnL}_{\\text{Short}} = N_{\\text{contracts}} \\times (P_{\\text{entry}} - P_{\\text{current}}) \\times 100{,}000 - \\text{Fees}$$

#### Tỷ lệ an toàn tài khoản (Account Margin Ratio):
$$\\text{Margin Ratio} = \\frac{\\text{Virtual Equity}}{\\text{Total Position Value}} = \\frac{\\text{Cash Balance} + \\text{PnL}_{\\text{unrealized}}}{N_{\\text{contracts}} \\times P_{\\text{current}} \\times 100{,}000}$$

- Nếu $\\text{Margin Ratio} < 13\\%$: Kích hoạt cảnh báo **Call Margin Ảo**.
- Nếu $\\text{Margin Ratio} < 10\\%$: Kích hoạt cơ chế **Force Liquidation Ảo** (tự động đóng toàn bộ vị thế với lệnh thị trường MP để bảo toàn vốn).

---

## 3. BỘ LỌC CỔ PHIẾU CƠ SỞ ĐA KHUNG THỜI GIAN (MULTI-HORIZON ALPHA)

Hệ thống cung cấp 3 bộ lọc danh mục cổ phiếu cơ sở độc lập tương ứng với 3 chân trời đầu tư:

\`\`\`
+-------------------------------------------------------------------------------+
|                      MULTI-HORIZON ALPHA STOCK BASKETS                        |
+------------------------+-----------------------------+------------------------+
|    WEEKLY HORIZON      |       MONTHLY HORIZON       |   QUARTERLY HORIZON    |
|   (Chiến lược Tuần)    |      (Chiến lược Tháng)     |    (Chiến lược Quý)    |
+------------------------+-----------------------------+------------------------+
| • Momentum Breakout    | • Mô hình CANSLIM thu nhỏ   | • BCTC tăng trưởng     |
| • Volume Surge > 200%  | • Sức mạnh giá RS > 80      | • Piotroski F-Score >= 7|
| • Fair Value Gap (FVG) | • Sóng ngành ICB dẫn dắt    | • ROE > 15%, D/E < 1.5 |
| • Mục tiêu: 5 - 10 ngày| • Mục tiêu: 20 - 45 ngày    | • Mục tiêu: 3 - 6 tháng|
+------------------------+-----------------------------+------------------------+
\`\`\`

### 3.1 Weekly Horizon (Alpha Tuần: Động Lượng & Dòng Tiền Đột Biến)
- **Điều kiện sàng lọc**:
  1. $V_{\\text{today}} \\ge 2.0 \\times \\text{SMA}_{20}(V)$: Khối lượng đột biến gấp đôi trung bình 20 phiên.
  2. $P_{\\text{close}} > \\text{SMA}_{20}(P)$ và $P_{\\text{close}} > \\text{SMA}_{50}(P)$.
  3. Xuất hiện **Bullish FVG** trong vòng 3 phiên gần nhất.
  4. Thanh khoản khớp lệnh bình quân phiên $> 15 \\text{ tỷ VND}$ (loại trừ penny rác).

### 3.2 Monthly Horizon (Alpha Tháng: Xu Hướng & Nhóm Ngành Dẫn Dắt)
- **Điều kiện sàng lọc**:
  1. **Relative Strength (RS Rating)** so với VN-Index trong 60 phiên gần nhất $\\ge 80$.
  2. **ICB Sector Momentum**: Thuộc top 3 ngành có dòng tiền khối ngoại và tự doanh mua ròng ròng rã 2 tuần.
  3. Nền giá tích lũy chặt chẽ (Volatility Contraction Pattern - VCP) với biên độ nến thu hẹp $< 8\\%$.

### 3.3 Quarterly Horizon (Alpha Quý: Cơ Bản Tăng Trưởng & Biên An Toàn)
- **Điều kiện sàng lọc (dựa trên module \`Finance\` của vnstock)**:
  1. Doanh thu & Lợi nhuận sau thuế tăng trưởng YoY $\\ge 20\\%$.
  2. $\\text{ROE} \\ge 15\\%$ và tỷ lệ Nợ vay / Vốn chủ sở hữu $\\text{D/E} < 1.5$.
  3. **Piotroski F-Score** đạt từ $7/9$ điểm trở lên.
  4. Định giá $\\text{P/E}$ hiện tại thấp hơn $\\text{P/E}$ trung bình 3 năm của chính cổ phiếu đó.

---

## 4. QUY TRÌNH QUẢN LÝ THANH TOÁN T+2 (T+2 SETTLEMENT LIFECYCLE)

\`\`\`
   [NGÀY T - Mua Cổ Phiếu]
   - Tiền bị trừ khỏi Sức mua (Purchasing Power)
   - Cổ phiếu ghi nhận vào bảng EquitySettlementLedger với status = 'PENDING_T2'
             │
             ▼
   [NGÀY T+1]
   - Cổ phiếu vẫn ở trạng thái PENDING_T2 (Chưa được phép bán)
             │
             ▼
   [NGÀY T+2: Sáng (09:00 - 11:30)]
   - Cổ phiếu tiếp tục bị khóa
             │
             ▼
   [NGÀY T+2: 13:00 Chiều] ───► Daemon chạy tự động:
                                 - Chuyển status = 'SETTLED_AVAILABLE'
                                 - Cổ phiếu chính thức có thể đặt lệnh Bán!
\`\`\`

---

## 5. DATABASE SCHEMA (POSTGRESQL / SQLMODEL)

\`\`\`python
from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import uuid

class PaperPortfolio(SQLModel, table=True):
    __tablename__ = "paper_portfolio"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    name: str = Field(default="Tài khoản Mô phỏng Chính")
    initial_capital: float = Field(default=100_000_000.0)    # Vốn ban đầu (VND)
    cash_balance: float = Field(default=100_000_000.0)       # Tiền mặt khả dụng
    locked_margin: float = Field(default=0.0)                # Ký quỹ phái sinh đang khóa
    unrealized_pnl: float = Field(default=0.0)               # Lãi/lỗ tạm tính
    realized_pnl: float = Field(default=0.0)                 # Lãi/lỗ đã chốt
    created_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ))

class PaperOrder(SQLModel, table=True):
    __tablename__ = "paper_order"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(foreign_key="paper_portfolio.id", index=True)
    symbol: str = Field(index=True)                          # VN30F1M hoặc HPG, FPT,...
    asset_type: str = Field(default="DERIVATIVES")           # DERIVATIVES hoặc EQUITY
    side: str = Field(index=True)                            # BUY hoặc SELL
    order_type: str = Field(default="LO")                    # LO, MP, ATO, ATC, STOP_LOSS
    price: float = Field()                                   # Mức giá đặt
    volume: int = Field()                                    # Khối lượng đặt
    filled_volume: int = Field(default=0)
    filled_price: Optional[float] = Field(default=None)
    status: str = Field(default="PENDING", index=True)       # PENDING, FILLED, CANCELLED, REJECTED
    stop_price: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ))
    filled_at: Optional[datetime] = Field(default=None)

class PaperPosition(SQLModel, table=True):
    __tablename__ = "paper_position"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(foreign_key="paper_portfolio.id", index=True)
    symbol: str = Field(index=True)                          # VN30F1M
    side: str = Field()                                      # LONG hoặc SHORT
    volume: int = Field(default=0)                           # Số hợp đồng đang giữ
    average_price: float = Field(default=0.0)                # Giá vốn bình quân
    current_price: float = Field(default=0.0)                # Giá thị trường hiện hành
    unrealized_pnl: float = Field(default=0.0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ))

class EquitySettlementLedger(SQLModel, table=True):
    __tablename__ = "equity_settlement_ledger"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(foreign_key="paper_portfolio.id", index=True)
    symbol: str = Field(index=True)
    bought_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ))
    settlement_due: datetime = Field(index=True)             # 13:00 ngày T+2
    volume: int = Field()
    cost_basis: float = Field()
    status: str = Field(default="PENDING_T2", index=True)    # PENDING_T2 -> SETTLED_AVAILABLE
\`\`\`

---

## 6. HƯỚNG DẪN TỰ CODE TỪNG BƯỚC (6-STEP DEV BLUEPRINT)

Kỹ sư backend triển khai theo thứ tự sau:

### Bước 1: Khởi Tạo Models & Chạy Alembic Migration
1. Tạo file \`backend/app/domains/simulation/domain/models.py\` chứa các model trên.
2. Tạo migration mới: \`uv run alembic revision --autogenerate -m "add_paper_trading_tables"\`.
3. Chạy nâng cấp DB: \`uv run alembic upgrade head\`.

### Bước 2: Viết Module \`order_matcher.py\` (Bộ Khớp Lệnh Thực Tế)
1. Triển khai tại \`backend/app/domains/simulation/application/order_matcher.py\`.
2. Nhận luồng tick gần nhất từ \`Quote.intraday()\`.
3. Duyệt danh sách các lệnh \`PENDING\` trong bảng \`PaperOrder\`:
   - Với lệnh Buy \`LO\`: Nếu tick.price <= order.price -> Cập nhật \`filled_volume\`, \`filled_price\`, đổi trạng thái \`FILLED\`.
   - Với lệnh Sell \`LO\`: Nếu tick.price >= order.price -> Khớp lệnh.
4. Cập nhật vị thế \`PaperPosition\` tương ứng (tính lại \`average_price\` nếu khớp thêm).

### Bước 3: Viết Module \`margin_calculator.py\`
1. Triển khai tại \`backend/app/domains/simulation/application/margin_calculator.py\`.
2. Mỗi khi có giá mới của \`VN30F1M\`:
   - Tính lại \`unrealized_pnl\` cho từng vị thế.
   - Cập nhật trường \`unrealized_pnl\` trong \`PaperPortfolio\`.
   - Tính \`Margin Ratio\`: Nếu < 10% -> Tự động sinh lệnh đóng vị thế cưỡng bức (\`Force Liquidation\`).

### Bước 4: Viết Module \`t_plus_2_manager.py\`
1. Triển khai tại \`backend/app/domains/simulation/application/t_plus_2_manager.py\`.
2. Lập lịch định kỳ vào lúc 13:00 các ngày làm việc (Thứ 2 đến Thứ 6).
3. Quét bảng \`EquitySettlementLedger\` tìm các row có \`settlement_due <= datetime.now(VN_TZ)\` và \`status = 'PENDING_T2'\`.
4. Cập nhật trạng thái thành \`SETTLED_AVAILABLE\`, cộng dồn khối lượng vào số lượng cổ phiếu khả dụng để bán.

### Bước 5: Viết Module \`alpha_screener.py\`
1. Triển khai tại \`backend/app/domains/simulation/application/alpha_screener.py\`.
2. Viết hàm \`screen_weekly_momentum()\`: Lấy nến ngày, tính SMA20, kiểm tra nổ vol 200% và FVG.
3. Viết hàm \`screen_monthly_canslim()\`: Tính RS Rating 60 ngày, phân nhóm ngành ICB.
4. Viết hàm \`screen_quarterly_fundamental()\`: Gọi \`Finance.ratio()\` và \`Finance.income_statement()\`, tính điểm Piotroski F-Score.

### Bước 6: Khởi Tạo API Endpoints Cho Frontend
Triển khai tại \`backend/app/domains/simulation/presentation/simulation_router.py\`:
- \`POST /api/v1/simulation/orders\`: Đặt lệnh mua/bán ảo mới.
- \`GET /api/v1/simulation/portfolio\`: Xem số dư, PnL, trạng thái ký quỹ.
- \`GET /api/v1/simulation/positions\`: Xem danh sách vị thế đang mở.
- \`GET /api/v1/simulation/alpha/baskets\`: Xem danh sách rổ cổ phiếu gợi ý theo Tuần, Tháng, Quý.

---

## 7. TEST MATRIX & TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

| Mã Test | Kịch bản thử nghiệm | Kết quả kỳ vọng |
|---|---|---|
| \`TEST-PAPER-01\` | Đặt lệnh Long VN30F1M giá 1300 khi thị trường đang giao dịch ở mức 1305 | Lệnh ở trạng thái \`PENDING\`, tiền ký quỹ 17% bị khóa tạm tính |
| \`TEST-PAPER-02\` | Thị trường xuất hiện tick khớp giá 1299 | Lệnh lập tức khớp (\`FILLED\`), sinh ra vị thế Long mới giá vốn 1300 |
| \`TEST-PAPER-03\` | Giá thị trường giảm từ 1300 xuống 1290 | PnL tạm tính giảm chính xác: $1 \\times (1290 - 1300) \\times 100{,}000 = -1{,}000{,}000 \\text{ VND}$ |
| \`TEST-PAPER-04\` | Đặt lệnh Mua cổ phiếu HPG vào 10:00 sáng Thứ Sáu | Lệnh khớp, tạo row trong \`EquitySettlementLedger\` với ngày đáo hạn là 13:00 Thứ Ba tuần sau |
| \`TEST-PAPER-05\` | Thử đặt lệnh Bán cổ phiếu vừa mua ở Test 04 vào sáng Thứ Hai | Hệ thống từ chối lệnh với mã lỗi \`400 Bad Request: Shares are pending T+2 settlement\` |
| \`TEST-PAPER-06\` | Đến 13:01 chiều Thứ Ba tuần sau | Cổ phiếu tự động chuyển thành \`SETTLED_AVAILABLE\`, cho phép đặt lệnh Bán bình thường |
| \`TEST-PAPER-07\` | Lọc cổ phiếu Weekly Alpha với điều kiện Vol > 200% SMA20 | Trả về danh sách chính xác các mã đáp ứng, không chứa mã bị thiếu dữ liệu |
| \`TEST-PAPER-08\` | Tính toán điểm Piotroski F-Score cho rổ Quarterly Alpha | Trả về điểm từ 0 đến 9 chính xác dựa trên dữ liệu tài chính BCTC |
`
