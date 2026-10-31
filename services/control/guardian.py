"""Persistent control-plane failure detection and bounded pre-dispatch repair."""
import logging
import time
from sqlalchemy import select
from services.control.store import Action, Event, Record, Store, configured_store


def inspect(store, now=None):
    now = time.time() if now is None else now
    checks = {}
    with store.transaction() as s:
        beat = s.get(Record, ("heartbeat", "integration-worker"))
        checks["integration_worker_heartbeat"] = bool(beat and now - beat.updated_at < 120)
        checks["integration_queue_lag"] = not bool(s.scalar(select(Event.event_id).where(Event.status == "received", Event.received_at < now - 300).limit(1)))
        checks["integration_unknown_outcomes"] = not bool(s.scalar(select(Action.action_id).where(Action.reconcile_only.is_(True), Action.unknown_since < now - 300).limit(1)))
        checks["pulzz_erp_receipt_delivery"] = not bool(s.scalar(select(Action.action_id).where(Action.callback_state == "pending", Action.created_at < now - 600).limit(1)))
        checks["integration_quarantine"] = not bool(s.scalar(select(Event.event_id).where(Event.status.in_(["quarantined", "blocked"])).limit(1)))
        checks["integration_action_failures"] = not bool(s.scalar(select(Action.action_id).where(Action.status.in_(["blocked", "rejected", "failed"])).limit(1)))
        checks["integration_action_lag"] = not bool(s.scalar(select(Action.action_id).where(Action.status == "ready", Action.created_at < now - 300).limit(1)))
        # Only unsent work is safely reclaimable without a provider lookup.
        for row in s.scalars(select(Action).where(Action.status == "leased", Action.lease_until < now).with_for_update(skip_locked=True)):
            row.status, row.lease_owner = ("outcome_unknown" if row.reconcile_only else "ready"), None
            store.audit(s, "guardian", "repair.unsent_lease_reclaimed", row.action_id)
        for name, good in checks.items():
            row = s.get(Record, ("incident", name))
            if not good:
                store.put(s, "incident", name, {"check": name, "status": "open", "severity": "high", "detected_at": row.body.get("detected_at", now) if row else now, "last_checked_at": now, "remediation": "Verify configuration, resume worker or reconcile provider outcome; never blindly replay ambiguous effects"})
            elif row and row.body.get("status") == "open":
                row.body = {**row.body, "status": "resolved", "resolved_at": now, "rechecked": True}
        store.put(s, "heartbeat", "integration-guardian", {"at": now, "checks": checks})
    return {"status": "healthy" if all(checks.values()) else "degraded", "checks": checks, "observed_at": now}


def main():
    store = configured_store()
    while True:
        try:
            inspect(store)
        except Exception:
            logging.exception("Guardian inspection failed")
        time.sleep(30)


if __name__ == "__main__":
    main()
