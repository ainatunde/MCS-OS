"""Tests for Guardian Watchdog & External Heartbeat Monitor (MCS-OS v2.2 W10)."""

from datetime import datetime, timedelta, timezone
import pytest

from services.guardian.watchdog import GuardianWatchdog, ALLOWLISTED_RUNBOOKS
from services.guardian.external_monitor import ExternalHeartbeatMonitor


def test_guardian_watchdog_healthy_probe():
    watchdog = GuardianWatchdog()

    res = watchdog.check_service_health(
        service_name="control_api",
        health_fn=lambda: {"status": "healthy", "version": "2.2.0"},
    )
    assert res.status == "healthy"
    assert res.service_name == "control_api"
    assert len(watchdog.active_incidents) == 0


def test_guardian_watchdog_detects_failure_and_creates_incident():
    watchdog = GuardianWatchdog()

    def failing_service():
        raise ConnectionResetError("Connection refused by PostgreSQL backend")

    res = watchdog.check_service_health(
        service_name="postgres_pool",
        health_fn=failing_service,
    )
    assert res.status == "down"
    assert len(watchdog.active_incidents) == 1
    inc = list(watchdog.active_incidents.values())[0]
    assert inc.severity == "high"
    assert inc.affected_scope == "postgres_pool"
    assert "Connection refused" in inc.message


def test_guardian_watchdog_allowlisted_runbook_execution():
    watchdog = GuardianWatchdog()

    # Allowed runbook execution
    success = watchdog.execute_allowlisted_runbook(
        runbook_name="runbook.worker.reclaim_expired_leases.v1",
        scope="outbox_workers",
    )
    assert success is True
    assert len(watchdog.runbook_audit_log) == 1
    assert watchdog.runbook_audit_log[0]["runbook"] == "runbook.worker.reclaim_expired_leases.v1"


def test_guardian_watchdog_rejects_unallowlisted_runbook():
    watchdog = GuardianWatchdog()

    with pytest.raises(PermissionError) as exc_info:
        watchdog.execute_allowlisted_runbook(
            runbook_name="runbook.arbitrary.shell_patch.v1",
            scope="database",
        )
    assert "not in the allowlisted repair catalogue" in str(exc_info.value)


def test_external_heartbeat_monitor_healthy_and_timeout_alerts():
    monitor = ExternalHeartbeatMonitor(timeout_seconds=120)

    # 1. Normal heartbeat ping
    now = datetime.now(timezone.utc)
    monitor.record_heartbeat("control-api-primary", metrics={"p99_latency_ms": 1.4})

    # Within 30 seconds -> no alerts
    alerts = monitor.evaluate_liveness(current_time=now + timedelta(seconds=30))
    assert len(alerts) == 0

    # 2. Heartbeat lapsed beyond 120s (e.g. 150 seconds later)
    alerts = monitor.evaluate_liveness(current_time=now + timedelta(seconds=150))
    assert len(alerts) == 1
    assert alerts[0].alert_level == "CRITICAL"
    assert alerts[0].sender == "control-api-primary"
    assert alerts[0].last_seen_seconds_ago >= 150.0
    assert "CRITICAL: MCS-OS heartbeat lost" in alerts[0].message
