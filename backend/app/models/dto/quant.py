"""Các đối tượng truyền tải dữ liệu (DTO) cho nghiên cứu định lượng và các động cơ phân tích."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import ForecastDirection, ForecastHorizon

# ==============================================================================
# REQUEST DTOs
# ==============================================================================


class ForecastCreate(SQLModel):
    """Payload ghi nhận một dự phóng mới phát ra từ hệ thống động cơ định lượng."""

    symbol: str = Field(max_length=20)
    horizon: str = Field(default=ForecastHorizon.T_PLUS_1, max_length=20)
    predicted_at: datetime
    predicted_value: float | None = None
    predicted_direction: str = Field(default=ForecastDirection.NEUTRAL, max_length=10)
    engine_weights: dict = Field(default_factory=dict)
    model_version: str = Field(max_length=40)
    parameter_snapshot: dict = Field(default_factory=dict)


class ForecastResolve(SQLModel):
    """Payload ghi nhận kết quả thực tế khi phiên giao dịch kết thúc."""

    actual_value: float
    actual_direction: str = Field(max_length=10)
    realized_at: datetime | None = None


class EnsembleSignalRequest(SQLModel):
    """Payload yêu cầu dự phóng Ensemble hợp nhất và tự động ghi sổ cái."""

    symbol: str = Field(default="VN30F1M", max_length=20)
    horizon: str = Field(default=ForecastHorizon.INTRADAY, max_length=20)
    custom_weights: dict | None = None


class EnsembleWeightsUpdate(SQLModel):
    """Payload điều chỉnh trọng số thủ công cho các động cơ."""

    w1: float = Field(ge=0.0, le=1.0)
    w2: float = Field(ge=0.0, le=1.0)
    w3: float = Field(ge=0.0, le=1.0)


# ==============================================================================
# RESPONSE DTOs
# ==============================================================================


class MacroIndicatorPublic(SQLModel):
    """Chỉ số kinh tế vĩ mô (vàng, tỷ giá USD/VND)."""

    indicator_code: str
    recorded_date: date
    value: float
    change_pct: float | None = None
    source: str


class MacroLatestResponse(SQLModel):
    """Ảnh chụp nhanh các chỉ số vĩ mô mới nhất."""

    as_of: date
    data: list[MacroIndicatorPublic]


class SymbolGroupResponse(SQLModel):
    """Danh sách các mã thành viên thuộc một rổ chỉ số (VN30, VN100,...)."""

    group: str
    count: int
    symbols: list[str]


class ForecastJournalPublic(SQLModel):
    """Bản ghi sổ cái dự phóng phục vụ kiểm toán và đánh giá hiệu năng."""

    id: uuid.UUID
    symbol: str
    horizon: str
    predicted_at: datetime
    predicted_value: float | None = None
    predicted_direction: str
    engine_weights: dict
    model_version: str
    parameter_snapshot: dict
    actual_value: float | None = None
    actual_direction: str | None = None
    realized_at: datetime | None = None
    error: float | None = None
    score: float | None = None
    status: str


class ForecastScoredPublic(SQLModel):
    """Kết quả chấm điểm sai số của dự phóng."""

    id: uuid.UUID
    error: float | None = None
    score: float | None = None
    status: str


class ForecastAggregateResponse(SQLModel):
    """Tổng hợp chỉ số chính xác (MAE, Tỷ lệ dự đoán đúng hướng) của mô hình."""

    count: int
    mae: float | None = None
    directional_accuracy: float | None = None
    scored_with_error: int


class InstitutionalFlowPublic(SQLModel):
    """Thông tin giao dịch của Khối ngoại và Tự doanh."""

    trading_date: date
    symbol: str
    foreign_buy_volume: int | None = None
    foreign_sell_volume: int | None = None
    foreign_net_volume: int | None = None
    foreign_buy_value: float | None = None
    foreign_sell_value: float | None = None
    foreign_net_value: float | None = None
    foreign_room_total: float | None = None
    foreign_room_current: float | None = None
    foreign_room_pct: float | None = None
    prop_buy_volume: int | None = None
    prop_sell_volume: int | None = None
    prop_net_volume: int | None = None
    prop_buy_value: float | None = None
    prop_sell_value: float | None = None
    prop_net_value: float | None = None
    source: str


class TechnicalEngineResponse(SQLModel):
    """Dữ liệu đầu ra của Động cơ 1: Kỹ thuật, Price Action & Khớp lệnh Tick."""

    symbol: str
    as_of: datetime
    score: float  # -1.0 đến +1.0
    rsi: float | None = None
    macd: dict = Field(default_factory=dict)
    vwap: float | None = None
    order_imbalance: float = 0.0  # -1.0 đến +1.0
    volume_delta: int = 0
    camarilla_levels: dict = Field(default_factory=dict)
    fvg_detected: bool = False
    fvg_details: dict = Field(default_factory=dict)
    liquidity_sweeps: dict = Field(default_factory=dict)


class FlowLiquidityEngineResponse(SQLModel):
    """Dữ liệu đầu ra của Động cơ 2: Thanh khoản, Dòng tiền tổ chức & Áp lực T+2."""

    as_of: datetime
    score: float  # -1.0 đến +1.0
    institutional_momentum: float = 0.0
    market_breadth: float | None = None
    t2_pressure: float = 0.0  # 0.0 đến 1.0
    macro_sentiment: float = 0.0


class QuantMLEngineResponse(SQLModel):
    """Dữ liệu đầu ra của Động cơ 3: Thống kê định lượng, Chênh lệch Basis & Monte Carlo."""

    symbol: str
    as_of: datetime
    score: float  # -1.0 đến +1.0
    basis_value: float = 0.0
    basis_zscore: float = 0.0
    historical_vol: float = 0.0
    parkinson_vol: float = 0.0
    session_phase: str = "CONTINUOUS"
    monte_carlo_targets: dict = Field(default_factory=dict)


class EnsembleSignalResponse(SQLModel):
    """Dữ liệu đầu ra của Hệ thống Hợp nhất Quyết định Ensemble đính kèm cảnh báo rủi ro."""

    journal_id: uuid.UUID
    symbol: str
    horizon: str
    predicted_at: datetime
    predicted_direction: str  # "LONG", "SHORT", "NEUTRAL"
    ensemble_score: float  # -1.0 đến +1.0
    confidence: float  # 0.0 đến 1.0
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    engine_weights: dict
    engine_scores: dict
    model_version: str = "v2.0.0"
    disclaimer: str = (
        "CẢNH BÁO RỦI RO (RULE 4): Tín hiệu mô phỏng định lượng mang tính chất tham khảo "
        "và nghiên cứu giáo dục, không phải là lời khuyên đầu tư tài chính hay khuyến nghị đặt lệnh."
    )


class EnsembleWeightsResponse(SQLModel):
    """Cấu trúc trọng số động theo thời gian phiên giao dịch hiện tại."""

    session_phase: str
    current_time_utc: datetime
    weights: dict
    schedule: dict
