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
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4

        from dnse import DNSEClient
        from dnse.api.common import build_signature, get_api_version

        tz_vn = timezone(timedelta(hours=7))
        date_val = datetime.now(tz_vn).strftime("%a, %d %b %Y %H:%M:%S GMT+7")
        date_header_name = "X-Aux-Date"
        nonce = uuid4().hex

        headers_list, signature = build_signature(
            settings.DNSE_API_SECRET,
            "GET",
            "/price/ohlc",
            date_val,
            "hmac-sha256",
            nonce=nonce,
            header_name=date_header_name,
        )

        sig_val = (
            f'Signature keyId="{settings.DNSE_API_KEY}",'
            f'algorithm="hmac-sha256",'
            f'headers="{headers_list}",'
            f'signature="{signature}",'
            f'nonce="{nonce}"'
        )

        client = DNSEClient(
            api_key=settings.DNSE_API_KEY,
            api_secret=settings.DNSE_API_SECRET,
        )
        query = {
            "symbol": symbol.strip().upper(),
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts,
            "type": sec_type,
        }
        url = client._build_url("/price/ohlc", query)
        req_headers = {
            date_header_name: date_val,
            "X-Signature": sig_val,
            "x-api-key": settings.DNSE_API_KEY,
            "version": get_api_version(),
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }

        resp = client._http.request("GET", url, headers=req_headers)
        body_text = resp.data.decode("utf-8")
        res_status = resp.status

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
