"""DNSE Proxy and Market Data Router."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

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

    query_params = {
        "symbol": symbol.strip().upper(),
        "resolution": resolution,
        "from": from_ts,
        "to": to_ts,
        "type": sec_type,
    }
    encoded_query = urllib.parse.urlencode(query_params)
    path = f"/price/ohlc?{encoded_query}"
    url = f"https://openapi.dnse.com.vn{path}"

    try:
        from dnse.api.common import (
            build_signature,
            get_api_version,
            get_date_header_name,
        )

        date_val = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S %z")
        date_header_name = get_date_header_name()
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

        req = urllib.request.Request(url, method="GET")
        req.add_header(date_header_name, date_val)
        req.add_header("X-Signature", sig_val)
        req.add_header("X-API-Key", settings.DNSE_API_KEY)
        req.add_header("version", get_api_version())
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)

    except urllib.error.HTTPError as http_err:
        err_msg = http_err.read().decode("utf-8") if http_err.fp else str(http_err)
        logger.warning(
            "[DNSEProxy] DNSE API returned HTTP %s for %s: %s",
            http_err.code,
            symbol,
            err_msg,
        )
        raise HTTPException(
            status_code=http_err.code,
            detail=f"DNSE API error: {err_msg}",
        ) from http_err
    except Exception as e:
        logger.error("[DNSEProxy] Failed to query DNSE OHLC for %s: %s", symbol, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to DNSE OpenAPI: {e}",
        ) from e


__all__ = ["router"]
