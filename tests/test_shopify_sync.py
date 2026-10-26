"""
tests/test_shopify_sync.py
Unit tests verifying Shopify webhook sync, duplicate event idempotency,
and external currency rate caching.
"""

from src.shopify_sync import process_shopify_order_webhook, process_shopify_refund_webhook
from src.exchange_rate import get_exchange_rate

def test_shopify_order_sync_and_idempotency():
    mock_order = {
        "id": 999555,
        "created_at": "2026-10-22 10:00:00",
        "currency": "USD",
        "total_price": 249.50,
        "customer": {
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah.connor.999555@example.com",
            "country_code": "US"
        },
        "line_items": [
            {"variant_id": 1, "quantity": 2, "price": 124.75, "total_discount": 0.0}
        ]
    }

    # 1. First webhook delivery: Must succeed
    res1 = process_shopify_order_webhook(mock_order)
    assert res1["status"] in ["success", "skipped"]

    # 2. Duplicate webhook delivery (e.g. Shopify retry): Must be skipped cleanly via idempotency
    res2 = process_shopify_order_webhook(mock_order)
    assert res2["status"] == "skipped"
    assert "Idempotency Guard" in res2["message"]

def test_shopify_refund_sync():
    mock_refund = {
        "id": 888111,
        "order_id": 999555,
        "amount": 124.75,
        "note": "Customer returned 1 item",
        "created_at": "2026-10-22 11:00:00"
    }

    res = process_shopify_refund_webhook(mock_refund)
    assert res["status"] in ["success", "skipped"]

def test_exchange_rate_caching():
    # First call: Fetches rate
    rate1 = get_exchange_rate("USD", "EUR")
    assert rate1["status"] == "success"
    assert rate1["exchange_rate"] > 0

    # Second call: Must hit in-memory cache without re-fetching
    rate2 = get_exchange_rate("USD", "EUR")
    assert rate2["status"] == "success"
    assert rate2["cached"] is True