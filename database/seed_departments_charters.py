#!/usr/bin/env python3
"""Authoritative Seeder for MCS-OS Departments (D01-D11) & Executive Agent Charters.

Governed by MCS-OS Master Specification v2.2 (§2, §4.2, §4.3):
- D01: Executive Operations & COO (coo)
- D02: Sales & Commercial Partnerships (commercial_lead / cco)
- D03: Brand, Content & Communications (cmo)
- D04: Intelligence & Research (intelligence_lead)
- D05: Technology, Engineering & Reliability (cto)
- D06: Finance & Treasury Operations (cfo)
- D07: Customer Operations & Support (customer_ops_lead)
- D08: Venture & Product Development (product_lead / cpo)
- D09: Compliance & Legal Operations (general_counsel)
- D10: People & Vendor Operations (people_vendor_lead / chro)
- D11: Independent Assurance & Audit (chief_auditor)

Idempotent: Uses ON CONFLICT (code) DO UPDATE and ON CONFLICT (charter_id) DO UPDATE.
"""

import json
import os
from pathlib import Path
import sys
import uuid
import yaml

import psycopg

ACCOUNTABLE_ROLES = {
    "D01": "coo",
    "D02": "commercial_lead",
    "D03": "cmo",
    "D04": "intelligence_lead",
    "D05": "cto",
    "D06": "cfo",
    "D07": "customer_ops_lead",
    "D08": "product_lead",
    "D09": "general_counsel",
    "D10": "people_vendor_lead",
    "D11": "chief_auditor",
}


def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url.replace("postgresql+psycopg://", "postgresql://")
    return "postgresql://mcs_policy_role:79f678bf952c7f4ff8eac0f72b13e00c4459b872@127.0.0.1:5432/mcs_os"


def seed(conn):
    base_dir = Path(__file__).resolve().parent.parent
    charters_dir = base_dir / "charters"
    if not charters_dir.exists():
        sys.exit(f"Charters directory not found: {charters_dir}")

    files = sorted(charters_dir.glob("*.yaml"))
    if not files:
        sys.exit(f"No charter YAML files found in {charters_dir}")

    print(f"Found {len(files)} charter definitions in {charters_dir}")

    with conn.cursor() as cur:
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                cdata = yaml.safe_load(f)

            code = cdata.get("department_id")
            title = cdata.get("title", f"Department {code}")
            role = ACCOUNTABLE_ROLES.get(code, "lead")
            dept_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mcs:department:{code}"))

            # 1. Upsert os_departments
            cur.execute("""
                INSERT INTO os_departments (id, code, name, accountable_role, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    accountable_role = EXCLUDED.accountable_role,
                    is_active = TRUE
            """, (dept_id, code, title, role))

            # 2. Upsert os_agent_charters
            charter_id = cdata.get("charter_id", f"chr-{code.lower()}")
            version = cdata.get("version", "v2.2")
            action_classes = cdata.get("authorized_action_classes", ["A0", "A1", "A2"])
            ceiling = action_classes[-1] if action_classes else "A2"
            daily_budget = float(cdata.get("daily_budget_usd", 1.5))
            allowed = cdata.get("standing_capabilities", [])
            prohibited = cdata.get("reserved_decisions", [])

            cur.execute("""
                INSERT INTO os_agent_charters (
                    charter_id, department_code, role_name, version, authority_ceiling,
                    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                ON CONFLICT (charter_id) DO UPDATE SET
                    department_code = EXCLUDED.department_code,
                    role_name = EXCLUDED.role_name,
                    version = EXCLUDED.version,
                    authority_ceiling = EXCLUDED.authority_ceiling,
                    daily_budget_usd = EXCLUDED.daily_budget_usd,
                    allowed_actions = EXCLUDED.allowed_actions,
                    prohibited_actions = EXCLUDED.prohibited_actions
            """, (
                charter_id, code, title, version, ceiling,
                daily_budget, json.dumps(allowed), json.dumps(prohibited)
            ))

            print(f"  + {code}: {title} (Accountable: {role}) -> {charter_id} [Ceiling: {ceiling}, Budget: ${daily_budget}/day]")

        conn.commit()

    print("\nAll 11 Executive Department Charters successfully seeded.")


def main():
    db_url = get_db_url()
    print(f"Connecting to Postgres at: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    with psycopg.connect(db_url) as conn:
        seed(conn)


if __name__ == "__main__":
    main()
