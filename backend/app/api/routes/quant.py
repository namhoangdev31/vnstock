"""FastAPI Router cho Hệ thống Phân tích Định lượng & Bộ Hợp nhất Tri-Engine (Phase 2).

Danh sách Endpoints:
- GET /quant/engine1/technical/{symbol} : Chỉ báo kỹ thuật, VWAP, dòng lệnh và cấu trúc giá Engine 1
- GET /quant/engine2/flow-liquidity     : Dòng tiền khối ngoại/tự doanh, độ rộng và áp lực T+2 Engine 2
- GET /quant/engine3/basis-volatility   : Chênh lệch Basis, Z-score, biến động và Monte Carlo Engine 3
- POST /quant/ensemble/signal           : Tín hiệu hợp nhất đa tầng, SL/TP và tự động ghi sổ nhật ký (RULE 3)
- GET /quant/ensemble/atc-forecast      : Kịch bản dự báo phiên khớp lệnh định kỳ đóng cửa ATC hôm nay
- GET /quant/ensemble/next-day-forecast : Kịch bản phân phối giá mục tiêu T+1 (Monte Carlo 1,000 runs)
- GET /quant/ensemble/weights           : Lấy cấu hình trọng số động hiện tại theo khung giờ phiên
- PUT /quant/ensemble/weights           : Cập nhật trọng số tùy chỉnh w1, w2, w3 (Chỉ dành cho Superuser)

Toàn bộ các endpoint đều được bảo vệ bằng JWT thông qua dependency CurrentUser.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.models.models_quant import (
    EnsembleSignalRequest,
    EnsembleSignalResponse,
    EnsembleWeightsResponse,
    EnsembleWeightsUpdate,
    FlowLiquidityEngineResponse,
    QuantMLEngineResponse,
    TechnicalEngineResponse,
)
from app.services.quant.ensemble_engine import EnsembleEngine
from app.services.quant.flow_engine import FlowLiquidityEngine
from app.services.quant.quant_ml_engine import QuantMLEngine
from app.services.quant.technical_engine import TechnicalEngine

router = APIRouter(prefix="/quant", tags=["quant"])


@router.get(
    "/engine1/technical/{symbol}",
    response_model=TechnicalEngineResponse,
    summary="Lấy kết quả phân tích kỹ thuật và dòng lệnh của Engine 1",
)
def get_engine1_technical(
    symbol: str,
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
) -> Any:
    """Trả về các chỉ báo kỹ thuật (RSI, MACD, BB, ATR), VWAP, mất cân bằng lệnh, FVG và Sweeps."""
    engine = TechnicalEngine(session=session)
    return engine.analyze(symbol=symbol.upper())


@router.get(
    "/engine2/flow-liquidity",
    response_model=FlowLiquidityEngineResponse,
    summary="Lấy kết quả phân tích dòng tiền tổ chức, độ rộng và áp lực T+2 của Engine 2",
)
def get_engine2_flow_liquidity(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
) -> Any:
    """Trả về xung lực dòng tiền khối ngoại/tự doanh, độ rộng thị trường, và chỉ số áp lực hàng T+2."""
    engine = FlowLiquidityEngine(session=session)
    return engine.analyze()


@router.get(
    "/engine3/basis-volatility",
    response_model=QuantMLEngineResponse,
    summary="Lấy kết quả phân tích Basis, độ biến động và mô phỏng Monte Carlo của Engine 3",
)
def get_engine3_basis_volatility(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str = "VN30F1M",
) -> Any:
    """Trả về độ lệch Basis Z-score, biến động Historical/Parkinson và phân vị Monte Carlo T+1."""
    engine = QuantMLEngine(session=session)
    return engine.analyze(symbol=symbol.upper())


@router.post(
    "/ensemble/signal",
    response_model=EnsembleSignalResponse,
    summary="Tính toán tín hiệu hợp nhất đa tầng và tự động lưu sổ nhật ký ForecastJournal (RULE 3)",
)
def compute_ensemble_signal(
    payload: EnsembleSignalRequest,
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
) -> Any:
    """Phối hợp 3 Engine, tự động cân đối trọng số theo giờ, tính SL/TP và chèn bản ghi vào ForecastJournal."""
    engine = EnsembleEngine(session=session)
    return engine.generate_signal(request=payload)


@router.get(
    "/ensemble/atc-forecast",
    summary="Dự báo kịch bản khớp lệnh định kỳ đóng cửa phiên ATC hôm nay",
)
def get_atc_forecast(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str = "VN30F1M",
) -> Any:
    """Dự phóng độ dịch chuyển giá và thiên hướng khớp lệnh trong đợt đấu thầu đóng cửa ATC."""
    engine3 = QuantMLEngine(session=session)
    res = engine3.analyze(symbol=symbol.upper())
    atc_pred = engine3.predict_atc_transition(
        current_price=res.basis_value + 1300.0,
        basis_zscore=res.basis_zscore,
    )
    return {
        "symbol": symbol.upper(),
        "as_of": res.as_of,
        "session_phase": res.session_phase,
        "basis_zscore": res.basis_zscore,
        **atc_pred,
        "disclaimer": (
            "CẢNH BÁO RỦI RO (RULE 4): Dự báo mang tính chất nghiên cứu định lượng mô phỏng, "
            "không cấu thành lời khuyên đầu tư hay khuyến nghị giao dịch."
        ),
    }


@router.get(
    "/ensemble/next-day-forecast",
    summary="Lấy dải giá mục tiêu phân phối Monte Carlo cho phiên tiếp theo (T+1)",
)
def get_next_day_forecast(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str = "VN30F1M",
) -> Any:
    """Mô phỏng 1,000 đường đi giá ngẫu nhiên Monte Carlo với các phân vị P05 (đáy), P50, P95 (đỉnh)."""
    engine3 = QuantMLEngine(session=session)
    res = engine3.analyze(symbol=symbol.upper())
    return {
        "symbol": symbol.upper(),
        "as_of": res.as_of,
        "historical_vol": res.historical_vol,
        "parkinson_vol": res.parkinson_vol,
        "monte_carlo_targets": res.monte_carlo_targets,
        "price_limit_band": "±7.0% (Quy chuẩn biên độ trần/sàn HOSE & Phái sinh)",
        "disclaimer": (
            "CẢNH BÁO RỦI RO (RULE 4): Dải phân phối mô phỏng Monte Carlo chỉ có giá trị tham khảo "
            "trong môi trường paper trading, không bảo đảm kết quả thực tế."
        ),
    }


@router.get(
    "/ensemble/weights",
    response_model=EnsembleWeightsResponse,
    summary="Xem cấu hình trọng số động hiện tại và thời gian biểu các pha phiên",
)
def get_ensemble_weights(
    current_user: CurrentUser,  # noqa: ARG001
) -> Any:
    """Trả về trọng số hiện tại của 3 Engine và bảng lịch trình điều phối động theo thời gian phiên."""
    engine = EnsembleEngine()
    return engine.get_weights_status()


@router.put(
    "/ensemble/weights",
    response_model=EnsembleWeightsResponse,
    summary="Cập nhật trọng số hợp nhất tùy chỉnh (Chỉ dành cho Superuser)",
)
def update_ensemble_weights(
    payload: EnsembleWeightsUpdate,
    current_user: CurrentUser,
) -> Any:
    """Thiết lập trọng số tùy biến w1, w2, w3. Yêu cầu quyền quản trị viên cao cấp (SuperUser)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Không đủ quyền hạn thực hiện thao tác"
        )
    engine = EnsembleEngine()
    engine.set_custom_weights_override(w1=payload.w1, w2=payload.w2, w3=payload.w3)
    return engine.get_weights_status()
