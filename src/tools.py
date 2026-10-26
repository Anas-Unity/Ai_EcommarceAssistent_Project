"""
src/tools.py
Deterministic SQL/Python tools for ecommerce operational investigations.
All calculations follow metrics_definitions.md standards.
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from src.exchange_rate import get_exchange_rate

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ecommerce.db"))

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# ============================================================================
# Tool 1: get_sales_summary
# ============================================================================
def get_sales_summary(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Calculate orders, gross revenue, net revenue, AOV, and refunds for a given UTC date range.
    Format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
    """
    # Normalize date strings to include complete boundaries if only date is passed
    if len(start_date) == 10:
        start_date = f"{start_date} 00:00:00"
    if len(end_date) == 10:
        end_date = f"{end_date} 23:59:59"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Completed or shipped orders only
    sales_query = """
        SELECT 
            COUNT(order_id) as total_orders,
            COALESCE(SUM(total_amount), 0.0) as gross_revenue
        FROM orders
        WHERE date >= ? AND date <= ?
          AND status IN ('completed', 'shipped')
    """
    cursor.execute(sales_query, (start_date, end_date))
    sales_res = cursor.fetchone()
    total_orders = sales_res["total_orders"]
    gross_revenue = round(sales_res["gross_revenue"], 2)

    # Calculate refunds within the period
    refund_query = """
        SELECT 
            COUNT(refund_id) as total_refunds,
            COALESCE(SUM(amount), 0.0) as refund_amount
        FROM refunds
        WHERE date >= ? AND date <= ?
    """
    cursor.execute(refund_query, (start_date, end_date))
    refund_res = cursor.fetchone()
    total_refunds = refund_res["total_refunds"]
    refund_amount = round(refund_res["refund_amount"], 2)

    # Calculate Margin ($)
    margin_query = """
        SELECT 
            COALESCE(SUM((oi.price - oi.discount - v.cost) * oi.quantity), 0.0) as gross_margin
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        WHERE o.date >= ? AND o.date <= ?
          AND o.status IN ('completed', 'shipped')
    """
    cursor.execute(margin_query, (start_date, end_date))
    margin_res = cursor.fetchone()
    gross_margin = round(margin_res["gross_margin"], 2)

    conn.close()

    net_revenue = round(gross_revenue - refund_amount, 2)
    aov = round(gross_revenue / total_orders, 2) if total_orders > 0 else 0.0
    margin_pct = round((gross_margin / gross_revenue) * 100, 2) if gross_revenue > 0 else 0.0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_orders": total_orders,
        "gross_revenue": gross_revenue,
        "refund_amount": refund_amount,
        "net_revenue": net_revenue,
        "gross_margin": gross_margin,
        "margin_percentage": margin_pct,
        "average_order_value": aov,
        "total_refunds": total_refunds
    }

# ============================================================================
# Tool 2: compare_sales_periods
# ============================================================================
def compare_sales_periods(
    current_start: str, 
    current_end: str, 
    previous_start: str, 
    previous_end: str
) -> Dict[str, Any]:
    """
    Compares two time periods (e.g. this week vs last week) and computes percentage changes.
    """
    current_period = get_sales_summary(current_start, current_end)
    previous_period = get_sales_summary(previous_start, previous_end)

    def calc_change(curr: float, prev: float):
        diff = round(curr - prev, 2)
        pct = round(((curr - prev) / prev) * 100, 2) if prev != 0 else (100.0 if curr > 0 else 0.0)
        return {"absolute_change": diff, "percentage_change": pct}

    return {
        "current_period": current_period,
        "previous_period": previous_period,
        "comparison": {
            "revenue": calc_change(current_period["gross_revenue"], previous_period["gross_revenue"]),
            "orders": calc_change(current_period["total_orders"], previous_period["total_orders"]),
            "aov": calc_change(current_period["average_order_value"], previous_period["average_order_value"]),
            "margin_pct_change": round(current_period["margin_percentage"] - previous_period["margin_percentage"], 2)
        }
    }

# ============================================================================
# Tool 3: get_product_performance
# ============================================================================
def get_product_performance(
    start_date: str, 
    end_date: str, 
    sort_by: str = "revenue", 
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Rank products by revenue, units, or margin over a date range.
    sort_by options: 'revenue', 'units', 'margin'
    """
    if len(start_date) == 10:
        start_date = f"{start_date} 00:00:00"
    if len(end_date) == 10:
        end_date = f"{end_date} 23:59:59"

    valid_sorts = {
        "revenue": "total_revenue DESC",
        "units": "total_units DESC",
        "margin": "total_margin DESC"
    }
    order_clause = valid_sorts.get(sort_by, "total_revenue DESC")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
        SELECT 
            p.product_id,
            p.title,
            p.category,
            SUM(oi.quantity) as total_units,
            ROUND(SUM((oi.price - oi.discount) * oi.quantity), 2) as total_revenue,
            ROUND(SUM((oi.price - oi.discount - v.cost) * oi.quantity), 2) as total_margin
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE o.date >= ? AND o.date <= ?
          AND o.status IN ('completed', 'shipped')
        GROUP BY p.product_id, p.title, p.category
        ORDER BY {order_clause}
        LIMIT ?
    """
    cursor.execute(query, (start_date, end_date, limit))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        rev = row["total_revenue"]
        margin = row["total_margin"]
        margin_pct = round((margin / rev) * 100, 2) if rev > 0 else 0.0
        results.append({
            "product_id": row["product_id"],
            "title": row["title"],
            "category": row["category"],
            "units_sold": row["total_units"],
            "revenue": rev,
            "margin": margin,
            "margin_percentage": margin_pct
        })
    return results

# ============================================================================
# Tool 4: get_refund_summary
# ============================================================================
def get_refund_summary(
    start_date: str, 
    end_date: str, 
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Summarize refunds over a period, optionally filtered by category, grouped by reason and category.
    """
    if len(start_date) == 10:
        start_date = f"{start_date} 00:00:00"
    if len(end_date) == 10:
        end_date = f"{end_date} 23:59:59"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Overall totals
    params = [start_date, end_date]
    cat_filter = ""
    if category:
        cat_filter = "AND p.category = ?"
        params.append(category)

    base_query = f"""
        SELECT 
            COUNT(DISTINCT r.refund_id) as total_refunds,
            COALESCE(SUM(r.amount), 0.0) as total_refund_amount
        FROM refunds r
        JOIN orders o ON r.order_id = o.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE r.date >= ? AND r.date <= ? {cat_filter}
    """
    cursor.execute(base_query, params)
    totals = cursor.fetchone()

    # Breakdown by category
    cat_query = f"""
        SELECT 
            p.category,
            COUNT(DISTINCT r.refund_id) as count,
            ROUND(SUM(r.amount), 2) as amount
        FROM refunds r
        JOIN orders o ON r.order_id = o.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE r.date >= ? AND r.date <= ? {cat_filter}
        GROUP BY p.category
        ORDER BY count DESC
    """
    cursor.execute(cat_query, params)
    categories_breakdown = [dict(row) for row in cursor.fetchall()]

    # Breakdown by reason
    reason_query = f"""
        SELECT 
            r.reason,
            COUNT(DISTINCT r.refund_id) as count,
            ROUND(SUM(r.amount), 2) as amount
        FROM refunds r
        JOIN orders o ON r.order_id = o.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE r.date >= ? AND r.date <= ? {cat_filter}
        GROUP BY r.reason
        ORDER BY count DESC
    """
    cursor.execute(reason_query, params)
    reasons_breakdown = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_refund_count": totals["total_refunds"],
        "total_refund_amount": round(totals["total_refund_amount"], 2),
        "by_category": categories_breakdown,
        "by_reason": reasons_breakdown
    }

# ============================================================================
# Tool 5: get_stockout_risk
# ============================================================================
def get_stockout_risk(
    lookback_days: int = 14, 
    target_coverage_days: int = 14
) -> List[Dict[str, Any]]:
    """
    Workflow B formulas:
    Average daily units = units sold / days observed
    Estimated days remaining = available stock / average daily units
    Suggested reorder = max(0, target coverage days * average daily units - available stock)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query units sold per variant in the lookback period
    query = """
        SELECT 
            v.variant_id,
            p.product_id,
            p.title as product_title,
            v.sku,
            v.size,
            v.color,
            i.available_units,
            i.reorder_threshold,
            COALESCE(SUM(oi.quantity), 0) as units_sold
        FROM variants v
        JOIN products p ON v.product_id = p.product_id
        JOIN inventory i ON v.variant_id = i.variant_id
        LEFT JOIN order_items oi ON v.variant_id = oi.variant_id
        LEFT JOIN orders o ON oi.order_id = o.order_id 
             AND o.status IN ('completed', 'shipped')
             AND o.date >= datetime('now', '-' || ? || ' days')
        GROUP BY v.variant_id
    """
    cursor.execute(query, (lookback_days,))
    rows = cursor.fetchall()
    conn.close()

    risk_list = []
    for r in rows:
        units_sold = r["units_sold"]
        available = r["available_units"]
        avg_daily = round(units_sold / lookback_days, 2) if lookback_days > 0 else 0.0

        if avg_daily > 0:
            days_remaining = round(available / avg_daily, 1)
            suggested_reorder = max(0, round((target_coverage_days * avg_daily) - available))
        else:
            # Handle zero-sales products separately as required by Workflow B
            days_remaining = 999.0 if available > 0 else 0.0
            suggested_reorder = 0

        # Flag variants with critical or low stock
        if days_remaining <= target_coverage_days or available <= r["reorder_threshold"]:
            risk_list.append({
                "variant_id": r["variant_id"],
                "product_id": r["product_id"],
                "product_title": r["product_title"],
                "sku": r["sku"],
                "size": r["size"],
                "color": r["color"],
                "available_stock": available,
                "reorder_threshold": r["reorder_threshold"],
                "units_sold_lookback": units_sold,
                "avg_daily_sales": avg_daily,
                "days_remaining": days_remaining,
                "suggested_reorder_units": suggested_reorder,
                "risk_status": "CRITICAL" if available == 0 else "WARNING"
            })

    # Sort by urgency (lowest days remaining first)
    risk_list.sort(key=lambda x: (x["available_stock"], x["days_remaining"]))
    return risk_list

# ============================================================================
# Tool 6: get_order
# ============================================================================
def get_order(order_id: int) -> Dict[str, Any]:
    """
    Retrieve single order metadata, customer info, line items, and refunds.
    Returns error dict if not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    order_query = """
        SELECT o.order_id, o.customer_id, c.name as customer_name, c.email as customer_email,
               o.date, o.status, o.currency, o.total_amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
    """
    cursor.execute(order_query, (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        return {"error": f"Order #{order_id} not found."}

    items_query = """
        SELECT oi.item_id, oi.variant_id, p.title as product_title, v.sku, v.size, v.color,
               oi.quantity, oi.price, oi.discount
        FROM order_items oi
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE oi.order_id = ?
    """
    cursor.execute(items_query, (order_id,))
    items = [dict(item) for item in cursor.fetchall()]

    refunds_query = """
        SELECT refund_id, date, amount, reason
        FROM refunds
        WHERE order_id = ?
    """
    cursor.execute(refunds_query, (order_id,))
    refunds = [dict(rf) for rf in cursor.fetchall()]

    conn.close()

    result = dict(order_row)
    result["items"] = items
    result["refunds"] = refunds
    return result

# ============================================================================
# Catalog Helper: search_products & get_product_details
# ============================================================================
def search_products(query: Optional[str] = None, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "SELECT product_id, title, category, status FROM products WHERE 1=1"
    params = []
    if query:
        sql += " AND title LIKE ?"
        params.append(f"%{query}%")
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " LIMIT ?"
    params.append(limit)
    cursor.execute(sql, params)
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

def get_product_details(product_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, title, category, status FROM products WHERE product_id = ?", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        return {"error": f"Product #{product_id} not found."}
    
    cursor.execute("""
        SELECT v.variant_id, v.sku, v.size, v.color, v.price, v.cost, i.available_units, i.reorder_threshold
        FROM variants v
        JOIN inventory i ON v.variant_id = i.variant_id
        WHERE v.product_id = ?
    """, (product_id,))
    variants = [dict(v) for v in cursor.fetchall()]
    conn.close()
    
    res = dict(prod)
    res["variants"] = variants
    return res

# ============================================================================
# Workflow B & D Tools: calculate_reorder_quantity, propose_discount, propose_inventory_alert
# ============================================================================

def calculate_reorder_quantity(
    variant_id: int, 
    target_coverage_days: int = 14, 
    lookback_days: int = 14
) -> Dict[str, Any]:
    """
    Workflow B exact formula:
    Average daily units = units sold / days observed
    Estimated days remaining = available stock / average daily units
    Suggested reorder = max(0, target coverage days * average daily units - available stock)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get variant and inventory info
    cursor.execute("""
        SELECT v.variant_id, v.product_id, p.title, v.sku, v.size, v.color, v.cost, v.price,
               i.available_units, i.reorder_threshold
        FROM variants v
        JOIN products p ON v.product_id = p.product_id
        JOIN inventory i ON v.variant_id = i.variant_id
        WHERE v.variant_id = ?
    """, (variant_id,))
    var = cursor.fetchone()

    if not var:
        conn.close()
        return {"error": f"Variant #{variant_id} not found."}

    # Get units sold in lookback window
    cursor.execute("""
        SELECT COALESCE(SUM(oi.quantity), 0) as units_sold
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        WHERE oi.variant_id = ?
          AND o.status IN ('completed', 'shipped')
          AND o.date >= datetime('now', '-' || ? || ' days')
    """, (variant_id, lookback_days))
    units_sold = cursor.fetchone()["units_sold"]
    conn.close()

    available_stock = var["available_units"]
    avg_daily_units = round(units_sold / lookback_days, 2) if lookback_days > 0 else 0.0

    if avg_daily_units > 0:
        days_remaining = round(available_stock / avg_daily_units, 1)
        suggested_reorder = max(0, round((target_coverage_days * avg_daily_units) - available_stock))
    else:
        # Brief requirement: Handle zero-sales products separately
        days_remaining = 999.0 if available_stock > 0 else 0.0
        suggested_reorder = 0

    return {
        "variant_id": variant_id,
        "product_id": var["product_id"],
        "product_title": var["title"],
        "sku": var["sku"],
        "available_stock": available_stock,
        "units_sold_lookback": units_sold,
        "avg_daily_units": avg_daily_units,
        "estimated_days_remaining": days_remaining,
        "target_coverage_days": target_coverage_days,
        "suggested_reorder_units": suggested_reorder,
        "estimated_cost": round(suggested_reorder * var["cost"], 2),
        "zero_sales_warning": avg_daily_units == 0
    }

def propose_discount(
    product_ids: List[int],
    discount_percentage: float,
    duration_days: int,
    reason: str,
    requester: str = "ai_operations_assistant"
) -> Dict[str, Any]:
    """
    Workflow D: Prepares a discount proposal in approval_requests.
    Checks post-discount margins before drafting the proposal.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify margin after discount for all affected products
    placeholders = ",".join("?" for _ in product_ids)
    cursor.execute(f"""
        SELECT p.product_id, p.title, v.variant_id, v.price, v.cost
        FROM products p
        JOIN variants v ON p.product_id = v.product_id
        WHERE p.product_id IN ({placeholders})
    """, product_ids)
    variants = cursor.fetchall()

    if not variants:
        conn.close()
        return {"error": "None of the specified products were found."}

    discount_factor = 1.0 - (discount_percentage / 100.0)
    margin_analysis = []
    has_negative_margin = False

    for v in variants:
        original_price = v["price"]
        cost = v["cost"]
        discounted_price = round(original_price * discount_factor, 2)
        post_discount_margin = round(discounted_price - cost, 2)
        post_discount_margin_pct = round((post_discount_margin / discounted_price) * 100, 2) if discounted_price > 0 else 0.0

        if post_discount_margin < 0:
            has_negative_margin = True

        margin_analysis.append({
            "variant_id": v["variant_id"],
            "title": v["title"],
            "original_price": original_price,
            "discounted_price": discounted_price,
            "cost": cost,
            "post_discount_margin": post_discount_margin,
            "post_discount_margin_pct": post_discount_margin_pct
        })

    payload = {
        "action_type": "create_discount",
        "product_ids": product_ids,
        "discount_percentage": discount_percentage,
        "duration_days": duration_days,
        "reason": reason,
        "margin_analysis": margin_analysis,
        "margin_warning": "Warning: Discount results in negative profit margin for one or more items!" if has_negative_margin else "Normal"
    }

    # Insert into approval_requests as 'pending'
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO approval_requests (action, payload, status, requester, reviewer, created_at, resolved_at)
        VALUES (?, ?, 'pending', ?, NULL, ?, NULL)
    """, ("propose_discount", json.dumps(payload), requester, now_str))
    
    proposal_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "proposal_created",
        "approval_request_id": proposal_id,
        "message": f"Proposal #{proposal_id} created and awaiting human review. The AI cannot execute discounts directly.",
        "payload": payload
    }

def propose_inventory_alert(
    variant_id: int,
    suggested_threshold: int,
    reason: str,
    requester: str = "ai_operations_assistant"
) -> Dict[str, Any]:
    """
    Workflow B/D: Prepares an inventory threshold adjustment alert in approval_requests.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    payload = {
        "action_type": "adjust_reorder_threshold",
        "variant_id": variant_id,
        "suggested_threshold": suggested_threshold,
        "reason": reason
    }

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO approval_requests (action, payload, status, requester, reviewer, created_at, resolved_at)
        VALUES (?, ?, 'pending', ?, NULL, ?, NULL)
    """, ("propose_inventory_alert", json.dumps(payload), requester, now_str))

    proposal_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "proposal_created",
        "approval_request_id": proposal_id,
        "message": f"Inventory alert #{proposal_id} created and awaiting human approval.",
        "payload": payload
    }