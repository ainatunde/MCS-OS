"""Comprehensive test suite for Scoped Product & Provider Adapters (MCS-OS v2.2 W04)."""

import pytest
from contracts.actions.envelope import ActionEnvelope, AuthorityClass, OutcomeState, canonical_payload_hash
from adapters.products.cloudstream_vcp import CloudStreamVCPAdapter
from adapters.products.cloudstream_forge import CloudStreamForgeAdapter
from adapters.products.aether_ads import AetherADSAdapter
from adapters.products.aether_adx import AetherADXAdapter
from adapters.products.tv_insights import TVInsightsAdapter
from adapters.products.africasignal import AfricaSignalAdapter
from adapters.products.mcs_app_factory import MCSAppFactoryAdapter
from adapters.providers.erpnext_adapter import ERPNextAdapter
from adapters.providers.litellm_proxy import LiteLLMProxyRouter, BudgetExceededError


def _make_envelope(action_type: str, department: str, product_slug: str, authority: str = "A2", payload: dict = None) -> ActionEnvelope:
    p = payload or {"test_key": "test_val"}
    return ActionEnvelope(
        action_id=f"act-test-{action_type}",
        task_id="tsk-test-001",
        charter_id=f"chr-{department.lower()}-001",
        department_id=department,
        product_slug=product_slug,
        action_type=action_type,
        authority_class=AuthorityClass(authority),
        payload=p,
        canonical_payload_hash=canonical_payload_hash(p),
        idempotency_key=f"idem-{action_type}-001",
        fencing_token=1,
        authorization_ref="standing:test",
        policy_version="v2.2",
        qualification_ref="v2.2-test",
    )


@pytest.mark.asyncio
async def test_all_seven_product_adapters_satisfy_protocol():
    adapters = [
        CloudStreamVCPAdapter(),
        CloudStreamForgeAdapter(),
        AetherADSAdapter(),
        AetherADXAdapter(),
        TVInsightsAdapter(),
        AfricaSignalAdapter(),
        MCSAppFactoryAdapter(),
    ]

    for adapter in adapters:
        caps = await adapter.describe_capabilities()
        assert len(caps) > 0, f"{adapter.product_slug} returned no capabilities"

        health = await adapter.read_health()
        assert health.status in ["healthy", "degraded", "down"]
        assert health.product_slug == adapter.product_slug

        metrics = await adapter.read_metrics("2026-10-01", "2026-10-15")
        assert len(metrics) > 0

        # Test lookup on non-existent action
        lookup = await adapter.lookup_outcome("non-existent", "non-existent")
        assert lookup.outcome == OutcomeState.NOT_APPLIED


@pytest.mark.asyncio
async def test_mcs_app_factory_tenant_isolation():
    adapter = MCSAppFactoryAdapter()

    # Valid tenant: visatrack-africa
    valid_env = _make_envelope(
        "support.subscriber.help.v1",
        "D07",
        "mcs-app-factory",
        payload={"tenant_id": "visatrack-africa", "query": "visa policy update"},
    )
    val_res = await adapter.validate_action(valid_env)
    assert val_res.is_valid is True

    receipt = await adapter.execute_action(valid_env)
    assert receipt.outcome == OutcomeState.APPLIED
    assert receipt.details["tenant_id"] == "visatrack-africa"

    # Valid tenant: skilledpath-africa
    valid_env2 = _make_envelope(
        "tenant.manifest.read.v1",
        "D01",
        "mcs-app-factory",
        payload={"tenant_id": "skilledpath-africa"},
    )
    val_res2 = await adapter.validate_action(valid_env2)
    assert val_res2.is_valid is True

    # Invalid / unverified tenant
    invalid_env = _make_envelope(
        "support.subscriber.help.v1",
        "D07",
        "mcs-app-factory",
        payload={"tenant_id": "unverified-phantom-tenant", "query": "hello"},
    )
    val_invalid = await adapter.validate_action(invalid_env)
    assert val_invalid.is_valid is False
    assert "not in the verified tenant registry" in val_invalid.errors[0]

    # Execute should return NOT_SUPPORTED
    bad_receipt = await adapter.execute_action(invalid_env)
    assert bad_receipt.outcome == OutcomeState.NOT_SUPPORTED


@pytest.mark.asyncio
async def test_erpnext_adapter_department_isolation_and_cost_centers():
    adapter = ERPNextAdapter()

    # D02 can upsert leads
    d02_env = _make_envelope(
        "crm.lead.upsert.v1",
        "D02",
        "cloudstream-vcp",
        payload={"lead_name": "Broadcaster A"},
    )
    val_d02 = await adapter.validate_action(d02_env)
    assert val_d02.is_valid is True

    receipt = await adapter.execute_action(d02_env)
    assert receipt.outcome == OutcomeState.APPLIED
    assert receipt.details["cost_center"] == "CloudStream-VCP"

    # D02 CANNOT create invoices (owned by D06)
    bad_d02_env = _make_envelope(
        "finance.invoice.create_draft.v1",
        "D02",
        "cloudstream-vcp",
        payload={"customer": "Broadcaster A", "items": []},
    )
    val_bad = await adapter.validate_action(bad_d02_env)
    assert val_bad.is_valid is False
    assert "Department isolation violation" in val_bad.errors[0]

    bad_receipt = await adapter.execute_action(bad_d02_env)
    assert bad_receipt.outcome == OutcomeState.NOT_SUPPORTED


@pytest.mark.asyncio
async def test_aether_adx_contract_independence():
    adx_adapter = AetherADXAdapter(endpoint_url="http://localhost:8090/v1/openrtb")
    caps = await adx_adapter.describe_capabilities()
    assert any("openrtb" in c.action_type for c in caps)
    health = await adx_adapter.read_health()
    assert "OpenRTB" in health.details["protocol"]


@pytest.mark.asyncio
async def test_litellm_proxy_budget_and_recovery():
    router = LiteLLMProxyRouter(daily_budget_usd=1.0)

    # Initial budget is 1.0
    assert router.get_remaining_budget() == 1.0

    # Normal completion works and records spend
    res = await router.complete_with_fallback(
        prompt="Analyze broadcast ad break",
        department="D04",
        action_id="act-llm-1",
    )
    assert res["model"] == "gemini-1.5-pro"
    assert res["cost_usd"] > 0.0
    assert router.spent_usd > 0.0

    # Simulate budget exhaustion
    router.spent_usd = 1.05

    # Standard call fails with BudgetExceededError
    with pytest.raises(BudgetExceededError):
        router.reserve_budget("D02", "act-llm-blocked", estimated_cost_usd=0.05, is_recovery=False)

    # Recovery reservation succeeds even with exhausted budget
    rec_res = router.reserve_budget("D11", "act-llm-recovery", estimated_cost_usd=0.05, is_recovery=True)
    assert rec_res.reservation_id.startswith("res_act-llm-recovery")
