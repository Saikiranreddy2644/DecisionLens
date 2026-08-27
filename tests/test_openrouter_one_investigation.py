# tests/test_openrouter_one_investigation.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investigation_engine.openrouter_summary import generate_summary_for_one_investigation

result = generate_summary_for_one_investigation(investigation_id=1)
print("\nRESULT:")
print(result)