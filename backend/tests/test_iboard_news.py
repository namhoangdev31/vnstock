"""Unit test for iBoard Real-time Market News (T & T-1)."""

from unittest.mock import patch

from app.domains.iboard.application.news_service import IBoardNewsService
from app.domains.iboard.application.schemas import IBoardNewsItem


def test_extract_symbol_keywords() -> None:
    assert (
        IBoardNewsService._extract_symbol("Hòa Phát công bố kết quả kinh doanh")
        == "HPG"
    )
    assert (
        IBoardNewsService._extract_symbol("Novaland giải quyết vướng mắc pháp lý")
        == "NVL"
    )
    assert (
        IBoardNewsService._extract_symbol(
            "Thị trường phái sinh sôi động phiên cuối tuần"
        )
        == "VN30F1M"
    )
    assert IBoardNewsService._extract_symbol("FPT Software đạt mốc mới") == "FPT"
    assert IBoardNewsService._extract_symbol("VCB tiếp tục giữ đà tăng trưởng") == "VCB"
    assert (
        IBoardNewsService._extract_symbol("Tin thị trường chung không có mã")
        == "VN-INDEX"
    )


def test_get_recent_news_empty() -> None:
    with patch.object(IBoardNewsService, "_fetch_rss_feeds", return_value=[]):
        # Reset cache
        IBoardNewsService._cached_news = []
        IBoardNewsService._last_fetched_ts = 0.0

        items = IBoardNewsService.get_recent_news(session=None, limit=5)
        assert items == []


def test_get_recent_news_cached() -> None:
    dummy_item = IBoardNewsItem(
        symbol="HPG",
        title="Hòa Phát bứt phá mạnh mẽ",
        published_at="10:30 10/10",
        url="https://example.com/hpg",
        source="CafeF",
        is_today=True,
    )
    with patch.object(IBoardNewsService, "_fetch_rss_feeds", return_value=[dummy_item]):
        IBoardNewsService._cached_news = []
        IBoardNewsService._last_fetched_ts = 0.0

        items = IBoardNewsService.get_recent_news(session=None, limit=10)
        assert len(items) == 1
        assert items[0].symbol == "HPG"
        assert items[0].title == "Hòa Phát bứt phá mạnh mẽ"
