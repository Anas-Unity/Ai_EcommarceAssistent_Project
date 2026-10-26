"""
src/shopify_sync.py
Shopify Synchronization Engine for orders, line items, refunds, and inventory.
Enforces idempotency to handle repeated webhook deliveries and out-of-order events.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any
from src.tools import DB_PATH

def process_shopify_order_webhook(webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingests an incoming Shopify 'orders/create' webhook.
    Idempotent: If order already exists, safely ignores repeated delivery.
    """
    order_id = webhook_payload.get("id")
    if not order_id:
        return {"status": "error", "message": "Missing order ID in payload."}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Idempotency Check: Prevent duplicate order insertion
    cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
    if cursor.fetchone():
        conn.close()
        return {
            "status": "skipped",
            "message": f"Idempotency Guard: Order #{order_id} has already been synced. Duplicate webhook ignored."
        }

    # 2. Reconcile Customer
    cust_data = webhook_payload.get("customer", {})
    cust_email = cust_data.get("email", f"customer_{order_id}@shopify.com")
    cust_name = f"{cust_data.get('first_name', 'Shopify')} {cust_data.get('last_name', 'Customer')}".strip()
    cust_country = cust_data.get("country_code", "US")

    cursor.execute("SELECT customer_id FROM customers WHERE email = ?", (cust_email,))
    existing_cust = cursor.fetchone()
    if existing_cust:
        customer_id = existing_cust[0]
    else:
        cursor.execute("""
            INSERT INTO customers (name, email, country, created_date)
            VALUES (?, ?, ?, ?)
        """, (cust_name, cust_email, cust_country, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
        customer_id = cursor.lastrowid

    # 3. Insert Order Record
    total_price = float(webhook_payload.get("total_price", 0.0))
    currency = webhook_payload.get("currency", "USD")
    order_date = webhook_payload.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    cursor.execute("""
        INSERT INTO orders (order_id, customer_id, date, status, currency, total_amount)
        VALUES (?, ?, ?, 'completed', ?, ?)
    """, (order_id, customer_id, order_date, currency, total_price))

    # 4. Ingest Line Items & Reconcile Inventory
    line_items = webhook_payload.get("line_items", [])
    synced_items_count = 0

    for item in line_items:
        variant_id = item.get("variant_id", 1)
        qty = int(item.get("quantity", 1))
        price = float(item.get("price", 0.0))
        discount = float(item.get("total_discount", 0.0))

        cursor.execute("""
            INSERT INTO order_items (order_id, variant_id, quantity, price, discount)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, variant_id, qty, price, discount))

        # Atomic inventory deduction
        cursor.execute("UPDATE inventory SET available_units = available_units - ? WHERE variant_id = ?", (qty, variant_id))
        cursor.execute("""
            INSERT INTO inventory_movements (variant_id, quantity_change, reason, timestamp)
            VALUES (?, ?, 'Shopify Order Fulfillment', ?)
        """, (variant_id, -qty, order_date))
        synced_items_count += 1

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "order_id": order_id,
        "items_synced": synced_items_count,
        "total_amount": total_price
    }

def process_shopify_refund_webhook(webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingests an incoming Shopify 'refunds/create' webhook.
    """
    refund_id = webhook_payload.get("id")
    order_id = webhook_payload.get("order_id")
    amount = float(webhook_payload.get("amount", 0.0))
    reason = webhook_payload.get("note", "Shopify Customer Refund")
    refund_date = webhook_payload.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    if not refund_id or not order_id:
        return {"status": "error", "message": "Missing refund or order ID in webhook."}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Idempotency check
    cursor.execute("SELECT refund_id FROM refunds WHERE refund_id = ?", (refund_id,))
    if cursor.fetchone():
        conn.close()
        return {
            "status": "skipped",
            "message": f"Idempotency: Refund #{refund_id} already recorded."
        }

    cursor.execute("""
        INSERT INTO refunds (refund_id, order_id, date, amount, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (refund_id, order_id, refund_date, amount, reason))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "refund_id": refund_id,
        "order_id": order_id,
        "amount": amount
    }