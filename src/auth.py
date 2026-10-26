"""
src/auth.py
Role-Based Access Control (RBAC) and permission matrices for ShopOps.
"""

from typing import List, Dict, Set

# Standard Roles
ROLE_MANAGER = "store_manager"
ROLE_ANALYST = "operations_analyst"
ROLE_SUPPORT = "support_rep"

VALID_ROLES = [ROLE_MANAGER, ROLE_ANALYST, ROLE_SUPPORT]

# Tool Permissions Matrix
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # Managers have unrestricted access to all operational tools
    ROLE_MANAGER: {
        "get_sales_summary",
        "compare_sales_periods",
        "get_product_performance",
        "get_refund_summary",
        "get_stockout_risk",
        "get_order",
        "search_products",
        "get_product_details",
        "calculate_reorder_quantity",
        "propose_discount",
        "propose_inventory_alert",
    },
    # Analysts can investigate and propose, but not access restricted write executions
    ROLE_ANALYST: {
        "get_sales_summary",
        "compare_sales_periods",
        "get_product_performance",
        "get_refund_summary",
        "get_stockout_risk",
        "get_order",
        "search_products",
        "get_product_details",
        "calculate_reorder_quantity",
        "propose_discount",
        "propose_inventory_alert",
    },
    # Support can only inspect customer orders and catalog details (no financial margin data)
    ROLE_SUPPORT: {
        "get_order",
        "search_products",
        "get_product_details",
    }
}

def is_tool_allowed_for_role(role: str, tool_name: str) -> bool:
    """Returns True if the role has permission to call this tool."""
    allowed_tools = ROLE_PERMISSIONS.get(role, set())
    return tool_name in allowed_tools

def can_review_approvals(role: str) -> bool:
    """Only managers can approve, reject, or execute proposals."""
    return role == ROLE_MANAGER