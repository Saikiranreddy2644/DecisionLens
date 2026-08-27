# tests/view_reports.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import get_connection

conn = get_connection("data/decisionlens.db")
cursor = conn.cursor()

# Top 10 highest-confidence investigations, with store/category names
cursor.execute("""
    SELECT i.investigation_id, s.store_name, c.category_name, i.year, i.week,
           i.confidence_score, i.evidence_coverage
    FROM investigations i
    JOIN stores s ON i.store_id = s.store_id
    JOIN categories c ON i.category_id = c.category_id
    ORDER BY i.confidence_score DESC
    LIMIT 10
""")

print(f"{'ID':<5}{'Store':<12}{'Category':<15}{'Week':<12}{'Confidence':<12}{'Coverage':<10}")
print("-" * 70)
for row in cursor.fetchall():
    inv_id, store, category, year, week, conf, coverage = row
    print(f"{inv_id:<5}{store:<12}{category:<15}{f'{year}-W{week:02d}':<12}{f'{conf:.0%}':<12}{coverage:<10}")

conn.close()