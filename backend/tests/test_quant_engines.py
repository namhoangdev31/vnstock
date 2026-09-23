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

from app.core.enums import ForecastDirection, ForecastHorizon, ForecastStatus
from app.core.models_base import AwareSQLModel
from app.domains.quant.application.engines import (
    EnsembleEngine,
    FlowLiquidityEngine,
    QuantMLEngine,
    TechnicalEngine,
)
from app.domains.quant.application.schemas import EnsembleSignalRequest
from app.domains.quant.domain.indicators import (
    compute_macd,
    compute_parkinson_volatility,
    compute_rsi,
    compute_vwap,
)
from app.domains.quant.domain.models import (
    ForecastJournal,
    InstitutionalFlow,
    MacroIndicator,
    MarketBreadth,
)


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
    """TEST-E2-04: Đột biến khối lượng ngày T-2 gấp 3 lần trung bình tạo chỉ số áp lực tiệm cận 1.0 (TRD §2.2.4)."""
    engine = FlowLiquidityEngine()
    # 20 ngày trung bình volume = 10,000; ngày T-2 bùng nổ = 30,000 (gấp 3 lần)
    volumes_spike_3x = [10_000.0] * 20 + [30_000.0, 12_000.0]
    assert engine.compute_t2_pressure_index(volumes_spike_3x) == 1.0

    # Khối lượng T-2 = 15,000 (gấp 1.5 lần avg_vol)
    # Enhanced formula: 0.85 * 1.0 + 0.15 * z_vol_clipped → ~0.975
    volumes_spike_1_5x = [10_000.0] * 20 + [15_000.0, 12_000.0]
    assert abs(engine.compute_t2_pressure_index(volumes_spike_1_5x) - 0.975) < 0.02

    # Khối lượng T-2 = 7,500 (dưới avg): Z-score component = 0 (below avg clipped)
    # Enhanced formula: 0.85 * 0.5 + 0.15 * 0.0 → 0.425
    volumes_normal = [10_000.0] * 20 + [7_500.0, 10_000.0]
    assert abs(engine.compute_t2_pressure_index(volumes_normal) - 0.425) < 0.02


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


def test_e2_07_market_breadth_with_ratio_ma20():
    """TEST-E2-07: Tính Market Breadth Index kết hợp tỷ lệ Ratio_MA20 theo TRD §2.2.3."""
    engine = FlowLiquidityEngine()
    breadth = {"advancers": 200, "decliners": 100, "unchanged": 100}
    # Total = 400, ADR = (200 - 100) / 400 = 0.25
    # Nếu ratio_ma20 = 0.60:
    # MBI = 0.70 * 0.25 + 0.30 * (2 * 0.60 - 1.0) = 0.175 + 0.30 * 0.20 = 0.175 + 0.060 = 0.235
    mbi = engine.compute_market_breadth(breadth, ratio_ma20=0.60)
    assert mbi == 0.235

    # Nếu không có ratio_ma20 (fallback RULE 3): MBI = ADR = 0.25
    mbi_raw = engine.compute_market_breadth(breadth)
    assert mbi_raw == 0.25


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


def test_e3_05_ato_opening_gap_classification():
    """TEST-E3-05: Phân loại độ lệch ATO Opening Gap lúc 08:45 dựa trên phân phối lịch sử (TRD §2.3.3)."""
    engine = QuantMLEngine()
    prev_close = 1300.0

    # Ca 1: Giá ATO = 1310.0 (+0.77%) -> BULLISH_GAP
    res_bull = engine.predict_ato_gap(
        current_price=1310.0,
        prev_close=prev_close,
        overnight_basis=3.0,
    )
    assert res_bull["gap_type"] == "BULLISH_GAP"
    assert res_bull["direction_bias"] == "BULLISH"
    assert res_bull["transition_score"] > 0.0

    # Ca 2: Giá ATO = 1290.0 (-0.77%) -> BEARISH_GAP
    res_bear = engine.predict_ato_gap(
        current_price=1290.0,
        prev_close=prev_close,
        overnight_basis=-2.0,
    )
    assert res_bear["gap_type"] == "BEARISH_GAP"
    assert res_bear["direction_bias"] == "BEARISH"
    assert res_bear["transition_score"] < 0.0

    # Ca 3: Giá ATO = 1301.0 (+0.077%) -> NORMAL_GAP
    res_norm = engine.predict_ato_gap(
        current_price=1301.0,
        prev_close=prev_close,
        overnight_basis=0.0,
    )
    assert res_norm["gap_type"] == "NORMAL_GAP"
    assert res_norm["direction_bias"] == "NEUTRAL"


def test_e3_06_monte_carlo_1000_distribution():
    """TEST-E3-06: 1,000 mô phỏng Monte Carlo T+1 tuân thủ trật tự phân vị P05 < P50 < P95."""
    engine = QuantMLEngine()
    ref_price = 1300.0
    targets = engine.simulate_monte_carlo_t1(
        current_price=ref_price,
        volatility=0.20,
        n_simulations=1000,
        seed=101,
    )
    assert targets["p05"] < targets["p50"] < targets["p95"]
    assert targets["p05"] >= ref_price * 0.93
    assert targets["p95"] <= ref_price * 1.07


def test_e3_07_floor_ceiling_reflection():
    """TEST-E3-07: Kịch bản biến động cực đại (volatility = 100%) vẫn tuyệt đối được rào chắn trong ±7%."""
    engine = QuantMLEngine()
    ref_price = 1300.0
    floor_limit = ref_price * 0.93
    ceiling_limit = ref_price * 1.07

    targets = engine.simulate_monte_carlo_t1(
        current_price=ref_price,
        volatility=1.0,  # Biến động 100% cực đoan
        n_simulations=1000,
        seed=999,
    )
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
    final_score, confidence, conflict, disagreement = engine.resolve_signal_conflicts(
        score_e1=0.80,  # Kỹ thuật tăng mạnh
        score_e2=0.10,
        score_e3=-0.80,  # Định lượng giảm mạnh
        weights=weights,
    )
    assert conflict is True
    assert final_score == 0.0
    assert confidence == 0.50
    assert disagreement > 0.0


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


def test_e1_edge_cases_and_sweeps():
    """Kiểm tra các trường hợp biên của Engine 1: FVG giảm, quét thanh khoản hai chiều, dữ liệu rỗng."""
    engine = TechnicalEngine()

    # 1. Dữ liệu rỗng
    empty_res = engine.analyze(symbol="VN30F1M", closes=[])
    assert empty_res.score == 0.0
    assert empty_res.rsi is None

    # 2. Bearish FVG: nến 0 high > nến 2 low
    # highs[i] < lows[i-2] -> khoảng trống giảm giá
    highs = [1310.0, 1300.0, 1285.0]
    lows = [1305.0, 1290.0, 1280.0]
    fvg_detected, fvg_details = engine.detect_fair_value_gaps(highs, lows)
    assert fvg_detected is True
    assert fvg_details.get("type") == "BEARISH_FVG"

    # 3. Liquidity Sweeps: Quét đỉnh rút râu (Bearish) và quét đáy rút râu (Bullish)
    # Quét đỉnh: High vượt đỉnh cũ nhưng close đóng thấp hơn
    s_highs = [1300.0] * 10 + [1310.0, 1302.0]
    s_lows = [1290.0] * 10 + [1295.0, 1296.0]
    s_closes = [1295.0] * 10 + [1305.0, 1298.0]
    sweeps = engine.detect_liquidity_sweeps(s_highs, s_lows, s_closes)
    assert "bearish_sweep" in sweeps
    assert "swing_high" in sweeps


def test_e2_edge_cases_and_rolling_flows():
    """Kiểm tra các trường hợp biên của Engine 2: Vĩ mô nhiều chiều, lịch sử dòng tiền rolling 5D, T+2 volumes."""
    engine = FlowLiquidityEngine()

    # 1. Macro với USD_VND tăng/giảm và vàng SJC
    records = [
        {
            "indicator_code": "USD_VND",
            "change_pct": -0.80,
        },  # VND tăng giá mạnh -> điểm dương
        {
            "indicator_code": "SJC_GOLD_BUY",
            "change_pct": 1.5,
        },  # Vàng tăng nóng -> điểm âm
        {
            "indicator_code": "SJC_GOLD_SELL",
            "change_pct": -1.5,
        },  # Vàng giảm mạnh -> điểm dương
        {"indicator_code": "UNKNOWN", "change_pct": 0.0},
        {"indicator_code": "USD_VND", "change_pct": None},
    ]
    m_score = engine.compute_macro_sentiment(records)
    assert isinstance(m_score, float)

    # 2. T+2 áp lực với danh sách quá ngắn hoặc volume = 0
    assert engine.compute_t2_pressure_index([1000.0]) == 0.0
    assert engine.compute_t2_pressure_index([0.0, 0.0, 0.0]) == 0.0

    # 3. Chuỗi dòng tiền > 5 ngày phân bổ theo ngày
    flows_10d = [
        {
            "trading_date": date(2026, 9, i),
            "foreign_net_value": 1e11 * i,
            "prop_net_value": 5e10 * i,
        }
        for i in range(1, 11)
    ]
    ifm_10d = engine.compute_institutional_momentum(flows_10d)
    assert -1.0 <= ifm_10d <= 1.0

    # 4. Market breadth với total <= 0
    assert (
        engine.compute_market_breadth({"advancers": 0, "decliners": 0, "unchanged": 0})
        == 0.0
    )


def test_e3_edge_cases_and_session_phases():
    """Kiểm tra các trường hợp biên của Engine 3: Toàn bộ các mốc phiên giao dịch, MC biên âm, ATO gap với zscore."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Ho_Chi_Minh")

    engine = QuantMLEngine()

    # 1. Toàn bộ 8 phiên giao dịch Việt Nam
    phases_to_test = [
        (datetime(2026, 9, 23, 8, 35, tzinfo=tz), "PRE_ATO"),
        (datetime(2026, 9, 23, 8, 50, tzinfo=tz), "ATO"),
        (datetime(2026, 9, 23, 10, 0, tzinfo=tz), "MORNING_CONTINUOUS"),
        (datetime(2026, 9, 23, 12, 0, tzinfo=tz), "MIDDAY_INTERMISSION"),
        (datetime(2026, 9, 23, 13, 30, tzinfo=tz), "AFTERNOON_CONTINUOUS"),
        (datetime(2026, 9, 23, 14, 20, tzinfo=tz), "PRE_ATC"),
        (datetime(2026, 9, 23, 14, 35, tzinfo=tz), "ATC"),
        (datetime(2026, 9, 23, 15, 30, tzinfo=tz), "POST_MARKET"),
    ]
    for dt_test, expected_phase in phases_to_test:
        assert engine.classify_session_phase(dt_test) == expected_phase

    # 2. Monte Carlo với current_price <= 0
    assert engine.simulate_monte_carlo_t1(0.0, 0.2)["p50"] == 0.0

    # 3. ATO gap với prev_close <= 0
    assert engine.predict_ato_gap(1300.0, 0.0)["transition_score"] == 0.0

    # 4. ATO gap với chuỗi historical_gaps phân phối 15 ngày
    hist_gaps = [0.1 * i for i in range(-7, 8)]
    gap_stat = engine.predict_ato_gap(1320.0, 1300.0, historical_gaps=hist_gaps)
    assert gap_stat["gap_type"] == "BULLISH_GAP"

    # 5. Full analyze chạy qua cả ATO và ATC phases
    ato_dt = datetime(2026, 9, 23, 8, 50, tzinfo=tz)
    res_ato = engine.analyze(symbol="VN30F1M", as_of=ato_dt, closes=[1300.0, 1305.0])
    assert -1.0 <= res_ato.score <= 1.0


def test_ens_short_direction_brackets():
    """Kiểm tra tính Stop Loss / Take Profit cho vị thế SHORT trong EnsembleEngine."""
    engine = EnsembleEngine()
    sl, tp = engine.calculate_risk_brackets(
        entry_price=1300.0,
        direction="SHORT",
        atr=5.0,
    )
    assert sl is not None and tp is not None
    assert sl > 1300.0  # Cắt lỗ ở giá cao hơn giá vào lệnh Short
    assert tp < 1300.0  # Chốt lời ở giá thấp hơn
    risk = sl - 1300.0
    reward = 1300.0 - tp
    assert reward / risk >= 2.0  # R:R >= 1:2.0


def test_e1_orderflow_branches_and_composite_score():
    """Kiểm tra các nhánh TickFlowAggregated, thuần bán, và tổ hợp điểm kỹ thuật."""
    from app.domains.quant.domain.models import TickFlowAggregated

    engine = TechnicalEngine()

    # 1. Truyền danh sách TickFlowAggregated
    tick_items = [
        TickFlowAggregated(
            trading_date=date(2026, 9, 23),
            symbol="VN30F1M",
            aggressive_buy_volume=500,
            aggressive_sell_volume=300,
            source="VCI",
        )
    ]
    delta, imb = engine.compute_orderflow_metrics(tick_items)
    assert delta == 200
    assert imb > 0.0

    # 2. 100% bán (buy_vol = 0)
    tick_sell_only = [
        TickFlowAggregated(
            trading_date=date(2026, 9, 23),
            symbol="VN30F1M",
            aggressive_buy_volume=0,
            aggressive_sell_volume=1000,
            source="VCI",
        )
    ]
    _, imb_sell = engine.compute_orderflow_metrics(tick_sell_only)
    assert imb_sell == -1.0

    # 3. DataFrame không có match_type
    import pandas as pd

    df_no_type = pd.DataFrame([{"price": 1300.0, "volume": 100}])
    d_no, imb_no = engine.compute_orderflow_metrics(df_no_type)
    assert d_no == 100

    # 4. detect_liquidity_sweeps với < 5 nến
    assert engine.detect_liquidity_sweeps([1300.0], [1290.0], [1295.0]) == {
        "bearish_sweep": False,
        "bullish_sweep": False,
    }

    # 5. Composite score: RSI quá bán (<30) + MACD Hist dương + FVG Bullish + Bullish Sweep
    score_bull = engine.compute_composite_score(
        rsi=25.0,
        macd_hist=1.5,
        vwap_diff_pct=-0.01,
        imbalance=0.5,
        fvg_detected=True,
        fvg_type="BULLISH_FVG",
        sweeps={"bullish_sweep": True},
    )
    assert score_bull > 0.0

    # 6. Composite score: RSI quá mua (>70) + MACD Hist âm + FVG Bearish + Bearish Sweep
    score_bear = engine.compute_composite_score(
        rsi=75.0,
        macd_hist=-1.5,
        vwap_diff_pct=0.01,
        imbalance=-0.5,
        fvg_detected=True,
        fvg_type="BEARISH_FVG",
        sweeps={"bearish_sweep": True},
    )
    assert score_bear < 0.0


def test_indicators_safety_edge_cases():
    """Kiểm tra độ an toàn của tất cả chỉ báo khi chuỗi nến ngắn hơn chu kỳ."""
    from app.domains.quant.domain.indicators import (
        compute_bollinger_bands,
        compute_historical_volatility,
        compute_parkinson_volatility,
        compute_rsi,
        compute_zscore,
    )

    # Chuỗi giá ngắn < period
    assert compute_rsi([100.0, 102.0], period=14) is None
    assert compute_bollinger_bands([100.0] * 5, period=20)["bandwidth"] == 0.0
    assert compute_bollinger_bands([], period=20)["upper"] == 0.0
    assert compute_historical_volatility([100.0]) == 0.0
    assert compute_parkinson_volatility([], []) == 0.0
    assert compute_zscore(10.0, 10.0, 0.0) == 0.0
    assert compute_zscore(12.0, 10.0, 2.0) == 1.0


def test_e1_with_session_fallback(sqlite_session):
    """Kiểm tra TechnicalEngine khi khởi tạo với DB Session."""
    from datetime import date

    from app.domains.market_data.domain.models import StockOHLCVDaily

    engine = TechnicalEngine(session=sqlite_session)
    # 1. Khi chưa có dữ liệu DB
    res = engine.analyze(symbol="VN30F1M")
    assert res.score == 0.0
    assert res.symbol == "VN30F1M"

    # 2. Khi có dữ liệu DB bars
    for i in range(25):
        bar = StockOHLCVDaily(
            symbol="VN30F1M",
            trading_date=date(2026, 8, 1 + (i % 28)),
            open=1300.0 + i,
            high=1310.0 + i,
            low=1295.0 + i,
            close=1305.0 + i,
            volume=10000 + i * 100,
            source="VCI",
        )
        sqlite_session.add(bar)
    sqlite_session.commit()

    res_db = engine.analyze(symbol="VN30F1M")
    assert res_db.symbol == "VN30F1M"
    assert res_db.vwap is not None
    assert -1.0 <= res_db.score <= 1.0


def test_e1_additional_branches():
    """Kiểm tra các nhánh phụ còn lại của TechnicalEngine: DF rỗng, FVG ngắn, vwap mismatched."""
    import pandas as pd

    engine = TechnicalEngine()

    # 1. compute_orderflow_metrics với DF rỗng hoặc thiếu volume
    assert engine.compute_orderflow_metrics(pd.DataFrame()) == (0, 0.0)
    assert engine.compute_orderflow_metrics(pd.DataFrame([{"price": 100}])) == (0, 0.0)

    # 2. total volume <= 0
    df_zero = pd.DataFrame([{"volume": 0, "match_type": "BUY"}])
    assert engine.compute_orderflow_metrics(df_zero) == (0, 0.0)

    # 3. detect_fair_value_gaps với dữ liệu ngắn < 3
    has_fvg, fvg_dict = engine.detect_fair_value_gaps([100.0], [90.0])
    assert not has_fvg and fvg_dict == {}

    # 4. detect_liquidity_sweeps với lookback rỗng
    sweeps = engine.detect_liquidity_sweeps(
        [100.0] * 5, [90.0] * 5, [95.0] * 5, window=0
    )
    assert not sweeps["bearish_sweep"] and not sweeps["bullish_sweep"]

    # 5. vwap fallback khi len(highs) != len(closes)
    res_mismatch = engine.analyze(
        symbol="VN30F1M",
        closes=[1300.0, 1305.0, 1310.0],
        highs=[1310.0, 1315.0],  # độ dài 2 != 3
        lows=[1290.0, 1295.0, 1300.0],
    )
    assert res_mismatch.vwap is not None


def test_advanced_ml_indicators_suite():
    """Kiểm tra toàn diện 7 hàm chỉ báo ML nâng cao mới được bổ sung trong indicators.py."""
    from app.domains.quant.domain.indicators import (
        compute_adaptive_zscore,
        compute_entropy,
        compute_exponential_smoothing,
        compute_linear_regression_slope,
        compute_roc,
        compute_rsi_smooth,
        detect_market_regime,
    )

    # 1. compute_rsi_smooth
    assert compute_rsi_smooth([100.0, 102.0]) is None
    trend_up = [100.0 + i * 2.0 for i in range(20)]
    rsi_up = compute_rsi_smooth(trend_up)
    assert rsi_up is not None and rsi_up > 0.5
    trend_down = [100.0 - i * 2.0 for i in range(20)]
    rsi_down = compute_rsi_smooth(trend_down)
    assert rsi_down is not None and rsi_down < -0.5

    # 2. detect_market_regime
    # Chuỗi ngắn
    assert detect_market_regime([100.0, 101.0]) == "RANGING"
    # Chuỗi có High/Low rõ xu hướng tăng (dx > 25)
    highs = [100.0 + i * 3.0 for i in range(20)]
    lows = [95.0 + i * 3.0 for i in range(20)]
    closes = [98.0 + i * 3.0 for i in range(20)]
    regime_hl = detect_market_regime(closes, highs=highs, lows=lows, window=14)
    assert regime_hl in ("TRENDING", "RANGING", "VOLATILE")
    # Fallback chỉ có closes
    regime_closes = detect_market_regime(closes, window=14)
    assert regime_closes in ("TRENDING", "RANGING", "VOLATILE")

    # 3. compute_roc
    assert compute_roc([100.0, 101.0], period=10) == 0.0
    assert compute_roc([0.0] * 12, period=10) == 0.0
    roc_val = compute_roc([100.0 + i * 1.0 for i in range(15)], period=10)
    assert roc_val > 0.0

    # 4. compute_linear_regression_slope
    assert compute_linear_regression_slope([100.0, 101.0]) == 0.0
    assert compute_linear_regression_slope([0.0] * 10) == 0.0
    slope_pos = compute_linear_regression_slope([100.0 + i * 2.0 for i in range(15)])
    assert slope_pos > 0.0
    slope_neg = compute_linear_regression_slope([100.0 - i * 2.0 for i in range(15)])
    assert slope_neg < 0.0

    # 5. compute_adaptive_zscore
    # Series ngắn
    assert compute_adaptive_zscore(10.0, [10.0, 11.0]) == 2.0
    # Series đều (std < 1e-9)
    assert compute_adaptive_zscore(10.0, [10.0] * 20) == 0.0
    # Series bình thường
    z_adapt = compute_adaptive_zscore(15.0, [10.0 + (i % 3) for i in range(20)])
    assert -5.0 <= z_adapt <= 5.0

    # 6. compute_entropy
    assert compute_entropy([]) == 0.0
    assert compute_entropy([0.0, 0.0, 0.0]) == 0.0
    # Phân phối đều -> entropy tiệm cận 1.0
    assert compute_entropy([1.0, 1.0, 1.0, 1.0]) >= 0.99
    # Phân phối lệch tập trung -> entropy thấp
    assert compute_entropy([100.0, 0.001, 0.001]) < 0.1

    # 7. compute_exponential_smoothing
    assert compute_exponential_smoothing([]) == []
    smoothed = compute_exponential_smoothing([10.0, 20.0, 30.0], alpha=0.4)
    assert len(smoothed) == 3
    assert smoothed[0] == 10.0
    assert smoothed[1] == 0.4 * 20.0 + 0.6 * 10.0
