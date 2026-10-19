"""DNSE OpenAPI Market Breadth Gateway.

Chuyên trách truy xuất độ rộng thị trường (Market Breadth) độc quyền qua thư viện:
dnse-sdk-openapi (DNSEClient):
- get_market_index: Chuỗi thời gian tỷ lệ độ rộng 100% Stacked Area & Snapshot mới nhất
- get_instruments & get_latest_trade / get_security_definition: Chi tiết phân bổ mã cổ phiếu
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from dnse import DNSEClient

from app.core.cache import realtime_cache
from app.core.config import settings
from app.domains.dnse.schemas import (
    DNSEIndexBreadth,
    MarketBreadthDetailResponse,
    MarketBreadthPoint,
    MarketBreadthSeriesResponse,
)

logger = logging.getLogger(__name__)
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

INDEX_CODE_MAP: dict[str, str] = {
    "vnindex": "VNINDEX",
    "hose": "VNINDEX",
    "vni": "VNINDEX",
    "vn30": "VN30",
    "hnx": "HNX",
    "hnxindex": "HNX",
    "hnx-index": "HNX",
    "hnx30": "HNX30",
    "upcom": "UPCOM",
    "upcomindex": "UPCOM",
}


class DNSEMarketBreadthGateway:
    """Gateway truy xuất độ rộng thị trường sử dụng độc quyền dnse-sdk-openapi."""

    @classmethod
    def _get_client(cls) -> DNSEClient | None:
        if not settings.DNSE_API_KEY or not settings.DNSE_API_SECRET:
            logger.warning("DNSE API Key/Secret chưa được cấu hình.")
            return None
        return DNSEClient(
            api_key=settings.DNSE_API_KEY,
            api_secret=settings.DNSE_API_SECRET,
        )

    @classmethod
    def normalize_code(cls, code: str) -> str:
        clean = (code or "").strip().lower()
        return INDEX_CODE_MAP.get(clean, clean.upper())

    @classmethod
    def _find_session_date(
        cls, client: DNSEClient, index_name: str
    ) -> tuple[date | None, dict[str, Any] | None]:
        """Tìm ngày phiên giao dịch gần nhất có dữ liệu (hỗ trợ ngoài giờ, cuối tuần, ngày lễ)."""
        now = datetime.now(VN_TZ)
        cur_date = now.date()

        for delta in range(5):
            target_d = cur_date - timedelta(days=delta)
            if target_d.weekday() >= 5:  # Thứ 7, Chủ Nhật bỏ qua
                continue
            t1 = int(
                datetime(
                    target_d.year, target_d.month, target_d.day, 8, 30, tzinfo=VN_TZ
                ).timestamp()
            )
            t2 = int(
                datetime(
                    target_d.year, target_d.month, target_d.day, 15, 30, tzinfo=VN_TZ
                ).timestamp()
            )
            try:
                code, body = client.get_market_index(
                    index_name, from_date=t1, to_date=t2, limit=1, order="DESC"
                )
                if code == 200:
                    data = json.loads(body)
                    indices = data.get("marketIndices") or []
                    if indices:
                        return target_d, indices[0]
            except Exception as e:
                logger.debug(
                    "Lỗi kiểm tra phiên ngày %s cho %s: %s", target_d, index_name, e
                )
        return None, None

    @classmethod
    def get_market_breadth_latest(cls, index_code: str) -> DNSEIndexBreadth | None:
        """Truy xuất snapshot độ rộng thị trường mới nhất của phiên hiện tại."""
        norm = cls.normalize_code(index_code)
        if not norm or norm == "VN30F1M":
            return None

        cache_key = f"market_breadth_latest:{norm}"
        cached = realtime_cache.get(cache_key)
        if isinstance(cached, dict):
            return DNSEIndexBreadth(**cached)

        client = cls._get_client()
        if not client:
            return None

        try:
            _, item = cls._find_session_date(client, norm)
            if item:
                ceil = int(item.get("fluctuationUpperLimitIssueCount") or 0)
                flr = int(item.get("fluctuationLowerLimitIssueCount") or 0)
                up_pure = int(item.get("fluctuationUpIssueCount") or 0)
                down_pure = int(item.get("fluctuationDownIssueCount") or 0)
                no_chg = int(item.get("fluctuationSteadinessIssueCount") or 0)

                res = DNSEIndexBreadth(
                    advance=up_pure + ceil,
                    ceiling=ceil,
                    unchanged=no_chg,
                    decline=down_pure + flr,
                    floor=flr,
                )
                realtime_cache.set(cache_key, res.model_dump(), ttl=5)
                return res
        except Exception as e:
            logger.warning(
                "DNSEClient.get_market_breadth_latest thất bại cho %s: %s", norm, e
            )

        return None

    @classmethod
    def get_market_breadth_series(cls, index_code: str) -> MarketBreadthSeriesResponse:
        """Truy xuất chuỗi thời gian độ rộng thị trường (100% Stacked Area) theo từng phút."""
        norm = cls.normalize_code(index_code)
        if not norm or norm == "VN30F1M":
            norm = "VN30"

        cache_key = f"market_breadth_series:{norm}"
        cached: Any = realtime_cache.get(cache_key)
        if isinstance(cached, dict):
            return MarketBreadthSeriesResponse(**cached)

        client = cls._get_client()
        if not client:
            return MarketBreadthSeriesResponse(index_code=norm, data=[], latest=None)

        points: list[MarketBreadthPoint] = []
        try:
            session_date, _ = cls._find_session_date(client, norm)
            if session_date:
                t1 = int(
                    datetime(
                        session_date.year,
                        session_date.month,
                        session_date.day,
                        8,
                        30,
                        tzinfo=VN_TZ,
                    ).timestamp()
                )
                t2 = int(
                    datetime(
                        session_date.year,
                        session_date.month,
                        session_date.day,
                        15,
                        30,
                        tzinfo=VN_TZ,
                    ).timestamp()
                )

                items_by_minute: dict[str, dict[str, Any]] = {}
                next_token: str | None = None

                for _ in range(10):  # Tối đa 10 trang x 1000 records (~10,000 ticks)
                    code, body = client.get_market_index(
                        norm,
                        from_date=t1,
                        to_date=t2,
                        limit=1000,
                        order="ASC",
                        next_page_token=next_token,
                    )
                    if code != 200:
                        break
                    data = json.loads(body)
                    records = data.get("marketIndices") or []
                    if not records:
                        break

                    for r in records:
                        tx = str(r.get("transactionTime") or "")
                        if len(tx) >= 16:
                            minute_key = tx[11:16]  # "HH:MM"
                            items_by_minute[minute_key] = r

                    next_token = data.get("nextPageToken")
                    if not next_token:
                        break

                for minute_str in sorted(items_by_minute.keys()):
                    item = items_by_minute[minute_str]
                    tx_str = str(item.get("transactionTime") or "")
                    try:
                        dt = datetime.strptime(
                            tx_str[:19], "%Y-%m-%d %H:%M:%S"
                        ).replace(tzinfo=VN_TZ)
                        ts = int(dt.timestamp())
                    except Exception:
                        ts = 0

                    ceil = int(item.get("fluctuationUpperLimitIssueCount") or 0)
                    flr = int(item.get("fluctuationLowerLimitIssueCount") or 0)
                    adv_pure = int(item.get("fluctuationUpIssueCount") or 0)
                    dec_pure = int(item.get("fluctuationDownIssueCount") or 0)
                    no_chg = int(item.get("fluctuationSteadinessIssueCount") or 0)

                    adv = adv_pure + ceil
                    dec = dec_pure + flr
                    tot = adv + dec + no_chg

                    if tot > 0:
                        ceil_pct = round((ceil / tot) * 100, 2)
                        adv_pure_pct = round((adv_pure / tot) * 100, 2)
                        unchanged_pct = round((no_chg / tot) * 100, 2)
                        dec_pure_pct = round((dec_pure / tot) * 100, 2)
                        flr_pct = round((flr / tot) * 100, 2)
                    else:
                        ceil_pct = adv_pure_pct = unchanged_pct = dec_pure_pct = (
                            flr_pct
                        ) = 0.0

                    pt = MarketBreadthPoint(
                        time=minute_str,
                        timestamp=ts,
                        advance=adv,
                        decline=dec,
                        unchanged=no_chg,
                        ceiling=ceil,
                        floor=flr,
                        total=tot,
                        ceiling_pct=ceil_pct,
                        advance_pure_pct=adv_pure_pct,
                        unchanged_pct=unchanged_pct,
                        decline_pure_pct=dec_pure_pct,
                        floor_pct=flr_pct,
                    )
                    points.append(pt)
        except Exception as e:
            logger.warning(
                "DNSEClient.get_market_breadth_series thất bại cho %s: %s", norm, e
            )

        latest_point = points[-1] if points else None
        result = MarketBreadthSeriesResponse(
            index_code=norm,
            data=points,
            latest=latest_point,
        )
        if points:
            realtime_cache.set(cache_key, result.model_dump(), ttl=15)
        return result

    @classmethod
    def get_market_breadth_detail(cls, index_code: str) -> MarketBreadthDetailResponse:
        """Truy xuất danh sách mã chứng khoán theo 5 phân nhóm độ rộng thị trường."""
        norm = cls.normalize_code(index_code)
        if not norm or norm == "VN30F1M":
            norm = "VN30"

        cache_key = f"market_breadth_detail:{norm}"
        cached: Any = realtime_cache.get(cache_key)
        if isinstance(cached, dict):
            return MarketBreadthDetailResponse(**cached)

        client = cls._get_client()
        if not client:
            return MarketBreadthDetailResponse(index_code=norm)

        ceil_list: list[str] = []
        adv_list: list[str] = []
        nc_list: list[str] = []
        dec_list: list[str] = []
        flr_list: list[str] = []

        try:
            # 1. Lấy danh sách mã chứng khoán theo chỉ số / rổ chỉ số qua DNSEClient.get_instruments
            symbols: list[str] = []
            if norm == "VN30":
                code, body = client.get_instruments(index_name="VN30", limit=50)
            elif norm == "HNX30":
                code, body = client.get_instruments(index_name="HNX30", limit=50)
            elif norm == "VNINDEX":
                code, body = client.get_instruments(
                    market_id="STO", security_group_id="ST", limit=1000
                )
            elif norm == "HNX":
                code, body = client.get_instruments(
                    market_id="STX", security_group_id="ST", limit=1000
                )
            elif norm == "UPCOM":
                code, body = client.get_instruments(
                    market_id="UPX", security_group_id="ST", limit=1000
                )
            else:
                code, body = client.get_instruments(
                    market_id="STO", security_group_id="ST", limit=1000
                )

            if code == 200:
                data = json.loads(body)
                symbols = [x["symbol"] for x in data.get("data", []) if x.get("symbol")]

            # 2. Phân loại mã cổ phiếu theo mức giá khớp vs tham chiếu/trần/sàn
            def _classify_symbol(sym: str) -> tuple[str, str | None]:
                try:
                    c1, b1 = client.get_latest_trade(sym)
                    c2, b2 = client.get_security_definition(sym)
                    if c1 == 200 and c2 == 200:
                        trades = json.loads(b1).get("trades", [])
                        defs = json.loads(b2)
                        if not trades or not defs:
                            return sym, None

                        # Ưu tiên khớp lệnh liên tục từ sàn G1
                        match_trade = next(
                            (
                                t
                                for t in trades
                                if t.get("boardId") == "G1"
                                and float(t.get("matchPrice") or 0) > 0
                            ),
                            None,
                        )
                        if not match_trade:
                            match_trade = next(
                                (
                                    t
                                    for t in trades
                                    if float(t.get("matchPrice") or 0) > 0
                                ),
                                None,
                            )

                        price = (
                            float(match_trade.get("matchPrice") or 0)
                            if match_trade
                            else 0.0
                        )
                        sec_def = defs[0]
                        basic = float(sec_def.get("basicPrice") or 0)
                        ceil_p = float(sec_def.get("ceilingPrice") or 0)
                        flr_p = float(sec_def.get("floorPrice") or 0)

                        if price <= 0 or basic <= 0:
                            return sym, "no_change"

                        if ceil_p > 0 and price >= ceil_p:
                            return sym, "ceiling"
                        if flr_p > 0 and price <= flr_p:
                            return sym, "floor"
                        if price > basic:
                            return sym, "advance"
                        if price < basic:
                            return sym, "decline"
                        return sym, "no_change"
                except Exception:
                    pass
                return sym, None

            if symbols:
                max_w = min(25, len(symbols))
                with ThreadPoolExecutor(max_workers=max_w) as executor:
                    futures = [executor.submit(_classify_symbol, s) for s in symbols]
                    for fut in as_completed(futures):
                        sym, cat = fut.result()
                        if cat == "ceiling":
                            ceil_list.append(sym)
                        elif cat == "floor":
                            flr_list.append(sym)
                        elif cat == "advance":
                            adv_list.append(sym)
                        elif cat == "decline":
                            dec_list.append(sym)
                        elif cat == "no_change" or cat is None:
                            nc_list.append(sym)

            ceil_list.sort()
            adv_list.sort()
            nc_list.sort()
            dec_list.sort()
            flr_list.sort()

        except Exception as e:
            logger.warning(
                "DNSEClient.get_market_breadth_detail thất bại cho %s: %s", norm, e
            )

        total_cnt = (
            len(ceil_list)
            + len(adv_list)
            + len(nc_list)
            + len(dec_list)
            + len(flr_list)
        )
        res = MarketBreadthDetailResponse(
            index_code=norm,
            ceiling=ceil_list,
            advance=adv_list,
            no_change=nc_list,
            decline=dec_list,
            floor=flr_list,
            total=total_cnt,
        )
        if total_cnt > 0:
            realtime_cache.set(cache_key, res.model_dump(), ttl=30)
        return res
