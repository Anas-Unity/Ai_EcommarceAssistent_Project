"""
src/test_agent.py
Tests the Gemini agent loop and confirms database audit logging in tool_runs.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3
from src.agent import run_investigation, DB_PATH

def test_loop():
    print("Testing Gemini Function Calling Loop...")
    question = "Can you look up order #1 and tell me who placed it, its status, and what items were ordered?"
    print(f"Question: '{question}'\n")

    result = run_investigation(question)

    print("=== Agent Response ===")
    print(result["answer"])
    print("\n=== Execution Summary ===")
    print(f"Request ID   : {result['request_id']}")
    print(f"Rounds Used  : {result['rounds_used']}")
    print(f"Tools Called : {len(result['executed_tools'])}")
    for t in result["executed_tools"]:
        print(f"  - Tool: {t['tool']} | Duration: {t['duration_ms']}ms | Status: {t['status']}")

    # Verify tool_runs table in SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tool_runs")
    count = cursor.fetchone()[0]
    print(f"\nAudit Log: Total rows in tool_runs table = {count}")
    conn.close()

if __name__ == "__main__":
    test_loop()