"""
verify_db.py
Verifies row counts and checks that injected business patterns are present.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ecommerce.db")

def verify():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Run generate_data.py first!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = [
        "customers", "products", "variants", "orders", 
        "order_items", "refunds", "inventory", 
        "inventory_movements", "discount_codes", 
        "approval_requests", "tool_runs"
    ]

    print("=== 1. Table Row Counts ===")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table:22}: {count:,} rows")

    print("\n=== 2. Pattern Verification ===")

    # Check Scenario 1: Weekend vs Weekday avg orders
    cursor.execute("""
        SELECT 
            CASE CAST(strftime('%w', date) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 6 THEN 'Saturday'
                ELSE 'Weekday'
            END as day_type,
            COUNT(*) * 1.0 / COUNT(DISTINCT date(date)) as avg_daily_orders
        FROM orders
        GROUP BY day_type
    """)
    print("Scenario 1 (Weekend sales):")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:.1f} orders/day")

    # Check Scenario 3: Stockout Product 42 (Alpine Winter Performance Jacket)
    cursor.execute("""
        SELECT p.title, i.available_units 
        FROM products p 
        JOIN variants v ON p.product_id = v.product_id
        JOIN inventory i ON v.variant_id = i.variant_id
        WHERE p.product_id = 42
        LIMIT 1
    """)
    prod = cursor.fetchone()
    print(f"\nScenario 3 (Stockout Product 42): {prod[0]} -> Available Stock: {prod[1]}")

    # Check Scenario 4: Refund rate by category
    cursor.execute("""
        SELECT p.category, COUNT(r.refund_id) as refund_count
        FROM refunds r
        JOIN orders o ON r.order_id = o.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        GROUP BY p.category
        ORDER BY refund_count DESC
    """)
    print("\nScenario 4 (High Refund Category):")
    for cat, count in cursor.fetchall():
        print(f"  {cat:15}: {count} refunds")

    # Check Scenario 5: VIP vs Regular AOV
    cursor.execute("""
        SELECT 
            CASE WHEN customer_id <= 600 THEN 'VIP Customer' ELSE 'Regular Customer' END as cust_group,
            AVG(total_amount) as aov
        FROM orders
        WHERE status = 'completed'
        GROUP BY cust_group
    """)
    print("\nScenario 5 (Customer AOV):")
    for grp, aov in cursor.fetchall():
        print(f"  {grp:18}: ${aov:.2f}")

    conn.close()

if __name__ == "__main__":
    verify()