"""Comprehensive tests for all 11 Department Workflows (MCS-OS v2.2 W05–W08)."""

import pytest
from services.workflows.d01_coo.workflow import COOWorkflow
from services.workflows.d02_commercial.workflow import CommercialWorkflow
from services.workflows.d03_cmo.workflow import CMOWorkflow
from services.workflows.d04_intelligence.workflow import IntelligenceWorkflow
from services.workflows.d05_cto.workflow import CTOWorkflow
from services.workflows.d06_cfo.workflow import CFOWorkflow
from services.workflows.d07_customer.workflow import CustomerWorkflow
from services.workflows.d08_venture.workflow import VentureWorkflow
from services.workflows.d09_compliance.workflow import ComplianceWorkflow
from services.workflows.d10_people_vendor.workflow import PeopleVendorWorkflow
from services.workflows.d11_assurance.workflow import AssuranceWorkflow


@pytest.mark.asyncio
async def test_d01_coo_workflow():
    wf = COOWorkflow()
    assert wf.charter["department_id"] == "D01"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert "07:30 WAT" in res.details["portfolio_summary"] or res.details["policy_decision"] is True


@pytest.mark.asyncio
async def test_d02_commercial_workflow():
    wf = CommercialWorkflow()
    assert wf.charter["department_id"] == "D02"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["is_authorized"] is True


@pytest.mark.asyncio
async def test_d03_cmo_workflow():
    wf = CMOWorkflow()
    assert wf.charter["department_id"] == "D03"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["is_authorized"] is True


@pytest.mark.asyncio
async def test_d03_cmo_workflow_rejects_ungrounded_content():
    wf = CMOWorkflow()
    res = await wf.run_cycle(trigger_event={"content": {"title": "Unverified Rumor", "summary": "No citations"}})
    assert res.status == "failed"
    assert "Missing required citation triple" in res.details["error"]


@pytest.mark.asyncio
async def test_d04_intelligence_workflow():
    wf = IntelligenceWorkflow()
    assert wf.charter["department_id"] == "D04"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["citation_triple"].startswith("sha256:")


@pytest.mark.asyncio
async def test_d05_cto_workflow():
    wf = CTOWorkflow()
    assert wf.charter["department_id"] == "D05"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["is_authorized"] is True


@pytest.mark.asyncio
async def test_d06_cfo_workflow():
    wf = CFOWorkflow()
    assert wf.charter["department_id"] == "D06"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["total_amount_usd"] == 1850.00


@pytest.mark.asyncio
async def test_d07_customer_workflow():
    wf = CustomerWorkflow()
    assert wf.charter["department_id"] == "D07"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["ticket_id"] == "TCK-8921"


@pytest.mark.asyncio
async def test_d08_venture_workflow():
    wf = VentureWorkflow()
    assert wf.charter["department_id"] == "D08"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["is_authorized"] is True


@pytest.mark.asyncio
async def test_d09_compliance_workflow():
    wf = ComplianceWorkflow()
    assert wf.charter["department_id"] == "D09"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1


@pytest.mark.asyncio
async def test_d10_people_vendor_workflow():
    wf = PeopleVendorWorkflow()
    assert wf.charter["department_id"] == "D10"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["supplier"] == "Hetzner Cloud GmbH"


@pytest.mark.asyncio
async def test_d11_assurance_workflow():
    wf = AssuranceWorkflow()
    assert wf.charter["department_id"] == "D11"
    res = await wf.run_cycle()
    assert res.status == "completed"
    assert res.actions_proposed == 1
    assert res.actions_executed == 1
    assert res.details["audit_state"]["waived_gates"] == 0
    assert res.details["audit_state"]["passed_gates"] == 20
