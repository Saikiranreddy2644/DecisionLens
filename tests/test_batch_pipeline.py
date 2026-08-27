# tests/test_batch_pipeline.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investigation_engine.batch_pipeline import run_batch_investigation, print_batch_summary

result = run_batch_investigation("dataset/superstore.csv", db_path="data/decisionlens.db")
print_batch_summary(result)