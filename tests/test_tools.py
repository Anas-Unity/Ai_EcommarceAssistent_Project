"""
tests/test_tools.py
Automated test suite verifying the 6 operational tools against the SQLite database.
"""

import pytest
from datetime import datetime, timedelta
from src.tools import (
    get_sales_summary,
    compare_sales_periods,
    get_product_performance,
    get_refund_summary,
    get_stockout_risk,
    get_order,
    search_products,
    get_product_details
)

TODAY = datetime.utcnow().strftime("%Y-%m-%d")
THIRTY_DAYS_AGO = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
SIXTY_DAYS_AGO = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")

# 1. Test get_sales_summary
def test_sales_summary_valid_metrics():
    summary = get_sales_summary(THIRTY_DAYS_AGO, TODAY)
    assert "total_orders" in summary
    assert "gross_revenue" in summary
    assert "net_revenue" in summary
    assert "average_order_value" in summary
    assert summary["total_orders"] > 0
    assert summary["gross_revenue"] >= summary["net_revenue"]
    assert summary["average_order_value"] > 0

# 2. Test compare_sales_periods
def test_compare_sales_periods():
    comparison = compare_sales_periods(
        current_start=THIRTY_DAYS_AGO,
        current_end=TODAY,
        previous_start=SIXTY_DAYS_AGO,
        previous_end=THIRTY_DAYS_AGO
    )
    assert "current_period" in comparison
    assert "previous_period" in comparison
    assert "comparison" in comparison
    assert "percentage_change" in comparison["comparison"]["revenue"]

# 3. Test get_product_performance
def test_product_performance_ranking():
    top_products = get_product_performance(THIRTY_DAYS_AGO, TODAY, sort_by="revenue", limit=5)
    assert isinstance(top_products, list)
    assert len(top_products) <= 5
    if len(top_products) > 1:
        # Check descending order
        assert top_products[0]["revenue"] >= top_products[1]["revenue"]

# 4. Test get_refund_summary and footwear anomaly
def test_refund_summary_detects_anomaly():
    refunds = get_refund_summary(SIXTY_DAYS_AGO, TODAY)
    assert refunds["total_refund_count"] > 0
    assert len(refunds["by_category"]) > 0
    # Footwear should be top refund category (Scenario 4)
    top_category = refunds["by_category"][0]["category"]
    assert top_category == "Footwear"

# 5. Test get_stockout_risk handles stockout & zero sales
def test_stockout_risk_and_zero_division():
    risks = get_stockout_risk(lookback_days=14, target_coverage_days=14)
    assert isinstance(risks, list)
    assert len(risks) > 0
    
    # Check that Product 42 (Alpine Winter Performance Jacket) is flagged CRITICAL (Scenario 3)
    p42_items = [r for r in risks if r["product_id"] == 42]
    assert len(p42_items) > 0
    assert any(item["available_stock"] == 0 for item in p42_items)
    assert any(item["risk_status"] == "CRITICAL" for item in p42_items)

# 6. Test get_order and unknown order handling
def test_get_order_existing():
    order = get_order(1)
    assert order["order_id"] == 1
    assert "customer_name" in order
    assert "items" in order
    assert len(order["items"]) > 0

def test_get_order_unknown():
    # Negative test scenario as required by brief: unknown order returns clean message
    order = get_order(9999999)
    assert "error" in order
    assert "not found" in order["error"].lower()

# 7. Test Catalog Helpers
def test_product_lookup_and_details():
    results = search_products(query="Alpine", limit=5)
    assert len(results) >= 1
    alpine_id = results[0]["product_id"]
    
    details = get_product_details(alpine_id)
    assert details["product_id"] == alpine_id
    assert "variants" in details
    assert len(details["variants"]) > 0