"""SQLAlchemy Models for MCS-OS Authoritative Control Plane (PostgreSQL 16).

Governed by MCS-OS Master Specification v2.2 Section 7:
  - 7.1 Execution lifecycle
  - 7.2 Task, Action, Approval, and Budget state machines
  - 7.3 Required relational entities
  - 7.4 Database invariants & atomic concurrency
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OSProduct(Base):
    __tablename__ = "os_products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    environment = Column(String(32), nullable=False, default="production")
    status = Column(String(32), nullable=False, default="active")  # active, paused, halted
    health_status = Column(String(32), nullable=False, default="healthy")  # healthy, degraded, down
    manifest_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class OSDepartment(Base):
    __tablename__ = "os_departments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(8), unique=True, nullable=False, index=True)  # D01 - D11
    name = Column(String(128), nullable=False)
    accountable_role = Column(String(64), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class OSAgentCharter(Base):
    __tablename__ = "os_agent_charters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_slug = Column(String(64), unique=True, nullable=False, index=True)
    department_code = Column(String(8), ForeignKey("os_departments.code"), nullable=False)
    product_slug = Column(String(64), nullable=True)  # NULL = corporate-wide
    primary_objective = Column(Text, nullable=False)
    authority_policy = Column(JSONB, nullable=False, default=dict)
    daily_cost_limit_usd = Column(Numeric(8, 4), nullable=False, default=2.0000)
    is_enabled = Column(Boolean, nullable=False, default=True)
    kill_switch_tripped = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class OSInboxEvent(Base):
    __tablename__ = "os_inbox_events"

    event_id = Column(String(128), primary_key=True)
    producer = Column(String(64), nullable=False, index=True)
    schema_version = Column(String(16), nullable=False, default="v1")
    product_slug = Column(String(64), nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    correlation_id = Column(String(128), nullable=False, index=True)
    causation_id = Column(String(128), nullable=True)
    payload_hash = Column(String(64), nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="unprocessed")  # unprocessed, processed, quarantined

    __table_args__ = (
        UniqueConstraint("producer", "event_id", name="uq_producer_event_id"),
    )


class OSTask(Base):
    __tablename__ = "os_tasks"

    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    department_code = Column(String(8), ForeignKey("os_departments.code"), nullable=False)
    product_slug = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    state = Column(String(32), nullable=False, default="observed", index=True)
    # observed, ready, planning, awaiting_approval, executing, verifying, blocked, completed, failed, abstained, cancelled
    priority = Column(Integer, nullable=False, default=3)
    langgraph_thread_id = Column(String(128), nullable=True, index=True)
    evidence_packet = Column(JSONB, nullable=False, default=dict)
    acceptance_criteria = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class OSActionOutbox(Base):
    __tablename__ = "os_action_outbox"

    action_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("os_tasks.task_id"), nullable=False)
    department_code = Column(String(8), ForeignKey("os_departments.code"), nullable=False)
    product_slug = Column(String(64), nullable=False, index=True)
    action_type = Column(String(128), nullable=False, index=True)
    authority_class = Column(String(4), nullable=False)  # A0, A1, A2, A3, A4
    idempotency_key = Column(String(256), unique=True, nullable=False, index=True)
    fencing_token = Column(BigInteger, nullable=False, default=0)
    canonical_payload_hash = Column(String(64), nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    authorization_ref = Column(String(128), nullable=True)

    execution_state = Column(String(32), nullable=False, default="proposed", index=True)
    # proposed, awaiting_approval, ready, leased, dispatching, provider_pending, confirmed, outcome_unknown, retry_wait, rejected, cancelled, expired, failed
    outcome_state = Column(String(32), nullable=False, default="pending", index=True)
    # not_applied, pending, applied, partially_applied, cancelled, unknown, not_supported

    lease_owner = Column(String(64), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)

    provider_reference = Column(String(128), nullable=True)
    provider_receipt = Column(JSONB, nullable=True)
    error_detail = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)


class OSApproval(Base):
    __tablename__ = "os_approvals"

    approval_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String(36), ForeignKey("os_action_outbox.action_id"), nullable=False)
    approver_id = Column(String(64), nullable=False)
    canonical_payload_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="granted")  # granted, denied, revoked, expired, superseded
    granted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class OSBudget(Base):
    __tablename__ = "os_budgets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cost_center = Column(String(64), nullable=False, index=True)
    period_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD (Africa/Lagos)
    currency = Column(String(4), nullable=False, default="USD")
    daily_ceiling_usd = Column(Numeric(10, 4), nullable=False, default=15.0000)
    reserved_usd = Column(Numeric(10, 4), nullable=False, default=0.0000)
    settled_usd = Column(Numeric(10, 4), nullable=False, default=0.0000)
    uncertain_usd = Column(Numeric(10, 4), nullable=False, default=0.0000)

    __table_args__ = (
        UniqueConstraint("cost_center", "period_date", name="uq_budget_cost_center_period"),
    )


class OSAuditEvent(Base):
    __tablename__ = "os_audit_events"

    audit_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(64), nullable=False, index=True)
    actor_role = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(128), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    details = Column(JSONB, nullable=False, default=dict)
