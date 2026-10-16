#!/usr/bin/env bash
# ==============================================================================
# MCS-OS Canonical Local CI & Assurance Qualification Gate (MCS-OS v2.2 W12)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " Starting MCS-OS Corporate Operating System CI Pipeline   "
echo " Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')                  "
echo " System: Multimedia Cloud Solutions (MCS-OS v2.2)         "
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}"

echo ">> 1. Verifying Python & Environment..."
if [ -z "${PYTHON_BIN:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi
echo "Using Python binary: ${PYTHON_BIN}"
"${PYTHON_BIN}" --version

echo ">> 2. Validating Action Envelope & Event Envelope Cryptographic Hashing..."
"${PYTHON_BIN}" -c "
from contracts.actions.envelope import ActionEnvelope, AuthorityClass, canonical_payload_hash
assert canonical_payload_hash({'test': 1}) == '1da06016289bd76a5ada4f52fc805ae0c394612f17ec6d0f0c29b636473c8a9d'
print('  [PASS] Cryptographic canonical hash invariant verified.')
"

echo ">> 3. Validating PostgreSQL 16 8-Role Least-Privilege DDL..."
"${PYTHON_BIN}" -c "
from database.schema_sql import POSTGRES_SCHEMA_SQL
for r in ['mcs_migration_role', 'mcs_ingress_role', 'mcs_planner_role', 'mcs_approver_role', 'mcs_policy_role', 'mcs_executor_role', 'mcs_reconciler_role', 'mcs_auditor_role']:
    assert r in POSTGRES_SCHEMA_SQL
print('  [PASS] 8-role least-privilege DDL schema verified.')
"

echo ">> 4. Validating All 11 Department Charters..."
"${PYTHON_BIN}" -c "
import yaml, glob
for i in range(1, 12):
    files = glob.glob(f'charters/d{i:02d}_*.yaml')
    assert len(files) == 1, f'Missing charter for D{i:02d}'
    with open(files[0], 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        assert data['department_id'] == f'D{i:02d}'
print('  [PASS] All 11 department charters structurally valid.')
"

echo ">> 5. Running Comprehensive Acceptance Test Suite (L01-L20)..."
"${PYTHON_BIN}" -m pytest tests/ -v --tb=short

echo "=========================================================="
echo " [SUCCESS] MCS-OS CI Gate Qualified: All Tests PASSED     "
echo " Ready for Single Integrated Launch Dossier Packaging     "
echo "=========================================================="
