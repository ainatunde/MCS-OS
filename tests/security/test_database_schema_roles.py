"""Tests for PostgreSQL 16 Schema, Role Segregation, and Security Definer Procedures."""

import pytest
from database.schema_sql import POSTGRES_SCHEMA_SQL


def test_schema_sql_declares_all_eight_roles():
    required_roles = [
        "mcs_migration_role",
        "mcs_ingress_role",
        "mcs_planner_role",
        "mcs_approver_role",
        "mcs_policy_role",
        "mcs_executor_role",
        "mcs_reconciler_role",
        "mcs_auditor_role",
    ]
    for role in required_roles:
        assert role in POSTGRES_SCHEMA_SQL, f"Role {role} missing from POSTGRES_SCHEMA_SQL"


def test_security_definer_planner_forces_proposed_state():
    # Planner MUST NOT be able to insert 'ready' state or arbitrary fencing tokens
    assert "fn_planner_propose_action" in POSTGRES_SCHEMA_SQL
    assert "'proposed', 'pending', 0" in POSTGRES_SCHEMA_SQL


def test_security_definer_policy_requires_hash_match():
    # Policy promotion to 'ready' must match canonical_payload_hash
    assert "fn_policy_promote_ready" in POSTGRES_SCHEMA_SQL
    assert "canonical_payload_hash = p_expected_hash" in POSTGRES_SCHEMA_SQL


def test_security_definer_executor_uses_skip_locked():
    # Atomic worker claiming must use FOR UPDATE SKIP LOCKED
    assert "fn_executor_claim_and_lease" in POSTGRES_SCHEMA_SQL
    assert "FOR UPDATE SKIP LOCKED" in POSTGRES_SCHEMA_SQL


def test_revocations_and_least_privilege_grants():
    # Public must have writes revoked
    assert "REVOKE ALL ON os_action_outbox FROM PUBLIC" in POSTGRES_SCHEMA_SQL
    # Planner only gets EXECUTE on propose_action, not direct INSERT on outbox
    assert "GRANT EXECUTE ON FUNCTION fn_planner_propose_action TO mcs_planner_role" in POSTGRES_SCHEMA_SQL
    # Policy only gets EXECUTE on promote_ready
    assert "GRANT EXECUTE ON FUNCTION fn_policy_promote_ready TO mcs_policy_role" in POSTGRES_SCHEMA_SQL
    # Executor only gets EXECUTE on claim_and_lease
    assert "GRANT EXECUTE ON FUNCTION fn_executor_claim_and_lease TO mcs_executor_role" in POSTGRES_SCHEMA_SQL
    # Ingress role grants
    assert "GRANT SELECT, INSERT ON os_inbox_events TO mcs_ingress_role" in POSTGRES_SCHEMA_SQL
    # Approver role grants
    assert "GRANT SELECT, INSERT, UPDATE ON os_approvals TO mcs_approver_role" in POSTGRES_SCHEMA_SQL


def test_schema_includes_all_nine_tables_and_rls():
    tables = [
        "os_products",
        "os_departments",
        "os_agent_charters",
        "os_inbox_events",
        "os_tasks",
        "os_action_outbox",
        "os_approvals",
        "os_budgets",
        "os_audit_events",
    ]
    for table in tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in POSTGRES_SCHEMA_SQL

    assert "ALTER TABLE os_action_outbox ENABLE ROW LEVEL SECURITY" in POSTGRES_SCHEMA_SQL
    assert "ALTER TABLE os_tasks ENABLE ROW LEVEL SECURITY" in POSTGRES_SCHEMA_SQL
    assert "ALTER TABLE os_approvals ENABLE ROW LEVEL SECURITY" in POSTGRES_SCHEMA_SQL


def test_schema_roles_have_no_cleartext_passwords():
    assert "change_in_production" not in POSTGRES_SCHEMA_SQL
    assert "PASSWORD" not in POSTGRES_SCHEMA_SQL


def test_reconciler_settle_outcome_preserves_dispatched_at():
    assert "fn_reconciler_settle_outcome" in POSTGRES_SCHEMA_SQL
    assert "dispatched_at = COALESCE(dispatched_at, clock_timestamp())" in POSTGRES_SCHEMA_SQL
