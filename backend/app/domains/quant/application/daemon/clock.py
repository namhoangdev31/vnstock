"""Vietnam market clock helpers for the autonomous quant daemon."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.simulation.domain.settlement import SettlementService

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@dataclass(frozen=True)
class MarketClockSnapshot:
    as_of: datetime
    session_phase: SessionPhase
    is_trading_window: bool


class VietnamMarketClock:
    def snapshot(self, dt: datetime | None = None) -> MarketClockSnapshot:
        as_of = dt or datetime.now(VN_TZ)
        vn_time = as_of.astimezone(_VN_TZ)
        phase = self.classify(vn_time)
        return MarketClockSnapshot(
            as_of=vn_time,
            session_phase=phase,
            is_trading_window=phase
            in {
                SessionPhase.PRE_ATO,
                SessionPhase.ATO,
                SessionPhase.MORNING_CONTINUOUS,
                SessionPhase.AFTERNOON_CONTINUOUS,
                SessionPhase.PRE_ATC,
                SessionPhase.ATC,
            },
        )

    @staticmethod
    def classify(dt: datetime) -> SessionPhase:
        vn_time = dt.astimezone(_VN_TZ)

        # Check for weekends and holidays first
        if not SettlementService.is_trading_day(vn_time.date()):
            return SessionPhase.OVERNIGHT_SIMULATION

        time_minutes = vn_time.hour * 60 + vn_time.minute

        if 510 <= time_minutes < 525:
            return SessionPhase.PRE_ATO
        if 525 <= time_minutes < 555:
            # 08:45–09:00: Derivatives pre-open/matching + 09:00–09:15: Equities ATO call auction
            return SessionPhase.ATO
        if 555 <= time_minutes < 690:
            # 09:15–11:30: Continuous trading
            return SessionPhase.MORNING_CONTINUOUS
        if 690 <= time_minutes < 780:
            return SessionPhase.MIDDAY_INTERMISSION
        if 780 <= time_minutes < 855:
            return SessionPhase.AFTERNOON_CONTINUOUS
        if 855 <= time_minutes < 870:
            return SessionPhase.PRE_ATC
        if 870 <= time_minutes < 885:
            return SessionPhase.ATC
        if 885 <= time_minutes < 1020:
            return SessionPhase.POST_MARKET
        if 1020 <= time_minutes <= 1440:
            return SessionPhase.OVERNIGHT_SIMULATION
        return SessionPhase.OVERNIGHT_SIMULATION
