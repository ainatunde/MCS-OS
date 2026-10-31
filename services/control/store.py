"""Authoritative state. PostgreSQL in production; SQLite is for isolated tests only."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import time
import uuid

from sqlalchemy import Boolean, Float, Integer, JSON, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Base(DeclarativeBase):
    pass


class Identity(Base):
    __tablename__ = "os_control_identity"
    identity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16), default="operator")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    scopes: Mapped[dict] = mapped_column(JSON, default=dict)
    secret_env: Mapped[str | None] = mapped_column(String(128), nullable=True)
    secret_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Record(Base):
    __tablename__ = "os_control_record"
    namespace: Mapped[str] = mapped_column(String(32), primary_key=True)
    record_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    product_slug: Mapped[str] = mapped_column(String(64), default="corporate", index=True)
    body: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


class Event(Base):
    __tablename__ = "os_control_event"
    producer: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    product_slug: Mapped[str] = mapped_column(String(64), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    envelope: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[float] = mapped_column(Float, default=time.time)


class Action(Base):
    __tablename__ = "os_control_action"
    action_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), unique=True)
    product_slug: Mapped[str] = mapped_column(String(64), index=True)
    department_id: Mapped[str] = mapped_column(String(8), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    effective_authority: Mapped[str] = mapped_column(String(4), default="A2")
    envelope: Mapped[dict] = mapped_column(JSON)
    input_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True)
    dependency_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receipt: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    fence: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_attempt: Mapped[float] = mapped_column(Float, default=0)
    approval: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    callback_state: Mapped[str] = mapped_column(String(32), default="none", index=True)
    callback_body: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    document_sequence: Mapped[int] = mapped_column(Integer, default=0)
    reconcile_only: Mapped[bool] = mapped_column(Boolean, default=False)
    unknown_since: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


class Store:
    def __init__(self, url: str):
        production = os.getenv("MCS_OS_ENV", "development") != "development"
        if production and not url.startswith("postgresql"):
            raise RuntimeError("Production control state requires PostgreSQL")
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                kwargs["poolclass"] = StaticPool
        else:
            kwargs.update(pool_size=3, max_overflow=2, pool_timeout=5)
        self.engine = create_engine(url, **kwargs)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self):
        with self.sessions.begin() as session:
            yield session

    def migrate(self):
        Base.metadata.create_all(self.engine)
        with self.transaction() as s:
            self.put(s, "schema", "version", {"version": 1})

    @staticmethod
    def put(s, namespace, key, body, product="corporate"):
        row = s.get(Record, (namespace, key))
        if row is None:
            row = Record(namespace=namespace, record_id=key, product_slug=product, body=body)
            s.add(row)
        else:
            row.body, row.updated_at = body, time.time()
        return row

    @staticmethod
    def audit(s, actor, operation, entity, details=None):
        Store.put(s, "audit", str(uuid.uuid4()), {"actor": actor, "operation": operation, "entity": entity, "details": details or {}, "at": time.time()})

    @staticmethod
    def halted(s, product):
        return s.get(Record, ("halt", "company_wide")) is not None or s.get(Record, ("halt", product)) is not None

    @staticmethod
    def public_action(row):
        return {"action_id": row.action_id, "product_slug": row.product_slug, "department_id": row.department_id, "provider": row.provider, "action_type": row.envelope["action_type"], "status": row.status, "receipt": row.receipt, "error": row.error, "callback_state": row.callback_state, "attempts": row.attempts, "created_at": row.created_at, "updated_at": row.updated_at}


def configured_store() -> Store:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL required; run migrations before starting")
    return Store(url)
