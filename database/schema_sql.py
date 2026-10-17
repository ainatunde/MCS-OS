"""Authoritative PostgreSQL 16 DDL, Role Definitions, and SECURITY DEFINER Transitions.

Governed by MCS-OS Master Specification v2.2:
  - Section 4.2: Least privilege & failure domains.
  - Section 4.3: Database roles and enforceable transitions.
  - Section 7.4: Concurrency, monotonic fencing, and compare-and-swap versions.
"""

POSTGRES_SCHEMA_SQL = """
-- 1. Create the 8 distinct runtime roles (non-superuser, no BYPASSRLS, NOLOGIN until secret rotation)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_migration_role') THEN
        CREATE ROLE mcs_migration_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_ingress_role') THEN
        CREATE ROLE mcs_ingress_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_planner_role') THEN
        CREATE ROLE mcs_planner_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_approver_role') THEN
        CREATE ROLE mcs_approver_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_policy_role') THEN
        CREATE ROLE mcs_policy_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_executor_role') THEN
        CREATE ROLE mcs_executor_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_reconciler_role') THEN
        CREATE ROLE mcs_reconciler_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcs_auditor_role') THEN
        CREATE ROLE mcs_auditor_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
END $$;

-- 2. Core Control Plane Tables (All 9 tables matching database/models.py)
CREATE TABLE IF NOT EXISTS os_products (
    id VARCHAR(36) PRIMARY KEY,
    slug VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    environment VARCHAR(32) NOT NULL DEFAULT 'production',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    health_status VARCHAR(32) NOT NULL DEFAULT 'healthy',
    manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS os_departments (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(8) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    accountable_role VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS os_agent_charters (
    charter_id VARCHAR(64) PRIMARY KEY,
    department_code VARCHAR(8) NOT NULL REFERENCES os_departments(code),
    role_name VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL DEFAULT 'v2.2',
    authority_ceiling VARCHAR(4) NOT NULL DEFAULT 'A2',
    daily_budget_usd FLOAT NOT NULL DEFAULT 1.5,
    allowed_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    prohibited_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_halted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS os_inbox_events (
    event_id VARCHAR(64) PRIMARY KEY,
    producer VARCHAR(64) NOT NULL,
    product_slug VARCHAR(64) NOT NULL,
    schema_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    correlation_id VARCHAR(64) NOT NULL,
    causation_id VARCHAR(64),
    payload_hash VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    processed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS os_tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    department_code VARCHAR(8) NOT NULL REFERENCES os_departments(code),
    product_slug VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'observed',
    priority INT NOT NULL DEFAULT 3,
    langgraph_thread_id VARCHAR(128),
    evidence_packet JSONB NOT NULL DEFAULT '{}'::jsonb,
    acceptance_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS os_action_outbox (
    action_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL REFERENCES os_tasks(task_id),
    department_code VARCHAR(8) NOT NULL REFERENCES os_departments(code),
    product_slug VARCHAR(64) NOT NULL,
    action_type VARCHAR(128) NOT NULL,
    authority_class VARCHAR(4) NOT NULL,
    idempotency_key VARCHAR(256) UNIQUE NOT NULL,
    fencing_token BIGINT NOT NULL DEFAULT 0,
    canonical_payload_hash VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    authorization_ref VARCHAR(128),
    execution_state VARCHAR(32) NOT NULL DEFAULT 'proposed',
    outcome_state VARCHAR(32) NOT NULL DEFAULT 'pending',
    lease_owner VARCHAR(64),
    lease_expires_at TIMESTAMPTZ,
    attempt_count INT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ,
    provider_reference VARCHAR(128),
    provider_receipt JSONB,
    error_detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    dispatched_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS os_approvals (
    approval_id VARCHAR(36) PRIMARY KEY,
    action_id VARCHAR(36) NOT NULL REFERENCES os_action_outbox(action_id),
    approver_id VARCHAR(64) NOT NULL,
    canonical_payload_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'granted',
    granted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS os_budgets (
    budget_id VARCHAR(64) PRIMARY KEY,
    department_code VARCHAR(8) NOT NULL REFERENCES os_departments(code),
    budget_date VARCHAR(10) NOT NULL,
    daily_limit_usd FLOAT NOT NULL DEFAULT 15.0,
    reserved_usd FLOAT NOT NULL DEFAULT 0.0,
    spent_usd FLOAT NOT NULL DEFAULT 0.0,
    recovery_reserve_usd FLOAT NOT NULL DEFAULT 2.0
);

CREATE TABLE IF NOT EXISTS os_audit_events (
    audit_id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    actor_role VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Enable Row Level Security
ALTER TABLE os_action_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_approvals ENABLE ROW LEVEL SECURITY;

-- 3. Security Definer Stored Functions enforcing Role Boundaries (§4.3)

-- Function: Planner can only propose actions. execution_state is FORCED to 'proposed'.
CREATE OR REPLACE FUNCTION fn_planner_propose_action(
    p_action_id VARCHAR(36),
    p_task_id VARCHAR(36),
    p_dept VARCHAR(8),
    p_product VARCHAR(64),
    p_type VARCHAR(128),
    p_auth_class VARCHAR(4),
    p_idemp_key VARCHAR(256),
    p_hash VARCHAR(64),
    p_payload JSONB
) RETURNS VARCHAR(36)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    INSERT INTO os_action_outbox (
        action_id, task_id, department_code, product_slug, action_type,
        authority_class, idempotency_key, canonical_payload_hash, payload,
        execution_state, outcome_state, fencing_token
    ) VALUES (
        p_action_id, p_task_id, p_dept, p_product, p_type,
        p_auth_class, p_idemp_key, p_hash, p_payload,
        'proposed', 'pending', 0
    );
    RETURN p_action_id;
END;
$$;

-- Function: Policy service promotes eligible action to 'ready'
CREATE OR REPLACE FUNCTION fn_policy_promote_ready(
    p_action_id VARCHAR(36),
    p_expected_hash VARCHAR(64)
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_updated INT;
BEGIN
    UPDATE os_action_outbox
    SET execution_state = 'ready'
    WHERE action_id = p_action_id
      AND canonical_payload_hash = p_expected_hash
      AND execution_state IN ('proposed', 'awaiting_approval');
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$;

-- Function: Executor claims next ready action atomically using FOR UPDATE SKIP LOCKED
CREATE OR REPLACE FUNCTION fn_executor_claim_and_lease(
    p_worker_id VARCHAR(64),
    p_lease_duration_seconds INT
) RETURNS TABLE (
    r_action_id VARCHAR(36),
    r_fencing_token BIGINT,
    r_action_type VARCHAR(128),
    r_product_slug VARCHAR(64),
    r_payload JSONB,
    r_idempotency_key VARCHAR(256)
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    WITH target AS (
        SELECT action_id
        FROM os_action_outbox
        WHERE execution_state = 'ready'
           OR (execution_state = 'leased' AND lease_expires_at < clock_timestamp())
        ORDER BY created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    UPDATE os_action_outbox o
    SET execution_state = 'leased',
        lease_owner = p_worker_id,
        lease_expires_at = clock_timestamp() + (p_lease_duration_seconds || ' seconds')::interval,
        fencing_token = o.fencing_token + 1,
        attempt_count = o.attempt_count + 1
    FROM target
    WHERE o.action_id = target.action_id
    RETURNING o.action_id, o.fencing_token, o.action_type, o.product_slug, o.payload, o.idempotency_key;
END;
$$;

-- Function: Reconciler settles outcome without overwriting original dispatched_at
CREATE OR REPLACE FUNCTION fn_reconciler_settle_outcome(
    p_action_id VARCHAR(36),
    p_execution_state VARCHAR(32),
    p_outcome_state VARCHAR(32),
    p_receipt JSONB
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    UPDATE os_action_outbox
    SET execution_state = p_execution_state,
        outcome_state = p_outcome_state,
        provider_receipt = p_receipt,
        dispatched_at = COALESCE(dispatched_at, clock_timestamp())
    WHERE action_id = p_action_id
      AND execution_state IN ('leased', 'dispatching', 'provider_pending', 'outcome_unknown');
    RETURN FOUND;
END;
$$;

-- 4. Revoke direct writes to tables and grant narrow function execution
REVOKE ALL ON os_action_outbox FROM PUBLIC;
REVOKE ALL ON os_tasks FROM PUBLIC;
REVOKE ALL ON os_approvals FROM PUBLIC;
REVOKE ALL ON os_inbox_events FROM PUBLIC;

GRANT SELECT, INSERT ON os_inbox_events TO mcs_ingress_role;
GRANT SELECT, INSERT, UPDATE ON os_approvals TO mcs_approver_role;
GRANT SELECT ON os_action_outbox TO mcs_planner_role, mcs_policy_role, mcs_executor_role, mcs_reconciler_role, mcs_auditor_role, mcs_approver_role;
GRANT EXECUTE ON FUNCTION fn_planner_propose_action TO mcs_planner_role;
GRANT EXECUTE ON FUNCTION fn_policy_promote_ready TO mcs_policy_role;
GRANT EXECUTE ON FUNCTION fn_executor_claim_and_lease TO mcs_executor_role;
GRANT EXECUTE ON FUNCTION fn_reconciler_settle_outcome TO mcs_reconciler_role;
GRANT INSERT ON os_audit_events TO mcs_auditor_role, mcs_executor_role, mcs_policy_role, mcs_approver_role, mcs_ingress_role;
"""
