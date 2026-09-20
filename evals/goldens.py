"""
Golden dataset for the PR review agents.

Each golden is a hand-written diff with exactly one deliberately planted defect
(or, for a "clean" golden, none at all). `expected_output` describes the planted
defect in prose — it is what the DeepEval judge compares the agent's finding
against, not a string the agent is expected to reproduce.
"""

from dataclasses import dataclass
from typing import List

from graph.state import PRReviewState
from tools.github_tool import DiffChunk


@dataclass
class DiffGolden:
    name: str
    filename: str
    diff: str
    expected_output: str


@dataclass
class CriticGolden:
    name: str
    security_findings: List[str]
    performance_findings: List[str]
    style_findings: List[str]
    expected_output: str


def as_state(golden: DiffGolden) -> PRReviewState:
    """Wrap a golden in the state shape the diff-reviewing agents read."""
    return {
        "pr_url": f"https://github.com/acme/{golden.name}/pull/1",
        "diff_chunks": [
            DiffChunk(
                filename=golden.filename,
                diff=golden.diff,
                start_line=1,
                end_line=len(golden.diff.splitlines()),
            )
        ],
        "security_findings": [],
        "performance_findings": [],
        "style_findings": [],
        "critic_output": [],
        "final_report": "",
        "error": None,
    }


def critic_state(golden: CriticGolden) -> PRReviewState:
    """Wrap a critic golden in the state shape the critic reads."""
    return {
        "pr_url": f"https://github.com/acme/{golden.name}/pull/1",
        "diff_chunks": [],
        "security_findings": golden.security_findings,
        "performance_findings": golden.performance_findings,
        "style_findings": golden.style_findings,
        "critic_output": [],
        "final_report": "",
        "error": None,
    }


SECURITY_GOLDENS = [
    DiffGolden(
        name="hardcoded-aws-credentials",
        filename="app/storage.py",
        diff='''@@ -1,5 +1,14 @@
 import boto3
 
+AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
+AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
+
+
+def get_s3_client():
+    return boto3.client(
+        "s3",
+        aws_access_key_id=AWS_ACCESS_KEY_ID,
+        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
+    )
''',
        expected_output=(
            "AWS credentials are hardcoded as string literals in app/storage.py "
            "instead of being read from the environment or a secrets manager, so "
            "they are committed to source control."
        ),
    ),
    DiffGolden(
        name="sql-injection-via-fstring",
        filename="app/users.py",
        diff='''@@ -10,3 +10,10 @@ def get_connection():
     return psycopg2.connect(DSN)
 
+
+def find_user_by_email(email):
+    conn = get_connection()
+    cursor = conn.cursor()
+    cursor.execute(f"SELECT id, name, role FROM users WHERE email = '{email}'")
+    return cursor.fetchone()
''',
        expected_output=(
            "The caller-supplied `email` value is interpolated directly into the "
            "SQL string with an f-string, allowing SQL injection. The query "
            "should use a parameterized statement instead."
        ),
    ),
    DiffGolden(
        name="unsafe-pickle-deserialization",
        filename="app/session.py",
        diff='''@@ -1,6 +1,15 @@
+import pickle
+
 from flask import request, jsonify
 
 from app import app
 
+
+@app.route("/session/restore", methods=["POST"])
+def restore_session():
+    blob = request.get_data()
+    session = pickle.loads(blob)
+    return jsonify(session)
''',
        expected_output=(
            "Untrusted request body bytes are passed to pickle.loads, which "
            "executes arbitrary code during deserialization and gives a remote "
            "attacker code execution."
        ),
    ),
]

SECURITY_CLEAN_GOLDEN = DiffGolden(
    name="clean-security-diff",
    filename="app/formatting.py",
    diff='''@@ -1,8 +1,12 @@
-def fmt(v):
-    return "%.2f" % v
+def format_currency(value: float) -> str:
+    """Render a float as a two-decimal currency string."""
+    return f"{value:.2f}"
''',
    expected_output=(
        "This diff only renames a function, adds a docstring and type hints, and "
        "switches to an f-string. It contains no security vulnerability of any "
        "kind — no secrets, no injection, no unsafe deserialization."
    ),
)

PERFORMANCE_GOLDENS = [
    DiffGolden(
        name="n-plus-one-queries",
        filename="app/reports.py",
        diff='''@@ -20,3 +20,13 @@ def get_session():
     return Session()
 
+
+def build_order_report(order_ids):
+    db = get_session()
+    rows = []
+    for order_id in order_ids:
+        order = db.query(Order).filter(Order.id == order_id).first()
+        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
+        rows.append((order.id, customer.name, order.total))
+    return rows
''',
        expected_output=(
            "The loop issues two database queries per order id, an N+1 query "
            "pattern. The orders and customers should be fetched in a single "
            "batched query or a join instead of one query per iteration."
        ),
    ),
    DiffGolden(
        name="quadratic-nested-scan",
        filename="app/dedupe.py",
        diff='''@@ -5,3 +5,12 @@ import hashlib
 
+
+def find_duplicates(incoming_records, known_records):
+    duplicates = []
+    for record in incoming_records:
+        for known in known_records:
+            if record.checksum == known.checksum:
+                duplicates.append(record)
+                break
+    return duplicates
''',
        expected_output=(
            "The nested loop compares every incoming record against every known "
            "record, giving O(n*m) quadratic behaviour. Building a set of known "
            "checksums first would make the lookup O(1) per record."
        ),
    ),
]

STYLE_GOLDENS = [
    DiffGolden(
        name="missing-docstring-and-poor-names",
        filename="app/calc.py",
        diff='''@@ -1,2 +1,8 @@
 import math
 
+
+def d(a, b, c):
+    x = a * b
+    y = x + c
+    return y
''',
        expected_output=(
            "The new public function `d` has no docstring, no type hints, and "
            "single-letter names (`d`, `a`, `b`, `c`, `x`, `y`) that do not "
            "convey meaning."
        ),
    ),
    DiffGolden(
        name="dead-code-and-unused-import",
        filename="app/stats.py",
        diff='''@@ -1,3 +1,12 @@
 import json
+import collections
 
+
+def mean(values: list) -> float:
+    """Return the arithmetic mean of `values`."""
+    total = sum(values)
+    return total / len(values)
+    print("computed mean")
''',
        expected_output=(
            "`collections` is imported but never used, and the print() call "
            "after the return statement is unreachable dead code."
        ),
    ),
]

CRITIC_GOLDENS = [
    CriticGolden(
        name="deduplicates-same-issue-across-reviewers",
        security_findings=[
            "CRITICAL | app/users.py | 42 | User-supplied email is interpolated "
            "into the SQL string, allowing SQL injection"
        ],
        performance_findings=[],
        style_findings=[
            "SUGGESTION | app/users.py | 42 | Avoid building SQL with an "
            "f-string; use a parameterized query"
        ],
        expected_output=(
            "A single finding for app/users.py line 42 about the SQL string "
            "being built from user input. The security and style reviewers "
            "reported the same underlying issue, so it must appear once, at the "
            "higher CRITICAL severity rather than SUGGESTION."
        ),
    ),
    CriticGolden(
        name="ranks-critical-before-lower-severities",
        security_findings=[
            "CRITICAL | app/storage.py | 3 | AWS secret access key hardcoded in source"
        ],
        performance_findings=[
            "WARNING | app/reports.py | 24 | Database query executed inside a "
            "loop, causing N+1 queries"
        ],
        style_findings=[
            "SUGGESTION | app/calc.py | 4 | Public function `d` is missing a docstring"
        ],
        expected_output=(
            "All three distinct findings are kept, ordered CRITICAL first "
            "(app/storage.py hardcoded key), then WARNING (app/reports.py N+1 "
            "queries), then SUGGESTION (app/calc.py missing docstring)."
        ),
    ),
]
