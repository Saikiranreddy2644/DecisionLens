# investigation_engine/evidence_aggregator.py
"""
Evidence Aggregator — combines all 8 analyzer outputs into a unified
Investigation Report with calculated confidence score and evidence coverage.

Takes: 8 analyzer results (from product_analyzer, category_analyzer, etc.)
Returns: Investigation Report object (structured, then rendered)
"""

import pandas as pd
import numpy as np
from utils.constants import (
    MAGNITUDE_SATURATION_STD,
)


class InvestigationReport:
    """Unified report combining all 8 analyzers' findings."""
    
    def __init__(self, store, category, year, week, analyzer_results, 
                 business_event_anomaly_score=0.91, 
                 kpi_correlation_strong=True):
        """
        Args:
            store, category, year, week: the anomaly coordinates
            analyzer_results: dict of {analyzer_name: result_dict} from all 8 analyzers
            business_event_anomaly_score: Isolation Forest score (0-1) from Anomaly Detection
            kpi_correlation_strong: whether revenue, profit, units all moved together
        """
        self.store = store
        self.category = category
        self.year = year
        self.week = week
        self.analyzer_results = analyzer_results
        self.business_event_anomaly_score = business_event_anomaly_score
        self.kpi_correlation_strong = kpi_correlation_strong
        
        # Aggregate evidence
        self._aggregate_evidence()
        self._calculate_confidence()
    
    def _aggregate_evidence(self):
        """Collect all analyzer outputs into ranked evidence list."""
        
        self.evidence = []
        self.coverage_count = 0
        self.total_analyzers = len(self.analyzer_results)
        
        # Process each analyzer
        for analyzer_name, result in self.analyzer_results.items():
            if result.get("sufficient_data", False):
                self.coverage_count += 1
                
                # Extract score and key findings
                score = result.get("analyzer_score", 0.0)
                
                self.evidence.append({
                    "analyzer": analyzer_name,
                    "score": score,
                    "sufficient_data": True,
                    "result": result,
                })
            else:
                # Analyzer couldn't run
                self.evidence.append({
                    "analyzer": analyzer_name,
                    "score": None,
                    "sufficient_data": False,
                    "reason": result.get("reason", "Insufficient data"),
                    "result": result,
                })
        
        # Sort by score (highest first)
        self.evidence = sorted(
            self.evidence,
            key=lambda x: x["score"] if x["score"] is not None else -1,
            reverse=True
        )
    
    def _calculate_confidence(self):
        """Apply the confidence formula."""
        
        # Extract scores from sufficient analyzers only
        sufficient_scores = [
            e["score"] for e in self.evidence 
            if e["sufficient_data"] and e["score"] is not None
        ]
        
        if not sufficient_scores:
            self.confidence_score = 0.0
            self.weighted_evidence = 0.0
            return
        
        # Weighted evidence: average of sufficient analyzer scores
        # (all have equal weight after individual magnitude×specificity calculation)
        self.weighted_evidence = np.mean(sufficient_scores)
        
        # Confidence formula:
        # (0.7 × weighted_evidence + 0.3 × anomaly_score) × correlation_gate
        
        anomaly_gate = self.business_event_anomaly_score
        correlation_gate = 1.0 if self.kpi_correlation_strong else 0.85
        
        self.confidence_score = (
            (0.7 * self.weighted_evidence + 0.3 * anomaly_gate) 
            * correlation_gate
        )
        
        # Clamp to [0, 1]
        self.confidence_score = max(0.0, min(self.confidence_score, 1.0))
    
    def get_evidence_coverage_string(self):
        """Format: '8/8 (100%)'"""
        pct = 100 * self.coverage_count / self.total_analyzers if self.total_analyzers > 0 else 0
        return f"{self.coverage_count}/{self.total_analyzers} ({pct:.0f}%)"
    
    def get_missing_analyzers(self):
        """List of analyzer names that couldn't run."""
        return [
            e["analyzer"] for e in self.evidence 
            if not e["sufficient_data"]
        ]
    
    def get_top_evidence(self, n=3):
        """Top N pieces of evidence by score."""
        return [e for e in self.evidence if e["sufficient_data"]][:n]
    
    def print_report(self):
        """Human-readable investigation report with detailed narration."""
        from investigation_engine.report_narration import generate_narration_for_evidence
    
        print("\n" + "="*80)
        print("INVESTIGATION REPORT")
        print("="*80)
    
        print(f"\nEvent Details:")
        print(f"  Store:     {self.store}")
        print(f"  Category:  {self.category}")
        print(f"  Week:      {self.year}-W{self.week:02d}")
    
        print(f"\nConfidence & Coverage:")
        print(f"  Confidence Score:    {self.confidence_score:.0%}")
        print(f"  Evidence Coverage:   {self.get_evidence_coverage_string()}")
        print(f"  Weighted Evidence:   {self.weighted_evidence:.3f}")
        print(f"  Anomaly Score:       {self.business_event_anomaly_score:.3f}")
    
        print(f"\nKey Findings (Ranked by Strength):")
        for i, evidence in enumerate(self.get_top_evidence(5), 1):
            narration = generate_narration_for_evidence(evidence["analyzer"], evidence["result"])
            if narration:
                print(f"  {i}. {narration}")
    
        missing = self.get_missing_analyzers()
        if missing:
            print(f"\nInsufficient Data For:")
            for analyzer in missing:
                result = self.analyzer_results[analyzer]
                print(f"  • {analyzer:20s} — {result.get('reason', 'Unknown')}")
    
        print(f"\nPrimary Root Cause:")
        top = self.get_top_evidence(1)
        if top:
            top_analyzer = top[0]["analyzer"]
            top_result = top[0]["result"]
            narration = generate_narration_for_evidence(top_analyzer, top_result)
            if narration:
                print(f"  {narration}")
    
        print("\nRecommended Actions:")
        top = self.get_top_evidence(1)
        if top:
            top_analyzer = top[0]["analyzer"]
            if top_analyzer == "top_contributor":
                contributors = top[0]["result"].get("top_contributors", [])
                if contributors:
                    product = contributors[0]["product"]
                    print(f"  1. Check {product} inventory availability at {self.store}")
                    print(f"  2. Investigate why {product} sales collapsed this week")
                    print(f"  3. Compare to other stores — is {product} unavailable company-wide?")
            elif top_analyzer == "store":
                print(f"  1. Audit {self.store} operations (staffing, local issues)")
                print(f"  2. Check for local supply chain disruptions")
                print(f"  3. Compare {self.store} metrics to peer stores")
            elif top_analyzer == "price":
                print(f"  1. Review pricing strategy for {self.category}")
                print(f"  2. Analyze demand elasticity — are customers price-sensitive?")
                print(f"  3. Consider promotional strategies to recover volume")
            elif top_analyzer == "historical":
                print(f"  1. Review incident reports from similar past weeks")
                print(f"  2. Apply lessons learned from previous recovery strategies")
        
        print("\n" + "="*80 + "\n")


def run_all_analyzers_and_aggregate(df, store, category, year, week,
                                    business_event_anomaly_score=0.91,
                                    kpi_correlation_strong=True):
    """
    Convenience function: run all 8 analyzers and aggregate into one report.
    
    Returns: InvestigationReport object
    """
    from investigation_engine.product_analyzer import analyze_product
    from investigation_engine.category_analyzer import analyze_category
    from investigation_engine.store_analyzer import analyze_store
    from investigation_engine.region_analyzer import analyze_region
    from investigation_engine.price_analyzer import analyze_price
    from investigation_engine.historical_analyzer import analyze_historical
    from investigation_engine.top_contributor_analyzer import analyze_top_contributor
    from investigation_engine.seasonality_analyzer import analyze_seasonality
    
    results = {
        "product": analyze_product(df, store, category, year, week),
        "category": analyze_category(df, store, category, year, week),
        "store": analyze_store(df, store, category, year, week),
        "region": analyze_region(df, store, category, year, week),
        "price": analyze_price(df, store, category, year, week),
        "historical": analyze_historical(df, store, category, year, week),
        "top_contributor": analyze_top_contributor(df, store, category, year, week),
        "seasonality": analyze_seasonality(df, store, category, year, week),
    }
    
    report = InvestigationReport(
        store=store,
        category=category,
        year=year,
        week=week,
        analyzer_results=results,
        business_event_anomaly_score=business_event_anomaly_score,
        kpi_correlation_strong=kpi_correlation_strong,
    )
    
    return report