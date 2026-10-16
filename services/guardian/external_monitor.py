"""Independent External Heartbeat Monitor (MCS-OS v2.2 §4.1 & §8).

Operates in an independent failure domain from the main MCS-OS control plane.
Tracks heartbeat pings from the Control API and Guardian.
If a heartbeat is missing beyond the 120-second deadline threshold, issues
immediate high-priority founder alerts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class HeartbeatRecord:
    sender: str
    last_ping_at: datetime
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class FounderAlert:
    alert_id: str
    sender: str
    last_seen_seconds_ago: float
    alert_level: str  # WARNING, CRITICAL
    message: str
    dispatched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExternalHeartbeatMonitor:
    def __init__(self, timeout_seconds: int = 120):
        self.timeout_seconds = timeout_seconds
        self.heartbeats: Dict[str, HeartbeatRecord] = {}
        self.alerts_history: List[FounderAlert] = []

    def record_heartbeat(self, sender: str, metrics: Optional[Dict[str, float]] = None) -> None:
        """Records a fresh incoming heartbeat ping."""
        self.heartbeats[sender] = HeartbeatRecord(
            sender=sender,
            last_ping_at=datetime.now(timezone.utc),
            metrics=metrics or {},
        )

    def evaluate_liveness(self, current_time: Optional[datetime] = None) -> List[FounderAlert]:
        """Scans all registered heartbeats. Generates alerts for any missing > 120s."""
        now = current_time or datetime.now(timezone.utc)
        alerts: List[FounderAlert] = []

        for sender, hb in self.heartbeats.items():
            elapsed = (now - hb.last_ping_at).total_seconds()
            if elapsed > self.timeout_seconds:
                alert = FounderAlert(
                    alert_id=f"alert-{sender}-{now.strftime('%Y%m%d%H%M%S')}",
                    sender=sender,
                    last_seen_seconds_ago=round(elapsed, 1),
                    alert_level="CRITICAL",
                    message=(
                        f"CRITICAL: MCS-OS heartbeat lost for '{sender}'. "
                        f"No ping received for {elapsed:.1f}s (threshold: {self.timeout_seconds}s). "
                        f"Control plane may be unreachable."
                    ),
                )
                alerts.append(alert)
                self.alerts_history.append(alert)

        return alerts
