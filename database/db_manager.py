# database/db_manager.py
"""
Database manager for DecisionLens — handles SQLite connection,
schema creation, and inserting Investigation Reports.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_connection(db_path: str = "data/decisionlens.db") -> sqlite3.Connection:
    """
    Opens a connection to the SQLite database, creating the parent
    directory if needed. Enables foreign key enforcement (off by
    default in SQLite).
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def initialize_schema(
    db_path: str = "data/decisionlens.db",
    schema_path: str = None
):
    """
    Runs schema.sql against the database and applies required schema updates.
    """
    if schema_path is None:
        schema_path = os.path.join(BASE_DIR, "database", "schema.sql")

    conn = get_connection(db_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(investigations)")
    columns = [row[1] for row in cursor.fetchall()]

    if "source" not in columns:
        cursor.execute(
            "ALTER TABLE investigations ADD COLUMN source TEXT NOT NULL DEFAULT 'superstore'"
        )

    conn.commit()
    conn.close()


def get_or_create_store(conn: sqlite3.Connection, store_name: str) -> int:
    """Returns store_id, inserting a new row if this store hasn't been seen."""
    cursor = conn.cursor()
    cursor.execute("SELECT store_id FROM stores WHERE store_name = ?", (store_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO stores (store_name) VALUES (?)", (store_name,))
    conn.commit()
    return cursor.lastrowid


def get_or_create_category(conn: sqlite3.Connection, category_name: str) -> int:
    """Returns category_id, inserting a new row if this category hasn't been seen."""
    cursor = conn.cursor()
    cursor.execute("SELECT category_id FROM categories WHERE category_name = ?", (category_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))
    conn.commit()
    return cursor.lastrowid


def insert_investigation_report(conn: sqlite3.Connection, report) -> int:
    """
    Inserts an InvestigationReport object (from evidence_aggregator.py)
    into the investigations + evidence tables.

    Returns the new investigation_id.
    """
    store_id = get_or_create_store(conn, report.store)
    category_id = get_or_create_category(conn, report.category)

    investigation_date = f"{report.year}-W{report.week:02d}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO investigations (
            store_id, category_id, source, investigation_date, year, week,
            metric, confidence_score, evidence_coverage, coverage_count,
            total_analyzers, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            store_id, category_id, "superstore", investigation_date, report.year, report.week,
            "Revenue", report.confidence_score, report.get_evidence_coverage_string(),
            report.coverage_count, report.total_analyzers, "open",
        ),
    )
    investigation_id = cursor.lastrowid

    for rank, evidence in enumerate(report.evidence, start=1):
        cursor.execute(
            """
            INSERT INTO evidence (
                investigation_id, analyzer_name, analyzer_score,
                sufficient_data, description, rank
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                investigation_id,
                evidence["analyzer"],
                evidence["score"],
                1 if evidence["sufficient_data"] else 0,
                evidence.get("reason", "") if not evidence["sufficient_data"] else "",
                rank,
            ),
        )

    conn.commit()
    return investigation_id


def get_investigation_count(db_path: str = "data/decisionlens.db") -> int:
    """Quick helper — how many investigations are currently stored."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM investigations")
    count = cursor.fetchone()[0]
    conn.close()
    return count