-- schema.sql
PRAGMA foreign_keys = ON;

-- 1. Customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    country TEXT NOT NULL,
    created_date TEXT NOT NULL
);

-- 2. Products
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'draft', 'archived'))
);

-- 3. Product Variants
CREATE TABLE IF NOT EXISTS variants (
    variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    sku TEXT UNIQUE NOT NULL,
    size TEXT,
    color TEXT,
    price REAL NOT NULL,
    cost REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 4. Orders
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('completed', 'shipped', 'cancelled', 'pending')),
    currency TEXT NOT NULL DEFAULT 'USD',
    total_amount REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 5. Order Line Items
CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    discount REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id)
);

-- 6. Refunds
CREATE TABLE IF NOT EXISTS refunds (
    refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- 7. Current Inventory
CREATE TABLE IF NOT EXISTS inventory (
    variant_id INTEGER PRIMARY KEY,
    available_units INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER NOT NULL DEFAULT 15,
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id)
);

-- 8. Inventory Movements (Audit Log)
CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    quantity_change INTEGER NOT NULL,
    reason TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id)
);

-- 9. Discount Codes
CREATE TABLE IF NOT EXISTS discount_codes (
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    percentage REAL NOT NULL,
    start_date TEXT NOT NULL,
    expiry TEXT NOT NULL
);

-- 10. Human Approval Requests (Pending/Approved/Rejected actions)
CREATE TABLE IF NOT EXISTS approval_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    requester TEXT NOT NULL,
    reviewer TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

-- 11. Tool Execution Runs (Audit log for LLM tool calls)
CREATE TABLE IF NOT EXISTS tool_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    arguments TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('success', 'error')),
    created_at TEXT NOT NULL
);

-- Indexes for fast querying during agent investigations
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(date);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_variant ON order_items(variant_id);
CREATE INDEX IF NOT EXISTS idx_refunds_order ON refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_refunds_date ON refunds(date);
CREATE INDEX IF NOT EXISTS idx_variants_product ON variants(product_id);