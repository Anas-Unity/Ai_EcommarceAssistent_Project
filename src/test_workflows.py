"""
src/test_workflows.py
Tests all 4 operational workflows required by Page 4 of the assignment brief:
Workflow A: Sales Decline Diagnosis
Workflow B: Replenishment Planning
Workflow C: Order Investigation
Workflow D: Propose Discount (Human-in-the-Loop)
"""

import sys
import os
import json
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import run_investigation, DB_PATH

def print_separator(title):
    print("\n" + "=" * 80)
    print(f" {title} ")
    print("=" * 80)

def test_all_workflows():
    # -------------------------------------------------------------
    # WORKFLOW A: Investigate a sales decline
    # -------------------------------------------------------------
    print_separator("WORKFLOW A: Investigate a Sales Decline")
    q_a = "Compare the last seven complete days with the previous seven. What drove the revenue change? Distinguish association from causation."
    print(f"User Prompt: '{q_a}'\n")
    res_a = run_investigation(q_a, max_rounds=5)
    print("=== AI Analysis ===")
    print(res_a["answer"])
    print(f"\nRounds: {res_a['rounds_used']} | Tools Called: {[t['tool'] for t in res_a['executed_tools']]}")

    # -------------------------------------------------------------
    # WORKFLOW B: Plan replenishment
    # -------------------------------------------------------------
    print_separator("WORKFLOW B: Plan Replenishment")
    q_b = "Which products may run out within two weeks, and how much should we reorder for our critical items?"
    print(f"User Prompt: '{q_b}'\n")
    res_b = run_investigation(q_b, max_rounds=5)
    print("=== AI Analysis ===")
    print(res_b["answer"])
    print(f"\nRounds: {res_b['rounds_used']} | Tools Called: {[t['tool'] for t in res_b['executed_tools']]}")

    # -------------------------------------------------------------
    # WORKFLOW C: Investigate an order
    # -------------------------------------------------------------
    print_separator("WORKFLOW C: Investigate an Order")
    q_c = "Check order #100. What was purchased, was anything refunded, and what is its current status?"
    print(f"User Prompt: '{q_c}'\n")
    res_c = run_investigation(q_c, max_rounds=5)
    print("=== AI Analysis ===")
    print(res_c["answer"])
    print(f"\nRounds: {res_c['rounds_used']} | Tools Called: {[t['tool'] for t in res_c['executed_tools']]}")

    # -------------------------------------------------------------
    # WORKFLOW D: Propose a discount (Approval Request)
    # -------------------------------------------------------------
    print_separator("WORKFLOW D: Propose a Discount")
    q_d = "We have slow-selling jackets (Product ID 42). Propose a 10 percent discount for 3 days and submit it for approval."
    print(f"User Prompt: '{q_d}'\n")
    res_d = run_investigation(q_d, max_rounds=5)
    print("=== AI Analysis ===")
    print(res_d["answer"])
    print(f"\nRounds: {res_d['rounds_used']} | Tools Called: {[t['tool'] for t in res_d['executed_tools']]}")

    # Verify that a pending proposal was created in approval_requests table
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT request_id, action, status, requester, payload FROM approval_requests ORDER BY request_id DESC LIMIT 1")
    approval_row = cursor.fetchone()
    print("\n=== Verification of approval_requests Table ===")
    if approval_row:
        print(f"Proposal ID : {approval_row[0]}")
        print(f"Action      : {approval_row[1]}")
        print(f"Status      : {approval_row[2]} (Must be 'pending' - AI cannot auto-execute!)")
        print(f"Requester   : {approval_row[3]}")
    else:
        print("No approval request found in database!")
    conn.close()

if __name__ == "__main__":
    test_all_workflows()