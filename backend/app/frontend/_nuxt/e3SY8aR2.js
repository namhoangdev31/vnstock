import{h as S,u as E,p as C,c as r,a as t,b as i,w as p,d as o,F as g,v as m,j as h,q as O,e as M,r as b,o as c,g as w,y as _,t as a}from"./CY0ZBfEj.js";import{_ as R,a as F}from"./C9-gN_qz.js";import{_ as $}from"./BDjQny7V.js";import"./CDBTxs1B.js";const D=`# TRD Phase 5: Sổ Nhật Ký Dự Báo (Forecast Journal) & Vòng Lặp Tự Học Có Kiểm Soát
## Hệ Thống Lưu Vết 100% Tín Hiệu, Tự Động Chấm Điểm Sai Số & Hiệu Chuẩn Trọng Số Engine

> **Tài liệu đặc tả kỹ thuật chi tiết dành cho kỹ sư phát triển backend (Self-Implementation Blueprint)**  
> *Phiên bản: 1.0.0 | Mục tiêu: Triển khai sổ cái kiểm toán tín hiệu bất biến, cơ chế tự động đối soát sau phiên và vòng lặp học hỏi có rào chắn chống Overfitting.*

---

## 1. NGUYÊN TẮC CỐT LÕI (PRIME DIRECTIVES)

Hệ thống lượng hóa chỉ thực sự giá trị khi nó **học hỏi được từ những sai lầm trong quá khứ** mà không bị suy thoái thành hiện tượng khớp quá mức trên nhiễu ngẫu nhiên (Overfitting).

1. **Minh Bạch Tuyệt Đối & Không Look-Ahead Bias (Master Rule 3)**:
   - Mọi dự báo (Direction, Target Price, Probability) đều phải được ghi cố định vào sổ cái tại thời điểm đưa ra quyết định (\`predicted_at\`).
   - Dữ liệu một khi đã ghi sổ KHÔNG ĐƯỢC PHÉP chỉnh sửa dự báo ban đầu; chỉ được cập nhật kết quả thực tế (\`actual_value\`, \`realized_at\`) khi tương lai đã ngã ngũ.
2. **Tự Động Hóa Tầng Tự Học (Autonomous Walk-Forward Gate & Auto-Promote)**:
   - Vòng lặp tự học vận hành **hoàn toàn tự động**: Hệ thống tự động đánh giá hiệu quả và tự kích hoạt trọng số Engine mới mà không cần Admin bấm duyệt thủ công.
   - Khi bộ trọng số mới vượt qua **Cổng Kiểm Thử Lăn (Walk-Forward Validation Gate)**: cải thiện Brier score / MAE, độ dịch chuyển <= 5%/kỳ và nằm trong biên an toàn [0.15, 0.60], hệ thống sẽ **tự động kích hoạt (Auto-Promote \`is_active = True\`)** vào luồng sinh tín hiệu live.
   - **Cầu Dao Tự Ngắt (Autonomous Circuit Breaker)**: Nếu sai số liên tiếp 3 phiên hoặc Drawdown mô phỏng vượt $-3%$, hệ thống tự động ngắt tính năng tự học, kích hoạt trọng số phòng thủ mặc định (\`0.33, 0.33, 0.34\`) và gửi cảnh báo khẩn cấp.
   - **Quyền Can Thiệp & Rollback Của Admin**: Quản trị viên luôn giữ quyền override, khóa tạm thời hoặc bấm **Rollback 1-click** về phiên bản trước bất kỳ lúc nào.

---

## 2. KIẾN TRÚC 2 TẦNG: GHI SỔ & TỰ ĐỘNG HIỆU CHUẨN (AUTO-PROMOTE ARCHITECTURE)

\`\`\`
   [TẦNG A: RECORD & MEASURE (Mandatory & Always-On)]
   1. Ensemble sinh tín hiệu ──► Ghi ForecastJournal (status = PENDING)
                                         │
   2. Phiên kết thúc (Reality resolves)  │
      Daemon tự động cập nhật:           ▼
      actual_value, realized_at ──► Chấm điểm: Brier Score, Directional Accuracy, MAE
                                         │
                                         ▼
   [TẦNG B: AUTONOMOUS RECALIBRATION & AUTO-PROMOTE (Auditable & Reversible)]
   3. Tính toán trọng số tối ưu mới dựa trên hiệu suất lăn 30 phiên gần nhất
   4. Kiểm tra điều kiện Anti-Overfit (Biên độ dịch chuyển trọng số <= 5%/kỳ, biên [0.15, 0.60])
   5. Chạy ngầm Walk-Forward Validation Gate so sánh với Baseline
                                         │
                                         ▼ (Vượt qua Walk-Forward Gate)
   6. [AUTO-PROMOTE ENGINE] ──► Tự động kích hoạt ModelVersionSnapshot mới (is_active = True)!
                                (Kèm Circuit Breaker ngắt tự động nếu Drawdown > 3% + Quyền Rollback cho Admin)
\`\`\`

---

## 3. CÔNG THỨC TOÁN HỌC CHẤM ĐIỂM SAI SỐ (SCORING FORMULAS)

### 3.1 Độ Chuẩn Xác Hướng Đi (Directional Accuracy - DA)
Đo lường tỷ lệ phần trăm dự đoán đúng hướng tăng/giảm của thị trường:
$$\\text{DA} = \\frac{1}{N} \\sum_{i=1}^N \\mathbb{I}\\left(\\text{sign}(\\Delta \\hat{y}_i) == \\text{sign}(\\Delta y_i)\\right)$$
- $\\Delta \\hat{y}_i$: Mức thay đổi giá dự kiến.
- $\\Delta y_i$: Mức thay đổi giá thực tế.
- $\\mathbb{I}(\\cdot)$: Hàm chỉ thị (nhận giá trị 1 nếu trùng hướng, 0 nếu sai hướng).

### 3.2 Brier Score (Đánh Giá Chất Lượng Xác Suất)
Brier Score đo lường sai số bình phương giữa xác suất dự báo $p_i \\in [0, 1]$ và kết quả nhị phân thực tế $o_i \\in \\{0, 1\\}$ (0: Giảm, 1: Tăng):
$$\\text{BS} = \\frac{1}{N} \\sum_{i=1}^N (p_i - o_i)^2$$
- Điểm càng gần 0.0: Mô hình dự báo xác suất càng hoàn hảo.
- Điểm 0.25: Tương đương với đoán mò ngẫu nhiên (50/50).
- Điểm > 0.25: Mô hình hiệu chuẩn xác suất kém.

### 3.3 Sai Số Biên Độ Giá (MAE & RMSE)
- **Mean Absolute Error (MAE)**:
  $$\\text{MAE} = \\frac{1}{N} \\sum_{i=1}^N |P_{\\text{predicted}} - P_{\\text{actual}}|$$
- **Root Mean Squared Error (RMSE)**:
  $$\\text{RMSE} = \\sqrt{\\frac{1}{N} \\sum_{i=1}^N (P_{\\text{predicted}} - P_{\\text{actual}})^2}$$

---

## 4. THUẬT TOÁN HIỆU CHUẨN TRỌNG SỐ ENGINE CÓ KIỂM SOÁT

### 4.1 Thuật Toán Softmax Hiệu Năng Lăn 30 Ngày (Rolling Softmax Rebalancing)
Hệ thống tính toán điểm hiệu quả tổng hợp $S_k$ cho từng Engine $k \\in \\{1, 2, 3\\}$ trong 30 ngày gần nhất:
$$S_k = \\alpha \\cdot \\text{DA}_k + (1 - \\alpha) \\cdot (1 - \\text{BS}_k)$$

Trọng số đề xuất mới $w_k^*$ được tính qua hàm Softmax với hệ số nhiệt độ $\\tau = 0.5$:
$$w_k^* = \\frac{\\exp(S_k / \\tau)}{\\sum_{j=1}^3 \\exp(S_j / \\tau)}$$

### 4.2 Rào Chắn Chống Overfitting (Safeguards)
1. **Giới hạn tốc độ dịch chuyển trọng số (Max Weight Shift)**:
   $$w_k^{\\text{bounded}} = w_k^{\\text{old}} + \\text{clip}\\left(w_k^* - w_k^{\\text{old}},\\, -0.05,\\, +0.05\\right)$$
   Trọng số của bất kỳ Engine nào không được thay đổi quá $\\pm 5\\%$ trong một chu kỳ hiệu chuẩn.
2. **Ngưỡng biên tối thiểu & tối đa (Weight Bounds)**:
   $$0.15 \\le w_k \\le 0.60 \\quad \\forall k \\in \\{1, 2, 3\\}$$
   Đảm bảo không bao giờ triệt tiêu hoàn toàn một Engine nào về 0.

---

## 5. DATABASE SCHEMA (POSTGRESQL / SQLMODEL)

\`\`\`python
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
import uuid

class ForecastJournal(SQLModel, table=True):
    __tablename__ = "forecast_journal"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(index=True)                          # VN30F1M, VN30,...
    horizon: str = Field(index=True)                         # ATC, T+1, WEEKLY, MONTHLY
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ), index=True)
    
    # Dự báo ban đầu
    predicted_direction: str = Field()                       # BULLISH, BEARISH, NEUTRAL
    predicted_target_price: Optional[float] = Field(default=None)
    predicted_probability: float = Field(default=0.5)        # 0.0 -> 1.0
    predicted_price_low: Optional[float] = Field(default=None)
    predicted_price_high: Optional[float] = Field(default=None)
    
    # Snapshot trọng số & phiên bản
    engine_weights: Dict[str, float] = Field(default={}, sa_column=Column(JSON))
    model_version: str = Field(default="v1.0.0", index=True)
    
    # Kết quả thực tế (Đối soát sau phiên)
    actual_value: Optional[float] = Field(default=None)
    realized_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="PENDING", index=True)       # PENDING, RESOLVED, SCORED
    
    # Điểm số sai số
    directional_correct: Optional[bool] = Field(default=None)
    brier_score: Optional[float] = Field(default=None)
    absolute_error: Optional[float] = Field(default=None)

class ModelVersionSnapshot(SQLModel, table=True):
    __tablename__ = "model_version_snapshot"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    version_tag: str = Field(unique=True, index=True)       # v1.0.0, v1.1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ))
    parameters_snapshot: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_active: bool = Field(default=False, index=True)
    rolling_30d_accuracy: Optional[float] = Field(default=None)
    rolling_30d_brier_score: Optional[float] = Field(default=None)
    auto_promoted: bool = Field(default=True)
    circuit_breaker_triggered: bool = Field(default=False)
    promoted_at: Optional[datetime] = Field(default=None)
    rollback_from: Optional[str] = Field(default=None)
\`\`\`

---

## 6. HƯỚNG DẪN TỰ CODE TỪNG BƯỚC (6-STEP DEV BLUEPRINT)

Kỹ sư backend triển khai theo thứ tự sau:

### Bước 1: Tạo Models & Migration
1. Tạo file \`backend/app/domains/quant/domain/models.py\` chứa 2 model trên (\`ForecastJournal\`, \`ModelVersionSnapshot\`).
2. Chạy \`uv run alembic revision --autogenerate -m "add_forecast_journal_tables"\`.
3. Chạy \`uv run alembic upgrade head\`.

### Bước 2: Tạo Logger Hook Trong Bộ Ensemble
1. Mở engine \`backend/app/domains/quant/application/engines/ensemble_engine.py\`.
2. Mỗi khi hàm \`generate_signal()\` sinh tín hiệu thành công:
   - Tự động gọi \`log_forecast_to_journal(...)\`.
   - Lưu bản ghi vào bảng \`ForecastJournal\` với \`status = 'pending'\`.

### Bước 3: Viết Worker Tự Động Đối Soát Sau Phiên (\`evaluator.py\`)
1. Được Daemon gọi vào khung giờ \`POST_MARKET_EVAL\` (14:45 - 15:30):
2. Triển khai tại \`backend/app/domains/quant/application/evaluator.py\`.
3. Quét các dòng \`status = 'pending'\` có \`horizon = 'ATC'\` của ngày hôm nay.
4. Lấy giá khớp ATC thực tế từ \`Quote.history()\`.
5. Cập nhật \`actual_value = price_atc\`, \`realized_at = datetime.now(VN_TZ)\`.
6. Tính \`directional_correct\`, \`brier_score\`, \`absolute_error\` và chuyển \`status = 'scored'\`.

### Bước 4: Viết Bộ Tính Toán Hiệu Chuẩn & Auto-Promote Engine (\`recalibration_engine.py\`)
1. Triển khai tại \`backend/app/domains/quant/application/recalibration_engine.py\`.
2. Hàm \`evaluate_and_auto_promote()\`:
   - Truy vấn 30 ngày gần nhất trong \`ForecastJournal\`.
   - Kiểm tra điều kiện Circuit Breaker (nếu 3 phiên liên tiếp lỗi hoặc Drawdown > 3%, kích hoạt cờ an toàn, khóa auto-promote).
   - Tính điểm S1, S2, S3 cho 3 Engine.
   - Áp dụng Softmax và hàm \`clip\` chênh lệch tối đa +-0.05, biên an toàn [0.15, 0.60].
   - Chạy Walk-Forward Validation Gate: nếu cải thiện Brier score / MAE, **tự động kích hoạt (Auto-Promote)**: tạo \`ModelVersionSnapshot\` mới với \`is_active = True\`, cập nhật phiên bản trước thành \`is_active = False\` mà không cần Admin duyệt thủ công.

### Bước 5: Viết API Endpoints Quản Trị & Rollback Khẩn Cấp
Triển khai tại \`backend/app/domains/quant/presentation/forecast_router.py\`:
- \`GET /api/v1/forecast\`: Xem lịch sử nhật ký dự báo kèm filter trạng thái, độ chính xác.
- \`GET /api/v1/forecast/aggregate\`: Lấy báo cáo thống kê sai số MAE và tỷ lệ đúng hướng (Directional Accuracy).
- \`POST /api/v1/forecast/{id}/resolve\`: Cập nhật kết quả thực tế khi phiên kết thúc.
- \`POST /api/v1/forecast/{id}/score\`: Tính điểm tự động cho dự báo.
- \`POST /api/v1/quant/recalibrate/auto-run\`: Kích hoạt vòng lặp tự đánh giá và auto-promote.
- \`POST /api/v1/quant/versions/{version_tag}/rollback\`: Khôi phục phiên bản trước đó tức thì khi Admin yêu cầu can thiệp.
- \`POST /api/v1/quant/circuit-breaker/reset\`: Khôi phục hoạt động bình thường sau khi gỡ cảnh báo Circuit Breaker.

### Bước 6: Kiểm Thử Độc Lập
1. Viết Unit Test giả lập 100 dự báo và đối soát kết quả.
2. Kiểm tra tính toàn vẹn của dữ liệu: Không có bản ghi nào bị ghi đè \`predicted_at\`.

---

## 7. TEST MATRIX & TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

| Mã Test | Kịch bản thử nghiệm | Kết quả kỳ vọng |
|---|---|---|
| \`TEST-JOURNAL-01\` | Ensemble sinh tín hiệu Long VN30F1M | Row được tạo trong \`ForecastJournal\` với \`status = 'PENDING'\`, \`predicted_at\` lưu chuẩn UTC |
| \`TEST-JOURNAL-02\` | Thử thay đổi trường \`predicted_target_price\` sau khi đã lưu | Hệ thống từ chối cập nhật hoặc kiểm toán phát hiện vi phạm tính toàn vẹn |
| \`TEST-JOURNAL-03\` | Chạy bộ chấm điểm phiên ATC: Dự báo Tăng ($P=0.8$), thực tế giá Tăng | \`directional_correct = True\`, \`brier_score = (0.8 - 1.0)^2 = 0.04\` |
| \`TEST-JOURNAL-04\` | Chạy bộ chấm điểm phiên ATC: Dự báo Tăng ($P=0.7$), thực tế giá Giảm | \`directional_correct = False\`, \`brier_score = (0.7 - 0.0)^2 = 0.49\` |
| \`TEST-JOURNAL-05\` | Tính toán MAE cho dự báo giá mục tiêu 1310 khi giá thực tế là 1305 | \`absolute_error = abs(1310 - 1305) = 5.0\` điểm |
| \`TEST-JOURNAL-06\` | Đề xuất trọng số mới tính ra chênh lệch +12% so với trọng số cũ | Thuật toán clip kẹp lại ở mức tối đa +5.0%, không bị nhảy vọt |
| \`TEST-JOURNAL-07\` | Vượt qua Walk-Forward Validation Gate | Tự động kích hoạt (Auto-Promote) phiên bản mới với \`is_active = True\` không cần Admin duyệt |
| \`TEST-JOURNAL-08\` | Kịch bản Drawdown vượt -3% hoặc 3 phiên sai liên tiếp | Circuit Breaker tự ngắt, khóa auto-promote và trả về trọng số an toàn mặc định |
| \`TEST-JOURNAL-09\` | Admin gọi API \`/rollback\` về phiên bản cũ | Hệ thống đổi cờ \`is_active\` tức thì, luồng live nhận lại trọng số cũ |
| \`TEST-JOURNAL-10\` | Báo cáo thống kê Winrate tổng quan 30 ngày | Trả về chính xác số lượng lệnh thắng / tổng số lệnh đã chốt |
`,P={class:"space-y-6"},L={class:"flex flex-col sm:flex-row sm:items-center justify-between gap-4"},H={class:"flex items-center gap-2 text-xs text-slate-400 font-mono mb-1"},I={class:"text-2xl font-bold tracking-tight text-white flex items-center gap-2"},U={class:"flex items-center gap-2"},B={class:"px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5"},G={class:"flex border-b border-slate-800 gap-4"},q=["onClick"],V={key:0},K={key:1},J={key:2,class:"space-y-6"},W={class:"p-6 rounded-2xl bg-surface-abyss border border-white/[0.08] shadow-2xl space-y-6"},z={class:"flex flex-col sm:flex-row sm:items-center justify-between gap-3"},Q={class:"text-base font-bold text-white flex items-center gap-2"},j={class:"overflow-x-auto rounded-xl border border-white/[0.06] bg-surface-abyss"},X={class:"w-full text-left text-xs font-mono"},Y={class:"bg-surface-abyss text-slate-400 uppercase text-[10px] tracking-wider border-b border-white/[0.06]"},Z={class:"py-3 px-4"},tt={class:"flex items-center gap-1"},nt={class:"divide-y divide-white/[0.04]"},et={class:"py-3 px-4 font-bold text-white"},it={class:"py-3 px-4"},ot={class:"px-2 py-0.5 rounded text-[10px] bg-white/[0.04] border border-white/[0.06] text-slate-300"},at={class:"py-3 px-4 text-slate-400"},st={class:"py-3 px-4 text-emerald-400 font-bold"},rt={class:"py-3 px-4 text-slate-200"},ct={class:"py-3 px-4 text-slate-300"},lt={class:"py-3 px-4 text-center"},ht={class:"p-5 rounded-xl bg-surface-midnight border border-white/[0.06] space-y-2 text-xs"},dt={class:"font-bold text-white flex items-center gap-1.5 font-mono"},Tt=S({__name:"phase-5",setup(ut){E({title:"TRD Phase 5: Forecast Journal - Vnstock Quants"});const d=b("spec"),{showSuccessToast:T}=C(),x=[{id:"spec",label:"Tài liệu đặc tả",icon:"i-heroicons-document-text"},{id:"tests",label:"Ma trận kiểm thử",icon:"i-heroicons-check-badge"},{id:"ledger",label:"Mô phỏng Sổ cái Audit",icon:"i-heroicons-clipboard-document-list"}],u=b([{id:1,symbol:"VN30F1M",horizon:"ATC_AUCTION",predictedAt:"14:15:00",prediction:"LONG (1328.5)",actual:"1330.2",mae:1.7,status:"SCORED"},{id:2,symbol:"VN30F1M",horizon:"NEXT_DAY (T+1)",predictedAt:"15:30:00 (Hôm qua)",prediction:"BULLISH (+12 pts)",actual:"+14.5 pts",mae:2.5,status:"SCORED"},{id:3,symbol:"VN30F1M",horizon:"ATC_AUCTION",predictedAt:"14:15:00 (Hôm nay)",prediction:"SHORT (1315.0)",actual:null,mae:null,status:"PENDING"},{id:4,symbol:"FPT",horizon:"WEEKLY_ALPHA",predictedAt:"Đầu tuần",prediction:"OUTPERFORM (+5%)",actual:null,mae:null,status:"PENDING"}]),k=()=>{u.value=u.value.map(l=>l.status==="PENDING"?{...l,actual:l.symbol==="VN30F1M"?"1313.8":"+6.2%",mae:(l.symbol==="VN30F1M",1.2),status:"SCORED"}:l),T("Đã đối soát sổ cái!","Các dự báo PENDING đã được backfill dữ liệu thực tế và chấm điểm độ chính xác.")},f=[{id:"TEST-JRN-01",group:"Ledger Persistence",scenario:"Ghi nhận dự báo tại thời điểm T với engine_weights và model_version",expectation:"Lưu vào database ngay lập tức với status='pending'; không cho phép sửa đổi predicted_at",status:"PASS"},{id:"TEST-JRN-02",group:"Realization Backfill",scenario:"Cập nhật actual_value khi phiên kết thúc",expectation:"Status chuyển sang 'resolved'; hệ thống lưu audit trail thời gian đối soát",status:"PASS"},{id:"TEST-JRN-03",group:"Automated Scoring",scenario:"Tính toán sai số tuyệt đối trung bình (MAE) và độ chính xác hướng đi (Directional Accuracy)",expectation:"Tự động tính đúng MAE; chuyển status sang 'scored'",status:"PASS"},{id:"TEST-RCAL-01",group:"Autonomous Recalibration",scenario:"Hiệu chuẩn trọng số Engine mới trên tập dữ liệu lịch sử",expectation:"Tự động Auto-Promote khi đạt chuẩn Walk-Forward Gate; duy trì Circuit Breaker và snapshot cho phép rollback",status:"PASS"}];return(l,n)=>{const v=M,s=w,y=R,N=F,A=$;return c(),r("div",P,[t("div",L,[t("div",null,[t("div",H,[i(v,{to:"/admin",class:"hover:text-emerald-400"},{default:p(()=>[...n[0]||(n[0]=[o("Dashboard",-1)])]),_:1}),n[1]||(n[1]=t("span",null,"/",-1)),n[2]||(n[2]=t("span",{class:"text-emerald-400"},"TRD Phase 5",-1))]),t("h1",I,[i(s,{name:"i-heroicons-archive-box",class:"w-7 h-7 text-rose-400"}),n[3]||(n[3]=o(" Phase 5: Sổ nhật ký dự báo (Forecast Journal) ",-1))]),n[4]||(n[4]=t("p",{class:"text-xs sm:text-sm text-slate-400 mt-1"}," Lưu vết 100% dự báo trước phiên, đối soát kết quả thực tế, chấm điểm MAE/Accuracy và hiệu chuẩn mô hình có kiểm soát. ",-1))]),t("div",U,[t("span",B,[i(s,{name:"i-heroicons-check-circle",class:"w-4 h-4"}),n[5]||(n[5]=o(" DoD Journal: 100% ",-1))])])]),t("div",G,[(c(),r(g,null,m(x,e=>t("button",{key:e.id,type:"button",class:_(["pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2",h(d)===e.id?"border-rose-400 text-rose-400":"border-transparent text-slate-400 hover:text-slate-200"]),onClick:pt=>d.value=e.id},[i(s,{name:e.icon,class:"w-4 h-4"},null,8,["name"]),o(" "+a(e.label),1)],10,q)),64))]),h(d)==="spec"?(c(),r("div",V,[i(y,{content:h(D),filename:"trd-phase-5-forecast-journal.md"},null,8,["content"])])):h(d)==="tests"?(c(),r("div",K,[i(N,{tests:f})])):h(d)==="ledger"?(c(),r("div",J,[t("div",W,[t("div",z,[t("div",null,[t("h3",Q,[i(s,{name:"i-heroicons-clipboard-document-list",class:"w-5 h-5 text-rose-400"}),n[6]||(n[6]=o(" Sổ cái Đối soát & Tự học (Forecast Audit Ledger) ",-1))]),n[7]||(n[7]=t("p",{class:"text-xs text-slate-400"}," Mỗi dự báo được snapshot trước khi phiên diễn ra; tự động chấm điểm khi có kết quả thực tế. ",-1))]),t("button",{type:"button",class:"px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto transition-colors shadow-lg shadow-rose-600/20",onClick:k},[i(s,{name:"i-heroicons-arrow-path",class:"w-4 h-4"}),n[8]||(n[8]=o(" Đối soát kết quả thực tế phiên hôm nay ",-1))])]),t("div",j,[t("table",X,[t("thead",Y,[t("tr",null,[n[10]||(n[10]=t("th",{class:"py-3 px-4"},"Mã / Tài sản",-1)),n[11]||(n[11]=t("th",{class:"py-3 px-4"},"Khung thời gian",-1)),n[12]||(n[12]=t("th",{class:"py-3 px-4"},"Thời điểm dự báo",-1)),n[13]||(n[13]=t("th",{class:"py-3 px-4"},"Kỳ vọng / Xu hướng",-1)),n[14]||(n[14]=t("th",{class:"py-3 px-4"},"Giá thực tế",-1)),t("th",Z,[t("div",tt,[n[9]||(n[9]=t("span",null,"Sai số",-1)),i(A,{text:"Mean Absolute Error"},{default:p(()=>[i(s,{name:"i-heroicons-information-circle",class:"w-3.5 h-3.5 text-aave-graphite cursor-help"})]),_:1})])]),n[15]||(n[15]=t("th",{class:"py-3 px-4 text-center"},"Trạng thái",-1))])]),t("tbody",nt,[(c(!0),r(g,null,m(h(u),e=>(c(),r("tr",{key:e.id,class:"hover:bg-white/[0.02] transition-colors"},[t("td",et,a(e.symbol),1),t("td",it,[t("span",ot,a(e.horizon),1)]),t("td",at,a(e.predictedAt),1),t("td",st,a(e.prediction),1),t("td",rt,a(e.actual||"Đang chờ phiên đối soát"),1),t("td",ct,a(e.mae!==null?e.mae.toFixed(1)+" pts":"N/A"),1),t("td",lt,[t("span",{class:_(["px-2 py-0.5 rounded text-[10px] font-bold",e.status==="SCORED"?"bg-emerald-500/10 text-emerald-400 border border-emerald-500/20":"bg-amber-500/10 text-amber-400 border border-amber-500/20"])},a(e.status),3)])]))),128))])])]),t("div",ht,[t("h4",dt,[i(s,{name:"i-heroicons-arrow-path-rounded-square",class:"w-4 h-4 text-rose-400"}),n[16]||(n[16]=o(" CƠ CHẾ TỰ HỌC TỰ ĐỘNG (AUTONOMOUS AUTO-PROMOTE & CIRCUIT BREAKER) ",-1))]),n[17]||(n[17]=t("p",{class:"text-slate-400 leading-relaxed"},[o(" Hệ thống tự động đánh giá Directional Accuracy và Brier Score trên 30 phiên gần nhất. Khi bộ trọng số mới vượt qua Cổng Walk-Forward Gate, phiên bản mới sẽ được tự động kích hoạt (Auto-Promote "),t("span",{class:"font-mono text-emerald-400 font-bold"},"is_active = true"),o(") mà không cần Admin duyệt thủ công. Nếu Drawdown vượt -3%, Circuit Breaker sẽ tự động khóa và phục hồi trọng số phòng thủ an toàn. ")],-1))])])])):O("",!0)])}}});export{Tt as default};
