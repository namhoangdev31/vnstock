"""Mô hình chu kỳ thanh toán T+2 và vòng đời tài sản thị trường chứng khoán Việt Nam (SettlementService).

Tuân thủ quy định thị trường chứng khoán Việt Nam (AGENTS §6.1 & §6.2):
- Equities (HOSE, HNX, UPCOM): Chu kỳ T+2.
  * Mua T+0: Tiền bị phong tỏa/trừ tức thì; Cổ phiếu về tài khoản lúc 13:00 ngày T+2.
  * Bán T+0: Cổ phiếu bị trừ tức thì; Tiền bán về tài khoản lúc 13:00 ngày T+2.
- Derivatives (VN30F1M Futures): Chu kỳ T+0.
  * Vị thế có thể mở và đóng trong cùng một phiên giao dịch (Intraday round-trip).
- Lịch nghỉ lễ Việt Nam: Bỏ qua Thứ 7, Chủ Nhật và các ngày nghỉ lễ quốc gia chính thức.
"""

from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Lịch các ngày nghỉ lễ cố định và tiêu biểu tại Việt Nam (Dương lịch & tham chiếu)
# Hỗ trợ mở rộng động hoặc cấu hình qua tham số
VIETNAM_HOLIDAYS_FIXED: set[tuple[int, int]] = {
    (1, 1),  # Tết Dương lịch (1/1)
    (4, 30),  # Ngày Giải phóng miền Nam (30/4)
    (5, 1),  # Ngày Quốc tế Lao động (1/5)
    (9, 2),  # Ngày Quốc khánh (2/9)
    (9, 3),  # Ngày nghỉ kèm Quốc khánh (3/9)
}

# Các ngày nghỉ lễ âm lịch / biến đổi theo năm (Tết Nguyên Đán, Giỗ Tổ Hùng Vương)
# Mở rộng cho các năm 2024, 2025, 2026, 2027
VIETNAM_SPECIAL_HOLIDAYS: set[date] = {
    # Tết Nguyên Đán 2026 (dự kiến Bính Ngọ từ 28 Tết đến Mùng 6)
    date(2026, 2, 14),
    date(2026, 2, 15),
    date(2026, 2, 16),
    date(2026, 2, 17),
    date(2026, 2, 18),
    date(2026, 2, 19),
    date(2026, 2, 20),
    # Nghỉ bù Quốc khánh 2026 (nếu có)
    date(2026, 9, 3),
}


class VietnamHolidayCalendar:
    """Bộ tra cứu ngày lễ thị trường chứng khoán Việt Nam."""

    @classmethod
    def is_holiday(cls, check_date: date) -> bool:
        """Kiểm tra ngày có rơi vào cuối tuần hoặc ngày nghỉ lễ thị trường hay không."""
        return not SettlementService.is_trading_day(check_date)


class SettlementStatus(StrEnum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"


class SettlementService:
    """Bộ xử lý chu kỳ thanh toán bù trừ T+2 và tính toán sức mua tài sản."""

    @classmethod
    def is_trading_day(cls, check_date: date) -> bool:
        """Kiểm tra một ngày có phải là ngày giao dịch hợp lệ của TTCK Việt Nam hay không."""
        # Thứ 7 (5) và Chủ Nhật (6) không giao dịch
        if check_date.weekday() >= 5:
            return False

        # Kiểm tra ngày lễ cố định
        if (check_date.month, check_date.day) in VIETNAM_HOLIDAYS_FIXED:
            return False

        # Kiểm tra ngày lễ đặc thù
        if check_date in VIETNAM_SPECIAL_HOLIDAYS:
            return False

        return True

    @classmethod
    def get_next_trading_day(cls, current_date: date) -> date:
        """Tìm ngày giao dịch kế tiếp."""
        candidate = current_date + timedelta(days=1)
        while not cls.is_trading_day(candidate):
            candidate += timedelta(days=1)
        return candidate

    @classmethod
    def calculate_settlement_date(cls, trade_date: date, cycle_days: int = 2) -> date:
        """Tính ngày thanh toán bù trừ T+N bỏ qua cuối tuần và ngày lễ."""
        settled = trade_date
        added_days = 0
        while added_days < cycle_days:
            settled += timedelta(days=1)
            if cls.is_trading_day(settled):
                added_days += 1
        return settled

    @classmethod
    def get_settlement_exact_time(
        cls, trade_date: date, cycle_days: int = 2
    ) -> datetime:
        """Thời điểm chính xác cổ phiếu/tiền về tài khoản (13:00:00 ngày T+N)."""
        settled_date = cls.calculate_settlement_date(trade_date, cycle_days)
        return datetime.combine(settled_date, time(13, 0, 0), tzinfo=VN_TZ)

    @classmethod
    def evaluate_settlement_status(
        cls,
        trade_time: datetime,
        current_time: datetime,
        asset_type: str = "EQUITY",
    ) -> SettlementStatus:
        """Đánh giá trạng thái thanh toán hiện tại của lệnh."""
        if asset_type.upper() in ("FUTURES", "DERIVATIVE"):
            # Phái sinh VN30F1M thanh toán tức thì T+0
            return SettlementStatus.SETTLED

        # Cổ phiếu cơ sở T+2
        settlement_moment = cls.get_settlement_exact_time(
            trade_time.date(), cycle_days=2
        )
        if current_time >= settlement_moment:
            return SettlementStatus.SETTLED
        return SettlementStatus.PENDING

    @classmethod
    def calculate_purchasing_power(
        cls,
        settled_cash: float,
        pending_cash: float,
        margin_ratio: float = 1.0,
        advance_fee_rate: float = 0.0,
    ) -> dict[str, float]:
        """Tính sức mua khả dụng theo chuẩn nghiệp vụ CTCK (có hỗ trợ ứng trước tiền bán).

        - settled_cash: Tiền mặt khả dụng tức thì (đã thanh toán T+2).
        - pending_cash: Tiền bán đang chờ về (T+1 hoặc sáng T+2).
        - margin_ratio: Tỷ lệ đòn bẩy ký quỹ (mặc định 1.0 = không vay margin).
        - advance_fee_rate: Tỷ lệ phí ứng trước tiền bán (nếu có).
        """
        # Tiền có thể ứng trước (nếu sử dụng dịch vụ ứng trước tiền bán)
        net_advanceable_cash = pending_cash * (1.0 - advance_fee_rate)
        base_purchasing_power = (settled_cash + net_advanceable_cash) * margin_ratio

        return {
            "settled_cash": round(settled_cash, 2),
            "pending_cash": round(pending_cash, 2),
            "net_advanceable_cash": round(net_advanceable_cash, 2),
            "total_purchasing_power": round(max(0.0, base_purchasing_power), 2),
        }
