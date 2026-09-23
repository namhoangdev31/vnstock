"""Các hằng số cấu hình, bảng tra cứu và danh sách trường cập nhật (Conflict Fields) cho DataSyncManager.

Tách riêng để tối ưu kiến trúc, giữ cho mã nguồn dịch vụ sync_service ngắn gọn và dễ bảo trì.
"""

from __future__ import annotations

from datetime import date

# Bảng tra cứu & thiết lập cấu hình định danh
# LƯU Ý: "UPCOM" bị loại bỏ — vnstock v4 từ chối tên sàn làm symbol giao dịch.
STANDARD_INDEXES: frozenset[str] = frozenset(
    {"VNINDEX", "VN30", "HNX", "HNX30"}
)

BOND_TYPE_CONFIG: dict[str, tuple[str, str]] = {
    "corporate": ("Trái phiếu DN", "corporate_bond"),
    "government": ("Trái phiếu Chính phủ", "government_bond"),
}

META_FINANCIAL_KEYS: frozenset[str] = frozenset(
    {"year", "yearReport", "quarter", "lengthReport", "ticker", "symbol"}
)

# Cấu hình danh sách trường cập nhật (Conflict Update Fields) cho từng Entity
STOCK_SYMBOL_UPDATE_FIELDS: list[str] = [
    "organ_name",
    "exchange",
    "industry",
    "icb_code",
    "icb_name",
    "asset_type",
    "lot_size",
    "is_active",
    "updated_at",
]

CW_STOCK_SYMBOL_UPDATE_FIELDS: list[str] = [
    "organ_name",
    "exchange",
    "industry",
    "asset_type",
    "lot_size",
    "is_active",
    "updated_at",
]

DERIV_STOCK_SYMBOL_UPDATE_FIELDS: list[str] = [
    "organ_name",
    "exchange",
    "industry",
    "asset_type",
    "lot_size",
    "is_active",
    "updated_at",
]

DERIVATIVE_CONTRACT_UPDATE_FIELDS: list[str] = [
    "underlying_symbol",
    "multiplier",
    "expiration_date",
    "is_active",
    "updated_at",
]

COVERED_WARRANT_UPDATE_FIELDS: list[str] = [
    "underlying_symbol",
    "issuer_name",
    "warrant_type",
    "exercise_price",
    "conversion_ratio",
    "exercise_ratio",
    "issue_date",
    "maturity_date",
    "last_trading_date",
    "settlement_type",
    "is_active",
    "updated_at",
]

BOND_SPECIFICATION_UPDATE_FIELDS: list[str] = [
    "bond_type",
    "issuer_symbol",
    "issuer_name",
    "par_value",
    "coupon_rate",
    "coupon_type",
    "tenor_years",
    "issue_date",
    "maturity_date",
    "is_active",
    "updated_at",
]

DAILY_OHLCV_UPDATE_FIELDS: list[str] = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "value",
    "open_interest",
    "basis",
    "source",
]

INTRADAY_OHLCV_UPDATE_FIELDS: list[str] = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
]

COMPANY_PROFILE_UPDATE_FIELDS: list[str] = [
    "company_name",
    "short_name",
    "industry_name",
    "established_date",
    "listed_date",
    "charter_capital",
    "outstanding_shares",
    "market_cap",
    "free_float_pct",
    "foreign_ownership_pct",
    "max_foreign_ownership_pct",
    "employee_count",
    "website",
    "address",
    "ceo_name",
    "auditor",
    "description",
    "updated_at",
]

FINANCIAL_REPORT_UPDATE_FIELDS: list[str] = [
    "report_scope",
    "is_audited",
    "revenue",
    "gross_profit",
    "operating_profit",
    "net_profit_parent",
    "total_assets",
    "short_term_assets",
    "cash_and_equivalents",
    "total_liabilities",
    "short_term_debt",
    "long_term_debt",
    "owners_equity",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "data",
    "source",
    "updated_at",
]

FINANCIAL_RATIO_UPDATE_FIELDS: list[str] = [
    "pe",
    "pb",
    "ps",
    "roe",
    "roa",
    "roic",
    "eps",
    "bvps",
    "gross_margin",
    "net_margin",
    "debt_to_equity",
    "quick_ratio",
    "current_ratio",
    "dividend_yield",
    "ev_to_ebitda",
    "ev_to_ebit",
    "p_to_fcf",
    "p_to_ocf",
    "fcf",
    "ebit_margin",
    "ebitda_margin",
    "asset_turnover",
    "inventory_turnover",
    "receivables_turnover",
    "debt_to_assets",
    "interest_coverage",
    "cash_ratio",
    "revenue_growth_yoy",
    "net_profit_growth_yoy",
    "revenue_growth_qoq",
    "net_profit_growth_qoq",
    "data",
    "source",
    "updated_at",
]

INSTITUTIONAL_FLOW_UPDATE_FIELDS: list[str] = [
    "foreign_buy_volume",
    "foreign_sell_volume",
    "foreign_net_volume",
    "foreign_buy_value",
    "foreign_sell_value",
    "foreign_net_value",
    "foreign_room_total",
    "foreign_room_current",
    "foreign_room_pct",
    "prop_buy_volume",
    "prop_sell_volume",
    "prop_net_volume",
    "prop_buy_value",
    "prop_sell_value",
    "prop_net_value",
]

COMPANY_SHAREHOLDER_UPDATE_FIELDS: list[str] = [
    "share_count",
    "ownership_pct",
    "is_institutional",
    "is_foreign",
    "is_state",
    "updated_at",
]

COMPANY_OFFICER_UPDATE_FIELDS: list[str] = [
    "share_count",
    "ownership_pct",
    "updated_at",
]

CORPORATE_EVENT_UPDATE_FIELDS: list[str] = [
    "event_title",
    "record_date",
    "effective_date",
    "cash_rate",
    "stock_rate",
    "ratio_string",
    "notes",
    "details",
    "source",
]

INDEX_CONSTITUENT_UPDATE_FIELDS: list[str] = [
    "weight",
    "free_float_shares",
    "updated_at",
]

COMPANY_SUBSIDIARY_UPDATE_FIELDS: list[str] = [
    "organ_name",
    "ownership_percent",
    "updated_at",
]

INSIDER_TRADING_UPDATE_FIELDS: list[str] = [
    "officer_position",
    "deal_quantity",
    "deal_price",
    "deal_ratio",
    "updated_at",
]

CAPITAL_HISTORY_UPDATE_FIELDS: list[str] = [
    "shares_issued",
    "description",
    "updated_at",
]


def get_third_thursday(year: int, month: int) -> date:
    """Tính ngày Thứ Năm lần thứ 3 trong tháng (ngày đáo hạn hợp đồng phái sinh VN30)."""
    first_day = date(year, month, 1)
    days_to_thursday = (3 - first_day.weekday()) % 7
    first_thursday = first_day.day + days_to_thursday
    return date(year, month, first_thursday + 14)


__all__ = [
    "BOND_SPECIFICATION_UPDATE_FIELDS",
    "BOND_TYPE_CONFIG",
    "CAPITAL_HISTORY_UPDATE_FIELDS",
    "COMPANY_OFFICER_UPDATE_FIELDS",
    "COMPANY_PROFILE_UPDATE_FIELDS",
    "COMPANY_SHAREHOLDER_UPDATE_FIELDS",
    "COMPANY_SUBSIDIARY_UPDATE_FIELDS",
    "CORPORATE_EVENT_UPDATE_FIELDS",
    "COVERED_WARRANT_UPDATE_FIELDS",
    "CW_STOCK_SYMBOL_UPDATE_FIELDS",
    "DAILY_OHLCV_UPDATE_FIELDS",
    "DERIVATIVE_CONTRACT_UPDATE_FIELDS",
    "DERIV_STOCK_SYMBOL_UPDATE_FIELDS",
    "FINANCIAL_RATIO_UPDATE_FIELDS",
    "FINANCIAL_REPORT_UPDATE_FIELDS",
    "INDEX_CONSTITUENT_UPDATE_FIELDS",
    "INSIDER_TRADING_UPDATE_FIELDS",
    "INSTITUTIONAL_FLOW_UPDATE_FIELDS",
    "INTRADAY_OHLCV_UPDATE_FIELDS",
    "META_FINANCIAL_KEYS",
    "STANDARD_INDEXES",
    "STOCK_SYMBOL_UPDATE_FIELDS",
    "get_third_thursday",
]
