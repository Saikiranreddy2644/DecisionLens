# tests/test_openrouter_batch.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investigation_engine.openrouter_batch_summary import generate_all_summaries_batched, print_batch_summary_report

result = generate_all_summaries_batched()
print_batch_summary_report(result)