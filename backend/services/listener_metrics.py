"""
Phase 7: Listener metrics for throughput and resilience monitoring.

Simple in-memory counters; can be replaced with Prometheus later.
"""
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ListenerMetrics:
    """In-memory metrics for the transaction listener."""

    tips_processed_total: int = 0
    failed_mints_count: int = 0
    retry_success_count: int = 0
    retry_fail_count: int = 0
    indexer_query_errors: int = 0
    last_processed_round: int = 0
    current_round: int | None = None  # From algod status, updated periodically
    last_heartbeat: float = field(default_factory=time.monotonic)
    # Rolling window: tips in last 60 seconds
    _tips_minute_window: list[float] = field(default_factory=list)
    _window_seconds: float = 60.0

    def record_tip_processed(self) -> None:
        self.tips_processed_total += 1
        now = time.monotonic()
        self._tips_minute_window.append(now)
        self._prune_window(now)

    def record_mint_failed(self) -> None:
        self.failed_mints_count += 1

    def record_retry_success(self) -> None:
        self.retry_success_count += 1

    def record_retry_fail(self) -> None:
        self.retry_fail_count += 1

    def record_indexer_error(self) -> None:
        self.indexer_query_errors += 1

    def set_last_round(self, round_num: int) -> None:
        self.last_processed_round = round_num

    def heartbeat(self) -> None:
        self.last_heartbeat = time.monotonic()

    def _prune_window(self, now: float) -> None:
        cutoff = now - self._window_seconds
        self._tips_minute_window = [t for t in self._tips_minute_window if t > cutoff]

    @property
    def tips_per_minute(self) -> float:
        now = time.monotonic()
        self._prune_window(now)
        if not self._tips_minute_window:
            return 0.0
        elapsed = now - min(self._tips_minute_window)
        if elapsed <= 0:
            return 0.0
        return len(self._tips_minute_window) * (60.0 / elapsed)

    def to_dict(self) -> dict:
        lag = None
        if self.current_round is not None and self.last_processed_round > 0:
            lag = max(0, self.current_round - self.last_processed_round)
        return {
            "tips_processed_total": self.tips_processed_total,
            "failed_mints_count": self.failed_mints_count,
            "retry_success_count": self.retry_success_count,
            "retry_fail_count": self.retry_fail_count,
            "indexer_query_errors": self.indexer_query_errors,
            "last_processed_round": self.last_processed_round,
            "current_round": self.current_round,
            "listener_lag_rounds": lag,
            "tips_per_minute": round(self.tips_per_minute, 2),
            "heartbeat_age_seconds": round(time.monotonic() - self.last_heartbeat, 1),
        }


# Singleton metrics instance
_metrics: ListenerMetrics | None = None


def get_listener_metrics() -> ListenerMetrics:
    global _metrics
    if _metrics is None:
        _metrics = ListenerMetrics()
    return _metrics
