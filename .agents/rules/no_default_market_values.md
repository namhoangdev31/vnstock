# Rule: Zero Default Values & Zero Mock Fallbacks for Market Data

## 1. Prime Directive
Mọi số liệu tài chính, chỉ số thị trường, giá cổ phiếu, khối lượng giao dịch, giá trị thanh khoản, độ rộng thị trường (market breadth), sổ lệnh (order book), tỷ lệ khớp lệnh mua/bán và báo cáo tài chính **BẮT BUỘC 100% PHẢI XUẤT PHÁT TỪ DỮ LIỆU THỰC TẾ** (từ cơ sở dữ liệu PostgreSQL hoặc adapter `vnstock`).

## 2. Các Hành Vi Nghiêm Cấm Tuyệt Đối (Zero Tolerance)
1. **Không Đặt Default Value Tĩnh**:
   - Nghiêm cấm gán các số mặc định tĩnh (hardcoded default values / fallback constants) như `raw_vol = 829_390_000`, `val_num = 19_176.09`, `price = 51477.0`, hoặc tạo mảng điểm nến giả lập để lấp vào chỗ thiếu dữ liệu.
2. **Không Viết Hàm Kẹp Ngưỡng Cưỡng Bức (No Clamping Overrides)**:
   - Tuyệt đối cấm các khối điều kiện kiểm tra ngưỡng để ghi đè số thực bằng số mẫu:
     ```python
     # HÀNH VI BỊ CẤM:
     if val_num > 35_000 or val_num < 5_000:
         val_num = 19_176.09
     ```
3. **Không Giả Lập Sổ Lệnh Hoặc Tỷ Lệ Mua/Bán Khi Không Có Nguồn**:
   - Nếu không có dữ liệu tick khớp lệnh hoặc sổ lệnh L2/L3 thật, không được tự ý cộng trừ bước giá và nhân tỷ lệ volume để chế ra sổ lệnh giả.
4. **Không Tạo Dữ Liệu Mock Mẫu Ở Frontend Để Thay Thế Trạng Thái Thiếu**:
   - Phía Frontend không tạo các mảng hằng số (như `defaultIndices = [...]` với giá 1,875.99, 10,272 Tỷ...) để giả bộ hệ thống đã có dữ liệu. Nếu chưa có dữ liệu, hiển thị skeleton loading hoặc `"-"`.

## 3. Quy Trình Xử Lý Khi Dữ Liệu Bị Rỗng Hoặc Lỗi
- **Backend**:
  - Trả về `None`, `null`, `0` hoặc chuỗi rỗng `"-"`.
  - Ghi log rõ ràng (`logger.warning` / `logger.info`) nêu rõ nguyên nhân thiếu dữ liệu để hỗ trợ debug hoặc kích hoạt pipeline đồng bộ dữ liệu.
- **Frontend**:
  - Hiển thị trạng thái loading, skeleton hoặc ký hiệu `-` (ví dụ: `volume: '-'`, `value: '-'`, `N/A`).
