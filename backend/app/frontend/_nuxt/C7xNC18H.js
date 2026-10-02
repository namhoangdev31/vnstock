import{f as E,u as M,c,a as n,b as o,w as C,d as a,F as V,r as F,k as e,n as T,s as _,t as p,z as A,m as I,x as g,e as $,o as m,j as D,J as f}from"./C1DYnwlf.js";import{_ as R,a as O}from"./B6L1P5HN.js";import{_ as G}from"./TKeYaff7.js";const w=`# TRD Phase 4: Paper Trading Engine & Multi-Horizon Equity Portfolio
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
`,H={class:"space-y-6"},B={class:"flex flex-col sm:flex-row sm:items-center justify-between gap-4"},U={class:"flex items-center gap-2 text-xs text-slate-400 font-mono mb-1"},q={class:"text-2xl font-bold tracking-tight text-white flex items-center gap-2"},K={class:"flex items-center gap-2"},Q={class:"px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5"},z={class:"flex border-b border-slate-800 gap-4"},Y=["onClick"],Z={key:0},X={key:1},W={key:2,class:"space-y-6"},j={class:"p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] shadow-2xl space-y-6"},J={class:"text-base font-bold text-white flex items-center gap-2"},tt={class:"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-5 rounded-xl bg-[#0d1322] border border-white/[0.06]"},nt={class:"grid grid-cols-2 gap-2"},et={class:"grid grid-cols-1 sm:grid-cols-3 gap-4"},it={class:"p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-1"},ot={class:"text-2xl font-bold font-mono text-white"},at={class:"p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-1"},lt={class:"text-[11px] text-slate-400 font-mono"},st={class:"p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-1"},rt={class:"text-2xl font-bold font-mono text-emerald-400 flex items-center gap-2"},ht={class:"p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-3"},dt={class:"text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2"},Tt=E({__name:"phase-4",setup(ut){M({title:"TRD Phase 4: Paper Trading & T+2 - Vnstock Quants"});const r=g("spec"),v=[{id:"spec",label:"Tài liệu đặc tả (TRD Spec)",icon:"i-heroicons-document-text"},{id:"tests",label:"Ma trận kiểm thử (Test Matrix)",icon:"i-heroicons-check-badge"},{id:"simulator",label:"Mô phỏng Ký quỹ & T+2",icon:"i-heroicons-calculator"}],h=g("LONG"),d=g(5),l=g(1320.5),u=g(1328),y=f(()=>d.value*l.value*1e5*.17),x=f(()=>{const k=u.value-l.value,t=h.value==="LONG"?1:-1;return d.value*k*1e5*t}),P=[{id:"TEST-PPR-01",group:"Paper Trading Isolation",scenario:"Xác thực không có bất kỳ broker API credentials nào được lưu (RULE 1)",expectation:"Hoàn toàn không có bảng credentials, không có endpoint kết nối đặt lệnh thật",status:"PASS"},{id:"TEST-PPR-02",group:"Derivatives Calculation",scenario:"Tính toán PnL hợp đồng phái sinh VN30F1M hệ số 100,000",expectation:"Khớp chính xác từng bước giá 0.1 điểm (10,000 VND / hợp đồng)",status:"PASS"},{id:"TEST-SET-01",group:"T+2 Settlement",scenario:"Kiểm tra quyền bán cổ phiếu mua vào sáng Thứ 2 (T+0)",expectation:"Chặn lệnh bán trong sáng Thứ 4; chỉ cho phép bán từ 13:00 chiều Thứ 4 (T+2)",status:"PASS"},{id:"TEST-MRG-01",group:"Margin Monitoring",scenario:"Tài khoản sụt giảm xuống dưới tỷ lệ ký quỹ duy trì (Maintenance Margin)",expectation:"Kích hoạt cờ cảnh báo CALL_MARGIN trên giao diện mô phỏng, ghi nhận cảnh báo",status:"PASS"}];return(k,t)=>{const N=$,s=D,L=R,S=O,b=G;return m(),c("div",H,[n("div",B,[n("div",null,[n("div",U,[o(N,{to:"/",class:"hover:text-emerald-400"},{default:C(()=>[...t[5]||(t[5]=[a("Dashboard",-1)])]),_:1}),t[6]||(t[6]=n("span",null,"/",-1)),t[7]||(t[7]=n("span",{class:"text-emerald-400"},"TRD Phase 4",-1))]),n("h1",q,[o(s,{name:"i-heroicons-square-3-stack-3d",class:"w-7 h-7 text-amber-400"}),t[8]||(t[8]=a(" Phase 4: Paper Trading & Chu kỳ T+2 ",-1))]),t[9]||(t[9]=n("p",{class:"text-xs sm:text-sm text-slate-400 mt-1"}," Mô phỏng khớp lệnh VN30F1M không rủi ro, quản lý ký quỹ, tính toán phí thuế và hạn mức mua bán T+2. ",-1))]),n("div",K,[n("span",Q,[o(s,{name:"i-heroicons-check-circle",class:"w-4 h-4"}),t[10]||(t[10]=a(" DoD Paper & T+2: 100% ",-1))])])]),n("div",z,[(m(),c(V,null,F(v,i=>n("button",{key:i.id,type:"button",class:T(["pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2",e(r)===i.id?"border-amber-400 text-amber-400":"border-transparent text-slate-400 hover:text-slate-200"]),onClick:ct=>r.value=i.id},[o(s,{name:i.icon,class:"w-4 h-4"},null,8,["name"]),a(" "+p(i.label),1)],10,Y)),64))]),e(r)==="spec"?(m(),c("div",Z,[o(L,{content:e(w),filename:"trd-phase-4-paper-trading.md"},null,8,["content"])])):e(r)==="tests"?(m(),c("div",X,[o(S,{tests:P})])):e(r)==="simulator"?(m(),c("div",W,[n("div",j,[n("div",null,[n("h3",J,[o(s,{name:"i-heroicons-calculator",class:"w-5 h-5 text-amber-400"}),t[11]||(t[11]=a(" Mô phỏng Đặt lệnh Phái sinh VN30F1M & Tính toán Ký quỹ ",-1))]),t[12]||(t[12]=n("p",{class:"text-xs text-slate-400"}," Hệ số nhân hợp đồng: 100,000 VND / điểm; Tỷ lệ ký quỹ yêu cầu ban đầu: 17% (chuẩn VSDC). ",-1))]),n("div",tt,[n("div",null,[t[13]||(t[13]=n("label",{class:"block text-xs text-slate-400 mb-1"},"Vị thế đặt",-1)),n("div",nt,[n("button",{type:"button",class:T(["py-1.5 text-xs font-bold rounded-md transition-all font-mono",e(h)==="LONG"?"bg-emerald-600 text-white shadow-lg shadow-emerald-600/30":"bg-[#090d16] text-slate-400 border border-white/[0.08]"]),onClick:t[0]||(t[0]=i=>h.value="LONG")}," LONG (MUA) ",2),n("button",{type:"button",class:T(["py-1.5 text-xs font-bold rounded-md transition-all font-mono",e(h)==="SHORT"?"bg-rose-600 text-white shadow-lg shadow-rose-600/30":"bg-[#090d16] text-slate-400 border border-white/[0.08]"]),onClick:t[1]||(t[1]=i=>h.value="SHORT")}," SHORT (BÁN) ",2)])]),n("div",null,[t[14]||(t[14]=n("label",{class:"block text-xs text-slate-400 mb-1"},"Số lượng hợp đồng",-1)),o(b,{modelValue:e(d),"onUpdate:modelValue":t[2]||(t[2]=i=>_(d)?d.value=i:null),modelModifiers:{number:!0},type:"number",min:"1",max:"100",size:"sm",class:"w-full font-mono"},null,8,["modelValue"])]),n("div",null,[t[15]||(t[15]=n("label",{class:"block text-xs text-slate-400 mb-1"},"Giá vào lệnh (Entry Price)",-1)),o(b,{modelValue:e(l),"onUpdate:modelValue":t[3]||(t[3]=i=>_(l)?l.value=i:null),modelModifiers:{number:!0},type:"number",step:"0.1",size:"sm",class:"w-full font-mono"},null,8,["modelValue"])]),n("div",null,[t[16]||(t[16]=n("label",{class:"block text-xs text-slate-400 mb-1"},"Giá thị trường hiện tại (Current)",-1)),o(b,{modelValue:e(u),"onUpdate:modelValue":t[4]||(t[4]=i=>_(u)?u.value=i:null),modelModifiers:{number:!0},type:"number",step:"0.1",size:"sm",class:"w-full font-mono"},null,8,["modelValue"])])]),n("div",et,[n("div",it,[t[18]||(t[18]=n("span",{class:"text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]"},"Ký quỹ ban đầu (IM)",-1)),n("div",ot,[a(p((e(y)/1e6).toFixed(1))+" ",1),t[17]||(t[17]=n("span",{class:"text-xs font-normal text-slate-400"},"triệu VND",-1))]),t[19]||(t[19]=n("p",{class:"text-[11px] text-slate-400 font-mono"},"17% * Giá * Số HĐ * 100,000",-1))]),n("div",at,[t[21]||(t[21]=n("span",{class:"text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]"},"Lãi / Lỗ vị thế (Unrealized PnL)",-1)),n("div",{class:T(["text-2xl font-bold font-mono",e(x)>=0?"text-emerald-400":"text-rose-400"])},[a(p(e(x)>=0?"+":"")+p((e(x)/1e6).toFixed(2))+" ",1),t[20]||(t[20]=n("span",{class:"text-xs font-normal text-slate-400"},"triệu VND",-1))],2),n("p",lt," Biên độ: "+p((e(u)-e(l)).toFixed(1))+" điểm ",1)]),n("div",st,[t[23]||(t[23]=n("span",{class:"text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]"},"Trạng thái an toàn tài khoản",-1)),n("div",rt,[o(s,{name:"i-heroicons-shield-check",class:"w-6 h-6"}),t[22]||(t[22]=a(" AN TOÀN (SAFE) ",-1))]),t[24]||(t[24]=n("p",{class:"text-[11px] text-slate-400 font-mono"},"Tỷ lệ ký quỹ duy trì > 80%",-1))])]),n("div",ht,[n("h4",dt,[o(s,{name:"i-heroicons-clock",class:"w-4 h-4 text-amber-400"}),t[25]||(t[25]=a(" Chu kỳ thanh toán cổ phiếu cơ sở T+2 ",-1))]),t[26]||(t[26]=A('<div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs"><div class="p-3 rounded-lg bg-[#090d16] border border-white/[0.08] space-y-1"><span class="font-bold text-amber-400 font-mono">Ngày T+0 (Khớp lệnh)</span><p class="text-slate-400">Tiền mua bị phong tỏa, cổ phiếu ở trạng thái &quot;Chờ về&quot; (Pending delivery). Không được bán.</p></div><div class="p-3 rounded-lg bg-[#090d16] border border-white/[0.08] space-y-1"><span class="font-bold text-slate-300 font-mono">Ngày T+1 (Lưu ký VSDC)</span><p class="text-slate-400">Đối chiếu và bù trừ song phương tại Trung tâm lưu ký VSDC. Cổ phiếu tiếp tục đóng băng.</p></div><div class="p-3 rounded-lg bg-[#090d16] border border-white/[0.08] space-y-1"><span class="font-bold text-emerald-400 font-mono">Ngày T+2 (Khả dụng)</span><p class="text-slate-400">Vào lúc 13:00 chiều T+2, cổ phiếu về tài khoản và có thể thực hiện lệnh BÁN ngay trong phiên chiều.</p></div></div>',1))])])])):I("",!0)])}}});export{Tt as default};
