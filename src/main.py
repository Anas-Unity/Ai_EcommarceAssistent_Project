"""
src/main.py
FastAPI Application with real-time SSE streaming, time-series charting analytics,
Role-Based Access Control (RBAC), Order/Refund Ledgers, and Idempotent Write Execution.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from src.agent import run_investigation_stream, run_investigation, DB_PATH
from src.auth import can_review_approvals, is_tool_allowed_for_role, ROLE_MANAGER
from src.simulator import simulate_new_orders
from src.shopify_sync import process_shopify_order_webhook, process_shopify_refund_webhook
from src.exchange_rate import get_exchange_rate

app = FastAPI(title="ShopOps AI Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_role: Optional[str] = "operations_analyst"

class ApprovalActionRequest(BaseModel):
    status: str
    reviewer: str = "store_manager"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------------------------------------
# Real-Time Streaming Endpoint with Role Enforcement (SSE)
# -------------------------------------------------------------
@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    def event_generator():
        for event in run_investigation_stream(req.message, user_role=req.user_role or "operations_analyst"):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# -------------------------------------------------------------
# Time-Series Endpoint for Interactive Graphs
# -------------------------------------------------------------
@app.get("/api/timeseries")
def get_timeseries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d 23:59:59")
    elif len(end_date) == 10:
        end_date = f"{end_date} 23:59:59"

    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
    elif len(start_date) == 10:
        start_date = f"{start_date} 00:00:00"

    sales_sql = """
        SELECT 
            date(o.date) as day,
            COUNT(DISTINCT o.order_id) as orders,
            ROUND(SUM((oi.price - oi.discount) * oi.quantity), 2) as gross_revenue,
            ROUND(SUM((oi.price - oi.discount - v.cost) * oi.quantity), 2) as margin
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        WHERE o.date >= ? AND o.date <= ?
          AND o.status IN ('completed', 'shipped')
        GROUP BY date(o.date)
        ORDER BY day ASC
    """
    cursor.execute(sales_sql, (start_date, end_date))
    daily_sales = {r["day"]: dict(r) for r in cursor.fetchall()}

    refunds_sql = """
        SELECT 
            date(date) as day,
            COUNT(refund_id) as refund_count,
            ROUND(SUM(amount), 2) as refund_amount
        FROM refunds
        WHERE date >= ? AND date <= ?
        GROUP BY date(date)
        ORDER BY day ASC
    """
    cursor.execute(refunds_sql, (start_date, end_date))
    daily_refunds = {r["day"]: dict(r) for r in cursor.fetchall()}
    conn.close()

    all_days = sorted(list(set(list(daily_sales.keys()) + list(daily_refunds.keys()))))
    series = []

    for d in all_days:
        s = daily_sales.get(d, {"orders": 0, "gross_revenue": 0.0, "margin": 0.0})
        r = daily_refunds.get(d, {"refund_count": 0, "refund_amount": 0.0})

        gross = s["gross_revenue"] or 0.0
        margin = s["margin"] or 0.0
        ref_amt = r["refund_amount"] or 0.0
        net = round(gross - ref_amt, 2)
        orders = s["orders"] or 0
        aov = round(gross / orders, 2) if orders > 0 else 0.0
        roi_margin_pct = round((margin / gross) * 100, 2) if gross > 0 else 0.0

        series.append({
            "date": d,
            "gross_revenue": gross,
            "net_revenue": net,
            "margin": margin,
            "orders": orders,
            "refund_amount": ref_amt,
            "refund_count": r["refund_count"],
            "aov": aov,
            "roi_margin_pct": roi_margin_pct
        })

    return {
        "start_date": start_date[:10],
        "end_date": end_date[:10],
        "points": series
    }

# -------------------------------------------------------------
# Dashboard Analytics with Dynamic Date Range Filter
# -------------------------------------------------------------
@app.get("/api/dashboard-analytics")
def get_dashboard_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d 23:59:59")
    elif len(end_date) == 10:
        end_date = f"{end_date} 23:59:59"

    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
    elif len(start_date) == 10:
        start_date = f"{start_date} 00:00:00"

    cursor.execute("""
        SELECT 
            COUNT(order_id) as total_orders,
            COALESCE(SUM(total_amount), 0.0) as gross_revenue
        FROM orders
        WHERE date >= ? AND date <= ?
          AND status IN ('completed', 'shipped')
    """, (start_date, end_date))
    kpi_cur = cursor.fetchone()
    gross_rev = round(float(kpi_cur["gross_revenue"] or 0.0), 2)
    orders_cnt = int(kpi_cur["total_orders"] or 0)
    aov = round(gross_rev / orders_cnt, 2) if orders_cnt > 0 else 0.0

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0.0) as refund_amt, COUNT(refund_id) as refund_cnt
        FROM refunds
        WHERE date >= ? AND date <= ?
    """, (start_date, end_date))
    ref_cur = cursor.fetchone()
    refund_amt = round(float(ref_cur["refund_amt"] or 0.0), 2)
    net_rev = round(gross_rev - refund_amt, 2)

    cursor.execute("""
        SELECT COALESCE(SUM((oi.price - oi.discount - v.cost) * oi.quantity), 0.0) as total_margin
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        WHERE o.date >= ? AND o.date <= ?
          AND o.status IN ('completed', 'shipped')
    """, (start_date, end_date))
    total_margin = round(float(cursor.fetchone()["total_margin"] or 0.0), 2)
    margin_pct = round((total_margin / gross_rev) * 100, 2) if gross_rev > 0 else 0.0

    cursor.execute("""
        SELECT 
            p.product_id, p.title, p.category,
            SUM(oi.quantity) as units_sold,
            ROUND(SUM((oi.price - oi.discount) * oi.quantity), 2) as revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE o.status IN ('completed', 'shipped')
          AND o.date >= ? AND o.date <= ?
        GROUP BY p.product_id
        ORDER BY revenue DESC
        LIMIT 5
    """, (start_date, end_date))
    best_products = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT 
            p.product_id, p.title, p.category,
            COALESCE(SUM(oi.quantity), 0) as units_sold,
            ROUND(COALESCE(SUM((oi.price - oi.discount) * oi.quantity), 0), 2) as revenue,
            i.available_units as current_stock
        FROM products p
        JOIN variants v ON p.product_id = v.product_id
        JOIN inventory i ON v.variant_id = i.variant_id
        LEFT JOIN order_items oi ON v.variant_id = oi.variant_id
        LEFT JOIN orders o ON oi.order_id = o.order_id 
             AND o.status IN ('completed', 'shipped')
             AND o.date >= ? AND o.date <= ?
        WHERE i.available_units > 10
        GROUP BY p.product_id
        ORDER BY units_sold ASC, revenue ASC
        LIMIT 5
    """, (start_date, end_date))
    worst_products = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT 
            p.category,
            COUNT(DISTINCT o.order_id) as orders_count,
            ROUND(SUM((oi.price - oi.discount) * oi.quantity), 2) as category_revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE o.status IN ('completed', 'shipped')
          AND o.date >= ? AND o.date <= ?
        GROUP BY p.category
        ORDER BY category_revenue DESC
    """, (start_date, end_date))
    categories = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT p.category, COUNT(r.refund_id) as refunds_count
        FROM refunds r
        JOIN orders o ON r.order_id = o.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN variants v ON oi.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE r.date >= ? AND r.date <= ?
        GROUP BY p.category
    """, (start_date, end_date))
    refunds_by_cat = {r["category"]: r["refunds_count"] for r in cursor.fetchall()}
    for cat in categories:
        cat["refunds_count"] = refunds_by_cat.get(cat["category"], 0)

    cursor.execute("""
        SELECT p.product_id, p.title, v.sku, v.size, v.color, i.available_units
        FROM inventory i
        JOIN variants v ON i.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE i.available_units = 0
        LIMIT 6
    """)
    stockouts = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "kpi": {
            "gross_revenue": gross_rev,
            "net_revenue": net_rev,
            "total_margin": total_margin,
            "margin_pct": margin_pct,
            "orders": orders_cnt,
            "aov": aov,
            "refund_amount": refund_amt
        },
        "best_products": best_products,
        "worst_products": worst_products,
        "categories": categories,
        "stockouts": stockouts
    }

# -------------------------------------------------------------
# Order & Refund Feed Endpoints for Navigation Views
# -------------------------------------------------------------
@app.get("/api/orders-list")
def get_orders_list(status: Optional[str] = None, limit: int = 50):
    """Returns recent orders filtered by status."""
    conn = get_db()
    cursor = conn.cursor()

    if status and status != "all":
        cursor.execute("""
            SELECT o.order_id, o.customer_id, c.name as customer_name, c.email,
                   o.date, o.status, o.total_amount,
                   COUNT(oi.item_id) as item_count
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = ?
            GROUP BY o.order_id
            ORDER BY o.date DESC
            LIMIT ?
        """, (status, limit))
    else:
        cursor.execute("""
            SELECT o.order_id, o.customer_id, c.name as customer_name, c.email,
                   o.date, o.status, o.total_amount,
                   COUNT(oi.item_id) as item_count
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            GROUP BY o.order_id
            ORDER BY o.date DESC
            LIMIT ?
        """, (limit,))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"orders": rows}

@app.get("/api/refunds-list")
def get_refunds_list(limit: int = 50):
    """Returns recent processed refunds with details."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.refund_id, r.order_id, r.date, r.amount, r.reason,
               c.name as customer_name,
               p.category as primary_category
        FROM refunds r
        JOIN orders o ON r.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN variants v ON oi.variant_id = v.variant_id
        LEFT JOIN products p ON v.product_id = p.product_id
        GROUP BY r.refund_id
        ORDER BY r.date DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"refunds": rows}

# -------------------------------------------------------------
# Approval Management with Role Authorization
# -------------------------------------------------------------
@app.get("/api/approvals")
def get_approvals():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT request_id, action, payload, status, requester, reviewer, created_at, resolved_at
        FROM approval_requests
        ORDER BY request_id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    approvals = []
    for r in rows:
        approvals.append({
            "request_id": r["request_id"],
            "action": r["action"],
            "payload": json.loads(r["payload"]) if r["payload"] else {},
            "status": r["status"],
            "requester": r["requester"],
            "reviewer": r["reviewer"],
            "created_at": r["created_at"],
            "resolved_at": r["resolved_at"]
        })
    return {"approvals": approvals}

@app.post("/api/approvals/{request_id}/action")
def act_on_approval(request_id: int, action_data: ApprovalActionRequest):
    if action_data.reviewer != ROLE_MANAGER and "manager" not in action_data.reviewer.lower():
        raise HTTPException(
            status_code=403, 
            detail="Permission Denied: Only Store Managers can approve or reject proposals."
        )

    if action_data.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'.")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM approval_requests WHERE request_id = ?", (request_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Proposal not found.")

    if row["status"] in ["approved", "rejected", "executed"]:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Proposal #{request_id} has already been {row['status']}.")

    resolved_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE approval_requests
        SET status = ?, reviewer = ?, resolved_at = ?
        WHERE request_id = ?
    """, (action_data.status, action_data.reviewer, resolved_time, request_id))
    conn.commit()
    conn.close()

    return {"message": f"Proposal #{request_id} {action_data.status} by {action_data.reviewer}."}

# =============================================================
# Idempotent Execution Endpoint: Executes Approved Proposal Exactly Once
# =============================================================
@app.post("/api/approvals/{request_id}/execute")
def execute_approved_proposal(request_id: int, user_role: str = Query("store_manager")):
    if user_role != ROLE_MANAGER and "manager" not in user_role.lower():
        raise HTTPException(
            status_code=403, 
            detail="Permission Denied: Only Store Managers can execute approved store actions."
        )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT request_id, action, payload, status FROM approval_requests WHERE request_id = ?", (request_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Proposal #{request_id} not found.")

    payload = json.loads(row["payload"])

    if payload.get("executed") is True:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"Idempotency Guardrail: Proposal #{request_id} has ALREADY been executed. Duplicate writes are blocked."
        )

    if row["status"] != "approved":
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot execute proposal #{request_id}: Current status is '{row['status']}'. It must be 'approved' first."
        )

    action = row["action"]
    execution_result = {}
    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.strftime("%Y-%m-%d")

    try:
        if action == "propose_discount":
            raw_pct = payload.get("discount_percentage", 10)
            pct_val = float(str(raw_pct).replace("%", ""))
            pct_dec = pct_val / 100.0
            duration = int(payload.get("duration_days", 3))
            expiry_str = (now_utc + timedelta(days=duration)).strftime("%Y-%m-%d")
            code_name = f"PROMO_P{request_id}_{int(pct_val)}"

            cursor.execute("""
                INSERT OR REPLACE INTO discount_codes (code, percentage, start_date, expiry)
                VALUES (?, ?, ?, ?)
            """, (code_name, pct_dec, now_str, expiry_str))
            
            execution_result = {
                "discount_code_created": code_name,
                "discount_percentage": pct_val,
                "valid_until": expiry_str
            }

        elif action == "propose_inventory_alert":
            var_id = int(payload.get("variant_id"))
            new_thresh = int(payload.get("suggested_threshold", 20))
            cursor.execute("UPDATE inventory SET reorder_threshold = ? WHERE variant_id = ?", (new_thresh, var_id))
            execution_result = {
                "variant_id": var_id,
                "new_reorder_threshold": new_thresh
            }

        payload["executed"] = True
        payload["executed_at"] = now_utc.strftime("%Y-%m-%d %H:%M:%S")
        payload["execution_result"] = execution_result

        cursor.execute("""
            UPDATE approval_requests 
            SET payload = ?, resolved_at = ?
            WHERE request_id = ?
        """, (json.dumps(payload), now_utc.strftime("%Y-%m-%d %H:%M:%S"), request_id))
        
        conn.commit()
    except Exception as err:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database Write Failure: {str(err)}")

    conn.close()

    return {
        "status": "success",
        "message": f"Proposal #{request_id} ({action}) successfully executed into store database.",
        "execution_details": execution_result
    }

@app.get("/api/tool-runs")
def get_tool_runs(limit: int = 15):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT run_id, request_id, tool, arguments, duration_ms, status, created_at
        FROM tool_runs
        ORDER BY run_id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return {"tool_runs": [dict(r) for r in rows]}

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/api/simulator/tick")
def trigger_simulator(count: int = 3):
    res = simulate_new_orders(count=count)
    return res

@app.post("/api/shopify/webhooks/orders")
def shopify_order_webhook_endpoint(payload: Dict[str, Any]):
    return process_shopify_order_webhook(payload)

@app.post("/api/shopify/webhooks/refunds")
def shopify_refund_webhook_endpoint(payload: Dict[str, Any]):
    return process_shopify_refund_webhook(payload)

@app.get("/api/currency/exchange-rate")
def exchange_rate_endpoint(base: str = "USD", target: str = "EUR"):
    return get_exchange_rate(base, target)