"""DNSE Proxy and Market Data Router."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dnse", tags=["dnse"])


@router.get("/price/ohlc")
async def get_dnse_ohlc(
    symbol: str = Query(
        ..., description="Mã chứng khoán hoặc hợp đồng phái sinh (VD: VN30F1M)"
    ),
    resolution: str = Query(
        "1", description="Độ phân giải nến: 1, 3, 5, 15, 30, 1h, 1D, 1W"
    ),
    from_ts: int = Query(
        ..., alias="from", description="Thời điểm bắt đầu (Unix timestamp giây)"
    ),
    to_ts: int = Query(
        ..., alias="to", description="Thời điểm kết thúc (Unix timestamp giây)"
    ),
    sec_type: str = Query(
        "DERIVATIVE", alias="type", description="Loại tài sản: DERIVATIVE, STOCK, INDEX"
    ),
) -> Any:
    """Proxy xác thực an toàn tới DNSE OpenAPI để lấy nến lịch sử OHLC.

    Tự động ký HMAC-SHA256 với credentials DNSE phía máy chủ và trả về dữ liệu nến,
    giúp Frontend tránh hoàn toàn lỗi CORS và không làm lộ API Key/Secret ra trình duyệt.
    """
    if not settings.DNSE_API_KEY or not settings.DNSE_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DNSE API credentials are not configured on server",
        )

    try:
        from dnse import DNSEClient

        client = DNSEClient(
            api_key=settings.DNSE_API_KEY,
            api_secret=settings.DNSE_API_SECRET,
        )
        # Bổ sung User-Agent chuẩn trình duyệt để WAF DNSE không reset connection
        headers_dict = dict(client._http.headers)
        headers_dict["User-Agent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        client._http.headers = headers_dict

        query = {
            "symbol": symbol.strip().upper(),
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts,
        }
        res_status, body_text = client.get_ohlc(sec_type, query=query)

        if 200 <= res_status < 300 and body_text:
            return json.loads(body_text)

        logger.warning(
            "[DNSEProxy] DNSE API returned HTTP %s for %s: %s",
            res_status,
            symbol,
            body_text,
        )
        raise HTTPException(
            status_code=res_status,
            detail=f"DNSE API error: {body_text}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[DNSEProxy] Failed to query DNSE OHLC for %s: %s", symbol, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to DNSE OpenAPI: {e}",
        ) from e


__all__ = ["router"]
