export const phase3Markdown = `# TRD Phase 3: Background Session Daemon (24/7 Continuous Engine)
## Vòng Lặp Giám Sát Tự Động Bám Sát Chu Kỳ Phiên Giao Dịch Thực Tế

> **Tài liệu đặc tả kỹ thuật chi tiết dành cho kỹ sư phát triển backend (Self-Implementation Blueprint)**  
> *Phiên bản: 1.0.0 | Mục tiêu: Triển khai tiến trình daemon 24/7 giám sát thị trường chứng khoán Việt Nam, đồng bộ dữ liệu đa phiên, kích hoạt kịch bản dự báo ATO/ATC và bảo vệ chống khóa IP.*

---

## 1. TỔNG QUAN VÀ MỤC TIÊU CỐT LÕI (PRIME MISSION)

Background Session Daemon là **trái tim vận hành tự động liên tục (24/7)** của hệ thống lượng hóa. Khác với các hệ thống thụ động chỉ chờ request từ người dùng, Daemon là tiến trình nền độc lập (\`background worker process\`) tự động thức dậy, bám sát từng nhịp đập của thị trường Việt Nam (từ phái sinh \`VN30F1M\` mở cửa lúc 08:45 đến thị trường cơ sở đóng cửa lúc 14:45, và tiếp tục chạy mô phỏng qua đêm 24/7).

### 1.1 Nguyên Tắc Vận Hành
1. **Zero Real-Money Execution (Master Rule 1)**: Daemon chỉ thu thập dữ liệu, chạy tính toán Tri-Engine, ghi nhận nhật ký dự báo (Forecast Journal) và cập nhật số dư mô phỏng (Paper Trading). Tuyệt đối không gọi bất kỳ API đặt lệnh tiền thật nào.
2. **Context-Aware Adaptive Frequency**: Tần suất thu thập dữ liệu thay đổi linh hoạt theo trạng thái phiên (cao điểm 300ms - 1s, thấp điểm 5 phút, qua đêm 15 phút) để tối ưu hóa băng thông và bảo vệ IP trước cơ chế rate-limit của các nguồn cấp dữ liệu (\`VCI\`, \`TCBS\`).
3. **Resilience & Self-Healing**: Khi kết nối mạng gián đoạn hoặc API nhà cung cấp trả về \`429 Too Many Requests\` / \`502 Bad Gateway\`, Daemon tự động chuyển sang chế độ Circuit Breaker, Exponential Backoff và tự phục hồi mà không làm sập ứng dụng chính.

---

## 2. STATE MACHINE: CHU KỲ PHIÊN GIAO DỊCH VIỆT NAM (VIETNAMESE MARKET SESSIONS)

Hệ thống hoạt động dựa trên một Finite State Machine (FSM) đồng bộ theo múi giờ \`Asia/Ho_Chi_Minh\` (UTC+7).

\`\`\`
   +-------------------------------------------------------------------------+
   |                        24/7 MARKET DAEMON FSM                           |
   +-------------------------------------------------------------------------+
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
     [08:30 - 08:45]                                       [14:45 - 08:30 T+1]
      PRE_ATO_SETUP                                       OVERNIGHT_SIMULATION
             │                                                     ▲
             ▼                                                     │
     [08:45 - 09:00]                                       [14:30 - 14:45]
       ATO_AUCTION                                           ATC_AUCTION
             │                                                     ▲
             ▼                                                     │
     [09:00 - 11:30]                                       [14:15 - 14:30]
    MORNING_CONTINUOUS                                      PRE_ATC_SETUP
             │                                                     ▲
             ▼                                                     │
     [11:30 - 13:00] ────────────────────────────────────► [13:00 - 14:15]
    MIDDAY_INTERMISSION                                 AFTERNOON_CONTINUOUS
\`\`\`

### 2.1 Bảng Trạng Thái Chi Tiết & Hành Vi Tương Ứng

| Trạng thái | Khung giờ (VN) | Trách nhiệm cốt lõi của Daemon | Tần suất Polling |
|---|---|---|---|
| \`PRE_ATO_SETUP\` | 08:30 - 08:45 | • Đồng bộ giá tham chiếu (\`Reference Price\`), giá đóng cửa hôm trước.<br>• Tính Basis qua đêm giữa \`VN30F1M\` và chỉ số \`VN30\`.<br>• Cập nhật các mốc hỗ trợ/kháng cự (Pivots, FVG) cho ngày mới. | 30 giây |
| \`ATO_AUCTION\` | 08:45 - 09:00 | • Giám sát đợt khớp lệnh định kỳ mở cửa của Phái sinh \`VN30F1M\`.<br>• Đo lường biên độ Gap mở cửa (Bullish/Bearish Gap Severity).<br>• Khởi tạo Engine 1 cho dữ liệu nến mở màn. | 1.0 giây |
| \`MORNING_CONTINUOUS\` | 09:00 - 11:30 | • Cả thị trường cơ sở & phái sinh hoạt động song song.<br>• Lấy luồng khớp lệnh tick-by-tick \`Quote.intraday()\`.<br>• Tính Orderflow Delta ($V_{buy} - V_{sell}$), VWAP, RSI/MACD nến 1m, 5m.<br>• Kiểm tra chạm ngưỡng Stop Loss / Take Profit của Paper Orders. | 1.0 - 2.0 giây |
| \`MIDDAY_INTERMISSION\` | 11:30 - 13:00 | • Thị trường nghỉ trưa.<br>• Chốt sổ tạm thời nến sáng, tính toán ma trận tương quan ngành.<br>• Tính toán trước áp lực hàng về của chu kỳ T+2 cho phiên chiều. | 60 giây |
| \`AFTERNOON_CONTINUOUS\` | 13:00 - 14:15 | • Phiên chiều bắt đầu: Lượng hàng mua bắt đáy phiên T-2 về tài khoản.<br>• Đo lường áp lực xả hàng T+2 (\`t_plus_2_pressure_index\`).<br>• Quét tín hiệu Liquidity Sweep tại các vùng đỉnh/đáy buổi sáng. | 1.0 - 2.0 giây |
| \`PRE_ATC_SETUP\` | 14:15 - 14:30 | • **Cực kỳ quan trọng**: Kích hoạt bộ dự báo đóng cửa ATC.<br>• Tính toán khối lượng mất cân bằng dự kiến rổ VN30.<br>• Sinh kịch bản giá đóng cửa kỳ vọng $P_{\\text{ATC}}$ và khoảng biến động. | 500ms - 1.0 giây |
| \`ATC_AUCTION\` | 14:30 - 14:45 | • Giám sát đợt khớp lệnh định kỳ đóng cửa toàn thị trường.<br>• Ghi nhận giá khớp ATC thực tế, đo độ lệch so với dự báo.<br>• Khớp các lệnh Paper Trading phiên ATC. | 500ms |
| \`POST_MARKET_EVAL\` | 14:45 - 15:30 | • Đối soát toàn bộ tín hiệu trong ngày ghi vào \`ForecastJournal\`.<br>• Tính Brier Score, Directional Accuracy, MAE cho từng Engine.<br>• Chốt PnL danh mục Paper Trading ngày hôm nay. | 60 giây |
| \`OVERNIGHT_SIMULATION\` | 15:30 - 08:30 (T+1) | • Chạy 24/7 mô phỏng Monte Carlo 10,000 kịch bản cho phiên T+1.<br>• Lọc danh mục cổ phiếu Alpha Tuần, Tháng, Quý.<br>• Đề xuất cập nhật trọng số Ensemble nếu đủ điều kiện (Governed Recalibration). | 5 - 15 phút |

---

## 3. THIẾT KẾ KIẾN TRÚC ASYNCIO DAEMON TRONG PYTHON

### 3.1 Cấu Trúc Thành Phần
\`\`\`
backend/app/domains/quant/application/daemon/
├── __init__.py
├── market_clock.py          # Quản lý giờ thị trường, xác định State hiện tại
├── session_state.py         # Enum trạng thái & Context Data của phiên
├── poller.py                # Pipeline lấy dữ liệu có Rate-Limiter & Caching
├── circuit_breaker.py       # Bộ ngắt mạch chống ban IP khi API lỗi liên tục
├── dispatcher.py            # Phân phối event tới Tri-Engine & Paper Trading
└── session_daemon.py        # Vòng lặp Asyncio chính (chạy nền vĩnh viễn)
\`\`\`

### 3.2 Thuật Toán Xác Định State Theo Thời Gian Thực (Time-based State Engine)

\`\`\`python
# Pseudo-code thuật toán market_clock.py
from datetime import datetime, time
import pytz

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

def get_current_session_state(dt: datetime | None = None) -> SessionState:
    now = dt or datetime.now(VN_TZ)
    
    # Cuối tuần (Thứ 7, Chủ Nhật) -> Luôn là OVERNIGHT_SIMULATION
    if now.weekday() in (5, 6):
        return SessionState.OVERNIGHT_SIMULATION
        
    t = now.time()
    
    if time(8, 30) <= t < time(8, 45):
        return SessionState.PRE_ATO_SETUP
    elif time(8, 45) <= t < time(9, 0):
        return SessionState.ATO_AUCTION
    elif time(9, 0) <= t < time(11, 30):
        return SessionState.MORNING_CONTINUOUS
    elif time(11, 30) <= t < time(13, 0):
        return SessionState.MIDDAY_INTERMISSION
    elif time(13, 0) <= t < time(14, 15):
        return SessionState.AFTERNOON_CONTINUOUS
    elif time(14, 15) <= t < time(14, 30):
        return SessionState.PRE_ATC_SETUP
    elif time(14, 30) <= t < time(14, 45):
        return SessionState.ATC_AUCTION
    elif time(14, 45) <= t < time(15, 30):
        return SessionState.POST_MARKET_EVAL
    else:
        return SessionState.OVERNIGHT_SIMULATION
\`\`\`

---

## 4. CHIẾN LƯỢC BẢO VỆ CHỐNG KHÓA IP (RATE LIMITING & CIRCUIT BREAKER)

### 4.1 Cơ Chế Token Bucket & Jittered Exponential Backoff
Khi gọi các endpoint của \`VCI\` hay \`TCBS\` thông qua \`vnstock\`, hệ thống phải tuân thủ nghiêm ngặt quy định:
- **Độ trễ tối thiểu**: Giữa 2 request cùng nhóm ticker phải cách nhau tối thiểu 250ms.
- **Retry với Jitter**: t_sleep = min(10.0, 0.5 * 2^retry + random(0, 0.5))

### 4.2 State Machine Của Circuit Breaker

\`\`\`
   [CLOSED (Bình thường)]
           │
           │  Lỗi liên tiếp >= 5 lần
           ▼
    [OPEN (Ngắt mạch)] ────────── Chờ 60s (Cool-down)
           │
           ▼
  [HALF-OPEN (Thử nghiệm)]
      │             │
      │ Thành công   │ Thất bại
      ▼             ▼
   [CLOSED]       [OPEN]
\`\`\`

- **Khi Circuit Breaker ở trạng thái \`OPEN\`**: Daemon không gửi request ra Internet nữa mà đọc dữ liệu gần nhất từ In-Memory Cache / PostgreSQL để duy trì hệ thống không bị crash.

---

## 5. DATA CONTRACTS & DATABASE SCHEMA

### 5.1 Bảng Nhật Ký Hoạt Động Daemon (\`DaemonSessionLog\`)

\`\`\`python
from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid

class DaemonSessionLog(SQLModel, table=True):
    __tablename__ = "daemon_session_log"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trading_date: str = Field(index=True)                  # YYYY-MM-DD
    state: str = Field(index=True)                         # MORNING_CONTINUOUS, ATC_AUCTION,...
    heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(VN_TZ))
    ticks_processed: int = Field(default=0)
    signals_emitted: int = Field(default=0)
    circuit_breaker_status: str = Field(default="CLOSED") # CLOSED, OPEN, HALF_OPEN
    last_error_message: Optional[str] = Field(default=None)
    execution_duration_ms: float = Field(default=0.0)
\`\`\`

### 5.2 API Endpoints Của Daemon
- \`GET /api/v1/quant/daemon/status\`: Trả về trạng thái hiện tại (Current state, uptime, circuit breaker, tick rate, last update).
- \`POST /api/v1/quant/daemon/pause\`: Tạm dừng tiến trình thu thập (Dành cho Admin debug).
- \`POST /api/v1/quant/daemon/resume\`: Kích hoạt tiếp tục tiến trình.
- \`POST /api/v1/quant/daemon/trigger-cycle\`: Kích hoạt thủ công 1 vòng lặp (Manual trigger test).

---

## 6. HƯỚNG DẪN TỰ CODE TỪNG BƯỚC (6-STEP DEV BLUEPRINT)

Kỹ sư backend chỉ cần làm theo đúng 6 bước dưới đây để hoàn thiện Phase 3:

### Bước 1: Tạo Module \`market_clock.py\`
1. Khai báo Enum \`SessionState\` bao gồm 9 trạng thái phiên.
2. Viết hàm \`get_current_session_state(dt=None)\` căn cứ theo múi giờ \`Asia/Ho_Chi_Minh\`.
3. Viết unit test xác thực hàm chuyển đúng state ở các mốc: 08:35, 08:48, 09:15, 12:00, 13:45, 14:20, 14:35, 15:00, 23:00.

### Bước 2: Tạo Module \`circuit_breaker.py\`
1. Định nghĩa class \`CircuitBreaker\` với các trạng thái \`CLOSED\`, \`OPEN\`, \`HALF_OPEN\`.
2. Ghi nhận \`failure_count\`. Nếu >= 5 lần ném ngoại lệ mạng liên tiếp -> chuyển \`OPEN\`, kích hoạt đồng hồ 60 giây.
3. Trong trạng thái \`OPEN\`, trả về \`fallback_data\` từ DB hoặc RAM.

### Bước 3: Tạo Module \`poller.py\` Lấy Dữ Liệu Thị Trường
1. Hàm \`poll_derivatives_intraday(symbol='VN30F1M')\`: Lấy tick từ \`Quote.intraday()\`.
2. Hàm \`poll_vn30_underlying_prices()\`: Lấy giá 30 cổ phiếu cơ sở từ \`Quote.history(interval='1m')\`.
3. Bọc toàn bộ lời gọi qua \`CircuitBreaker\` và bộ rate-limiter delay 0.25s.

### Bước 4: Tạo Module \`dispatcher.py\` Phân Phối Tín Hiệu
1. Khi nhận được dữ liệu nến mới hoặc tick mới:
   - Đẩy dữ liệu vào Engine 1, 2, 3 của Phase 2.
   - Gọi \`EnsembleDecisionSystem.evaluate()\` để sinh tín hiệu.
   - Nếu có tín hiệu (Buy/Sell), lưu vào \`ForecastJournal\` (\`pending\`).
   - Đẩy sang Paper Trading Engine (Phase 4) kiểm tra khớp lệnh ảo.

### Bước 5: Viết Vòng Lặp Asyncio Chính Trong \`session_daemon.py\`
1. Khởi tạo tác vụ nền bằng \`asyncio.create_task(run_continuous_daemon())\`.
2. Sử dụng \`asyncio.sleep(interval)\` với \`interval\` lấy động theo \`state\`:
   - \`MORNING_CONTINUOUS\`: 1.0 giây.
   - \`ATC_AUCTION\` & \`PRE_ATC_SETUP\`: 0.5 giây.
   - \`MIDDAY_INTERMISSION\`: 60.0 giây.
   - \`OVERNIGHT_SIMULATION\`: 300.0 giây (5 phút).
3. Bắt tín hiệu ngắt OS \`SIGTERM\`, \`SIGINT\` để shutdown an toàn (Graceful Shutdown).

### Bước 6: Tích Hợp Vào FastAPI \`lifespan\` Trong \`backend/app/main.py\`
1. Khởi động task \`session_daemon\` bên trong hàm \`@asynccontextmanager async def lifespan(app: FastAPI)\` khi server khởi động.
2. Dừng task khi server tắt (\`task.cancel()\`).

---

## 7. TEST MATRIX & TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

| Mã Test | Kịch bản thử nghiệm | Kết quả kỳ vọng |
|---|---|---|
| \`TEST-DAEMON-01\` | Chạy hàm \`get_current_session_state\` với mock time là 08:47 sáng thứ Hai | Trả về chính xác trạng thái \`SessionState.ATO_AUCTION\` |
| \`TEST-DAEMON-02\` | Chạy hàm \`get_current_session_state\` với mock time là 14:22 chiều thứ Sáu | Trả về chính xác trạng thái \`SessionState.PRE_ATC_SETUP\` |
| \`TEST-DAEMON-03\` | Mock thời gian lúc 22:00 hoặc ngày Chủ Nhật | Trả về chính xác trạng thái \`SessionState.OVERNIGHT_SIMULATION\` |
| \`TEST-DAEMON-04\` | Giả lập nguồn cấp dữ liệu ném lỗi \`HTTP 429 Too Many Requests\` 5 lần liên tiếp | Circuit Breaker chuyển sang \`OPEN\`, log lỗi an toàn, không làm crash app |
| \`TEST-DAEMON-05\` | Sau 60 giây ở trạng thái \`OPEN\`, request kế tiếp thành công | Circuit Breaker tự động chuyển về \`HALF_OPEN\` rồi \`CLOSED\` |
| \`TEST-DAEMON-06\` | Polling trong phiên liên tục (\`MORNING_CONTINUOUS\`) | Tần suất đo được ổn định trong dải 1.0s ± 200ms |
| \`TEST-DAEMON-07\` | Khi nhận lệnh \`SIGTERM\` tắt server | Daemon hoàn tất vòng lặp hiện tại, ghi log kết thúc và dừng lại sạch sẽ |
| \`TEST-DAEMON-08\` | Heartbeat API \`/api/v1/quant/daemon/status\` | Trả về HTTP 200 kèm JSON chứa \`state\`, \`uptime_seconds\`, \`ticks_processed\` |
`
