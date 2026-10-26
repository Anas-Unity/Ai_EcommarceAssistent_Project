"""
src/tool_schemas.py
Explicit JSON Schemas for Gemini function calling.
"""

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "Calculate orders, gross revenue, net revenue, refunds, and AOV for a UTC date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format."
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_sales_periods",
            "description": "Compare sales metrics between two time windows (e.g. this week vs last week).",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_start": {"type": "string", "description": "Current period start date."},
                    "current_end": {"type": "string", "description": "Current period end date."},
                    "previous_start": {"type": "string", "description": "Previous period start date."},
                    "previous_end": {"type": "string", "description": "Previous period end date."}
                },
                "required": ["current_start", "current_end", "previous_start", "previous_end"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_performance",
            "description": "Rank top products by sales revenue, unit volume, or profit margin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date 'YYYY-MM-DD'."},
                    "end_date": {"type": "string", "description": "End date 'YYYY-MM-DD'."},
                    "sort_by": {
                        "type": "string",
                        "enum": ["revenue", "units", "margin"],
                        "description": "Metric to rank by."
                    },
                    "limit": {"type": "integer", "description": "Number of products to return (default: 10)."}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_refund_summary",
            "description": "Summarize refunds over a period, optionally filtered by category, grouped by reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date 'YYYY-MM-DD'."},
                    "end_date": {"type": "string", "description": "End date 'YYYY-MM-DD'."},
                    "category": {"type": "string", "description": "Optional category filter."}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stockout_risk",
            "description": "Forecast inventory depletion and calculate recommended replenishment units.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {"type": "integer", "description": "Lookback window for sales velocity (default: 14)."},
                    "target_coverage_days": {"type": "integer", "description": "Target days of safety stock (default: 14)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Retrieve exact details for an order including line items, customer, and refund status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "Numeric Order ID."}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search product catalog by name keyword or category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search product title."},
                    "category": {"type": "string", "description": "Category name filter."},
                    "limit": {"type": "integer", "description": "Max results to return."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Fetch detailed variant specifications, costs, and current stock for a product ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID."}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_reorder_quantity",
            "description": "Calculate replenishment units for a specific variant given target coverage days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "variant_id": {"type": "integer", "description": "The variant ID."},
                    "target_coverage_days": {"type": "integer", "description": "Safety coverage target in days (default: 14)."},
                    "lookback_days": {"type": "integer", "description": "Sales velocity lookback window in days (default: 14)."}
                },
                "required": ["variant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_discount",
            "description": "Draft an approval proposal for a discount on slow-selling products. Checks profit margins first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of product IDs to discount."
                    },
                    "discount_percentage": {"type": "number", "description": "Percentage discount (e.g. 10 for 10%)."},
                    "duration_days": {"type": "integer", "description": "Duration in days."},
                    "reason": {"type": "string", "description": "Business justification."}
                },
                "required": ["product_ids", "discount_percentage", "duration_days", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_inventory_alert",
            "description": "Draft an approval proposal to adjust safety stock threshold for a variant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "variant_id": {"type": "integer", "description": "The variant ID."},
                    "suggested_threshold": {"type": "integer", "description": "New safety threshold level."},
                    "reason": {"type": "string", "description": "Reason for threshold change."}
                },
                "required": ["variant_id", "suggested_threshold", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "Retrieve the current currency conversion exchange rate for base and target currencies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_currency": {
                        "type": "string",
                        "description": "Base currency code (e.g. 'USD', 'EUR', 'GBP')."
                    },
                    "target_currency": {
                        "type": "string",
                        "description": "Target currency code (e.g. 'EUR', 'CAD', 'GBP')."
                    }
                },
                "required": ["base_currency", "target_currency"]
            }
        }
    },
]