export const phase5Markdown = `# TRD Phase 5: Sổ Nhật Ký Dự Báo (Forecast Journal) & Vòng Lặp Tự Học Có Kiểm Soát
## Hệ Thống Lưu Vết 100% Tín Hiệu, Tự Động Chấm Điểm Sai Số & Hiệu Chuẩn Trọng Số Engine

> **Tài liệu đặc tả kỹ thuật chi tiết dành cho kỹ sư phát triển backend (Self-Implementation Blueprint)**  
> *Phiên bản: 1.0.0 | Mục tiêu: Triển khai sổ cái kiểm toán tín hiệu bất biến, cơ chế tự động đối soát sau phiên và vòng lặp học hỏi có rào chắn chống Overfitting.*

---

## 1. NGUYÊN TẮC CỐT LÕI (PRIME DIRECTIVES)

Hệ thống lượng hóa chỉ thực sự giá trị khi nó **học hỏi được từ những sai lầm trong quá khứ** mà không bị suy thoái thành hiện tượng khớp quá mức trên nhiễu ngẫu nhiên (Overfitting).

1. **Minh Bạch Tuyệt Đối & Không Look-Ahead Bias (Master Rule 3)**:
   - Mọi dự báo (Direction, Target Price, Probability) đều phải được ghi cố định vào sổ cái tại thời điểm đưa ra quyết định (\`predicted_at\`).
   - Dữ liệu một khi đã ghi sổ KHÔNG ĐƯỢC PHÉP chỉnh sửa dự báo ban đầu; chỉ được cập nhật kết quả thực tế (\`actual_value\`, \`realized_at\`) khi tương lai đã ngã ngũ.
2. **Học Có Kiểm Soát (Governed Learning - No Live Code Mutation)**:
   - Vòng lặp tự học chỉ được phép đề xuất thay đổi **tham số & trọng số của Ensemble** (Engine 1, 2, 3 weights), tuyệt đối không tự sửa code logic.
   - Mọi đề xuất hiệu chuẩn đều phải tạo thành một phiên bản mới (\`model_version\`) kèm snapshot đầy đủ.
   - **Human-in-the-Loop Gate (Master Rule 4)**: Cần có xác nhận phê duyệt của người quản trị trước khi phiên bản mới được áp dụng vào luồng sinh tín hiệu thực tế. Nút bấm Rollback luôn khả dụng để quay về phiên bản cũ ngay lập tức.

---

## 2. KIẾN TRÚC 2 TẦNG: GHI SỔ & HIỆU CHUẨN (LAYER A & LAYER B)

\`\`\`
   [TẦNG A: RECORD & MEASURE (Mandatory & Always-On)]
   1. Ensemble sinh tín hiệu ──► Ghi ForecastJournal (status = PENDING)
                                         │
   2. Phiên kết thúc (Reality resolves)  │
      Daemon tự động cập nhật:           ▼
      actual_value, realized_at ──► Chấm điểm: Brier Score, Directional Accuracy, MAE
                                         │
                                         ▼
   [TẦNG B: GOVERNED RECALIBRATION (Auditable & Reversible)]
   3. Tính toán trọng số tối ưu mới dựa trên hiệu suất lăn 30 phiên gần nhất
   4. Kiểm tra điều kiện Anti-Overfit (Biên độ dịch chuyển trọng số <= 5%/kỳ)
   5. Tạo bản ghi ModelVersionSnapshot (status = PROPOSED)
                                         │
                                         ▼
   6. [Human Approval Gate API] ──► Quản trị viên duyệt ──► Kích hoạt phiên bản mới!
                                (Hoặc bấm Rollback để phục hồi phiên bản trước)
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
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
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

### Bước 4: Viết Bộ Tính Toán Hiệu Chuẩn Trọng Số (\`recalibration_engine.py\`)
1. Triển khai tại \`backend/app/domains/quant/application/recalibration_engine.py\`.
2. Hàm \`compute_proposed_weights()\`:
   - Truy vấn 30 ngày gần nhất trong \`ForecastJournal\`.
   - Tính điểm S1, S2, S3 cho 3 Engine.
   - Áp dụng Softmax và hàm \`clip\` chênh lệch tối đa +-0.05.
   - Tạo một bản ghi mới trong \`ModelVersionSnapshot\` với \`is_active = False\`.

### Bước 5: Viết API Endpoints Quản Trị Phê Duyệt & Rollback
Triển khai tại \`backend/app/domains/quant/presentation/forecast_router.py\`:
- \`GET /api/v1/forecast\`: Xem lịch sử nhật ký dự báo kèm filter trạng thái, độ chính xác.
- \`GET /api/v1/forecast/aggregate\`: Lấy báo cáo thống kê sai số MAE và tỷ lệ đúng hướng (Directional Accuracy).
- \`POST /api/v1/forecast/{id}/resolve\`: Cập nhật kết quả thực tế khi phiên kết thúc.
- \`POST /api/v1/forecast/{id}/score\`: Tính điểm tự động cho dự báo.
- \`POST /api/v1/quant/versions/{version_tag}/promote\`: Phê duyệt kích hoạt phiên bản mới (yêu cầu quyền Admin).
- \`POST /api/v1/quant/versions/{version_tag}/rollback\`: Khôi phục phiên bản trước đó chỉ với 1 click.

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
| \`TEST-JOURNAL-07\` | Đề xuất trọng số phiên bản mới | Model snapshot lưu với \`is_active = False\`, chưa tác động tới luồng sinh tín hiệu thực tế |
| \`TEST-JOURNAL-08\` | Gọi API \`/promote\` phiên bản mới | Phiên bản cũ chuyển \`is_active = False\`, phiên bản mới chuyển \`is_active = True\` |
| \`TEST-JOURNAL-09\` | Gọi API \`/rollback\` về phiên bản cũ | Hệ thống đổi cờ \`is_active\` tức thì, luồng live nhận lại trọng số cũ |
| \`TEST-JOURNAL-10\` | Báo cáo thống kê Winrate tổng quan 30 ngày | Trả về chính xác số lượng lệnh thắng / tổng số lệnh đã chốt |
`
