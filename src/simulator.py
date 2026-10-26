"""
src/simulator.py
Live Store Event Simulator.
Generates periodic orders and inventory ticks to simulate real-time Shopify webhooks.
"""

import os
import random
import sqlite3
from datetime import datetime, timezone, timedelta
from src.tools import DB_PATH

def simulate_new_orders(count: int = 3):
    """Generates fresh customer orders occurring 'right now'."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get random customers & variants (excluding stocked out variants)
    cursor.execute("SELECT customer_id FROM customers ORDER BY RANDOM() LIMIT ?", (count,))
    cust_ids = [r[0] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT v.variant_id, v.price, v.cost, i.available_units 
        FROM variants v 
        JOIN inventory i ON v.variant_id = i.variant_id 
        WHERE i.available_units > 2
        ORDER BY RANDOM() LIMIT 20
    """)
    variants = cursor.fetchall()

    if not variants or not cust_ids:
        conn.close()
        return {"status": "no_available_inventory"}

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    created_orders = []

    for cust_id in cust_ids:
        num_items = random.randint(1, 3)
        chosen_vars = random.sample(variants, min(num_items, len(variants)))

        total_amt = 0.0
        line_items = []

        for v in chosen_vars:
            v_id, price, cost, stock = v
            qty = random.randint(1, 2)
            total_amt += price * qty
            line_items.append((v_id, qty, price))

            # Deduct inventory for real-time stock sync
            cursor.execute("UPDATE inventory SET available_units = available_units - ? WHERE variant_id = ?", (qty, v_id))
            cursor.execute("""
                INSERT INTO inventory_movements (variant_id, quantity_change, reason, timestamp)
                VALUES (?, ?, 'Order Sale (Live Simulator)', ?)
            """, (v_id, -qty, now_utc))

        cursor.execute("""
            INSERT INTO orders (customer_id, date, status, currency, total_amount)
            VALUES (?, ?, 'completed', 'USD', ?)
        """, (cust_id, now_utc, round(total_amt, 2)))
        order_id = cursor.lastrowid

        for li in line_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, variant_id, quantity, price, discount)
                VALUES (?, ?, ?, ?, 0.0)
            """, (order_id, li[0], li[1], li[2]))

        created_orders.append({"order_id": order_id, "customer_id": cust_id, "total": round(total_amt, 2)})

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "timestamp": now_utc,
        "orders_created": len(created_orders),
        "details": created_orders
    }

if __name__ == "__main__":
    res = simulate_new_orders(5)
    print("Simulator tick:", res)