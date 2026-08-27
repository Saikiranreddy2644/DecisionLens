# investigation_engine/report_narration.py
"""
Narration module — translates raw analyzer outputs into 
business-readable findings for the Investigation Report.
"""


def narrate_product_analysis(result):
    """Narrate Product Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    products = result.get("top_products", [])
    if not products:
        return "Product-level analysis inconclusive."
    
    top_product = products[0]
    hist_share = top_product.get("historical_avg_share", 0)
    this_share = top_product.get("this_week_share", 0)
    share_change = (hist_share - this_share) * 100
    
    product_name = top_product.get("product", "Unknown Product")
    
    return (
        f"Product mix shifted: {product_name} share fell {share_change:.1f} percentage points "
        f"(from {hist_share:.1%} to {this_share:.1%})."
    )


def narrate_category_analysis(result):
    """Narrate Category Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    cat_share = result.get("this_category_share_of_store", 0)
    hist_share = result.get("historical_avg_share_of_store", 0)
    share_change = (hist_share - cat_share) * 100
    category = result.get("category", "Category")
    
    return (
        f"{category} underperformed: share dropped {share_change:.1f} percentage points "
        f"(from {hist_share:.1%} to {cat_share:.1%})."
    )


def narrate_store_analysis(result):
    """Narrate Store Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    this_share = result.get("this_store_share", 0)
    hist_share = result.get("this_store_historical_avg_share", 0)
    share_change = (hist_share - this_share) * 100
    store = result.get("store", "Store")
    
    if abs(share_change) < 2:
        return f"Store performance in line with historical average (stable)."
    else:
        return (
            f"{store} is isolated: share fell {share_change:.1f} percentage points "
            f"while other stores remained stable. Store-specific issue."
        )


def narrate_region_analysis(result):
    """Narrate Region Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    region_share = result.get("this_region_share_of_category", 0)
    hist_share = result.get("historical_avg_share_of_category", 0)
    share_change = (hist_share - region_share) * 100
    
    if abs(share_change) < 5:
        return f"Region unaffected (stable)."
    else:
        return (
            f"Regional impact: region's share fell {share_change:.1f} percentage points. "
            f"Possible supply chain or logistics issue."
        )


def narrate_price_analysis(result):
    """Narrate Price Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    elasticity_signal = result.get("elasticity_signal", 0)
    
    if elasticity_signal < 0.1:
        return "Price is NOT the driver (no elasticity signal detected)."
    else:
        return (
            f"Price-driven decline detected. Unit price moved, "
            f"quantity responded inversely (elasticity: {elasticity_signal:.2f}). "
            f"Demand sensitivity issue."
        )


def narrate_historical_analysis(result):
    """Narrate Historical Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    precedent_count = result.get("precedent_count", 0)
    total_weeks = result.get("total_historical_weeks", 0)
    novelty = result.get("novelty", 0)
    
    if novelty > 0.8:
        return (
            f"UNPRECEDENTED: Only {precedent_count}/{total_weeks} prior weeks showed similar patterns. "
            f"This is a genuine anomaly."
        )
    elif novelty > 0.5:
        return (
            f"Some historical precedent: {precedent_count}/{total_weeks} prior weeks similar. "
            f"Pattern recognized but still significant."
        )
    else:
        return (
            f"Pattern has historical precedent ({precedent_count}/{total_weeks} prior weeks), "
            f"but current magnitude is still material."
        )


def narrate_top_contributor_analysis(result):
    """Narrate Top Contributor Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    contributors = result.get("top_contributors", [])
    if not contributors:
        return "No specific product drivers identified."
    
    top = contributors[0]
    product = top.get("product", "Unknown")
    contribution = top.get("contribution", 0)
    this_week_value = top.get("this_week_value", 0)
    hist_avg = top.get("historical_avg_weekly_value", 0)
    
    total_deviation = result.get("total_abs_deviation", 1)
    concentration = (abs(contribution) / total_deviation * 100) if total_deviation else 0
    
    return (
        f"{product} is the PRIMARY DRIVER: ₹{abs(contribution):.0f} impact "
        f"({concentration:.0f}% of total). "
        f"Fell from ₹{hist_avg:.0f} to ₹{this_week_value:.0f}."
    )


def narrate_seasonality_analysis(result):
    """Narrate Seasonality Analyzer findings."""
    if not result.get("sufficient_data", False):
        return None
    
    this_week = result.get("this_week_value", 0)
    seasonal_mean = result.get("seasonal_baseline_mean", 0)
    consistency = result.get("seasonal_consistency", 0)
    week = result.get("week", 0)
    
    pct_below = ((seasonal_mean - this_week) / seasonal_mean * 100) if seasonal_mean else 0
    
    if consistency > 0.7:
        return (
            f"Week {week} is normally predictable. "
            f"This {pct_below:.0f}% decline is ATYPICAL for this week."
        )
    else:
        return (
            f"Week {week} has high seasonal variance. "
            f"Current performance within normal range."
        )


def generate_narration_for_evidence(analyzer_name, result):
    """Route to appropriate narration function."""
    narrators = {
        "product": narrate_product_analysis,
        "category": narrate_category_analysis,
        "store": narrate_store_analysis,
        "region": narrate_region_analysis,
        "price": narrate_price_analysis,
        "historical": narrate_historical_analysis,
        "top_contributor": narrate_top_contributor_analysis,
        "seasonality": narrate_seasonality_analysis,
    }
    
    narrator = narrators.get(analyzer_name)
    if narrator:
        return narrator(result)
    return None