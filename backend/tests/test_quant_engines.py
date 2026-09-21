"""Bộ kiểm thử đơn vị toàn diện cho các Động cơ Định lượng Phase 2 & Bộ Hợp nhất Tín hiệu.

Kiểm chứng toàn bộ các kịch bản kiểm thử đã định nghĩa trong Ma trận Test TRD Phase 2:
- Engine 1: RSI, MACD, Bollinger Bands, ATR, VWAP an toàn khi volume = 0, Orderflow Delta,
            Order Imbalance 100% mua chủ động, FVG, Quét thanh khoản (Sweeps), nến Doji.
- Engine 2: Fallback khi thiếu số liệu tự doanh (Rule 3), độ rộng thị trường 100% mã giảm,
            Lịch thanh toán T+2 Việt Nam, áp lực xả hàng T+2, tác động tỷ giá USD/VND.
- Engine 3: Chênh lệch Basis & Z-Score, Tín hiệu đảo chiều Mean-Reversion, biến động Parkinson,
            Dự báo phiên ATC, Mô phỏng Monte Carlo 1,000 kịch bản trong biên độ trần/sàn ±7%.
- Ensemble: Tự động chuẩn hóa trọng số, Triệt tiêu xung đột tín hiệu, Ngưỡng phân loại xu hướng,
            Stop Loss / Take Profit động với R:R >= 1:2.0, Tự động ghi sổ ForecastJournal (Rule 3),
            và Thông báo cảnh báo rủi ro (Rule 4).
"""

from datetime import date

import pandas as pd
import pytest
from sqlmodel import Session, create_engine

from app.models.enums import ForecastDirection, ForecastHorizon, ForecastStatus
from app.models.models_base import AwareSQLModel
from app.models.models_quant import (
    EnsembleSignalRequest,
    ForecastJournal,
    InstitutionalFlow,
    MacroIndicator,
    MarketBreadth,
)
from app.services.quant.ensemble_engine import EnsembleEngine
from app.services.quant.flow_engine import FlowLiquidityEngine
from app.services.quant.indicators import (
    compute_macd,
    compute_parkinson_volatility,
    compute_rsi,
    compute_vwap,
)
from app.services.quant.quant_ml_engine import QuantMLEngine
from app.services.quant.technical_engine import TechnicalEngine


# Fixture tạo database SQLite in-memory phục vụ kiểm thử đơn vị thuần túy không phụ thuộc PostgreSQL
@pytest.fixture(name="sqlite_session")
def sqlite_session_fixture():
    engine = create_engine("sqlite:///:memory:")
    AwareSQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ===========================================================================
# NHÓM 1: ENGINE 1 (PHÂN TÍCH KỸ THUẬT & DÒNG LỆNH)
# ===========================================================================


def test_e1_01_rsi_macd_calculation():
    """TEST-E1-01: Kiểm tra tính toán RSI 14 & MACD (12, 26, 9) trên chuỗi nến chuẩn."""
    # Chuỗi giá tăng liên tục mô phỏng xu hướng tăng mạnh
    closes = [100.0 + i * 1.5 for i in range(40)]
    rsi = compute_rsi(closes, period=14)
    macd = compute_macd(closes, fast=12, slow=26, signal=9)

    assert rsi is not None
    assert 50.0 < rsi <= 100.0  # Xu hướng tăng mạnh thì RSI phải ở mức cao
    assert macd["dif"] > 0.0
    assert macd["hist"] != 0.0


def test_e1_02_vwap_multi_timeframe():
    """TEST-E1-02: Kiểm tra công thức tính giá bình quân VWAP đa khung nến trong ngày."""
    prices = [1280.0, 1282.0, 1285.0, 1283.0]
    volumes = [100.0, 200.0, 300.0, 400.0]
    vwap = compute_vwap(prices, volumes)

    assert vwap is not None
    # Bình quân gia quyền: (1280*100 + 1282*200 + 1285*300 + 1283*400) / 1000 = 1283.10
    expected = (1280 * 100 + 1282 * 200 + 1285 * 300 + 1283 * 400) / 1000.0
    assert abs(vwap - expected) < 0.01


def test_e1_03_vwap_zero_volume_safety():
    """TEST-E1-03: Dữ liệu nến có khối lượng bằng 0 tuyệt đối KHÔNG được ném ngoại lệ chia cho 0."""
    prices = [1280.0, 1282.0, 1285.0]
    volumes = [0.0, 0.0, 0.0]
    vwap = compute_vwap(prices, volumes)

    # Cơ chế phòng hộ: trả về mức giá đóng cửa gần nhất
    assert vwap == 1285.0


def test_e1_04_orderflow_delta():
    """TEST-E1-04: Tính toán chênh lệch dòng lệnh Orderflow Delta = Mua chủ động - Bán chủ động."""
    engine = TechnicalEngine()
    df_ticks = pd.DataFrame(
        {
            "match_type": ["BUY", "BUY", "SELL", "BUY", "SELL"],
            "volume": [10, 20, 15, 30, 25],
        }
    )
    delta, imbalance = engine.compute_orderflow_metrics(df_ticks)

    # Mua: 10 + 20 + 30 = 60, Bán: 15 + 25 = 40. Delta = 20, Tổng = 100
    assert delta == 20
    assert imbalance == 0.20


def test_e1_05_order_imbalance_pure_buy():
    """TEST-E1-05: Khối lượng 100% mua chủ động bắt buộc trả về Imbalance Ratio = +1.0."""
    engine = TechnicalEngine()
    df_ticks = pd.DataFrame(
        {
            "match_type": ["BUY", "BUY"],
            "volume": [50, 50],
        }
    )
    delta, imbalance = engine.compute_orderflow_metrics(df_ticks)

    assert delta == 100
    assert imbalance == 1.0


def test_e1_06_fair_value_gap_detection():
    """TEST-E1-06: Nhận diện khoảng trống mất cân bằng giá Fair Value Gap (Bullish & Bearish FVG)."""
    engine = TechnicalEngine()

    # FVG Tăng giá: Low3 > High1
    highs_bull = [1200.0, 1220.0, 1230.0]
    lows_bull = [1190.0, 1205.0, 1210.0]  # Low3=1210 > High1=1200
    detected_bull, details_bull = engine.detect_fair_value_gaps(highs_bull, lows_bull)
    assert detected_bull is True
    assert details_bull["type"] == "BULLISH_FVG"
    assert details_bull["bottom"] == 1200.0
    assert details_bull["top"] == 1210.0

    # FVG Giảm giá: High3 < Low1
    highs_bear = [1250.0, 1230.0, 1215.0]  # High3=1215 < Low1=1235
    lows_bear = [1235.0, 1210.0, 1200.0]
    detected_bear, details_bear = engine.detect_fair_value_gaps(highs_bear, lows_bear)
    assert detected_bear is True
    assert details_bear["type"] == "BEARISH_FVG"


def test_e1_07_liquidity_sweep():
    """TEST-E1-07: Nhận diện bẫy quét thanh khoản đỉnh rút râu (Bearish Liquidity Sweep)."""
    engine = TechnicalEngine()
    # 20 nến trước đó với đỉnh cục bộ tại 1300
    highs = [1280.0] * 19 + [1300.0, 1305.0]
    lows = [1270.0] * 21
    # Nến cuối chọc qua 1300 lên 1305 nhưng đóng cửa tụt lại ở 1290
    closes = [1275.0] * 19 + [1295.0, 1290.0]

    sweeps = engine.detect_liquidity_sweeps(highs, lows, closes, window=20)
    assert sweeps["bearish_sweep"] is True
    assert sweeps["bullish_sweep"] is False


def test_e1_08_doji_candles_parkinson_volatility():
    """TEST-E1-08: Chuỗi nến Doji liên tiếp (High == Low) phải xử lý an toàn log(1)=0 mà không crash."""
    highs = [1300.0, 1300.0, 1300.0, 1300.0]
    lows = [1300.0, 1300.0, 1300.0, 1300.0]
    vol = compute_parkinson_volatility(highs, lows)
    assert vol == 0.0


# ===========================================================================
# NHÓM 2: ENGINE 2 (THANH KHOẢN, DÒNG TIỀN & T+2)
# ===========================================================================


def test_e2_01_missing_prop_desk_flow_fallback():
    """TEST-E2-01: Fallback chuẩn xác khi nguồn feed thiếu số liệu tự doanh (Tuân thủ RULE 3)."""
    engine = FlowLiquidityEngine()
    # Có số liệu khối ngoại (+300 tỷ), số liệu tự doanh là None
    flows = [
        InstitutionalFlow(
            trading_date=date(2026, 9, 18),
            symbol="VN30",
            foreign_net_value=300_000_000_000.0,
            prop_net_value=None,
            source="VCI",
        )
    ]
    ifm = engine.compute_institutional_momentum(flows)
    assert ifm > 0.0  # Tự động co giãn theo khối ngoại sẵn có mà không gây lỗi


def test_e2_02_market_breadth_all_decliners():
    """TEST-E2-02: Độ rộng thị trường khi 100% mã giảm bắt buộc trả về điểm -1.0."""
    engine = FlowLiquidityEngine()
    breadth = MarketBreadth(
        trading_date=date(2026, 9, 18),
        exchange="HOSE",
        advancers=0,
        decliners=400,
        unchanged=0,
    )
    mbi = engine.compute_market_breadth(breadth)
    assert mbi == -1.0


def test_e2_03_vietnamese_t2_settlement_calendar():
    """TEST-E2-03: Lịch thanh toán T+2 bỏ qua cuối tuần (Mua Thứ 6 -> Hàng về 13:00 Thứ 3)."""
    engine = FlowLiquidityEngine()
    friday = date(2026, 9, 18)  # Thứ 6
    t2_date = engine.compute_t2_settlement_date(friday)
    # Thứ 6 + 1 ngày làm việc = Thứ 2 (21/09), + 2 ngày làm việc = Thứ 3 (22/09)
    assert t2_date == date(2026, 9, 22)
    assert t2_date.weekday() == 1  # Đúng là Thứ 3


def test_e2_04_t2_pressure_volume_spike():
    """TEST-E2-04: Đột biến khối lượng ngày T-2 gấp 3 lần trung bình tạo chỉ số áp lực tiệm cận 1.0."""
    engine = FlowLiquidityEngine()
    # 20 ngày trung bình volume = 10,000; ngày T-2 bùng nổ = 30,000 (gấp 3 lần)
    volumes = [10_000.0] * 20 + [30_000.0, 12_000.0]
    pressure = engine.compute_t2_pressure_index(volumes)
    assert pressure == 1.0


def test_e2_05_usd_vnd_macro_impact():
    """TEST-E2-05: Tỷ giá USD/VND tăng mạnh >0.5%/ngày tác động tiêu cực đến điểm số vĩ mô."""
    engine = FlowLiquidityEngine()
    macro_records = [
        MacroIndicator(
            recorded_date=date(2026, 9, 18),
            indicator_code="USD_VND",
            value=25450.0,
            change_pct=0.75,  # Tỷ giá tăng đột biến +0.75%
            source="VCB",
        )
    ]
    macro_score = engine.compute_macro_sentiment(macro_records)
    assert macro_score < 0.0  # Tác động tiêu cực (điểm âm)


def test_e2_06_dynamic_reweighting_when_breadth_none():
    """TEST-E2-06: Dynamic reweighting khi market_breadth là None (tỷ trọng 0.35 tái phân bổ)."""
    engine = FlowLiquidityEngine()
    assert engine.compute_market_breadth(None) is None

    # Khi breadth = None, w_ifm = 0.45/0.75 = 0.6, w_t2 = -0.20/0.75, w_macro = 0.10/0.75
    # Giả sử IFM = 1.0, t2_pressure = 0.0, macro = 0.0 -> score = 0.6
    score = engine.compute_composite_score(
        institutional_momentum=1.0,
        market_breadth=None,
        t2_pressure=0.0,
        macro_sentiment=0.0,
    )
    assert score == 0.6

    # Phân tích trả về FlowLiquidityEngineResponse với market_breadth=None
    res = engine.analyze(
        flows=[],
        breadth=None,
        daily_volumes=[],
        macro_items=[],
    )
    assert res.market_breadth is None
    assert res.score == 0.0


# ===========================================================================
# NHÓM 3: ENGINE 3 (ĐỊNH LƯỢNG ML, BASIS & CHUYỂN PHIÊN)
# ===========================================================================


def test_e3_01_basis_zscore_calculation():
    """TEST-E3-01: Tính toán Basis phái sinh - cơ sở và điểm Z-Score."""
    engine = QuantMLEngine()
    futures_price = 1320.0
    spot_price = 1300.0
    # Basis = +20.0, lịch sử mean = 0.0, std = 5.0 -> Z = +4.0 (giới hạn kịch khung +3.0 khi ít mẫu)
    basis_val, basis_z = engine.compute_basis_zscore(
        futures_price=futures_price,
        spot_index_price=spot_price,
        historical_basis=[-5.0, 0.0, 5.0],
    )
    assert basis_val == 20.0
    assert basis_z > 2.0


def test_e3_02_basis_mean_reversion_short_bias():
    """TEST-E3-02: Phái sinh quá đắt (Z > +2.0) kích hoạt thiên hướng Short trong Engine 3."""
    engine = QuantMLEngine()
    score = engine.compute_composite_score(basis_zscore=2.5, transition_score=0.0)
    assert score < 0.0  # Thiên hướng Short (điểm âm)


def test_e3_03_basis_discount_long_bias():
    """TEST-E3-03: Phái sinh chiết khấu sâu (Z < -2.0) kích hoạt thiên hướng Long trong Engine 3."""
    engine = QuantMLEngine()
    score = engine.compute_composite_score(basis_zscore=-2.5, transition_score=0.0)
    assert score > 0.0  # Thiên hướng Long (điểm dương)


def test_e3_04_atc_transition_projection():
    """TEST-E3-04: Dự báo mức dịch chuyển giá đóng cửa cân bằng trong phiên ATC."""
    engine = QuantMLEngine()
    pred = engine.predict_atc_transition(
        current_price=1300.0,
        basis_zscore=2.0,
        order_imbalance=-0.5,
    )
    assert "projected_price" in pred
    assert "expected_delta" in pred
    assert pred["expected_delta"] < 0.0  # Basis cao + áp lực bán kéo giá hội tụ xuống


def test_e3_05_monte_carlo_price_limits():
    """TEST-E3-05: 1,000 mô phỏng Monte Carlo T+1 phải tuyệt đối nằm trong biên độ trần/sàn ±7%."""
    engine = QuantMLEngine()
    ref_price = 1300.0
    targets = engine.simulate_monte_carlo_t1(
        current_price=ref_price,
        volatility=0.25,
        n_simulations=1000,
        seed=42,
    )
    floor_limit = ref_price * 0.93
    ceiling_limit = ref_price * 1.07

    assert targets["p05"] >= floor_limit
    assert targets["p95"] <= ceiling_limit
    assert targets["p05"] <= targets["p50"] <= targets["p95"]


# ===========================================================================
# NHÓM 4: BỘ HỢP NHẤT (ENSEMBLE) & SỔ NHẬT KÝ FORECAST JOURNAL
# ===========================================================================


def test_ens_01_weights_auto_normalization():
    """TEST-ENS-01: Trọng số tùy chỉnh bất kỳ phải tự động chuẩn hóa đảm bảo tổng = 1.0."""
    engine = EnsembleEngine()
    custom = {"w1": 2.0, "w2": 2.0, "w3": 4.0}
    norm_w = engine.normalize_weights(custom)

    assert abs(sum(norm_w.values()) - 1.0) < 1e-4
    assert norm_w["w1"] == 0.25
    assert norm_w["w2"] == 0.25
    assert norm_w["w3"] == 0.50


def test_ens_02_conflict_resolution_neutralizes():
    """TEST-ENS-02: Tín hiệu cực đoan đối nghịch (E1 > +0.5 & E3 < -0.5) phải triệt tiêu về NEUTRAL."""
    engine = EnsembleEngine()
    weights = {"w1": 0.5, "w2": 0.2, "w3": 0.3}
    final_score, confidence, conflict = engine.resolve_signal_conflicts(
        score_e1=0.80,  # Kỹ thuật tăng mạnh
        score_e2=0.10,
        score_e3=-0.80,  # Định lượng giảm mạnh
        weights=weights,
    )
    assert conflict is True
    assert final_score == 0.0
    assert confidence == 0.50


def test_ens_03_forecast_journal_auto_logging(sqlite_session):
    """TEST-ENS-03: Bắt buộc tự động chèn bản ghi vào ForecastJournal trạng thái 'pending' (RULE 3)."""
    engine = EnsembleEngine(session=sqlite_session)
    request = EnsembleSignalRequest(symbol="VN30F1M", horizon=ForecastHorizon.INTRADAY)

    # Cung cấp chuỗi giá mẫu hợp lệ cho technical engine
    highs = [1290.0 + i for i in range(30)]
    lows = [1280.0 + i for i in range(30)]
    closes = [1285.0 + i for i in range(30)]

    res = engine.generate_signal(
        request=request,
        entry_price=1315.0,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    # Kiểm tra bản ghi kiểm toán trong database
    journal_row = sqlite_session.get(ForecastJournal, res.journal_id)
    assert journal_row is not None
    assert journal_row.symbol == "VN30F1M"
    assert journal_row.status == ForecastStatus.PENDING
    assert journal_row.model_version == "v2.0.0"
    assert "engine_scores" in journal_row.parameter_snapshot


def test_ens_04_direction_thresholds():
    """TEST-ENS-04: Phân loại xu hướng theo ngưỡng TRD: >= +0.35 LONG, <= -0.35 SHORT, còn lại NEUTRAL."""
    engine = EnsembleEngine()
    assert engine.classify_direction(0.40) == ForecastDirection.BULLISH
    assert engine.classify_direction(-0.40) == ForecastDirection.BEARISH
    assert engine.classify_direction(0.15) == ForecastDirection.NEUTRAL


def test_ens_05_dynamic_risk_brackets_ratio():
    """TEST-ENS-05: Khoảng cắt lỗ và chốt lời phải đảm bảo tỷ lệ Risk:Reward tối thiểu 1:2.0."""
    engine = EnsembleEngine()
    entry = 1300.0
    atr = 6.0
    sl, tp = engine.calculate_risk_brackets(
        entry_price=entry,
        direction="LONG",
        atr=atr,
    )
    assert sl is not None and tp is not None
    risk = entry - sl
    reward = tp - entry
    assert reward / risk >= 2.0  # Tỷ lệ R:R >= 1:2.0


def test_ens_06_rule_4_disclaimer_presence():
    """TEST-ENS-06: Phản hồi tín hiệu bắt buộc phải chứa cảnh báo rủi ro giáo dục (RULE 4)."""
    engine = EnsembleEngine()
    request = EnsembleSignalRequest(symbol="VN30F1M")
    res = engine.generate_signal(request=request)
    assert "CẢNH BÁO RỦI RO" in res.disclaimer
    assert "RULE 4" in res.disclaimer
