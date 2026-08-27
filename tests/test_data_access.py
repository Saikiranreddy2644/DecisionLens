# tests/test_data_access.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.data_access import (
    get_overview_stats, get_events_table,
    get_investigation_detail, get_analytics_data
)

print("Testing data_access.py...")

stats = get_overview_stats()
print(f"\nOverview Stats:")
print(f"  Investigations: {stats['total_investigations']}")
print(f"  Events:         {stats['total_events']}")
print(f"  Recommendations:{stats['total_recommendations']}")
print(f"  High Priority:  {stats['high_priority_count']}")
print(f"  Avg Confidence: {stats['avg_confidence']:.1%}")

df = get_events_table()
print(f"\nEvents Table: {len(df)} rows, columns: {df.columns.tolist()}")

detail = get_investigation_detail(1)
print(f"\nInvestigation #1 Detail:")
print(f"  Store:    {detail['investigation']['store_name']}")
print(f"  Category: {detail['investigation']['category_name']}")
print(f"  Evidence rows: {len(detail['evidence'])}")
print(f"  Has recommendation: {detail['recommendation'] is not None}")
print(f"  Has summary: {detail['summary'] is not None}")

analytics = get_analytics_data()
print(f"\nAnalytics:")
print(f"  Top analyzer: {analytics['top_analyzers'][0]}")
print(f"  Confidence scores count: {len(analytics['confidence_scores'])}")
print(f"  Stores: {len(analytics['store_rollup'])}")

print("\n✓ data_access.py verified")