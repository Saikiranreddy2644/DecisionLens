# tests/test_recommendation_engine.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investigation_engine.recommendation_engine import generate_recommendations, print_recommendation_summary

result = generate_recommendations("data/decisionlens.db")
print_recommendation_summary(result)