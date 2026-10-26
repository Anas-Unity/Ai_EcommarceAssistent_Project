"""
src/agent.py
Autonomous tool-calling agent with live step-by-step status streaming,
retry logic, Gemini 3 thought signature preservation, and SQLite audit logging.
"""

import json
import os
import time
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Generator
from src.auth import is_tool_allowed_for_role, ROLE_ANALYST, ROLE_MANAGER, ROLE_SUPPORT

from dotenv import load_dotenv
from openai import OpenAI

from src.exchange_rate import get_exchange_rate
from src.tool_schemas import TOOLS_SPEC
from src.tools import (
    get_sales_summary,
    compare_sales_periods,
    get_product_performance,
    get_refund_summary,
    get_stockout_risk,
    get_order,
    search_products,
    get_product_details,
    calculate_reorder_quantity,
    propose_discount,
    propose_inventory_alert,
    DB_PATH
)

load_dotenv()

TOOL_REGISTRY = {
    "get_sales_summary": get_sales_summary,
    "compare_sales_periods": compare_sales_periods,
    "get_product_performance": get_product_performance,
    "get_refund_summary": get_refund_summary,
    "get_stockout_risk": get_stockout_risk,
    "get_order": get_order,
    "search_products": search_products,
    "get_product_details": get_product_details,
    "calculate_reorder_quantity": calculate_reorder_quantity,
    "propose_discount": propose_discount,
    "propose_inventory_alert": propose_inventory_alert,
    "get_exchange_rate": get_exchange_rate,
}

TOOL_HUMAN_NAMES = {
    "compare_sales_periods": "Comparing period-over-period sales metrics",
    "get_product_performance": "Ranking top & bottom catalog performance",
    "get_stockout_risk": "Forecasting inventory depletion & stockout risks",
    "get_refund_summary": "Analyzing return rates and category anomalies",
    "get_sales_summary": "Aggregating store financial totals",
    "get_order": "Fetching order line items and customer records",
    "search_products": "Searching product catalog",
    "get_product_details": "Reading variant specifications and unit costs",
    "calculate_reorder_quantity": "Calculating replenishment batch size",
    "propose_discount": "Evaluating post-discount margins & drafting proposal",
    "propose_inventory_alert": "Drafting inventory safety alert",
    "get_exchange_rate": "Fetching currency exchange rate",
}

def get_system_prompt() -> str:
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    yesterday_str = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")
    seven_days_ago = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d")
    eight_days_ago = (now_utc - timedelta(days=8)).strftime("%Y-%m-%d")
    fourteen_days_ago = (now_utc - timedelta(days=14)).strftime("%Y-%m-%d")

    return f"""You are an expert Ecommerce Operations AI Assistant for a Shopify-style store.
Current UTC Date: {today_str}.

Standard Date Reference Guidelines:
- Complete day boundaries: Yesterday is {yesterday_str}.
- Last 7 complete days: {seven_days_ago} to {yesterday_str}.
- Previous 7 complete days: {fourteen_days_ago} to {eight_days_ago}.

Strict Operational Guidelines:
1. Always base all statements on verified data returned by tools. Never invent or hallucinate metrics.
2. In Workflow A (Sales Decline Investigations):
   - Compare the periods with compare_sales_periods.
   - Inspect product/category performance with get_product_performance.
   - Check stockouts/refunds where relevant.
   - CRITICAL: Distinguish association/correlation from causation. A stockout may explain part of a decline, but data does not prove it caused every lost sale.
3. In Workflow B (Replenishment):
   - Identify stockout risk with get_stockout_risk.
   - Calculate suggested reorders using calculate_reorder_quantity.
   - Note that starting estimates do not account for supplier lead times, seasonality, or demand suppressed by earlier stockouts.
4. In Workflow D (Discounts / Sensitive Writes):
   - You CANNOT directly execute discounts or refunds.
   - Always propose them using propose_discount so a human manager can review and approve them.
"""

def get_client() -> OpenAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=90.0
    )

def log_tool_run(request_id: str, tool_name: str, args: str, duration_ms: float, status: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tool_runs (request_id, tool, arguments, duration_ms, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                tool_name,
                args,
                round(duration_ms, 2),
                status,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to log tool run: {e}")

def run_investigation_stream(
    user_prompt: str, 
    user_role: str = "operations_analyst", 
    max_rounds: int = 5
) -> Generator[Dict[str, Any], None, None]:
    client = get_client()
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    request_id = str(uuid.uuid4())

    # Filter tool specifications based on user role
    available_tools = [
        t for t in TOOLS_SPEC 
        if is_tool_allowed_for_role(user_role, t["function"]["name"])
    ]

    role_notice = f"Current User Role: {user_role}."
    if user_role == ROLE_SUPPORT:
        role_notice += " Restricted to customer order inspection only. Financial margins and discount proposals are unauthorized."

    yield {
        "type": "status",
        "step": "plan",
        "message": f"Analyzing question for role [{user_role}] using {model}..."
    }

    messages = [
        {"role": "system", "content": f"{get_system_prompt()}\n\n{role_notice}"},
        {"role": "user", "content": user_prompt}
    ]

    executed_tools = []
    rounds = 0

    while rounds < max_rounds:
        rounds += 1

        response = None
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=available_tools if available_tools else None,
                    tool_choice="auto" if available_tools else "none",
                    temperature=0.0
                )
                break
            except Exception as e:
                if attempt == 0:
                    yield {
                        "type": "status",
                        "step": "retry",
                        "message": "Transient network delay detected. Retrying API call..."
                    }
                    time.sleep(1.5)
                else:
                    yield {
                        "type": "error",
                        "message": f"API Error: {str(e)}."
                    }
                    return

        choice = response.choices[0]
        message = choice.message

        if not message.tool_calls:
            yield {
                "type": "status",
                "step": "finalizing",
                "message": "Synthesizing executive report..."
            }
            yield {
                "type": "complete",
                "request_id": request_id,
                "answer": message.content or "Investigation concluded.",
                "rounds_used": rounds,
                "executed_tools": executed_tools
            }
            return

        formatted_tool_calls = []
        for tc in message.tool_calls:
            tc_dict = {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            extra = getattr(tc, "extra_content", None)
            if not extra and hasattr(tc, "model_extra") and tc.model_extra:
                extra = tc.model_extra.get("extra_content")
            if extra:
                tc_dict["extra_content"] = extra
            formatted_tool_calls.append(tc_dict)

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": formatted_tool_calls
        })

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            raw_args = tool_call.function.arguments
            human_desc = TOOL_HUMAN_NAMES.get(tool_name, f"Executing {tool_name}")

            yield {
                "type": "tool_start",
                "tool": tool_name,
                "message": f"{human_desc}..."
            }

            start_time = time.perf_counter()
            tool_status = "success"

            # Enforce Role Authorization Check
            if not is_tool_allowed_for_role(user_role, tool_name):
                result_payload = {"error": f"Permission Denied: Role '{user_role}' is not authorized to call '{tool_name}'."}
                tool_status = "error"
            elif tool_name not in TOOL_REGISTRY:
                result_payload = {"error": f"Tool '{tool_name}' is not in allowlisted functions."}
                tool_status = "error"
            else:
                try:
                    kwargs = json.loads(raw_args) if raw_args else {}
                    tool_func = TOOL_REGISTRY[tool_name]
                    result_payload = tool_func(**kwargs)
                except Exception as err:
                    result_payload = {"error": f"Execution error in {tool_name}: {str(err)}"}
                    tool_status = "error"

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            log_tool_run(request_id, tool_name, raw_args, duration_ms, tool_status)

            tool_info = {
                "tool": tool_name,
                "arguments": raw_args,
                "duration_ms": round(duration_ms, 2),
                "status": tool_status
            }
            executed_tools.append(tool_info)

            yield {
                "type": "tool_done",
                "tool": tool_name,
                "duration_ms": round(duration_ms, 2),
                "message": f"{'✓' if tool_status == 'success' else '✗'} {human_desc} ({round(duration_ms, 1)}ms)"
            }

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result_payload)
            })

    yield {
        "type": "complete",
        "request_id": request_id,
        "answer": "Maximum execution rounds reached before conclusion.",
        "rounds_used": rounds,
        "executed_tools": executed_tools
    }

def run_investigation(user_prompt: str, user_role: str = "operations_analyst", max_rounds: int = 5) -> Dict[str, Any]:
    final_res = {}
    for ev in run_investigation_stream(user_prompt, user_role, max_rounds):
        if ev.get("type") == "complete":
            final_res = ev
        elif ev.get("type") == "error":
            return {"answer": ev["message"], "request_id": "", "rounds_used": 1, "executed_tools": []}
    return final_res