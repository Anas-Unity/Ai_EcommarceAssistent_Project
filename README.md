# Ai_EcommarceAssistent_Project

# ShopOps AI — Autonomous Ecommerce Operations Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Google Gemini](https://img.shields.io/badge/Gemini-Function--Calling-4285F4.svg?logo=google&logoColor=white)](https://aistudio.google.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4+-FF6384.svg?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![Tests](https://img.shields.io/badge/pytest-15%2F15%20Passing-brightgreen.svg)](https://docs.pytest.org/)

An enterprise-grade autonomous operations assistant designed for Shopify-style e-commerce stores. Rather than relying on Large Language Models to perform unreliable mental arithmetic over raw records, **ShopOps AI** combines **deterministic Python and parameterized SQL** with **Gemini function calling** via the OpenAI Chat Completions compatibility endpoint.

The assistant diagnoses period-over-period sales declines, forecasts safety stock replenishment, reconciles order histories, ingests live Shopify webhooks, and drafts sensitive promotional writes through a strictly audited **Human-in-the-Loop approval workflow with Role-Based Access Control (RBAC)**.

---

## 📑 Table of Contents
1. [System Architecture](#-system-architecture)
2. [Technology Stack](#-technology-stack)
3. [Standardized Metric Definitions](#-standardized-metric-definitions)
4. [Injected Ground Truth Scenarios](#-injected-ground-truth-scenarios)
5. [The 4 Core Investigation Workflows](#-the-4-core-investigation-workflows)
6. [Role-Based Access Control (RBAC) & Idempotency](#-role-based-access-control-rbac--idempotency)
7. [Minimalist Dashboard & UI Layout](#-minimalist-dashboard--ui-layout)
8. [Shopify Sync Engine & Cached Currency API](#-shopify-sync-engine--cached-currency-api)
9. [Automated Evaluation Benchmark (50 Scenarios)](#-automated-evaluation-benchmark-50-scenarios)
10. [Setup & Installation Instructions](#-setup--installation-instructions)
11. [REST API Documentation](#-rest-api-documentation)
12. [Automated Test Suite Verification](#-automated-test-suite-verification)
13. [Project Directory Layout](#-project-directory-layout)

---

## 🏛️ System Architecture

```text
                                 ┌────────────────────────────────────────────────────────┐
                                 │              Browser Client (Vanilla HTML/CSS/JS)      │
                                 │  • Minimalist Store Dashboard  • Multi-Line Chart.js   │
                                 │  • Real-Time Copilot (SSE)     • Admin Approval Inbox  │
                                 └───────────────────────────┬────────────────────────────┘
                                                             │ HTTP / SSE Stream
                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           FastAPI Microservice Layer                                        │
│                                                                                                             │
│  ┌───────────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────────────────┐  │
│  │    Agent Orchestrator     │    │   Role Access Control    │    │        Shopify Sync Engine           │  │
│  │  • Gemini Tool Dispatch   │    │  • Store Manager (Admin) │    │  • orders/create Webhook Ingestion   │  │
│  │  • Thought Signature Echo │    │  • Operations Analyst    │    │  • refunds/create Webhook Ingestion  │  │
│  │  • 90s Timeout & Retries  │    │  • Support Specialist    │    │  • Idempotency & Auto-Reconciliation │  │
│  └─────────────┬─────────────┘    └────────────┬─────────────┘    └──────────────────┬───────────────────┘  │
└────────────────┼───────────────────────────────┼─────────────────────────────────────┼──────────────────────┘
                 │ Execution (Allowlist Only)    │ Permissions Matrix                  │ Atomic Ingest
                 ▼                               ▼                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     SQLite Relational Database Engine                                       │
│                                                                                                             │
│  • customers (5,000 rows)         • orders (20,000+ rows)             • inventory (900 variants)            │
│  • products (300 items)           • order_items (58,000+ line items)  • inventory_movements (10,000 rows)   │
│  • variants (900 SKUs)            • refunds (1,000 rows)              • discount_codes (50+ active promos)  │
│  • tool_runs (Audit Trail)        • approval_requests (Idempotent Human-in-the-Loop Action Inbox)           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

💻 Technology Stack

| Component         | Technology                | Description                                                                                                                    |
| :---------------- | :------------------------ | :----------------------------------------------------------------------------------------------------------------------------- |
| **LLM Reasoning** | Google Gemini             | Accessed via OpenAI Chat Completions compatibility endpoint (`gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-3.5-flash-lite`). |
| **Backend API**   | FastAPI & Pydantic        | High-speed ASGI server with Pydantic schema validation and SSE streaming.                                                      |
| **Database**      | SQLite3                   | Relational schema with foreign keys, indexes, and parameterized SQL queries.                                                   |
| **Frontend UI**   | HTML5 / CSS3 / Vanilla JS | Zero-build frontend featuring responsive flexbox/grid, Chart.js, and Marked.js.                                                |
| **Live Visuals**  | Chart.js 4.4              | Dual-axis, multi-line interactive time-series chart with gradient fills.                                                       |
| **Unit Testing**  | pytest                    | 15 comprehensive automated test suites covering math, RBAC, idempotency, and webhooks.                                         |

📐 Standardized Metric Definitions

To ensure strict consistency across all analytical tools, metrics follow
standardized formulas (docs/metrics_definitions.md):

  - Timezone Standard: All database timestamps are generated, persisted, and
    queried in UTC (YYYY-MM-DD HH:MM:SS). Complete days span 00:00:00 to
    23:59:59 UTC.
  - Order Inclusion Criteria: Only orders marked completed or shipped count
    toward top-line financial metrics. Orders marked cancelled or pending are
    excluded.
  - Gross Revenue:
    \sum (\text{item\_quantity} \times \text{item\_price} - \text{item\_discount})
    across valid orders.
  - Net Revenue: \text{Gross Revenue} - \sum(\text{refund\_amount}).
  - Gross Margin ($):
    \text{Gross Revenue} - \sum(\text{item\_quantity} \times \text{variant\_cost}).
  - Gross Margin (%): (\text{Gross Margin} / \text{Gross Revenue}) \times 100.
  - Average Order Value (AOV):
    \text{Gross Revenue} / \text{Total Completed Orders}.
  - Average Daily Sales Velocity:
    \text{Units Sold in Window} / \text{Days Observed}.
  - Days of Stock Remaining:
    \text{Available Units} / \text{Average Daily Velocity} (zero-sales items
    safely handled to prevent division-by-zero).
  - Suggested Reorder Quantity:
    \max(0, \text{Target Coverage Days} \times \text{Average Daily Sales} - \text{Available Units}).

🎯 Injected Ground Truth Scenarios

The synthetic generator (src/generate_data.py) seeded SQLite with 12 months of
realistic transactions using a fixed random seed (SEED = 42). This injects six
verifiable ground truths used to grade the AI:

1.  Weekend Sales Volume Surge: Order volume increases by 30%–40% on Saturdays
    and Sundays relative to weekdays.
2.  Promotional Margin Degradation (FLASH50): A 5-day flash sale 30 days prior
    surges order volume 2.2x, but cuts gross profit margin in half.
3.  Product Stockout Collapse (Product ID 42): Alpine Winter Performance Jacket
    was driven to 0 available stock 14 days ago. Sales immediately dropped to
    zero.
4.  Category Refund Spike (Footwear): ~60% of all store refunds cluster in
    Footwear, overwhelmingly citing sizing and fit issues.
5.  Returning Customer Basket Premium (VIP AOV): Customers 1 through 600
    purchase 3 to 6 items per order (versus 1 to 3 for standard customers),
    generating an AOV more than double the store baseline ($634 vs. $286).
6.  Recent Pipeline Friction: 15% cancellation and pending order rate in the
    most recent 7 days (compared to a 3% normal baseline).

🔍 The 4 Core Investigation Workflows

📉 Workflow A: Sales Decline Diagnosis

  - Prompt: "Compare the last seven complete days with the previous seven. What
    drove the revenue change? Distinguish association from causation."
  - Behavior: Automatically determines exact complete-week UTC boundaries, calls
    compare_sales_periods, ranks category/product performance, and checks
    stockout risk.
  - Causal Guardrail: The model explicitly distinguishes correlation from
    causation (notes that while out-of-stock jackets correlate with lost
    revenue, the data does not prove stockouts caused every single lost sale).

📦 Workflow B: Replenishment Planning

  - Prompt: "Which products may run out within two weeks, and how much should we
    reorder?"
  - Behavior: Evaluates 14-day sales velocity, flags critical 0-stock variants
    (e.g. Alpine Winter Performance Jacket), and computes exact recommended
    reorder quantities using safety stock formulas.

🔎 Workflow C: Order Deep-Dive

  - Prompt: "Check order #100. What was purchased, was anything refunded, and
    what is its current status?"
  - Behavior: Fetches order header, customer identity, line item specs, and
    refund audit history.
  - Hallucination Guardrail: Querying non-existent orders (e.g. Order #9999999)
    returns a clean "Order not found" error without fabricating fake records.

🏷️ Workflow D: Margin-Checked Discount Proposals

  - Prompt: "We have slow-selling jackets (Product ID 42). Propose a 10 percent
    discount for 3 days and submit it for approval."
  - Behavior: Checks variant costs and verifies that post-discount profit
    margins remain positive (~54%) before drafting.
  - Safety Guardrail: The AI cannot apply discounts directly. It drafts a
    pending proposal in approval_requests for human manager review.

🛡️ Role-Based Access Control (RBAC) & Idempotency

Permissions Matrix (src/auth.py)

| Feature / Action                  | Store Manager (Admin) | Operations Analyst | Support Specialist |
| :-------------------------------- | :-------------------: | :----------------: | :----------------: |
| Order Lookup (`get_order`)        | Allowed               | Allowed            | Allowed            |
| Catalog Search & Details          | Allowed               | Allowed            | Allowed            |
| Financial Summaries & Margins     | Allowed               | Allowed            | **Denied (403)**   |
| Sales Decline Diagnostics         | Allowed               | Allowed            | **Denied (403)**   |
| Inventory & Replenishment Tools   | Allowed               | Allowed            | **Denied (403)**   |
| Draft Approval Proposals          | Allowed               | Allowed            | **Denied (403)**   |
| Review Proposals (Approve/Reject) | Allowed               | **Denied (403)**   | **Denied (403)**   |
| Execute Store Writes to SQLite    | Allowed               | **Denied (403)**   | **Denied (403)**   |

Idempotency Guardrail

When an action is approved by a manager, clicking ⚡ Execute Store Write:

1.  Creates the real promotional code in discount_codes or updates
    inventory.reorder_threshold.
2.  Encodes executed: true directly into the approval payload.
3.  Locks the proposal with an EXECUTED badge.
4.  If a duplicate execution is triggered, the system rejects it with an
    Idempotency Guardrail alert: "Proposal #X has ALREADY been executed.
    Duplicate writes are blocked."

🎨 Minimalist Dashboard & UI Layout

The interface is structured into an organized, minimalist operations workspace:

  - Left Navigation Sidebar:

      - 📈 Store Analytics: Interactive Chart.js time-series graph, KPIs, Best
        Sellers, and Slow Movers.
      - ✅ Confirmed Orders: Filtered ledger of all completed and shipped
        customer checkouts.
      - ⚡ Live & New Orders: Real-time stream with a one-click "⚡ Simulate New
        Incoming Orders" button.
      - ❌ Cancelled Orders: Audit table monitoring checkout friction
        (Scenario 6).
      - 🔄 Returns & Refunds: Processed return logs with the Footwear anomaly
        filter.
      - 🤖 AI Operations Copilot: Opens the 3-column operations workspace.
      - Active Role Dropdown: Live role switching (Store Manager, Operations
        Analyst, Support Specialist).

  - AI Copilot 3-Column Workspace:

      - Left Panel: 📥 Admin Approval Inbox (Interactive cards with Approve,
        Reject, and Execute buttons).
      - Center Panel: 💬 Conversational Stream with a Quick Workflow Dropdown (A,
        B, C, D) and real-time step-by-step thinking pills.
      - Right Panel: 🔍 Live Tool Execution Trace displaying sub-millisecond
        query latencies, parameters, and status codes.

🔄 Shopify Sync Engine & Cached Currency API

1. Shopify Webhook Synchronization (src/shopify_sync.py)

  - Ingests real-world Shopify JSON payloads for orders/create and
    refunds/create.
  - Idempotency: Checks orders.order_id before inserting; repeated webhook
    deliveries from Shopify retries are safely skipped.
  - Atomic Ledger Reconciliation: Automatically decrements inventory units and
    records an audit row in inventory_movements.

2. Cached Exchange-Rate Engine (src/exchange_rate.py)

  - Provides currency conversion across USD, EUR, GBP, CAD, AUD, JPY, and PKR.
  - Cache Policy: 1-hour in-memory TTL prevents redundant external API hits.

📊 Automated Evaluation Benchmark (50 Scenarios)

The assistant was benchmarked using an automated evaluation harness
(src/evaluate.py) against the standardized 50-question evaluation dataset
(data/eval_dataset.json):

======================================================================
EVALUATION BENCHMARK SUMMARY (docs/evaluation_report.md)
======================================================================
Total Evaluation Scenarios    : 50 Operational Test Cases
Evaluated Test Batch          : 15 Representative Multi-Turn Cases
Average Reasoning Rounds      : 1.87 rounds (< 2.0 target)
Average Round-Trip Latency    : 5,005.8 ms
P95 Round-Trip Latency        : 8,254.7 ms
Schema & Parameter Adherence  : 100%
RBAC Security Block Rate      : 100%
Idempotency Success Rate      : 100%
Evaluation Report Emitted     : docs/evaluation_report.md

🚀 Setup & Installation Instructions

Prerequisites

  - Python 3.11, 3.12, or 3.13 installed
  - Google Gemini API Key (Google AI Studio)

1. Clone & Enter Repository

git clone https://github.com/your-username/ecommerce_ai_assistant.git
cd ecommerce_ai_assistant

2. Create Virtual Environment

# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on Mac / Linux
source venv/bin/activate

3. Install Dependencies

pip install -r requirements.txt

4. Configure Environment Variables

Create a .env file in the root directory:

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

(Supports gemini-1.5-flash, gemini-2.0-flash, or gemini-3.5-flash-lite).

5. Generate Database & Seed Ground Truths

# Generates 12 months of synthetic data with 6 injected business patterns
python src/generate_data.py

# Verifies database integrity and pattern presence
python src/verify_db.py

6. Run the Test Suites

python -m pytest tests/ -v

7. Launch the Web Application

python -m uvicorn src.main:app --reload --port 8000

Open your browser and navigate to: 👉 http://127.0.0.1:8000

📡 REST API Documentation

| Endpoint                        | Method | Role Required | Description                                                                             |
| :------------------------------ | :----: | :-----------: | :-------------------------------------------------------------------------------------- |
| `/api/chat/stream`              | `POST` | Any           | Real-time Server-Sent Events (SSE) stream for conversational investigations.            |
| `/api/timeseries`               | `GET`  | Any           | Returns daily aggregated points for multi-metric Chart.js graphs.                       |
| `/api/dashboard-analytics`      | `GET`  | Any           | Filterable KPIs, best sellers, slow movers, and category returns by date range.         |
| `/api/orders-list`              | `GET`  | Any           | Returns order records filtered by status (`completed`, `cancelled`, `all`).             |
| `/api/refunds-list`             | `GET`  | Any           | Returns refund audit records.                                                           |
| `/api/approvals`                | `GET`  | Any           | Lists pending, approved, and executed proposals.                                        |
| `/api/approvals/{id}/action`    | `POST` | Manager       | Approves or rejects a proposal (`{"status": "approved", "reviewer": "store_manager"}`). |
| `/api/approvals/{id}/execute`   | `POST` | Manager       | Idempotently executes approved writes into SQLite tables.                               |
| `/api/tool-runs`                | `GET`  | Any           | Fetches audit telemetry and execution latencies from `tool_runs`.                       |
| `/api/simulator/tick`           | `POST` | Any           | Simulates live incoming customer checkouts and inventory deductions.                    |
| `/api/shopify/webhooks/orders`  | `POST` | Webhook       | Ingests incoming Shopify orders with duplicate webhook deduplication.                   |
| `/api/shopify/webhooks/refunds` | `POST` | Webhook       | Ingests incoming Shopify refunds.                                                       |
| `/api/currency/exchange-rate`   | `GET`  | Any           | Fetches reference conversion rates with 1-hour caching.                                 |

Interactive Swagger documentation is available at: http://127.0.0.1:8000/docs.

✅ Automated Test Suite Verification

All 15 automated tests pass deterministically via pytest:

================================== test session starts ==================================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.7.0
rootdir: E:\ecommerce_ai_assistant
configfile: pytest.ini
collected 15 items

tests/test_rbac.py::test_support_role_restrictions PASSED                         [  6%]
tests/test_rbac.py::test_analyst_role_permissions PASSED                          [ 13%]
tests/test_rbac.py::test_analyst_cannot_approve_proposal PASSED                   [ 20%]
tests/test_rbac.py::test_idempotent_execution_guardrail PASSED                    [ 26%]
tests/test_shopify_sync.py::test_shopify_order_sync_and_idempotency PASSED        [ 33%]
tests/test_shopify_sync.py::test_shopify_refund_sync PASSED                       [ 40%]
tests/test_shopify_sync.py::test_exchange_rate_caching PASSED                     [ 46%]
tests/test_tools.py::test_sales_summary_valid_metrics PASSED                      [ 53%]
tests/test_tools.py::test_compare_sales_periods PASSED                            [ 60%]
tests/test_tools.py::test_product_performance_ranking PASSED                      [ 66%]
tests/test_tools.py::test_refund_summary_detects_anomaly PASSED                   [ 73%]
tests/test_tools.py::test_stockout_risk_and_zero_division PASSED                  [ 80%]
tests/test_tools.py::test_get_order_existing PASSED                               [ 86%]
tests/test_tools.py::test_get_order_unknown PASSED                                [ 93%]
tests/test_tools.py::test_product_lookup_and_details PASSED                       [100%]

================================== 15 passed in 3.99s ===================================

📁 Project Directory Layout

ecommerce_ai_assistant/
├── data/
│   ├── ecommerce.db             # Generated SQLite operational database
│   ├── eval_dataset.json        # 50 standardized evaluation test scenarios
│   └── injected_scenarios.json  # Injected ground truth metadata
├── docs/
│   ├── evaluation_report.md     # Automated benchmark & latency report
│   └── metrics_definitions.md   # Standard business metric boundary formulas
├── src/
│   ├── __init__.py
│   ├── agent.py                 # Gemini tool loop, SSE streaming, thought signature handler
│   ├── auth.py                  # Role-Based Access Control matrix
│   ├── create_eval_dataset.py   # 50-scenario dataset generator
│   ├── evaluate.py              # Automated evaluation benchmark harness
│   ├── exchange_rate.py         # In-memory cached currency rate engine
│   ├── generate_data.py         # Synthetic Shopify data generator (Seed: 42)
│   ├── main.py                  # FastAPI server & REST API endpoints
│   ├── schema.sql               # Database DDL schema & constraints
│   ├── shopify_sync.py          # Shopify webhook ingestion & reconciliation engine
│   ├── simulator.py             # Live store event simulator
│   ├── tool_schemas.py          # JSON function-calling specifications
│   ├── tools.py                 # 10 deterministic SQL/Python operational tools
│   └── verify_db.py             # Ground truth verification script
├── static/
│   └── index.html               # Minimalist Dashboard & AI Copilot interface
├── tests/
│   ├── test_rbac.py             # RBAC & idempotency test suite
│   ├── test_shopify_sync.py     # Shopify webhook & caching test suite
│   └── test_tools.py            # Read-only operational tools test suite
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Frozen Python package dependencies
└── README.md                    # Complete project documentation

📄 License

This project is open-source and available under the MIT License.
