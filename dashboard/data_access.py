# dashboard/data_access.py
"""
Single source of truth for all database reads in the DecisionLens dashboard.
Every page calls functions from here — no raw SQL anywhere else.
"""

import sqlite3
import pandas as pd
import os
from database.db_manager import initialize_schema

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "decisionlens.db")


def get_connection():
    initialize_schema(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# Overview
# ─────────────────────────────────────────────

def get_overview_stats(source: str = "superstore") -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM investigations WHERE source = ?", (source,))
    total_investigations = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT year || '-' || week)
        FROM investigations WHERE source = ?
    """, (source,))
    total_events = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM recommendations r
        JOIN investigations i ON r.investigation_id = i.investigation_id
        WHERE i.source = ?
    """, (source,))
    total_recommendations = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM recommendations r
        JOIN investigations i ON r.investigation_id = i.investigation_id
        WHERE i.source = ? AND r.priority = 'immediate'
    """, (source,))
    high_priority = cursor.fetchone()[0]

    cursor.execute("""
        SELECT AVG(confidence_score)
        FROM investigations WHERE source = ?
    """, (source,))
    avg_confidence = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT s.store_name, COUNT(*) as count
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        WHERE i.source = ?
        GROUP BY s.store_name
        ORDER BY count DESC
        LIMIT 10
    """, (source,))
    store_breakdown = [{"store": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT c.category_name, COUNT(*) as count
        FROM investigations i
        JOIN categories c ON i.category_id = c.category_id
        WHERE i.source = ?
        GROUP BY c.category_name
        ORDER BY count DESC
    """, (source,))
    category_breakdown = [{"category": row[0], "count": row[1]} for row in cursor.fetchall()]

    conn.close()
    return {
        "total_investigations": total_investigations,
        "total_events": total_events,
        "total_recommendations": total_recommendations,
        "high_priority_count": high_priority,
        "avg_confidence": avg_confidence,
        "store_breakdown": store_breakdown,
        "category_breakdown": category_breakdown,
    }


# ─────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────

def get_events_table(source: str = "superstore") -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            i.investigation_id,
            s.store_name        AS store,
            c.category_name     AS category,
            i.year,
            i.week,
            i.investigation_date AS period,
            i.confidence_score,
            i.evidence_coverage,
            i.coverage_count,
            COALESCE(r.priority, 'none') AS priority
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        JOIN categories c ON i.category_id = c.category_id
        LEFT JOIN recommendations r ON i.investigation_id = r.investigation_id
        WHERE i.source = ?
        ORDER BY i.confidence_score DESC
    """, conn, params=(source,))
    conn.close()
    return df


# ─────────────────────────────────────────────
# Investigation Detail
# ─────────────────────────────────────────────

def get_investigation_detail(investigation_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.investigation_id, s.store_name, c.category_name,
               i.year, i.week, i.investigation_date,
               i.confidence_score, i.evidence_coverage, i.coverage_count,
               i.total_analyzers, i.status, i.source
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        JOIN categories c ON i.category_id = c.category_id
        WHERE i.investigation_id = ?
    """, (investigation_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    investigation = dict(row)

    cursor.execute("""
        SELECT analyzer_name, analyzer_score, sufficient_data, rank, description
        FROM evidence
        WHERE investigation_id = ?
        ORDER BY rank
    """, (investigation_id,))
    evidence = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT action, priority, rationale, status
        FROM recommendations
        WHERE investigation_id = ?
    """, (investigation_id,))
    rec_row = cursor.fetchone()
    recommendation = dict(rec_row) if rec_row else None

    cursor.execute("""
        SELECT summary_text, generated_by
        FROM summaries
        WHERE investigation_id = ?
    """, (investigation_id,))
    sum_row = cursor.fetchone()
    summary = dict(sum_row) if sum_row else None

    conn.close()
    return {
        "investigation": investigation,
        "evidence": evidence,
        "recommendation": recommendation,
        "summary": summary,
    }


# ─────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────

def get_analytics_data(source: str = "superstore") -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.analyzer_name, COUNT(*) as times_ranked_1
        FROM evidence e
        JOIN investigations i ON e.investigation_id = i.investigation_id
        WHERE e.rank = 1 AND e.sufficient_data = 1 AND i.source = ?
        GROUP BY e.analyzer_name
        ORDER BY times_ranked_1 DESC
    """, (source,))
    top_analyzers = [{"analyzer": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT confidence_score
        FROM investigations
        WHERE source = ?
    """, (source,))
    confidence_scores = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT s.store_name, COUNT(*) as count, AVG(i.confidence_score) as avg_conf
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        WHERE i.source = ?
        GROUP BY s.store_name
        ORDER BY count DESC
    """, (source,))
    store_rollup = [{"store": row[0], "count": row[1], "avg_confidence": row[2]}
                    for row in cursor.fetchall()]

    cursor.execute("""
        SELECT c.category_name, COUNT(*) as count, AVG(i.confidence_score) as avg_conf
        FROM investigations i
        JOIN categories c ON i.category_id = c.category_id
        WHERE i.source = ?
        GROUP BY c.category_name
        ORDER BY count DESC
    """, (source,))
    category_rollup = [{"category": row[0], "count": row[1], "avg_confidence": row[2]}
                       for row in cursor.fetchall()]

    cursor.execute("""
        SELECT COALESCE(r.priority, 'none'), COUNT(*) as count
        FROM investigations i
        LEFT JOIN recommendations r ON i.investigation_id = r.investigation_id
        WHERE i.source = ?
        GROUP BY r.priority
    """, (source,))
    priority_breakdown = [{"priority": row[0], "count": row[1]}
                          for row in cursor.fetchall()]

    conn.close()
    return {
        "top_analyzers": top_analyzers,
        "confidence_scores": confidence_scores,
        "store_rollup": store_rollup,
        "category_rollup": category_rollup,
        "priority_breakdown": priority_breakdown,
    }


# ─────────────────────────────────────────────
# Mode B helpers
# ─────────────────────────────────────────────

def clear_demo_data():
    """Delete all demo_upload rows before a fresh run."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT investigation_id FROM investigations WHERE source = 'demo_upload'
    """)
    demo_ids = [row[0] for row in cursor.fetchall()]

    if demo_ids:
        placeholders = ",".join("?" * len(demo_ids))
        cursor.execute(f"DELETE FROM summaries WHERE investigation_id IN ({placeholders})", demo_ids)
        cursor.execute(f"DELETE FROM recommendations WHERE investigation_id IN ({placeholders})", demo_ids)
        cursor.execute(f"DELETE FROM evidence WHERE investigation_id IN ({placeholders})", demo_ids)
        cursor.execute(f"DELETE FROM investigations WHERE investigation_id IN ({placeholders})", demo_ids)

    conn.commit()
    conn.close()
    return len(demo_ids)


def get_stores(source: str = "superstore") -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT s.store_name
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        WHERE i.source = ?
        ORDER BY s.store_name
    """, (source,))
    stores = [row[0] for row in cursor.fetchall()]
    conn.close()
    return stores


def get_categories(source: str = "superstore") -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT c.category_name
        FROM investigations i
        JOIN categories c ON i.category_id = c.category_id
        WHERE i.source = ?
        ORDER BY c.category_name
    """, (source,))
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories