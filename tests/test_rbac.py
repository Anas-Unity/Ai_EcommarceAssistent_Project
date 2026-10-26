"""
tests/test_rbac.py
Automated test suite verifying Role-Based Access Control and Idempotency.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.auth import is_tool_allowed_for_role, ROLE_MANAGER, ROLE_ANALYST, ROLE_SUPPORT

client = TestClient(app)

# 1. Test RBAC Tool Permissions
def test_support_role_restrictions():
    # Support cannot access sales or stockout tools
    assert not is_tool_allowed_for_role(ROLE_SUPPORT, "get_sales_summary")
    assert not is_tool_allowed_for_role(ROLE_SUPPORT, "get_stockout_risk")
    assert not is_tool_allowed_for_role(ROLE_SUPPORT, "propose_discount")
    # Support can only inspect orders
    assert is_tool_allowed_for_role(ROLE_SUPPORT, "get_order")

def test_analyst_role_permissions():
    # Analysts can investigate and propose
    assert is_tool_allowed_for_role(ROLE_ANALYST, "compare_sales_periods")
    assert is_tool_allowed_for_role(ROLE_ANALYST, "propose_discount")

# 2. Test Non-Manager Approval Block
def test_analyst_cannot_approve_proposal():
    # Attempting to approve as analyst must be blocked with 403 Forbidden
    response = client.post("/api/approvals/1/action", json={
        "status": "approved",
        "reviewer": "operations_analyst"
    })
    assert response.status_code == 403
    assert "Permission Denied" in response.json()["detail"]

# 3. Test Idempotent Write Execution
def test_idempotent_execution_guardrail():
    # First, let's create a fresh proposal via propose_discount tool
    from src.tools import propose_discount
    prop = propose_discount(product_ids=[42], discount_percentage=10, duration_days=3, reason="Test Idempotency")
    prop_id = prop["approval_request_id"]

    # Manager approves proposal
    approve_res = client.post(f"/api/approvals/{prop_id}/action", json={
        "status": "approved",
        "reviewer": "store_manager"
    })
    assert approve_res.status_code == 200

    # 1st Execution: Must succeed
    exec_1 = client.post(f"/api/approvals/{prop_id}/execute?user_role=store_manager")
    assert exec_1.status_code == 200
    assert exec_1.json()["status"] == "success"

    # 2nd Execution (Duplicate): Must be rejected by Idempotency Guardrail
    exec_2 = client.post(f"/api/approvals/{prop_id}/execute?user_role=store_manager")
    assert exec_2.status_code == 400
    assert "Idempotency Guardrail" in exec_2.json()["detail"]