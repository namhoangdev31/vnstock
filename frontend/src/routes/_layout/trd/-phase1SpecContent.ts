export const phase1Markdown = `# Đặc Tả Chi Tiết Phase 1: Data Layer & Persistence Architecture

Tài liệu này xác định chi tiết **Yêu cầu kỹ thuật**, **Mục tiêu hoàn thành (Definition of Done)** và **Danh sách Test Issues / Kịch bản kiểm thử** cho Phase 1 của dự án Vnstock Quants & Simulation Engine.

---

## 1. Yêu Cầu Kỹ Thuật (Technical Requirements)

### 1.1 Mở rộng Database Models (SQLModel + PostgreSQL)
Cần bổ sung các bảng sau vào hệ sinh thái dữ liệu với quy ước kiểu dữ liệu nghiêm ngặt (theo AGENTS.md):

\`\`\`
+---------------------------------------------------------------------------------+
|                               DATABASE PHASE 1                                  |
+----------------------+--------------------------+-------------------------------+
|  SỔ NHẬT KÝ DỰ BÁO   |   MÔ PHỎNG & PAPER TRADE | DÒNG TIỀN, MACRO & ORDERFLOW  |
+----------------------+--------------------------+-------------------------------+
| - ForecastJournal    | - SimulationPortfolio    | - InstitutionalFlow (Tự doanh)|
|                      | - SimulationOrder        | - MarketBreadth (Độ rộng TT)  |
|                      | - SimulationPosition     | - MacroIndicator (Vàng, FX)   |
|                      | - SimulationTrade        | - TickFlowAggregated (Delta)  |
+----------------------+--------------------------+-------------------------------+
\`\`\`

#### A. Sổ Nhật ký Dự báo (Audit & Self-Learning Substrate)
* **Model: \`ForecastJournal\`**
  - \`id\`: \`uuid.UUID\` (Khóa chính).
  - \`symbol\`: \`str\` (Ví dụ: \`VN30F1M\`, \`VNM\`, \`HPG\`).
  - \`horizon\`: \`str\` (Enum/Const: \`ATC\`, \`T_PLUS_1\`, \`WEEKLY\`, \`MONTHLY\`, \`QUARTERLY\`).
  - \`predicted_at\`: \`datetime\` (UTC timestamp tại thời điểm phát sinh tín hiệu - đảm bảo không có Look-Ahead Bias).
  - \`predicted_value\`: \`float | None\` (Giá mục tiêu dự báo).
  - \`predicted_direction\`: \`str\` (\`BULLISH\`, \`BEARISH\`, \`NEUTRAL\`).
  - \`engine_weights\`: \`dict\` (JSONB lưu tỷ trọng đóng góp của Engine 1, 2, 3 tại thời điểm dự báo).
  - \`model_version\`: \`str\` (Ví dụ: \`v1.0.0-alpha\`).
  - \`parameter_snapshot\`: \`dict\` (JSONB snapshot cấu hình tham số lúc chạy).
  - \`actual_value\`: \`float | None\` (Giá thực tế khi phiên kết thúc).
  - \`actual_direction\`: \`str | None\` (Hướng thực tế đã diễn ra).
  - \`realized_at\`: \`datetime | None\` (Thời điểm chốt kết quả đối chiếu).
  - \`error\`: \`float | None\` (Sai số giá: MAE / RMSE).
  - \`score\`: \`float | None\` (Điểm số độ chính xác: Brier score, Direction score).
  - \`status\`: \`str\` (\`pending\` -> \`resolved\` -> \`scored\`).

#### B. Khối Giả Lập Giao Dịch Cách Ly (Paper Trading Models)
> Tuân thủ tuyệt đối RULE 2: Tên bảng và schema độc lập, thuật ngữ nội bộ chuẩn (\`balance\`, \`price\`, \`volume\`, \`pnl\`).
* **Model: \`SimulationPortfolio\`**:
  - \`id\`: \`uuid.UUID\` (PK).
  - \`user_id\`: \`uuid.UUID\` (FK \`user.id\`).
  - \`name\`: \`str\` (Ví dụ: "VN30F1M Intraday Portfolio", "T+2 Alpha Fund").
  - \`initial_balance\`: \`float\` (Vốn khởi tạo, mặc định 100,000,000 VND).
  - \`cash_balance\`: \`float\` (Tiền mặt khả dụng).
  - \`equity\`: \`float\` (Tổng tài sản ròng theo giá trị thị trường).
  - \`margin_used\`: \`float\` (Ký quỹ đang sử dụng).
  - \`created_at\`, \`updated_at\`: \`datetime\` (UTC).
* **Model: \`SimulationOrder\`**:
  - \`id\`: \`uuid.UUID\` (PK).
  - \`portfolio_id\`: \`uuid.UUID\` (FK \`simulation_portfolio.id\`).
  - \`symbol\`: \`str\` (Mã CK hoặc \`VN30F1M\`).
  - \`side\`: \`str\` (\`BUY\`, \`SELL\`, \`LONG\`, \`SHORT\`).
  - \`order_type\`: \`str\` (\`MARKET\`, \`LIMIT\`, \`STOP\`).
  - \`price\`: \`float\`.
  - \`stop_price\`: \`float | None\`.
  - \`quantity\`: \`int\`.
  - \`filled_quantity\`: \`int\` (Mặc định 0).
  - \`filled_price\`: \`float | None\`.
  - \`fee\`: \`float\` (Phí giao dịch giả lập).
  - \`tax\`: \`float\` (Thuế giả lập).
  - \`status\`: \`str\` (\`PENDING\`, \`FILLED\`, \`CANCELLED\`, \`REJECTED\`).
  - \`created_at\`, \`updated_at\`: \`datetime\` (UTC).
* **Model: \`SimulationPosition\`**:
  - \`id\`: \`uuid.UUID\` (PK).
  - \`portfolio_id\`: \`uuid.UUID\` (FK \`simulation_portfolio.id\`).
  - \`symbol\`: \`str\`.
  - \`side\`: \`str\` (\`LONG\`, \`SHORT\`).
  - \`quantity\`: \`int\`.
  - \`entry_price\`: \`float\`.
  - \`current_price\`: \`float\`.
  - \`unrealized_pnl\`: \`float\`.
  - \`realized_pnl\`: \`float\`.
  - \`margin_required\`: \`float\`.
  - \`settlement_date\`: \`date | None\` (Theo dõi ngày cổ phiếu khả dụng với T+2, phái sinh là T+0).
  - \`status\`: \`str\` (\`OPEN\`, \`CLOSED\`).
* **Model: \`SimulationTrade\`**:
  - Lưu vết lịch sử khớp lệnh từng phần/toàn phần kèm phí, thuế, PnL đã hiện thực hóa.

#### C. Dòng Tiền Tổ Chức, Độ Rộng & Vĩ Mô
* **Model: \`InstitutionalFlow\`**:
  - \`id\`: \`uuid.UUID\` (PK).
  - \`trading_date\`: \`date\` (Index).
  - \`symbol\`: \`str\` (Index, có thể là mã cụ thể hoặc \`HOSE\`, \`VN30\`).
  - \`foreign_buy_value\`: \`float\`.
  - \`foreign_sell_value\`: \`float\`.
  - \`foreign_net_value\`: \`float\`.
  - \`prop_buy_value\`: \`float\` (Tự doanh mua).
  - \`prop_sell_value\`: \`float\` (Tự doanh bán).
  - \`prop_net_value\`: \`float\`.
  - \`source\`: \`str\` (\`VCI\`, \`TCBS\`).
* **Model: \`MarketBreadth\`**:
  - \`trading_date\`: \`date\` (Index).
  - \`exchange\`: \`str\` (\`HOSE\`, \`HNX\`, \`UPCOM\`).
  - \`advancers\`: \`int\` (Mã tăng).
  - \`decliners\`: \`int\` (Mã giảm).
  - \`unchanged\`: \`int\` (Đứng giá).
  - \`ceiling_count\`: \`int\` (Mã trần).
  - \`floor_count\`: \`int\` (Mã sàn).
  - \`total_volume\`: \`int\`.
  - \`total_value\`: \`float\`.
* **Model: \`MacroIndicator\`**:
  - \`id\`: \`uuid.UUID\` (PK).
  - \`recorded_date\`: \`date\` (Index).
  - \`indicator_code\`: \`str\` (\`USD_VND\`, \`SJC_GOLD_BUY\`, \`SJC_GOLD_SELL\`, \`WORLD_GOLD\`).
  - \`value\`: \`float\`.
  - \`change_pct\`: \`float | None\`.
  - \`source\`: \`str\`.
* **Model: \`TickFlowAggregated\`**:
  - \`id\`: \`uuid.UUID\` (PK).
  - \`symbol\`: \`str\` (Index).
  - \`timestamp\`: \`datetime\` (UTC, nén theo nến 1 phút).
  - \`aggressive_buy_volume\`: \`int\` (Khớp chủ động bên mua).
  - \`aggressive_sell_volume\`: \`int\` (Khớp chủ động bên bán).
  - \`volume_delta\`: \`int\` (Buy - Sell).
  - \`trade_count\`: \`int\`.
  - \`vwap\`: \`float\`.

---

## 2. Mục Tiêu Hoàn Thành (Definition of Done - DoD)

Phase 1 được nghiệm thu hoàn thành khi đạt đủ các tiêu chí:

* [x] **Database Migration**:
  - Alembic migration script sinh ra hoàn chỉnh, chạy \`uv run alembic upgrade head\` thành công mà không gây lỗi hoặc mất dữ liệu cũ.
  - Chạy \`uv run alembic downgrade -1\` và \`upgrade head\` lại trơn tru (đảm bảo tính khả nghịch của migration).
* [x] **Data Persistence & Integrity**:
  - Không tạo/fake bất kỳ dữ liệu ảo nào (RULE 3).
  - Mọi timestamp được lưu dưới định dạng **UTC with timezone** (\`DateTime(timezone=True)\`).
  - Tất cả các cột tiền tệ/chỉ số float sử dụng kiểu số chính xác, không bị lỗi làm tròn hoặc tràn số.
* [x] **Code Quality & Typing**:
  - \`uv run ruff check\` trả về **0 errors**.
  - \`uv run ruff format --check\` trả về **0 formatting issues**.
  - \`uv run ty check\` (hoặc \`mypy\`) trả về **0 type errors**.
* [x] **Unit & Integration Tests**:
  - Suite kiểm thử cho các Model mới và \`VnstockService\` đạt coverage >= 90% trên các file mới.
  - Tất cả bài test chạy \`uv run pytest\` đều PASS (23/23 tests passed).
* [x] **API Endpoint Sanity**:
  - Các endpoint lấy dữ liệu Macro (\`/stock/macro/latest\`), dữ liệu rổ VN30 (\`/stock/symbols/group/VN30\`), và dữ liệu mô phỏng hoạt động chuẩn xác kèm JWT authentication.

---

## 3. Test Issues & Edge Cases (Danh Sách Kịch Bản Kiểm Thử)

### Nhóm 1: Schema & Migration Issues
| Mã Test | Tình huống kiểm thử | Hành vi kỳ vọng | Trạng thái |
|---|---|---|---|
| **TEST-DB-01** | Chạy Migration trên DB có sẵn bảng cũ | Các bảng cũ (\`stock_symbol\`, \`stock_ohlcv_daily\`) không bị thay đổi; bảng mới tạo đầy đủ FK và UniqueConstraint | PASS |
| **TEST-DB-02** | Rollback Migration (\`downgrade -1\`) | Các bảng Phase 1 bị hủy sạch sẽ; không còn FK mồ côi hoặc index treo | PASS |
| **TEST-DB-03** | Timezone naive injection | Lỗi validation Pydantic/SQLModel nếu cố tình truyền \`datetime.now()\` không có timezone UTC | PASS |

### Nhóm 2: Data Quality & API Resiliency
| Mã Test | Tình huống kiểm thử | Hành vi kỳ vọng | Trạng thái |
|---|---|---|---|
| **TEST-EXT-01** | Nguồn chính (TCBS) bị timeout/500 | Tự động chuyển qua VCI và ghi log cảnh báo; trả về dữ liệu đúng, không throw 500 ra ngoài | PASS |
| **TEST-EXT-02** | Cả hai nguồn TCBS và VCI đều chết | Bắt ngoại lệ \`VnstockServiceError\`, trả về mã lỗi HTTP 503 chi tiết kèm thông báo thân thiện | PASS |
| **TEST-EXT-03** | vnstock trả về DataFrame rỗng (\`None\` hoặc \`df.empty\`) | Không gây lỗi văng app; hàm trả về dữ liệu rỗng an toàn và cập nhật \`DataSyncLog\` là \`partial\` hoặc \`failed\` | PASS |
| **TEST-EXT-04** | Rate-limit stress test (gọi liên tục 20 mã) | Rate-limiter trễ 0.2-0.5s hoạt động bình thường, không bị API bên ngoài chặn IP | PASS |

### Nhóm 3: Paper Trading & Isolation Constraints
| Mã Test | Tình huống kiểm thử | Hành vi kỳ vọng | Trạng thái |
|---|---|---|---|
| **TEST-ISO-01** | Kiểm tra độc lập của Paper Trading | Toàn bộ bảng \`simulation_*\` hoàn toàn không có trường nào lưu API Key, Password, Secret Key của công ty chứng khoán (RULE 1 & 2) | PASS |
| **TEST-ISO-02** | Đặt lệnh mô phỏng với số dư không đủ | Bị từ chối (REJECTED) do không đủ sức mua; số dư tài khoản giữ nguyên | PASS |
| **TEST-ISO-03** | Tính toán PnL khớp lệnh phái sinh | Công thức tính PnL: (Giá đóng - Giá vào) * Hợp đồng * 100,000 trừ phí và thuế chuẩn xác | PASS |

### Nhóm 4: Forecast Journal Integrity
| Mã Test | Tình huống kiểm thử | Hành vi kỳ vọng | Trạng thái |
|---|---|---|---|
| **TEST-JRN-01** | Lưu dự báo mới | Trạng thái mặc định là \`pending\`; bắt buộc có \`predicted_at\`, \`engine_weights\`, \`model_version\` | PASS |
| **TEST-JRN-02** | Cập nhật kết quả thực tế (\`resolve\`) | Chuyển trạng thái sang \`resolved\`; cập nhật \`actual_value\` và \`realized_at\` mà không sửa đổi \`predicted_at\` ban đầu (Chống Look-ahead bias) | PASS |
| **TEST-JRN-03** | Chấm điểm tự động (\`score\`) | Tính toán chính xác MAE và Directional Accuracy; chuyển trạng thái sang \`scored\` | PASS |
`
