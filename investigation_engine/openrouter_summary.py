# investigation_engine/openrouter_summary.py
"""
Phase 7: AI narration layer via OpenRouter (free tier).
Narrates already-complete investigation data into a short business
summary. Does NOT perform analysis — Phases 1-6 already decided
everything; this only writes it in plain English.
"""

import os
import requests
from database.db_manager import get_connection, initialize_schema

OPENROUTER_MODEL =   "openai/gpt-oss-20b"
OPENROUTER_URL = "https://api.groq.com/openai/v1/chat/completions"

PROMPT_TEMPLATE = """You are a retail analytics assistant. Below are FACTS already
computed by a statistical analysis system. Write a 3-4 sentence business
summary using ONLY the facts given. Do NOT invent numbers, causes, or
recommendations not listed below. Be direct and business-appropriate.

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

Write the summary now:"""


import time

def _call_openrouter(prompt: str, timeout_seconds: int = 20, max_retries: int = 3) -> str:
    """
    Single OpenRouter API call with automatic retry on rate limits (429).
    Reads the server's Retry-After header when present instead of guessing
    a wait time, falling back to a fixed backoff if the header is missing.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    last_error = None

    for attempt in range(1, max_retries + 1):
        response = requests.post(
            url=OPENROUTER_URL,
            headers={"Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}"},
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=timeout_seconds,
        )

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # content can be a string or a list of blocks
            if isinstance(content, list):
                # extract only text blocks, skip safety/metadata blocks
                text = " ".join(
                    block["text"] for block in content
                    if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
                ).strip()
            else:
                text = str(content).strip()
            
            # If we got nothing useful, raise so the fallback kicks in
            if not text or len(text) < 20:
                raise RuntimeError(f"Model returned unusable content: {content}")

            replacements = {
                "\u202f": " ",
                "\u00a0": " ",
                "\u2011": "-",
                "\u2018": "'", "\u2019": "'",
                "\u201c": '"', "\u201d": '"',
                "\u2013": "-", "\u2014": "-",
            }
            for bad, good in replacements.items():
                text = text.replace(bad, good)

            import re
            text = re.sub(r"\s+%", "%", text)

            return text

        if response.status_code == 429:
            last_error = f"HTTP 429: {response.text[:200]}"
            if attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) + 1 if retry_after else 15 * attempt
                print(f"    Rate limited, retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
                continue

        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

    raise RuntimeError(last_error)


def generate_summary_for_one_investigation(investigation_id: int, db_path: str = "data/decisionlens.db") -> dict:
    """
    Generates and stores a summary for exactly ONE investigation.
    Used for isolated testing before running the full batch.
    """
    initialize_schema(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.investigation_id, s.store_name, c.category_name, i.year, i.week,
               i.confidence_score, i.evidence_coverage,
               r.action, r.priority, r.rationale
        FROM investigations i
        JOIN stores s ON i.store_id = s.store_id
        JOIN categories c ON i.category_id = c.category_id
        JOIN recommendations r ON i.investigation_id = r.investigation_id
        WHERE i.investigation_id = ?
    """, (investigation_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return {"status": "FAILED", "error": f"Investigation {investigation_id} not found or has no recommendation"}

    (inv_id, store, category, year, week, confidence,
     coverage, action, priority, rationale) = row

    cursor.execute("""
        SELECT analyzer_name, analyzer_score, rank
        FROM evidence
        WHERE investigation_id = ? AND sufficient_data = 1 AND rank <= 3
        ORDER BY rank
    """, (investigation_id,))
    evidence_rows = cursor.fetchall()
    evidence_lines = "\n".join(
        f"  {rank}. {name} (score={score:.2f})" for name, score, rank in evidence_rows
    ) or "  (none)"

    prompt = PROMPT_TEMPLATE.format(
        store=store, category=category, year=year, week=week,
        confidence=confidence, coverage=coverage,
        evidence_lines=evidence_lines,
        action=action, priority=priority, rationale=rationale,
    )

    print(f"Prompt sent:\n{'-'*80}\n{prompt}\n{'-'*80}\n")

    try:
        summary_text = _call_openrouter(prompt)
    except Exception as e:
        conn.close()
        return {"status": "FAILED", "error": str(e)}

    cursor.execute(
        "INSERT INTO summaries (investigation_id, summary_text, generated_by) VALUES (?, ?, ?)",
        (investigation_id, summary_text, "openrouter"),
    )
    conn.commit()
    conn.close()

    return {"status": "OK", "investigation_id": investigation_id, "summary": summary_text}