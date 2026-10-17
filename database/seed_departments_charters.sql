-- Authoritative Seed: Departments (D01-D11) & Executive Charters
BEGIN;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('c522d1f3-66a0-5803-80ad-5a559cec27c1', 'D01', 'Executive Operations & COO', 'coo', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d01-coo', 'D01', 'Executive Operations & COO', 'v2.2', 'A2',
    15.0, '["coo.briefing.compile.v1", "coo.task.prioritize.v1", "coo.exception.escalate.v1"]'::jsonb, '["Company strategy modification", "Product closure or wind-down", "Capital allocation changes", "Policy changes"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('a19df983-fa34-544d-a520-0c947c524118', 'D02', 'Sales & Commercial Partnerships', 'commercial_lead', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d02-commercial', 'D02', 'Sales & Commercial Partnerships', 'v2.2', 'A2',
    25.0, '["crm.lead.upsert.v1", "crm.opportunity.upsert.v1", "crm.quotation.create_draft.v1", "campaign.create_direct.v1", "openrtb.dsp.onboard.v1"]'::jsonb, '["Final contract execution", "Commercial exclusivity commitments", "Non-standard warranties", "Discounts or revenue shares outside approved policy"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('c2c5b1e7-e26e-5433-828e-1006c32cd508', 'D03', 'Marketing & Communications (CMO)', 'cmo', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d03-cmo', 'D03', 'Marketing & Communications (CMO)', 'v2.2', 'A2',
    20.0, '["content.social.publish.v1", "content.editorial.publish.v1", "content.correction.withdraw.v1"]'::jsonb, '["New public commitments or corporate positions", "Crisis communications and sensitive allegations", "Unapproved brand advertising campaigns or ad spend"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('dad85351-c6df-5529-a17e-295467da9a15', 'D04', 'Intelligence & Research', 'intelligence_lead', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d04-intelligence', 'D04', 'Intelligence & Research', 'v2.2', 'A1',
    15.0, '["intelligence.signal.route.v1", "intelligence.radar.collect.v1", "claims.verify.v1"]'::jsonb, '["Adding new unreviewed data sources", "Prohibited scraping or terms-of-service bypass", "Material expansion of retained personal data"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('882f47de-2d9c-5664-862c-3bf14cf8b8f8', 'D05', 'Technology, Engineering & Reliability (CTO)', 'cto', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d05-cto', 'D05', 'Technology, Engineering & Reliability (CTO)', 'v2.2', 'A2',
    30.0, '["engineering.ci.verify.v1", "engineering.release.deploy_staging.v1", "engineering.runbook.execute.v1", "schedule.feed.sync.v1"]'::jsonb, '["Breaking API contract migrations", "Destructive production database migrations", "New infrastructure commitments", "Exceptions to security or access control policies"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('01aee04d-5118-5c31-9b33-26e7c86fab18', 'D06', 'Finance & Treasury Operations (CFO)', 'cfo', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d06-cfo', 'D06', 'Finance & Treasury Operations (CFO)', 'v2.2', 'A2',
    10.0, '["finance.customer.upsert.v1", "finance.invoice.create_draft.v1", "finance.invoice.submit_a2.v1", "finance.payment.record_draft.v1", "finance.reconciliation.verify.v1"]'::jsonb, '["External treasury bank transfers", "Adding new vendor payment beneficiaries", "Statutory tax filings", "Bad debt write-offs", "Payment terms exceeding standard policy limits"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('f9bdfaf1-e718-5e6d-a172-dde2176de84e', 'D07', 'Customer Success & Operations', 'customer_ops_lead', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d07-customer', 'D07', 'Customer Success & Operations', 'v2.2', 'A2',
    20.0, '["support.issue.create.v1", "support.issue.update_status.v1", "support.ticket.triage.v1", "support.subscriber.help.v1", "stream.diagnose.v1"]'::jsonb, '["Customer refunds outside standing policy limits", "Identity authentication bypasses", "Contractual compensation promises", "Service level agreement exceptions"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('4e0e44f6-ac38-5abb-92d9-8f60eb551c95', 'D08', 'Venture & Product Development', 'product_lead', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d08-venture', 'D08', 'Venture & Product Development', 'v2.2', 'A2',
    20.0, '["venture.brief.generate.v1", "venture.scaffold.execute.v1"]'::jsonb, '["New venture incubation greenlight", "Commercial production launch", "Product capital allocation changes", "Commercial commitments to external partners"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('7a7b77dd-4921-5da3-8e50-574b9394fe48', 'D09', 'Legal & Regulatory Compliance Administration', 'general_counsel', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d09-compliance', 'D09', 'Legal & Regulatory Compliance Administration', 'v2.2', 'A1',
    10.0, '["compliance.rights.audit.v1", "compliance.retraction.issue.v1", "compliance.privacy.export.v1"]'::jsonb, '["Formal legal advice or statutory interpretation", "Executing legal agreements or contracts", "Formal litigation responses", "Statutory regulatory filings"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('8e30e06c-393d-52de-b353-58acd0371d31', 'D10', 'People & Vendor Administration', 'people_vendor_lead', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d10-people-vendor', 'D10', 'People & Vendor Administration', 'v2.2', 'A2',
    10.0, '["procurement.supplier.upsert.v1", "procurement.purchase_order.create_draft.v1", "vendor.access.revoke.v1"]'::jsonb, '["Hiring, termination, and employment contracts", "Compensation and equity adjustments", "Binding new vendor master services agreements", "Approving new subscriptions above standing threshold"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;

INSERT INTO os_departments (id, code, name, accountable_role, is_active)
VALUES ('15cb5f01-64fe-5bf8-8a93-4eed076ca89a', 'D11', 'Independent Assurance & Guardian Verifier', 'chief_auditor', TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    accountable_role = EXCLUDED.accountable_role,
    is_active = TRUE;

INSERT INTO os_agent_charters (
    charter_id, department_code, role_name, version, authority_ceiling,
    daily_budget_usd, allowed_actions, prohibited_actions, is_halted
) VALUES (
    'chr-d11-assurance', 'D11', 'Independent Assurance & Guardian Verifier', 'v2.2', 'A2',
    20.0, '["assurance.controls.audit.v1", "guardian.health.probe.v1", "guardian.recovery.runbook.execute.v1"]'::jsonb, '["Waiving failed acceptance criteria", "Granting launch authorization without 100% control qualification", "Overriding security role boundaries or audit trail logging"]'::jsonb, FALSE
)
ON CONFLICT (charter_id) DO UPDATE SET
    department_code = EXCLUDED.department_code,
    role_name = EXCLUDED.role_name,
    version = EXCLUDED.version,
    authority_ceiling = EXCLUDED.authority_ceiling,
    daily_budget_usd = EXCLUDED.daily_budget_usd,
    allowed_actions = EXCLUDED.allowed_actions,
    prohibited_actions = EXCLUDED.prohibited_actions;
COMMIT;
