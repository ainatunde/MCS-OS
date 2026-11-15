"""Morning briefing (D01): once a day at 07:00 WAT, never twice, retried on failure, always sent even when a
source is down, and watched by the Guardian."""
from datetime import datetime
import json
import time

import httpx
import pytest

from services.control import briefing
from services.control.briefing import LAGOS, briefing_current, render, run_once
from services.control.store import Action, Base, Record, Store, digest

PULZZ = {"subscribers": {"total": 1250, "new": 4, "paid_active": 3},
         "plan_requests": {"new": 1, "new_value": {"NGN": 50000}, "waiting": 1, "by_status": {}, "decided": {}},
         "sponsorships": {"live": 1, "booked_minor": {"NGN": 1200000}},
         "supplier_leads": {"new": 2, "delivered": 1},
         "guardian": {"open": 1, "by_severity": {"critical": 1}, "critical_checks": ["web_ready"]},
         "corporate_bridge": {"status": "healthy", "errors": []}}
ERP = {"receivables": {"open_invoices": 3, "outstanding": {"NGN": "150000.00"}, "overdue_invoices": 1, "overdue": {"NGN": "20000"}},
       "draft_invoices": 0, "invoices_posted_or_changed": {"count": 2, "value": {"NGN": "70000"}},
       "payments_received": {"count": 1, "value": {"NGN": "50000"}},
       "payables": {"open_bills": 0, "outstanding": {}, "overdue_bills": 0}}


def at(day: str, hh: int, mm: int = 0) -> float:
    return datetime.strptime(f"{day} {hh:02d}:{mm:02d}", "%Y-%m-%d %H:%M").replace(tzinfo=LAGOS).timestamp()


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.setenv("MCS_OS_ENV", "development")
    monkeypatch.setenv("PULZZ_URL", "http://pulzz.test")
    monkeypatch.setenv("MCS_PULZZ_RECEIPT_TOKEN", "fixture-receipt-token-32-characters-minimum")
    monkeypatch.setenv("MCS_PULZZ_SIGNING_SECRET", "fixture-signing-secret-32-characters-minimum")
    monkeypatch.setenv("MCS_ERP_GATEWAY_URL", "http://gateway.test")
    monkeypatch.setenv("MCS_ERP_GATEWAY_TOKEN", "fixture-gateway-token-32-characters-minimum")
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"last_success_at": time.time() - 3600, "last_result": "ok", "last_bytes": 2_470_000_000}))
    monkeypatch.setenv("MCS_BACKUP_STATUS_FILE", str(status))
    st = Store("sqlite:///" + str(tmp_path / "control.db"))
    Base.metadata.drop_all(st.engine)
    st.migrate()
    yield st
    st.engine.dispose()


def client(pulzz=200, erp=200):
    def handler(request):
        if request.url.host == "pulzz.test":
            assert request.headers["X-MCS-Signature"] and request.url.path.endswith("/summary")
            return httpx.Response(pulzz, json=PULZZ)
        assert request.headers["Authorization"].startswith("Bearer ") and request.url.path == "/v1/summary"
        return httpx.Response(erp, json=ERP)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_sends_once_a_day_from_seven_lagos_time(store):
    sent = []
    sender = lambda *m: sent.append(m)
    assert run_once(store, at("2026-11-16", 6, 59), client=client(), sender=sender) == "not_due"
    assert run_once(store, at("2026-11-16", 7, 0), client=client(), sender=sender) == "sent"
    assert run_once(store, at("2026-11-16", 9, 0), client=client(), sender=sender) == "already_sent"
    assert run_once(store, at("2026-11-17", 7, 5), client=client(), sender=sender) == "sent"
    assert len(sent) == 2
    with store.transaction() as s:
        body = s.get(Record, ("briefing", "2026-11-16")).body
        assert body["status"] == "sent" and body["subject"].startswith("MCS briefing Mon 16 Nov") and body["sources_missing"] == []


def test_a_running_send_is_not_repeated_and_a_failure_retries_after_ten_minutes(store):
    with store.transaction() as s:
        store.put(s, "briefing", "2026-11-16", {"status": "sending", "claimed_at": at("2026-11-16", 7, 0), "attempts": 1})
    assert run_once(store, at("2026-11-16", 7, 2), client=client(), sender=lambda *m: None) == "in_progress"

    def broken(*m):
        raise OSError("smtp down")
    assert run_once(store, at("2026-11-16", 7, 6), client=client(), sender=broken) == "failed"
    with store.transaction() as s:
        assert s.get(Record, ("briefing", "2026-11-16")).body == {"day": "2026-11-16", "status": "failed", "attempts": 2,
                                                                 "attempted_at": at("2026-11-16", 7, 6), "error": "OSError"}
    assert run_once(store, at("2026-11-16", 7, 10), client=client(), sender=lambda *m: None) == "waiting_retry"
    assert run_once(store, at("2026-11-16", 7, 17), client=client(), sender=lambda *m: None) == "sent"


def test_a_source_that_is_down_is_named_and_the_briefing_still_goes(store):
    sent = []
    assert run_once(store, at("2026-11-16", 7, 0), client=client(pulzz=503), sender=lambda *m: sent.append(m)) == "sent"
    subject, text, html = sent[0]
    assert "Pulzz figures unavailable (HTTP 503)" in text and "Owed to us: NGN 150,000 on 3 invoices" in text
    with store.transaction() as s:
        assert s.get(Record, ("briefing", "2026-11-16")).body["sources_missing"] == ["pulzz"]


def test_the_email_puts_what_needs_the_owner_first(store):
    with store.transaction() as s:
        payload = {"target_external_ref": "tvinsights:plan_request:9"}
        s.add(Action(action_id="void-9", idempotency_key="k9", product_slug="tv-insights", department_id="D06",
                     provider="mcs-erp", envelope={"action_type": "finance.invoice.void_draft.v1", "payload": payload},
                     input_hash=digest(payload), status="awaiting_approval", created_at=at("2026-11-16", 5, 0)))
        store.put(s, "heartbeat", "integration-guardian", {"checks": {"a": True, "offhost_backup_fresh": True}})
    import os
    with open(os.environ["MCS_BACKUP_STATUS_FILE"], "w") as handle:
        json.dump({"last_success_at": at("2026-11-16", 6, 0), "last_result": "ok", "last_bytes": 2_470_000_000}, handle)
    data = briefing.gather(store, client(), at("2026-11-16", 7, 0))
    subject, text, html = render(data)
    assert subject == "MCS briefing Mon 16 Nov: 4 items need you"
    needs = text.split("NEEDS YOU")[1].split("PULZZ")[0]
    assert "Approval waiting: finance.invoice.void_draft.v1 (D06), 2.0 h old" in needs
    assert "Overdue customer invoices: 1 (NGN 20,000)" in needs and "Pulzz plan requests waiting: 1" in needs
    assert "Pulzz critical: web_ready" in needs
    assert "Sponsorships live: 1 (NGN 12,000 booked)" in text and "Subscribers: 1,250 (4 new), 3 on a paid plan" in text
    assert "Checks: 2 of 2 passing" in text and "Last off-host backup 1.0 h ago, 2.47 GB" in text
    assert "<script" not in html and "Needs you" in html


def test_all_clear_when_nothing_needs_the_owner(store):
    quiet = {**PULZZ, "plan_requests": {**PULZZ["plan_requests"], "waiting": 0}, "guardian": {"open": 0, "critical_checks": []}}
    data = {"day": "2026-11-16", "errors": {}, "pulzz": quiet,
            "erp": {**ERP, "receivables": {**ERP["receivables"], "overdue_invoices": 0}},
            "os": {"waiting": [], "blocked": [], "checks_failing": [], "checks_total": 16, "done": {}, "findings": []},
            "backup": {"ok": True, "hours_ago": 4.5, "gb": 2.47}}
    subject, text, _ = render(data)
    assert subject == "MCS briefing Mon 16 Nov: all clear" and "Nothing needs you today." in text


def test_guardian_reports_a_missed_or_stalled_briefing(store):
    assert briefing_current(store, at("2026-11-16", 6, 0)) is False                   # no sender heartbeat yet
    with store.transaction() as s:
        store.put(s, "heartbeat", "briefing", {"at": time.time()})
    now = time.time()
    local = datetime.fromtimestamp(now, LAGOS)
    expected_fresh = (local.hour, local.minute) < (7, 30)                              # fresh install: only a due day counts
    assert briefing_current(store, now) is expected_fresh
    with store.transaction() as s:
        store.put(s, "briefing", briefing.lagos_day(now), {"status": "sent"})
        store.put(s, "briefing", briefing.lagos_day(now - 86400), {"status": "sent"})
    assert briefing_current(store, now) is True
    with store.transaction() as s:
        s.get(Record, ("heartbeat", "briefing")).updated_at = now - 600
    assert briefing_current(store, now) is False                                       # the sender stopped
