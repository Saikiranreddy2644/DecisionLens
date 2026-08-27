# tests/test_openrouter_five.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investigation_engine.openrouter_summary import generate_summary_for_one_investigation

for investigation_id in [7, 8, 9, 10, 11]:
    print(f"\n{'='*80}\nInvestigation {investigation_id}\n{'='*80}")
    result = generate_summary_for_one_investigation(investigation_id)
    if result["status"] == "OK":
        print(f"✓ SUCCESS: {result['summary'][:150]}...")
    else:
        print(f"✗ FAILED: {result['error']}")