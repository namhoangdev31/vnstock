"""Application Service for Real-time Market News (iBoard News Ticker).

Thu thập và sàng lọc tin tức tài chính trong ngày hoặc ngày hôm trước (T và T-1)
từ các nguồn chính thống (CafeF, Vietstock), tự động nhận diện mã cổ phiếu
và phục vụ cho thanh marquee tiêu đề trên Bảng giá thông minh.
"""

from __future__ import annotations

import logging
import random
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from threading import Lock

from sqlmodel import Session

from app.core.models_base import VN_TZ
from app.domains.iboard.application.schemas import IBoardNewsItem

logger = logging.getLogger(__name__)

# Từ điển ánh xạ tên doanh nghiệp / thuật ngữ sang mã cổ phiếu tương ứng
COMPANY_KEYWORD_MAP: dict[str, str] = {
    "Vingroup": "VIC",
    "VinFast": "VFS",
    "Vinhomes": "VHM",
    "Vincom Retail": "VRE",
    "Hòa Phát": "HPG",
    "Hoa Phat": "HPG",
    "Hoa Sen": "HSG",
    "Nam Kim": "NKG",
    "FPT": "FPT",
    "Vietcombank": "VCB",
    "Techcombank": "TCB",
    "VietinBank": "CTG",
    "BIDV": "BID",
    "MBBank": "MBB",
    "MB Bank": "MBB",
    "VPBank": "VPB",
    "ACB": "ACB",
    "SHB": "SHB",
    "Novaland": "NVL",
    "Đất Xanh": "DXG",
    "Phát Đạt": "PDR",
    "Khang Điền": "KDH",
    "Nam Long": "NLG",
    "Masan": "MSN",
    "Thế Giới Di Động": "MWG",
    "Điện Máy Xanh": "MWG",
    "Bách Hóa Xanh": "MWG",
    "Vinamilk": "VNM",
    "Sabeco": "SAB",
    "Bảo Việt": "BVH",
    "PV GAS": "GAS",
    "PVD": "PVD",
    "PVS": "PVS",
    "BSR": "BSR",
    "SSI": "SSI",
    "VNDIRECT": "VND",
    "Vietcap": "VCI",
    "HSC": "HCM",
    "SHS": "SHS",
    "PNJ": "PNJ",
    "Phái sinh": "VN30F1M",
    "VN30F": "VN30F1M",
    "Hợp đồng tương lai": "VN30F1M",
    "VN-Index": "VNINDEX",
    "VN30": "VN30",
    "HNX": "HNX",
    "UPCoM": "UPCOM",
}

TICKER_REGEX = re.compile(r"\b([A-Z]{3}|VN30F1M|VNINDEX|VN30|HNX)\b")

# Các từ viết tắt 3 chữ cái không phải mã cổ phiếu
IGNORED_ACRONYMS = {
    "USD",
    "VND",
    "GDP",
    "CPI",
    "FED",
    "VTV",
    "IMF",
    "WTO",
    "VCCI",
    "UBCK",
    "DNSE",
    "VSD",
    "SCIC",
    "OPEC",
    "CEO",
    "EVN",
    "FDI",
    "DMC",
}

RSS_FEEDS = [
    "https://cafef.vn/thi-truong-chung-khoan.rss",
    "https://cafef.vn/doanh-nghiep.rss",
    "https://cafef.vn/tai-chinh-ngan-hang.rss",
]


class IBoardNewsService:
    """Use Case: Thu thập và xoay vòng tin tức tài chính trong ngày / hôm trước."""

    _cached_news: list[IBoardNewsItem] = []
    _last_fetched_ts: float = 0.0
    _ttl_seconds: float = 300.0  # 5 phút TTL
    _lock: Lock = Lock()

    @classmethod
    def _extract_symbol(cls, title: str) -> str:
        """Trích xuất mã cổ phiếu trọng tâm từ tiêu đề bài viết."""
        title_lower = title.lower()
        for kw, sym in COMPANY_KEYWORD_MAP.items():
            if kw.lower() in title_lower:
                return sym

        matches = TICKER_REGEX.findall(title)
        for m in matches:
            if m not in IGNORED_ACRONYMS:
                return m

        return "VN-INDEX"

    @classmethod
    def _fetch_rss_feeds(cls) -> list[IBoardNewsItem]:
        """Tải các nguồn RSS chính thức và trích xuất tin tức hôm nay / hôm trước."""
        now_vn = datetime.now(VN_TZ)
        today = now_vn.date()
        yesterday = today - timedelta(days=1)

        seen_titles: set[str] = set()
        news_items: list[IBoardNewsItem] = []

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        for url in RSS_FEEDS:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=4) as resp:
                    xml_bytes = resp.read()
                    root = ET.fromstring(xml_bytes)
                    for item in root.findall(".//item"):
                        title_el = item.find("title")
                        title = (
                            (title_el.text or "").strip()
                            if title_el is not None
                            else ""
                        )
                        if not title or title in seen_titles:
                            continue

                        seen_titles.add(title)
                        pub_el = item.find("pubDate")
                        pub_str = (
                            (pub_el.text or "").strip() if pub_el is not None else ""
                        )
                        link_el = item.find("link")
                        link = (
                            (link_el.text or "").strip() if link_el is not None else ""
                        )

                        try:
                            dt = parsedate_to_datetime(pub_str).astimezone(VN_TZ)
                        except Exception:
                            continue

                        item_date = dt.date()
                        # Chỉ lấy tin trong ngày hoặc ngày hôm trước (T hoặc T-1)
                        if item_date not in (today, yesterday):
                            continue

                        is_today = item_date == today
                        time_str = dt.strftime("%H:%M %d/%m")
                        symbol = cls._extract_symbol(title)

                        news_items.append(
                            IBoardNewsItem(
                                symbol=symbol,
                                title=title,
                                published_at=time_str,
                                url=link or None,
                                source="CafeF",
                                is_today=is_today,
                            )
                        )
            except Exception as e:
                logger.warning("Không thể tải RSS từ %s: %s", url, e)

        # Sắp xếp theo thứ tự mới nhất trước
        return news_items

    @classmethod
    def get_recent_news(
        cls,
        session: Session | None = None,
        limit: int = 30,
        randomize: bool = False,
    ) -> list[IBoardNewsItem]:
        """Truy xuất danh sách tin tức trong ngày hoặc ngày hôm trước.

        Áp dụng In-memory cache với TTL 5 phút.
        """
        now = time.time()
        with cls._lock:
            if not cls._cached_news or (now - cls._last_fetched_ts) > cls._ttl_seconds:
                fresh_items = cls._fetch_rss_feeds()
                if fresh_items:
                    cls._cached_news = fresh_items
                    cls._last_fetched_ts = now
                    logger.info(
                        "Đã cập nhật %d tin tức trong ngày/hôm trước vào cache iBoard",
                        len(fresh_items),
                    )

            result = list(cls._cached_news)

        if not result:
            return []

        if randomize:
            shuffled = list(result)
            random.shuffle(shuffled)
            return shuffled[:limit]

        return result[:limit]


__all__ = ["IBoardNewsService"]
