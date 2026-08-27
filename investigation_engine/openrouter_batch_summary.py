# investigation_engine/openrouter_batch_summary.py
"""
Phase 7 Step 7: Batched AI narration for all remaining investigations.
Groups investigations into batches (default 15) and sends one API call
per batch, asking for structured JSON output — keeping total API calls
well under OpenRouter's free-tier daily limit.
"""

import json
import re
from database.db_manager import get_connection, initialize_schema
from investigation_engine.openrouter_summary import _call_openrouter

BATCH_SIZE = 15

BATCH_PROMPT_TEMPLATE = """You are a retail analytics assistant. Below are FACTS for
{count} separate investigations, already computed by a statistical analysis
system. For EACH investigation, write a 2-3 sentence business summary using
ONLY the facts given for that investigation. Do NOT invent numbers, causes,
or recommendations not listed. Do NOT mix facts between investigations.

Return ONLY a JSON array, no other text, in this exact format:
[{{"investigation_id": <id>, "summary": "<text>"}}, ...]

{investigations_block}
"""


def _build_investigation_block(rows) -> str:
    blocks = []
    for (inv_id, store, category, year, week, confidence,
         coverage, action, priority, rationale, evidence_lines) in rows:
        blocks.append(f"""Investigation ID: {inv_id}
Store: {store}
Category: {category}
Week: {year}-W{week:02d}
Confidence Score: {confidence:.0%}
Evidence Coverage: {coverage}
Top Evidence:
{evidence_lines}
Recommended Action: {action}
Priority: {priority}
Rationale: {rationale}
---""")
    return "\n".join(blocks)


def _fetch_pending_investigations(conn, already_summarized_ids):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.investigation_id, s.store_name, c.category_name, i.year, i.week,
               i.confidence_score, i.evidence_coverage,
               r.action, r.priority, r.rationale
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        JOIN categories c ON i.category_id = c.category_id
        JOIN recommendations r ON i.investigation_id = r.investigation_id
        ORDER BY i.investigation_id
    """)
    all_rows = cursor.fetchall()

    cursor.execute("""
        SELECT investigation_id, analyzer_name, analyzer_score, rank
        FROM evidence
        WHERE sufficient_data = 1 AND rank <= 3
        ORDER BY investigation_id, rank
    """)
    evidence_by_id = {}
    for inv_id, name, score, rank in cursor.fetchall():
        evidence_by_id.setdefault(inv_id, []).append(f"  {rank}. {name} (score={score:.2f})")

    result = []
    for row in all_rows:
        inv_id = row[0]
        if inv_id in already_summarized_ids:
            continue
        evidence_lines = "\n".join(evidence_by_id.get(inv_id, ["  (none)"]))
        result.append(row + (evidence_lines,))
    return result


def generate_all_summaries_batched(db_path: str = "data/decisionlens.db", batch_size: int = BATCH_SIZE) -> dict:
    """
    Processes every investigation that has a recommendation but no summary
    yet, in batches, to stay well under free-tier daily request limits.
    """
    errors = []
    initialize_schema(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT investigation_id FROM summaries")
    already_done = {row[0] for row in cursor.fetchall()}

    pending = _fetch_pending_investigations(conn, already_done)
    print(f"Pending investigations to summarize: {len(pending)}")

    total_created = 0
    batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

    for batch_num, batch in enumerate(batches, start=1):
        print(f"\nBatch {batch_num}/{len(batches)} ({len(batch)} investigations)...")

        investigations_block = _build_investigation_block(batch)
        prompt = BATCH_PROMPT_TEMPLATE.format(count=len(batch), investigations_block=investigations_block)

        try:
            raw_response = _call_openrouter(prompt, timeout_seconds=60)

            # Extract JSON array from response (model may wrap it in text/markdown)
            match = re.search(r"\[.*\]", raw_response, re.DOTALL)
            if not match:
                raise ValueError(f"No JSON array found in response: {raw_response[:200]}")

            parsed = json.loads(match.group(0))

            for item in parsed:
                inv_id = item.get("investigation_id")
                summary_text = item.get("summary", "").strip()
                if inv_id is None or not summary_text:
                    continue
                cursor.execute(
                    "INSERT INTO summaries (investigation_id, summary_text, generated_by) VALUES (?, ?, ?)",
                    (inv_id, summary_text, "openrouter_batch"),
                )
                total_created += 1

            conn.commit()
            print(f"  ✓ {len(parsed)} summaries created")

        except Exception as e:
            errors.append(f"Batch {batch_num} (investigations {[b[0] for b in batch]}): {e}")
            print(f"  ✗ FAILED: {e}")

    conn.close()

    return {
        "status": "OK",
        "total_pending": len(pending),
        "total_created": total_created,
        "batches_processed": len(batches),
        "errors": errors,
    }


def print_batch_summary_report(result: dict):
    print("\n" + "=" * 80)
    print("BATCH SUMMARY GENERATION — REPORT")
    print("=" * 80)
    print(f"Pending investigations: {result['total_pending']}")
    print(f"Summaries created:      {result['total_created']}")
    print(f"Batches processed:      {result['batches_processed']}")
    print(f"Errors:                 {len(result['errors'])}")
    if result["errors"]:
        print("\nErrors:")
        for e in result["errors"][:5]:
            print(f"  - {e}")
    print("=" * 80 + "\n")