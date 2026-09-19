export const phase6Markdown = `# TRD Phase 6: Frontend Dashboards & Trạm Điều Hành Giao Dịch Lượng Hóa
## Xây Dựng Trạm Điều Hành Phái Sinh, Radar Dòng Tiền, Bảng Kịch Bản ATC/T+1 & Terminal Giao Dịch Mô Phỏng

> **Tài liệu đặc tả kỹ thuật chi tiết dành cho kỹ sư phát triển frontend & fullstack (Self-Implementation Blueprint)**  
> *Phiên bản: 1.0.0 | Công nghệ: React 18, TanStack Router, TanStack Query, TailwindCSS, Lightweight Charts / Recharts, Lucide Icons.*

---

## 1. TỔNG QUAN & NGUYÊN TẮC THIẾT KẾ (DESIGN PRINCIPLES)

Giao diện người dùng là **trung tâm chỉ huy (Command Center)** hiển thị toàn bộ thành quả phân tích của Tri-Engine và hệ thống mô phỏng.

1. **Aesthetics & Performance First**:
   - Giao diện tài chính chuyên nghiệp phong cách Dark Mode hiện đại (Bloomberg / TradingView style), màu sắc tinh chỉnh theo độ tương phản chuẩn (Bullish: \`#10B981\` Emerald, Bearish: \`#EF4444\` Rose, Warning: \`#F59E0B\` Amber, Accent: \`#6366F1\` Indigo).
   - Biểu đồ nến mượt mà với thư viện \`lightweight-charts\` hoặc \`recharts\` với khả năng render hàng ngàn điểm dữ liệu không giật lag.
2. **Clear Simulation Labeling (Master Rule 2 & 4)**:
   - Mọi khu vực giao dịch, nút bấm, số dư tài khoản đều phải có nhãn cảnh báo trực quan: **\`[MÔ PHỎNG / PAPER TRADING 100%]\`** để người dùng không nhầm lẫn với tài khoản tiền thật.
   - Không chứa bất kỳ liên kết hoặc nút bấm nạp/rút tiền thật nào.
3. **Responsive & Real-time Connectivity**:
   - Tối ưu hiển thị đa thiết bị (Desktop màn hình rộng, Laptop, Tablet, Mobile).
   - Cơ chế tự động cập nhật dữ liệu qua TanStack Query với tần suất đồng bộ theo trạng thái phiên (1s - 5s).

---

## 2. KIẾN TRÚC 4 MÀN HÌNH CỐT LÕI (4 CORE SCREENS)

\`\`\`
+-------------------------------------------------------------------------------+
|                            FRONTEND DASHBOARDS (4 TABS)                       |
+-----------------------+-----------------------+---------------+---------------+
|        TAB 1          |         TAB 2         |     TAB 3     |     TAB 4     |
|  Trạm Phái Sinh Live  |  Radar Dòng Tiền & T+2| Dự Báo ATC/T+1| Paper Cockpit |
+-----------------------+-----------------------+---------------+---------------+
| • Nến 1m/5m VN30F1M   | • Khối ngoại & Tự doan| • Cung cầu ATC| • Đặt lệnh ảo |
| • Orderflow Delta     | • Độ rộng sàn (A/D)   | • Monte Carlo | • Quản lý lệnh|
| • Đồ thị Basis Spread | • Áp lực T+2 chiều    | • Dải P10-P90 | • Danh mục T+2|
| • Tín hiệu Long/Short | • Tỷ giá & Giá Vàng   | • Brier Score | • Ký quỹ PnL  |
+-----------------------+-----------------------+---------------+---------------+
\`\`\`

### 2.1 Tab 1: Trạm Điều Hành Phái Sinh Live (Derivatives Command Station)
- **Mục tiêu**: Giám sát biến động từng phút của hợp đồng \`VN30F1M\` và tín hiệu từ Ensemble Decision System.
- **Các thành phần (Components)**:
  1. \`DerivativesPriceHeader\`: Hiển thị giá hiện tại, thay đổi điểm, % tăng giảm, giá trần/sàn/tham chiếu, Basis hiện hành ($P_{\\text{F1M}} - I_{\\text{VN30}}$).
  2. \`InteractiveCandleChart\`: Biểu đồ nến tương tác (hỗ trợ khung 1m, 5m, 15m), tích hợp đường VWAP và các dải Bollinger Bands.
  3. \`OrderflowDeltaBar\`: Biểu đồ cột thể hiện tương quan Mua chủ động vs. Bán chủ động ($V_{buy} - V_{sell}$) theo từng phút.
  4. \`EnsembleSignalCard\`: Thẻ tín hiệu chiến lược:
     - Badge tín hiệu: \`LONG\`, \`SHORT\`, hoặc \`NEUTRAL\`.
     - Độ tin cậy (Confidence Score): $0\\% \\rightarrow 100\\%$.
     - Vùng giá vào lệnh khuyến nghị (Entry Zone).
     - Mức cắt lỗ động: $\\text{Stop Loss} = \\text{Entry} \\pm k \\times \\text{ATR}_{14}$.
     - Mức chốt lời động: $\\text{Take Profit}$.
     - Đường bám sát Trailing Stop.

### 2.2 Tab 2: Radar Dòng Tiền & Độ Rộng Thị Trường (Flow & Breadth Radar)
- **Mục tiêu**: Bóc tách hành vi của các dòng tiền lớn và dự phóng rủi ro thanh khoản phiên chiều.
- **Các thành phần**:
  1. \`InstitutionalFlowChart\`: Biểu đồ thanh ngang thể hiện giá trị mua/bán ròng của Khối ngoại và Tự doanh trên rổ VN30.
  2. \`MarketBreadthGauge\`: Đồng hồ đo tỷ lệ Cổ phiếu tăng / Cổ phiếu giảm (Advance/Decline Ratio) trên toàn sàn HOSE.
  3. \`TPlus2PressureMeter\`: Thước đo áp lực hàng T+2:
     - Tính toán tỷ lệ lượng hàng bắt đáy phiên $T-2$ có lãi/lỗ và áp lực chốt lời vào 13:00 - 14:15.
  4. \`MacroSummaryTicker\`: Bảng tóm tắt tỷ giá USD/VND (VCB) và giá vàng miếng SJC.

### 2.3 Tab 3: Bảng Kịch Bản Dự Báo ATC & T+1 (ATC & T+1 Prediction Terminal)
- **Mục tiêu**: Cung cấp bức tranh xác suất cho phiên khớp lệnh đóng cửa ATC (14:30 - 14:45) và xu hướng ngày tiếp theo.
- **Các thành phần**:
  1. \`AtcImbalanceMonitor\`: Hiển thị khối lượng khớp dự kiến và độ lệch giá ATO/ATC so với giá trước giờ đấu giá.
  2. \`MonteCarloDistributionChart\`: Đồ thị phân phối xác suất 10,000 kịch bản giá:
     - Thể hiện vùng giá trung vị (P50).
     - Biên độ xác suất $80\\%$ (vùng giữa P10 và P90).
     - Đường giới hạn biên độ trần/sàn $\\pm 7\\%$.
  3. \`ForecastLedgerTable\`: Bảng đối soát các dự báo trong quá khứ kèm kết quả thực tế và điểm Brier Score.

### 2.4 Tab 4: Terminal Giao Dịch Mô Phỏng (Paper Trading Cockpit)
- **Mục tiêu**: Trải nghiệm giao dịch phái sinh và cổ phiếu với số dư ảo 100%, bảo vệ an toàn vốn tuyệt đối.
- **Các thành phần**:
  1. \`VirtualAccountOverview\`: Thẻ thông tin vốn ban đầu, số dư tiền mặt, tỷ lệ ký quỹ đã sử dụng, PnL tạm tính và PnL đã chốt.
  2. \`OrderPlacementForm\`: Form đặt lệnh ảo:
     - Chọn loại hợp đồng (\`VN30F1M\`) hoặc mã cổ phiếu cơ sở.
     - Chọn loại lệnh: \`LO\`, \`MP\`, \`ATO\`, \`ATC\`, \`STOP_LOSS\`.
     - Nhập khối lượng, mức giá đặt và thiết lập Stop Loss / Take Profit tự động.
  3. \`ActivePositionsTable\`: Bảng danh sách vị thế đang mở kèm nút đóng nhanh (Quick Close Position).
  4. \`OrderHistoryTable\`: Bảng lịch sử lệnh (Chờ khớp, Đã khớp, Đã hủy).
  5. \`AlphaBasketsRebalanceCard\`: Bảng danh mục cổ phiếu khuyến nghị theo Tuần / Tháng / Quý kèm nút "Mua theo tỷ trọng ảo".

---

## 3. CẤU TRÚC THƯ MỤC SOURCE CODE FRONTEND

\`\`\`
frontend/src/
├── components/
│   └── trading/
│       ├── DerivativesPriceHeader.tsx
│       ├── InteractiveCandleChart.tsx
│       ├── OrderflowDeltaBar.tsx
│       ├── EnsembleSignalCard.tsx
│       ├── InstitutionalFlowChart.tsx
│       ├── MarketBreadthGauge.tsx
│       ├── TPlus2PressureMeter.tsx
│       ├── MonteCarloDistributionChart.tsx
│       ├── VirtualAccountOverview.tsx
│       ├── OrderPlacementForm.tsx
│       ├── ActivePositionsTable.tsx
│       └── AlphaBasketsRebalanceCard.tsx
├── hooks/
│   ├── useDerivativesLive.ts        # TanStack Query polling 1s dữ liệu VN30F1M
│   ├── useMarketBreadth.ts          # Lấy độ rộng thị trường & dòng tiền
│   ├── useAtcForecast.ts            # Lấy kịch bản dự báo ATC và Monte Carlo
│   └── usePaperTrading.ts           # Quản lý số dư ảo, đặt lệnh, huỷ lệnh
└── routes/_layout/
    ├── trading.tsx                  # Giao diện chính tích hợp 4 Tab
    └── trd/
        ├── phase-1.tsx
        ├── phase-2.tsx
        ├── phase-3.tsx
        ├── phase-4.tsx
        ├── phase-5.tsx
        └── phase-6.tsx              # Trang tài liệu tương tác Phase 6
\`\`\`

---

## 4. HƯỚNG DẪN TỰ CODE TỪNG BƯỚC (6-STEP DEV BLUEPRINT)

Kỹ sư frontend triển khai theo thứ tự sau:

### Bước 1: Cài Đặt Thư Viện Biểu Đồ
Chạy lệnh cài đặt các thư viện cần thiết:
\`\`\`bash
bun add lightweight-charts recharts
\`\`\`

### Bước 2: Tạo Custom Hooks Cho Dữ Liệu
1. Viết hook \`useDerivativesLive(symbol='VN30F1M')\`:
   - Sử dụng \`useQuery\` với \`refetchInterval: 1000\` (1 giây trong phiên liên tục).
   - Tích hợp hàm fallback khi API bị lỗi mạng để không làm vỡ giao diện.
2. Viết hook \`usePaperTrading()\`:
   - Cung cấp mutation \`placeOrderMutation\` gọi \`POST /api/v1/simulation/orders\`.
   - Cung cấp mutation \`cancelOrderMutation\` gọi \`DELETE /api/v1/simulation/orders/{id}\`.

### Bước 3: Xây Dựng Component \`InteractiveCandleChart\`
1. Khởi tạo \`createChart\` từ thư viện \`lightweight-charts\` bên trong thẻ \`<div>\` ref.
2. Thêm Series nến: \`chart.addCandlestickSeries({ upColor: '#10B981', downColor: '#EF4444' })\`.
3. Tích hợp ResizeObserver để biểu đồ tự co giãn theo chiều rộng màn hình.

### Bước 4: Xây Dựng Component \`OrderPlacementForm\`
1. Sử dụng \`react-hook-form\` hoặc state React để quản lý các trường: \`symbol\`, \`side\`, \`price\`, \`volume\`, \`order_type\`.
2. Kiểm tra tính hợp lệ trước khi gửi: Số dư tiền ảo phải đủ ký quỹ 17%.
3. Hiển thị thông báo xác nhận: "Lệnh mô phỏng đã được gửi vào sổ lệnh ảo thành công!" bằng \`sonner\` toast.

### Bước 5: Xây Dựng Component \`MonteCarloDistributionChart\`
1. Sử dụng \`recharts\` dạng \`AreaChart\` với dải tô màu gradient từ P10 đến P90.
2. Đánh dấu mốc giá hiện tại và mốc giá trung vị kỳ vọng P50.
3. Kẻ đường viền màu đỏ/xanh cho biên độ giới hạn trần/sàn +-7%.

### Bước 6: Tích Hợp Vào Route Chính
1. Tạo route \`frontend/src/routes/_layout/trading.tsx\`.
2. Sử dụng component \`Tabs\` từ \`@/components/ui/tabs\` để chuyển đổi giữa 4 màn hình mượt mà.
3. Thêm link điều hướng trên thanh \`Sidebar\` để người dùng dễ dàng truy cập.

---

## 5. TEST MATRIX & TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

| Mã Test | Kịch bản thử nghiệm | Kết quả kỳ vọng |
|---|---|---|
| \`TEST-FE-01\` | Mở màn hình Trạm Phái Sinh trên trình duyệt | Biểu đồ nến tải mượt mà, giá nhảy realtime không bị chớp nháy toàn màn hình |
| \`TEST-FE-02\` | Chuyển đổi khung thời gian nến (1m, 5m, 15m) | Biểu đồ cập nhật lại dữ liệu chuỗi nến đúng khung thời gian tương ứng |
| \`TEST-FE-03\` | Nhập form đặt lệnh Mua 1 hợp đồng VN30F1M | Form hiển thị chính xác số tiền ký quỹ yêu cầu tạm tính ($P \\times 100{,}000 \\times 17\\%$) |
| \`TEST-FE-04\` | Số dư tiền ảo không đủ ký quỹ | Nút đặt lệnh bị vô hiệu hóa kèm tooltip cảnh báo "Số dư khả dụng không đủ" |
| \`TEST-FE-05\` | Đặt lệnh thành công | Danh sách vị thế đang mở và sổ lệnh lập tức refetch và hiển thị lệnh mới |
| \`TEST-FE-06\` | Xem biểu đồ phân phối Monte Carlo | Thấy rõ dải xác suất P10 - P50 - P90 nằm hoàn toàn trong biên trần/sàn +-7% |
| \`TEST-FE-07\` | Kiểm tra độ phản hồi trên màn hình di động (< 768px) | Giao diện tự động xếp chồng theo chiều dọc (stacked layout), không bị tràn ngang |
| \`TEST-FE-08\` | Mất kết nối Internet tạm thời | Giao diện hiển thị badge "Offline / Reconnecting" mà không bị crash trắng trang |
`
