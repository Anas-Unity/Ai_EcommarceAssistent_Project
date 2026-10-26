"""
generate_data.py
Generates 12 months of synthetic Shopify-style data with 6 known business patterns.
Fixed random seed is used for deterministic reproducibility.
"""

import json
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from faker import Faker

# Fixed seed for reproducibility
SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ecommerce.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
SCENARIOS_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "injected_scenarios.json")

# Time window: 365 days up to today
END_DATE = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
START_DATE = END_DATE - timedelta(days=365)

CATEGORIES = ["Apparel", "Footwear", "Accessories", "Electronics", "Home & Living"]
SIZES = ["S", "M", "L", "XL"]
COLORS = ["Black", "White", "Navy", "Heather Grey", "Olive"]

def init_db(conn):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()

def generate_data():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    init_db(conn)

    print("Generating synthetic data...")

    # ==========================================
    # 1. CUSTOMERS (5,000)
    # ==========================================
    print("-> Generating 5,000 customers...")
    customers = []
    for i in range(1, 5001):
        created_dt = START_DATE + timedelta(days=random.randint(0, 300))
        customers.append((
            fake.name(),
            f"user_{i}_{fake.unique.email()}",
            random.choice(["US", "CA", "GB", "AU", "DE"]),
            created_dt.strftime("%Y-%m-%d %H:%M:%S")
        ))
    cursor.executemany(
        "INSERT INTO customers (name, email, country, created_date) VALUES (?, ?, ?, ?)",
        customers
    )
    conn.commit()

    # ==========================================
    # 2. PRODUCTS (300) & VARIANTS (900)
    # ==========================================
    print("-> Generating 300 products and 900 variants...")
    products = []
    variants = []
    
    stockout_product_id = 42

    for p_id in range(1, 301):
        category = CATEGORIES[p_id % len(CATEGORIES)]
        if p_id == stockout_product_id:
            title = "Alpine Winter Performance Jacket"
            category = "Apparel"
        else:
            title = f"{fake.word().capitalize()} {category[:-1]} {p_id}"
            
        products.append((title, category, "active"))

    cursor.executemany(
        "INSERT INTO products (title, category, status) VALUES (?, ?, ?)",
        products
    )
    conn.commit()

    variant_id_counter = 1
    stockout_variant_ids = []
    
    for p_id in range(1, 301):
        base_price = round(random.uniform(25.0, 180.0), 2)
        base_cost = round(base_price * random.uniform(0.35, 0.55), 2)

        for v_idx in range(3):
            size = SIZES[v_idx % len(SIZES)]
            color = COLORS[(p_id + v_idx) % len(COLORS)]
            sku = f"SKU-{p_id:03d}-{size}-{color[:3].upper()}"
            
            variants.append((p_id, sku, size, color, base_price, base_cost))
            
            if p_id == stockout_product_id:
                stockout_variant_ids.append(variant_id_counter)
            variant_id_counter += 1

    cursor.executemany(
        "INSERT INTO variants (product_id, sku, size, color, price, cost) VALUES (?, ?, ?, ?, ?, ?)",
        variants
    )
    conn.commit()

    # ==========================================
    # 3. DISCOUNT CODES (50)
    # ==========================================
    print("-> Generating 50 discount codes...")
    promo_start = END_DATE - timedelta(days=35)
    promo_end = END_DATE - timedelta(days=30)
    
    discounts = [
        ("FLASH50", 0.50, promo_start.strftime("%Y-%m-%d"), promo_end.strftime("%Y-%m-%d")),
        ("WELCOME10", 0.10, START_DATE.strftime("%Y-%m-%d"), END_DATE.strftime("%Y-%m-%d")),
        ("SPRING15", 0.15, (START_DATE + timedelta(days=90)).strftime("%Y-%m-%d"), (START_DATE + timedelta(days=120)).strftime("%Y-%m-%d")),
    ]
    for d_idx in range(4, 51):
        d_start = START_DATE + timedelta(days=random.randint(10, 300))
        d_end = d_start + timedelta(days=random.randint(3, 14))
        discounts.append((
            f"PROMO{d_idx}_{random.randint(5, 25)}",
            round(random.choice([0.05, 0.10, 0.15, 0.20, 0.25]), 2),
            d_start.strftime("%Y-%m-%d"),
            d_end.strftime("%Y-%m-%d")
        ))
    cursor.executemany(
        "INSERT INTO discount_codes (code, percentage, start_date, expiry) VALUES (?, ?, ?, ?)",
        discounts
    )
    conn.commit()

    # ==========================================
    # 4. ORDERS & ORDER ITEMS (~20,000 orders distributed over 365 days)
    # ==========================================
    print("-> Generating ~20,000 orders distributed smoothly across 365 days...")
    
    cursor.execute("""
        SELECT v.variant_id, v.product_id, v.price, v.cost, p.category 
        FROM variants v JOIN products p ON v.product_id = p.product_id
    """)
    variant_lookup = {row[0]: {"product_id": row[1], "price": row[2], "cost": row[3], "category": row[4]} for row in cursor.fetchall()}
    all_variant_ids = list(variant_lookup.keys())

    vip_customer_ids = list(range(1, 601))
    regular_customer_ids = list(range(601, 5001))

    orders = []
    order_items = []
    refund_candidates = []

    stockout_start_date = END_DATE - timedelta(days=14)
    recent_decline_start = END_DATE - timedelta(days=7)

    order_id = 1
    for day_offset in range(365):
        current_day = START_DATE + timedelta(days=day_offset)
        day_of_week = current_day.weekday()
        is_weekend = day_of_week in (5, 6)

        # Baseline: ~55 orders/day (weekends 65-75)
        base_orders = random.randint(60, 72) if is_weekend else random.randint(46, 56)

        # Scenario 2: Flash promo surge
        if promo_start <= current_day <= promo_end:
            base_orders = int(base_orders * 1.8)

        # Injected Pattern: Last 7 days sales drop by ~20%
        if current_day >= recent_decline_start:
            base_orders = int(base_orders * 0.75)

        for _ in range(base_orders):
            order_time = current_day + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            order_date_str = order_time.strftime("%Y-%m-%d %H:%M:%S")

            is_vip = random.random() < 0.35
            cust_id = random.choice(vip_customer_ids) if is_vip else random.choice(regular_customer_ids)

            # Scenario 6: Last 7 days cancellation spike (15% vs 3%)
            is_recent = current_day >= recent_decline_start
            if is_recent and random.random() < 0.15:
                status = random.choice(["cancelled", "pending"])
            elif random.random() < 0.03:
                status = "cancelled"
            else:
                status = "completed"

            num_items = random.randint(3, 6) if is_vip else random.randint(1, 3)

            order_total = 0.0
            order_has_footwear = False

            for _ in range(num_items):
                # Scenario 3: Product 42 stockout
                if order_time >= stockout_start_date:
                    v_id = random.choice([x for x in all_variant_ids if x not in stockout_variant_ids])
                else:
                    if random.random() < 0.08:
                        v_id = random.choice(stockout_variant_ids)
                    else:
                        v_id = random.choice(all_variant_ids)

                v_info = variant_lookup[v_id]
                qty = random.randint(1, 2)
                item_price = v_info["price"]

                discount = round(item_price * 0.50, 2) if (promo_start <= current_day <= promo_end) else 0.0
                line_total = (item_price - discount) * qty
                order_total += line_total

                if v_info["category"] == "Footwear":
                    order_has_footwear = True

                order_items.append((
                    order_id,
                    v_id,
                    qty,
                    item_price,
                    discount
                ))

            order_total = round(order_total, 2)
            orders.append((
                order_id,
                cust_id,
                order_date_str,
                status,
                "USD",
                order_total
            ))

            if status == "completed":
                refund_candidates.append({
                    "order_id": order_id,
                    "date": order_time,
                    "total": order_total,
                    "has_footwear": order_has_footwear
                })

            order_id += 1

    print(f"-> Inserting {len(orders)} orders and {len(order_items)} order items...")
    cursor.executemany(
        "INSERT INTO orders (order_id, customer_id, date, status, currency, total_amount) VALUES (?, ?, ?, ?, ?, ?)",
        orders
    )
    cursor.executemany(
        "INSERT INTO order_items (order_id, variant_id, quantity, price, discount) VALUES (?, ?, ?, ?, ?)",
        order_items
    )
    conn.commit()

    # ==========================================
    # 5. REFUNDS (1,000)
    # ==========================================
    print("-> Generating 1,000 refunds with Footwear refund spike...")
    refunds = []
    footwear_orders = [o for o in refund_candidates if o["has_footwear"]]
    other_orders = [o for o in refund_candidates if not o["has_footwear"]]

    selected_footwear = random.sample(footwear_orders, min(600, len(footwear_orders)))
    selected_other = random.sample(other_orders, min(400, len(other_orders)))

    for candidate in (selected_footwear + selected_other):
        refund_date = candidate["date"] + timedelta(days=random.randint(1, 7))
        if refund_date > END_DATE:
            refund_date = END_DATE
        amount = round(candidate["total"] * random.uniform(0.5, 1.0), 2)
        refunds.append((
            candidate["order_id"],
            refund_date.strftime("%Y-%m-%d %H:%M:%S"),
            amount,
            random.choice(["Size did not fit", "Defective material", "Customer changed mind"])
        ))

    cursor.executemany(
        "INSERT INTO refunds (order_id, date, amount, reason) VALUES (?, ?, ?, ?)",
        refunds
    )
    conn.commit()

    # ==========================================
    # 6. INVENTORY
    # ==========================================
    print("-> Generating inventory and inventory movements...")
    inventory_rows = []
    movements = []

    for v_id in all_variant_ids:
        if v_id in stockout_variant_ids:
            available_stock = 0
            threshold = 20
        else:
            available_stock = random.randint(15, 120)
            threshold = random.randint(10, 25)

        inventory_rows.append((v_id, available_stock, threshold))

    cursor.executemany(
        "INSERT INTO inventory (variant_id, available_units, reorder_threshold) VALUES (?, ?, ?)",
        inventory_rows
    )

    for _ in range(10000):
        v_id = random.choice(all_variant_ids)
        m_date = START_DATE + timedelta(days=random.randint(0, 360))
        change = random.randint(20, 100) if random.random() < 0.7 else -random.randint(1, 10)
        movements.append((
            v_id,
            change,
            "Supplier Restock" if change > 0 else "Cycle Count Adjustment",
            m_date.strftime("%Y-%m-%d %H:%M:%S")
        ))

    cursor.executemany(
        "INSERT INTO inventory_movements (variant_id, quantity_change, reason, timestamp) VALUES (?, ?, ?, ?)",
        movements
    )
    conn.commit()

    conn.close()
    print("Database regeneration complete!")

if __name__ == "__main__":
    generate_data()