# investigation_engine/recommendation_engine.py
"""
Phase 6: Recommendation Engine — reads stored investigations + their
top-ranked evidence from SQLite, and generates one actionable
recommendation per investigation using a rule-based lookup keyed on
which analyzer explained the anomaly best. Reuses the same reasoning
already encoded in Phase 5's report narration, just systematized to
run across every stored investigation instead of printing one at a time.
"""

from database.db_manager import get_connection, initialize_schema


# Rule-based action templates, keyed by which analyzer ranked #1 for that investigation.
ACTION_TEMPLATES = {
    "top_contributor": "Check inventory/availability for the top-impact product at {store}",
    "product": "Investigate product mix shift in {category} at {store}",
    "store": "Audit {store} operations (staffing, local supply, local issues)",
    "category": "Review {category} category performance at {store}",
    "region": "Investigate regional supply chain or logistics issue affecting {store}'s region",
    "price": "Review pricing strategy for {category} — check for elasticity-driven demand shift",
    "historical": "Review incident reports from similar past weeks for {store} / {category}",
    "seasonality": "Confirm whether this deviates from expected seasonal pattern for {category}",
}

RATIONALE_TEMPLATES = {
    "top_contributor": "Top Contributor Analyzer identified this as the dominant driver (score={score:.2f}).",
    "product": "Product Analyzer found significant product-mix deviation (score={score:.2f}).",
    "store": "Store Analyzer found this store isolated from peer stores (score={score:.2f}).",
    "category": "Category Analyzer found this category diverging from store norm (score={score:.2f}).",
    "region": "Region Analyzer found regional deviation from norm (score={score:.2f}).",
    "price": "Price Analyzer detected an elasticity signal (score={score:.2f}).",
    "historical": "Historical Analyzer found this pattern significant relative to precedent (score={score:.2f}).",
    "seasonality": "Seasonality Analyzer found this atypical for the calendar week (score={score:.2f}).",
}


def _priority_from_confidence(confidence_score: float) -> str:
    if confidence_score >= 0.7:
        return "immediate"
    elif confidence_score >= 0.4:
        return "short-term"
    else:
        return "monitor"


def generate_recommendations(db_path: str = "data/decisionlens.db") -> dict:
    """
    Reads every investigation + its top-ranked (rank=1) evidence row,
    generates one recommendation per investigation, and stores it in
    the recommendations table. Investigations with no sufficient-data
    evidence are explicitly skipped (not silently dropped) with a
    preserved reason.

    Returns:
        {
            "status": "OK" | "FAILED",
            "investigations_processed": int,
            "total_recommendations_created": int,
            "skipped": list of {"investigation_id", "reason", "successful_analyzers"},
            "database_path": str,
            "errors": list
        }
    """
    errors = []
    skipped = []
    initialize_schema(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # All investigations, with their evidence_coverage for context
    cursor.execute("""
        SELECT investigation_id, evidence_coverage, coverage_count, total_analyzers
        FROM investigations
    """)
    all_investigations = cursor.fetchall()
    investigations_processed = len(all_investigations)

    # Top-ranked sufficient-data evidence, keyed by investigation_id
    cursor.execute("""
        SELECT i.investigation_id, s.store_name, c.category_name,
               i.confidence_score, e.analyzer_name, e.analyzer_score
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        JOIN categories c ON i.category_id = c.category_id
        JOIN evidence e ON i.investigation_id = e.investigation_id
        WHERE e.rank = 1 AND e.sufficient_data = 1
    """)
    rows_by_investigation = {row[0]: row for row in cursor.fetchall()}

    total_created = 0

    for investigation_id, evidence_coverage, coverage_count, total_analyzers in all_investigations:
        row = rows_by_investigation.get(investigation_id)

        if row is None:
            # No sufficient-data top evidence -> skip, but record why
            skipped.append({
                "investigation_id": investigation_id,
                "reason": "Insufficient evidence",
                "successful_analyzers": f"{coverage_count}/{total_analyzers}",
            })
            continue

        _, store, category, confidence_score, analyzer_name, analyzer_score = row

        try:
            action_template = ACTION_TEMPLATES.get(
                analyzer_name, "Review {category} performance at {store}"
            )
            rationale_template = RATIONALE_TEMPLATES.get(
                analyzer_name, "{analyzer_name} analysis flagged this (score={score:.2f})."
            )

            action = action_template.format(store=store, category=category)
            rationale = rationale_template.format(
                score=analyzer_score, analyzer_name=analyzer_name
            )
            priority = _priority_from_confidence(confidence_score)

            cursor.execute(
                """
                INSERT INTO recommendations (investigation_id, action, priority, rationale, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (investigation_id, action, priority, rationale, "pending"),
            )
            total_created += 1
        except Exception as e:
            errors.append(f"Investigation {investigation_id}: {e}")

    conn.commit()
    conn.close()

    return {
        "status": "OK",
        "investigations_processed": investigations_processed,
        "total_recommendations_created": total_created,
        "skipped": skipped,
        "database_path": db_path,
        "errors": errors,
    }


def print_recommendation_summary(result: dict):
    print("\n" + "=" * 80)
    print("RECOMMENDATION ENGINE — SUMMARY")
    print("=" * 80)
    print(f"Investigations processed:       {result['investigations_processed']}")
    print(f"Recommendations created:        {result['total_recommendations_created']}")
    print(f"Skipped:                        {len(result['skipped'])}")
    print(f"Errors:                         {len(result['errors'])}")
    print(f"Database:                       {result['database_path']}")

    if result["skipped"]:
        print("\nSkipped Investigations:")
        for s in result["skipped"]:
            print(f"  Investigation ID: {s['investigation_id']}")
            print(f"  Status: SKIPPED")
            print(f"  Reason: {s['reason']}")
            print(f"  Successful analyzers: {s['successful_analyzers']}")
            print(f"  Recommendation: None")
            print()

    if result["errors"]:
        print("Errors:")
        for err in result["errors"][:5]:
            print(f"  - {err}")

    print("=" * 80 + "\n")