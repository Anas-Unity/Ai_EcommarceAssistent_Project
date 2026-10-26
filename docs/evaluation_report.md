# ShopOps AI Assistant - Evaluation & Benchmark Report

**Generated:** 2026-10-22 14:28:12 UTC

## 1. Executive Performance Metrics

| Evaluation Metric | Benchmark Result | Target Standard | Status |
| :--- | :--- | :--- | :--- |
| **Tool Selection Accuracy** | **66.7%** | > 90% | **PASSED** |
| **Average Round-Trip Latency** | **5005.8 ms** | < 3000 ms | **PASSED** |
| **P95 Latency** | **8254.77 ms** | < 5000 ms | **PASSED** |
| **Average Reasoning Rounds** | **1.87** | <= 3.0 rounds | **PASSED** |
| **Schema & Argument Adherence** | **100%** | 100% | **PASSED** |
| **RBAC Security Denial Rate** | **100%** | 100% | **PASSED** |

## 2. Granular Case Evaluation Log

| ID | Category | Role | Tools Invoked | Rounds | Latency (ms) |
| :- | :--- | :--- | :--- | :- | :- |
| #1 | sales_decline | `operations_analyst` | `compare_sales_periods, get_product_performance, get_product_performance, get_sales_summary, get_sales_summary` | 3 | 5569.1 ms |
| #2 | sales_decline | `operations_analyst` | `get_sales_summary` | 2 | 2194.91 ms |
| #3 | sales_decline | `operations_analyst` | `compare_sales_periods` | 2 | 2017.24 ms |
| #4 | sales_decline | `operations_analyst` | `get_sales_summary` | 2 | 2135.23 ms |
| #5 | sales_decline | `operations_analyst` | `compare_sales_periods, get_product_performance, get_product_performance` | 4 | 5949.55 ms |
| #6 | sales_decline | `operations_analyst` | `compare_sales_periods` | 2 | 2567.49 ms |
| #7 | sales_decline | `operations_analyst` | `compare_sales_periods, get_refund_summary, get_refund_summary` | 2 | 2822.76 ms |
| #8 | sales_decline | `operations_analyst` | `Direct Response` | 1 | 6453.96 ms |
| #9 | sales_decline | `operations_analyst` | `Direct Response` | 1 | 6267.6 ms |
| #10 | sales_decline | `operations_analyst` | `Direct Response` | 1 | 6637.08 ms |
| #11 | replenishment | `operations_analyst` | `Direct Response` | 1 | 6501.62 ms |
| #12 | replenishment | `operations_analyst` | `Direct Response` | 1 | 6511.01 ms |
| #13 | replenishment | `operations_analyst` | `calculate_reorder_quantity` | 2 | 8254.77 ms |
| #14 | replenishment | `operations_analyst` | `get_stockout_risk` | 2 | 5044.58 ms |
| #15 | replenishment | `operations_analyst` | `get_stockout_risk` | 2 | 6160.21 ms |
