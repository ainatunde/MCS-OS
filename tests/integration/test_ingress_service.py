"""Tests for services/ingress/service.py (Deduplication and Event Intake)."""

from datetime import datetime, timezone
import hashlib
import json
import pytest

from contracts.events.envelope import EventEnvelope
from services.ingress.service import IngressService


def make_event(event_id: str, payload: dict):
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    p_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return EventEnvelope(
        event_id=event_id,
        producer="cloudstream-vcp",
        schema_version="v1",
        product_slug="cloudstream-vcp",
        occurred_at=datetime.now(timezone.utc),
        correlation_id=f"corr-{event_id}",
        payload_hash=p_hash,
        payload=payload,
    )


def test_ingress_deduplication():
    service = IngressService()
    event = make_event("evt-100", {"ad_break_id": "ab-1", "impressions": 500})

    res1 = service.ingest(event)
    assert res1.accepted is True
    assert res1.is_duplicate is False

    # Second arrival of exact same event
    res2 = service.ingest(event)
    assert res2.accepted is True
    assert res2.is_duplicate is True


def test_ingress_different_events():
    service = IngressService()
    e1 = make_event("evt-1", {"value": 1})
    e2 = make_event("evt-2", {"value": 2})

    assert service.ingest(e1).is_duplicate is False
    assert service.ingest(e2).is_duplicate is False
