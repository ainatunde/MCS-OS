# ==============================================================================
# MCS-OS Canonical Local CI & Assurance Qualification Gate (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting MCS-OS Corporate Operating System CI Pipeline   " -ForegroundColor Cyan
Write-Host " Date: $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')         " -ForegroundColor Cyan
Write-Host " System: Multimedia Cloud Solutions (MCS-OS v2.2)         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$env:PYTHONPATH = $RepoRoot

$PythonBin = "python"
foreach ($Candidate in @(
    (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
    (Join-Path $RepoRoot "..\mcs-platform\.venv\Scripts\python.exe"),
    (Join-Path $RepoRoot "..\tv-insights\.venv\Scripts\python.exe"),
    (Join-Path $RepoRoot "..\AfricaSignal\.venv\Scripts\python.exe")
)) {
    if (Test-Path $Candidate) {
        $PythonBin = (Resolve-Path $Candidate).Path
        break
    }
}

Push-Location $RepoRoot
try {
    Write-Host ">> 1. Verifying Python & Environment..." -ForegroundColor Yellow
    & $PythonBin --version
    if ($LASTEXITCODE -ne 0) { throw "Python version check failed ($LASTEXITCODE)" }

    Write-Host ">> 2. Validating Cryptographic Hash Invariants..." -ForegroundColor Yellow
    & $PythonBin -c "
from contracts.actions.envelope import ActionEnvelope, AuthorityClass, canonical_payload_hash
assert canonical_payload_hash({'test': 1}) == '1da06016289bd76a5ada4f52fc805ae0c394612f17ec6d0f0c29b636473c8a9d'
print('  [PASS] Cryptographic canonical hash invariant verified.')
"
    if ($LASTEXITCODE -ne 0) { throw "Cryptographic hash invariant check failed ($LASTEXITCODE)" }

    Write-Host ">> 3. Validating PostgreSQL 16 8-Role Least-Privilege DDL..." -ForegroundColor Yellow
    & $PythonBin -c "
from database.schema_sql import POSTGRES_SCHEMA_SQL
for r in ['mcs_migration_role', 'mcs_ingress_role', 'mcs_planner_role', 'mcs_approver_role', 'mcs_policy_role', 'mcs_executor_role', 'mcs_reconciler_role', 'mcs_auditor_role']:
    assert r in POSTGRES_SCHEMA_SQL
print('  [PASS] 8-role least-privilege DDL schema verified.')
"
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL DDL check failed ($LASTEXITCODE)" }

    Write-Host ">> 4. Validating All 11 Department Charters..." -ForegroundColor Yellow
    & $PythonBin -c "
import yaml, glob
for i in range(1, 12):
    files = glob.glob(f'charters/d{i:02d}_*.yaml')
    assert len(files) == 1, f'Missing charter for D{i:02d}'
    with open(files[0], 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        assert data['department_id'] == f'D{i:02d}'
print('  [PASS] All 11 department charters structurally valid.')
"
    if ($LASTEXITCODE -ne 0) { throw "Department charter validation failed ($LASTEXITCODE)" }

    Write-Host ">> 5. Running Comprehensive Acceptance Test Suite (L01-L20)..." -ForegroundColor Yellow
    & $PythonBin -m pytest tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) { throw "Pytest suite failed ($LASTEXITCODE)" }

    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " [SUCCESS] MCS-OS CI Gate Qualified: All Tests PASSED     " -ForegroundColor Green
    Write-Host " Ready for Single Integrated Launch Dossier Packaging     " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} finally {
    Pop-Location
}
