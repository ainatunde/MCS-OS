"""Durable event routing, scoped provider effects and receipt delivery.

An expired dispatched lease is reconciled, never blindly resent. The ERP owns
operation idempotency and the product owns source eligibility/receipt application.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import time
import uuid

import httpx
from sqlalchemy import or_, select

from services.control.security import DEPARTMENTS, signed_headers, validate_provider_session
from services.control.store import Action, Event, Identity, Record, Store, configured_store, digest

log = logging.getLogger(__name__)
KINDS = {"plan_request": "TV-Insights Subscription", "intel_report": "TV-Insights Intelligence Report", "lead_assignment": "TV-Insights Lead Delivery", "sponsorship": "TV-Insights Sponsorship"}


class IntegrationWorker:
    def __init__(self, store: Store, client=None):
        self.store = store
        self.client = client or httpx.Client(timeout=20, follow_redirects=False)
        self.owner = str(uuid.uuid4())
        self.company = os.environ.get("ERP_COMPANY", "Multimedia Cloud Solutions Ltd.")

    def enqueue(self, s, key, kind, department, payload, event, dependency=None):
        action_id = "int-" + digest(key)[:48]
        original = {"schema_version": 1, "action_id": action_id, "revision_id": "1", "action_type": kind, "department_id": department, "product_slug": "tv-insights", "company": self.company, "idempotency_key": key, "payload": payload, "canonical_payload_hash": digest(payload), "authorization_ref": "standing:pulzz-integration:v1"}
        existing = s.get(Action, action_id)
        if existing:
            if existing.envelope["payload"] != payload:
                raise ValueError("Economic key reused with changed financial payload; reconciliation required")
            return action_id
        row = Action(action_id=action_id, idempotency_key=key, product_slug="tv-insights", department_id=department, provider="mcs-erp", envelope=original, input_hash=digest(original), dependency_id=dependency, event_id=event.event_id, status="ready", callback_state="none")
        s.add(row)
        return action_id

    def route_one(self):
        with self.store.transaction() as s:
            e = s.scalar(select(Event).where(Event.status == "received").order_by(Event.received_at).with_for_update(skip_locked=True).limit(1))
            if e is None:
                return False
            try:
                with s.begin_nested():
                    p = e.envelope["payload"]
                    if e.producer != "tv-insights" or e.product_slug != "tv-insights":
                        raise ValueError("No qualified workflow for producer/product")
                    if p.get("source_kind") not in {*KINDS, "lead", "sponsorship"} or not p.get("source_revision"):
                        raise ValueError("Versioned source identity required")
                    if p.get("company", self.company) != self.company:
                        raise ValueError("Source company scope mismatch")
                    self.store.put(s, "task", e.event_id, {"department_id": "D02" if p["source_kind"] == "lead" else "D06", "product_slug": e.product_slug, "source_kind": p["source_kind"], "source_id": p["source_id"], "source_revision": p["source_revision"], "status": "observed", "event_id": e.event_id}, e.product_slug)
                    if e.event_type == "commercial.source.withdrawn.v1":
                        original = s.get(Action, "int-" + digest(p["external_ref"])[:48])
                        if p["source_kind"] == "lead" and original:
                            original.callback_state = "none"
                            original.callback_body = None
                            # Keep the original input hash for audit, erase copied contacts.
                            original.envelope = {**original.envelope, "payload": {"lead_name": "Withdrawn Pulzz contact"}}
                            for old_event in s.scalars(select(Event).where(Event.producer == e.producer)):
                                old_payload = old_event.envelope.get("payload", {})
                                if old_payload.get("source_kind") == "lead" and old_payload.get("source_id") == p["source_id"]:
                                    old_event.envelope = {**old_event.envelope, "payload": {k: v for k, v in old_payload.items() if k not in {"customer", "lead_name", "contact_email", "contact_phone", "title", "organisation"}}}
                            if original.status in {"ready", "leased", "awaiting_approval"} and not original.reconcile_only:
                                original.status = "cancelled"
                            else:
                                target = self.enqueue(s, p["external_ref"] + ":suppress:" + p["source_revision"][:16], "crm.lead.suppress.v1", "D02", {"target_external_ref": p["external_ref"]}, e, original.action_id)
                                s.flush()
                                s.get(Action, target).document_sequence = original.document_sequence + 1
                        e.status = "routed"
                        return True
                    if e.event_type not in {"commercial.order.requested.v1", "commercial.plan.requested.v1", "crm.lead.inquiry.v1"}:
                        raise ValueError("Unqualified source event type")
                    if not p.get("eligible_for_draft", p["source_kind"] == "lead"):
                        e.status, e.error = "blocked", "Commercial eligibility/contract requires review"
                        return True
                    if p["source_kind"] == "lead":
                        if not p.get("consent_version") or not p.get("consented_at"):
                            raise ValueError("CRM purpose/consent evidence required")
                        self.enqueue(s, p["external_ref"], "crm.lead.upsert.v1", "D02", {"lead_name": p["customer"]["name"], "email_id": p["customer"].get("email"), "company_name": p["customer"].get("organisation"), "status": "Lead"}, e)
                    else:
                        amount, currency = p.get("amount_minor"), p.get("currency")
                        if type(amount) is not int or amount <= 0 or currency not in {"NGN", "USD"}:
                            raise ValueError("Positive integer amount and qualified currency required")
                        c = p["customer"]
                        if not c.get("name"):
                            raise ValueError("Customer identity required")
                        customer_key = p["customer_ref"]
                        customer_id = self.enqueue(s, customer_key, "finance.customer.upsert.v1", "D06", {"customer_name": c["name"], "customer_type": "Company" if c.get("organisation") else "Individual", "customer_group": "Insights Suppliers" if p["source_kind"] == "lead_assignment" else "Insights Subscribers", "territory": "All Territories"}, e)
                        invoice = {"customer_ref": customer_key, "currency": currency, "company": self.company, "items": [{"item_code": KINDS[p["source_kind"]], "qty": 1, "rate": str(amount // 100) + "." + str(amount % 100).zfill(2), "cost_center": "TV-Insights-Pulzz - MCS"}], "cost_center": "TV-Insights-Pulzz - MCS", "source_invoice_reference": p.get("invoice_reference")}
                        self.enqueue(s, p["external_ref"], "finance.invoice.create_draft.v1", "D06", invoice, e, customer_id)
                    e.status = "routed"
                    self.store.audit(s, "workflow:D06", "event.routed", e.event_id)
            except (ValueError, KeyError, TypeError) as exc:
                e.status, e.error = "quarantined", str(exc)
                self.store.put(s, "incident", "event:" + e.event_id, {"summary": str(exc), "status": "open", "severity": "high", "product_slug": e.product_slug})
            return True

    def claim(self):
        now = time.time()
        with self.store.transaction() as s:
            # Recover only pre-dispatch leases; sent work becomes unknown.
            for old in s.scalars(select(Action).where(Action.status.in_(["leased", "dispatching"]), Action.lease_until < now).with_for_update(skip_locked=True)):
                if old.status == "dispatching":
                    old.reconcile_only = True
                    old.unknown_since = old.unknown_since or now
                old.status = "outcome_unknown" if old.reconcile_only else "ready"
                old.error = "Lease expired; provider reconciliation required" if old.status == "outcome_unknown" else None
            candidates = s.scalars(select(Action).where(Action.status.in_(["ready", "outcome_unknown"]), Action.next_attempt <= now).order_by(Action.created_at).with_for_update(skip_locked=True).limit(20))
            for row in candidates:
                if self.store.halted(s, row.product_slug):
                    continue
                if row.dependency_id:
                    parent = s.get(Action, row.dependency_id)
                    if not parent or parent.status != "confirmed":
                        continue
                reconciling = row.status == "outcome_unknown" or row.reconcile_only
                row.reconcile_only = reconciling
                row.status, row.lease_owner, row.lease_until = "leased", self.owner, now + 90
                row.fence += 1
                row.attempts += 1
                row.updated_at = now
                return row.action_id, row.fence, reconciling
        return None

    def _gateway(self, body=None, key=None):
        url = os.environ["MCS_ERP_GATEWAY_URL"].rstrip("/")
        token, secret = os.environ["MCS_ERP_GATEWAY_TOKEN"], os.environ["MCS_ERP_SIGNING_SECRET"]
        if key is not None:
            from urllib.parse import quote
            response = self.client.get(url + "/v1/outcomes/" + quote(key, safe=""), headers={"Authorization": "Bearer " + token})
        else:
            response = self.client.post(url + "/v1/actions", json=body, headers=signed_headers(token, secret, body))
        if response.status_code >= 400:
            raise RuntimeError("ERP gateway HTTP " + str(response.status_code))
        result = response.json()
        if result.get("operation_outcome") not in {"applied", "not_applied", "unknown", "pending"}:
            raise RuntimeError("Invalid ERP operation outcome")
        return result

    def execute_one(self):
        claimed = self.claim()
        if claimed is None:
            return False
        action_id, fence, reconciling = claimed
        dispatched = False
        try:
            # A signed historical event does not authorize a changed/withdrawn source.
            if not reconciling:
                with self.store.transaction() as s:
                    candidate = s.get(Action, action_id)
                    event = s.get(Event, ("tv-insights", candidate.event_id)) if candidate.event_id else None
                    source = event.envelope["payload"] if event else None
                if source:
                    from urllib.parse import quote
                    source_url = os.environ["PULZZ_URL"].rstrip("/") + "/api/integrations/mcs-os/sources/" + quote(source["source_kind"], safe="") + "/" + str(int(source["source_id"]))
                    observed = self.client.get(source_url, headers=signed_headers(os.environ["MCS_PULZZ_RECEIPT_TOKEN"], os.environ["MCS_PULZZ_SIGNING_SECRET"], {}))
                    if observed.status_code != 200:
                        raise RuntimeError("Source eligibility lookup unavailable")
                    current = observed.json()
                    current = current.get("payload", current)
                    withdrawal = event.event_type == "commercial.source.withdrawn.v1"
                    if current.get("source_revision") != source["source_revision"] or (bool(current.get("eligible_for_draft", current.get("source_kind") == "lead")) == withdrawal):
                        with self.store.transaction() as s:
                            row = s.get(Action, action_id, with_for_update=True)
                            if row.fence == fence:
                                row.status, row.error = "cancelled", "Product source changed or became ineligible"
                                self.store.put(s, "task", row.event_id, {"status": "cancelled", "department_id": row.department_id, "reason": row.error}, row.product_slug)
                        return True
            with self.store.transaction() as s:
                row = s.get(Action, action_id, with_for_update=True)
                if row.lease_owner != self.owner or row.fence != fence:
                    return True
                if self.store.halted(s, row.product_slug):
                    row.status = "ready"
                    return True
                if row.provider != "mcs-erp":
                    row.status, row.error = "blocked", "Product action not qualified for autonomous dispatch"
                    return True
                if row.effective_authority == "A3":
                    a = row.approval or {}
                    identity = s.get(Identity, a.get("actor_id", ""))
                    parent = s.get(Identity, identity.parent_id) if identity and identity.parent_id else identity
                    valid_identity = identity and identity.enabled and (identity.expires_at is None or identity.expires_at > time.time()) and parent and parent.enabled and parent.role == identity.role
                    allowed = DEPARTMENTS.get(identity.role, []) if identity else []
                    if not valid_identity or not validate_provider_session(identity) or ("*" not in allowed and row.department_id not in allowed) or a.get("revoked") or a.get("input_hash") != row.input_hash or a.get("expires_at", 0) <= time.time():
                        row.status, row.error = "awaiting_approval", "Approval expired/revoked"
                        return True
                body = dict(row.envelope)
                if body.get("task_id"):
                    from contracts.actions.envelope import ActionEnvelope
                    from services.policy.engine import PolicyEngine
                    engine = PolicyEngine()
                    checked = ActionEnvelope.model_validate(body)
                    checked.authorization_ref = "verified:" + row.action_id
                    if row.approval:
                        engine.record_approval(checked.authorization_ref, checked.canonical_payload_hash)
                    decision = engine.evaluate(checked)
                    if not decision.admitted:
                        row.status, row.error = decision.promoted_state, "; ".join(decision.reasons)
                        return True
                    body = {"schema_version": 1, "action_id": row.action_id, "revision_id": "1", "action_type": checked.action_type, "department_id": row.department_id, "product_slug": row.product_slug, "company": self.company, "idempotency_key": row.idempotency_key, "payload": checked.payload, "canonical_payload_hash": checked.canonical_payload_hash, "authorization_ref": checked.authorization_ref}
                body["fencing_token"] = fence
                if row.dependency_id and row.envelope["action_type"] != "crm.lead.suppress.v1":
                    parent = s.get(Action, row.dependency_id)
                    payload = dict(body["payload"])
                    payload.pop("customer_ref", None)
                    payload["customer"] = parent.receipt["provider_reference"]
                    body["payload"], body["canonical_payload_hash"] = payload, digest(payload)
                row.status = "dispatching"
                key = row.idempotency_key
            dispatched = True
            result = self._gateway(key=key) if reconciling else self._gateway(body=body)
            with self.store.transaction() as s:
                row = s.get(Action, action_id, with_for_update=True)
                if row.fence != fence or row.lease_owner != self.owner:
                    return True
                outcome = result.get("operation_outcome")
                if outcome == "applied":
                    if not result.get("provider_reference"):
                        raise RuntimeError("Missing provider effect reference")
                    if row.dependency_id and row.envelope["action_type"] != "crm.lead.suppress.v1":
                        source = s.get(Event, ("tv-insights", row.event_id)).envelope["payload"]
                        if result.get("amount_minor") != source["amount_minor"] or result.get("currency") != source["currency"]:
                            raise RuntimeError("ERP source amount or currency differs")
                    row.status, row.receipt, row.error = "confirmed", result, None
                    row.callback_state = "pending" if row.event_id and (row.dependency_id or row.envelope["action_type"] == "crm.lead.upsert.v1") else "none"
                    row.reconcile_only = False
                    self.store.audit(s, self.owner, "effect.confirmed", action_id, {"provider_reference": result.get("provider_reference"), "document_state": result.get("document_state")})
                elif outcome == "not_applied" and reconciling:
                    row.status, row.error = "ready", "Provider positively confirmed no effect"
                    row.reconcile_only, row.unknown_since = False, None
                else:
                    row.status, row.error = "outcome_unknown", "Provider outcome not confirmed"
                    row.reconcile_only, row.unknown_since = True, row.unknown_since or time.time()
                row.updated_at, row.next_attempt = time.time(), time.time() + 30
        except Exception as exc:
            # Error text intentionally excludes remote bodies, credentials and source PII.
            with self.store.transaction() as s:
                row = s.get(Action, action_id, with_for_update=True)
                if row.fence == fence and row.lease_owner == self.owner:
                    row.status, row.error = ("outcome_unknown" if dispatched or reconciling else "ready"), type(exc).__name__ + ": integration dependency unavailable"
                    row.reconcile_only = dispatched or reconciling
                    row.unknown_since = (row.unknown_since or time.time()) if row.reconcile_only else None
                    row.next_attempt, row.updated_at = time.time() + min(300, 15 * row.attempts), time.time()
        return True

    def deliver_one(self):
        # Commit the exact payload and a delivery lease BEFORE the network call.
        # A lost HTTP response reuses byte-equivalent content and receipt identity.
        now = time.time()
        with self.store.transaction() as s:
            for stale in s.scalars(select(Action).where(Action.callback_state == "sending", Action.lease_until < now).with_for_update(skip_locked=True)):
                stale.callback_state = "pending"
            row = s.scalar(select(Action).where(Action.callback_state == "pending", Action.next_attempt <= now).with_for_update(skip_locked=True).limit(1))
            if not row or self.store.halted(s, row.product_slug):
                return False
            e = s.get(Event, ("tv-insights", row.event_id))
            p, receipt = e.envelope["payload"], row.receipt
            body = row.callback_body or {"schema_version": 1, "receipt_id": "receipt:" + digest({"event_id": row.event_id, "provider": receipt["provider_reference"], "state": receipt["document_state"], "sequence": row.document_sequence}), "event_id": row.event_id, "product_slug": "tv-insights", "company": self.company, "source_kind": p["source_kind"], "source_id": p["source_id"], "source_revision": p["source_revision"], "provider_reference": receipt["provider_reference"], "document_state": receipt["document_state"], "operation_outcome": "applied", "occurred_at": datetime.now(timezone.utc).isoformat(), "amount_minor": receipt.get("amount_minor", 0), "currency": receipt.get("currency"), "sequence": row.document_sequence}
            row.callback_body, row.callback_state = body, "sending"
            row.lease_until, row.lease_owner = now + 90, self.owner
            action_id = row.action_id
        accepted = False
        try:
            url = os.environ["PULZZ_URL"].rstrip("/") + "/api/integrations/mcs-os/receipts"
            response = self.client.post(url, json=body, headers=signed_headers(os.environ["MCS_PULZZ_RECEIPT_TOKEN"], os.environ["MCS_PULZZ_SIGNING_SECRET"], body))
            accepted = response.status_code in {200, 201}
        except (httpx.HTTPError, RuntimeError, KeyError):
            pass
        with self.store.transaction() as s:
            row = s.get(Action, action_id, with_for_update=True)
            if row.lease_owner != self.owner or row.callback_body != body:
                return True
            row.callback_state = "delivered" if accepted else "pending"
            row.error = None if accepted else "Product receipt not accepted; retry pending"
            row.updated_at, row.next_attempt = time.time(), time.time() + 60
            if accepted:
                task = s.get(Record, ("task", row.event_id))
                if task:
                    task.body = {**task.body, "status": "completed", "provider_reference": row.receipt["provider_reference"], "document_state": row.receipt["document_state"]}
        return True

    def refresh_one(self):
        # ERP posting/allocation is independent of initial draft creation.
        with self.store.transaction() as s:
            row = s.scalar(select(Action).where(Action.status == "confirmed", Action.callback_state == "delivered", Action.next_attempt <= time.time()).with_for_update(skip_locked=True).limit(1))
            if not row:
                return False
            key, action_id = row.idempotency_key, row.action_id
            row.next_attempt = time.time() + 120
        try:
            result = self._gateway(key=key)
            if result.get("operation_outcome") != "applied":
                raise RuntimeError("Confirmed ERP record not observable")
            with self.store.transaction() as s:
                row = s.get(Action, action_id, with_for_update=True)
                if result.get("provider_reference") != row.receipt.get("provider_reference"):
                    raise RuntimeError("ERP reference changed")
                if result.get("amount_minor") != row.receipt.get("amount_minor") or result.get("currency") != row.receipt.get("currency"):
                    raise RuntimeError("ERP financial projection changed")
                if result.get("document_state") != row.receipt.get("document_state") or time.time() - row.updated_at >= 300:
                    row.receipt, row.callback_body = result, None
                    row.document_sequence += 1
                    row.callback_state, row.next_attempt = "pending", time.time()
                    row.updated_at = time.time()
                incident = s.get(Record, ("incident", "reconciliation:" + action_id))
                if incident:
                    incident.body = {**incident.body, "status": "resolved", "rechecked": True, "resolved_at": time.time()}
        except Exception:
            with self.store.transaction() as s:
                self.store.put(s, "incident", "reconciliation:" + action_id, {"status": "open", "severity": "high", "summary": "Previously confirmed ERP document could not be reconciled", "action_id": action_id})
        return True

    def cycle(self):
        self.route_one()
        self.execute_one()
        self.refresh_one()
        self.deliver_one()
        with self.store.transaction() as s:
            self.store.put(s, "heartbeat", "integration-worker", {"worker_id": self.owner, "at": time.time()})


def main():
    logging.basicConfig(level=logging.INFO)
    worker = IntegrationWorker(configured_store())
    while True:
        try:
            worker.cycle()
        except Exception as exc:
            log.error("Integration cycle failed: %s", type(exc).__name__)
        time.sleep(5)


if __name__ == "__main__":
    main()
