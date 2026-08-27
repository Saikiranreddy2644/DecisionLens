# utils/constants.py

# Tier A: hard-required — pipeline cannot run without these
HARD_REQUIRED_COLUMNS = ["Date", "Store", "Category", "Product", "Revenue", "Quantity"]

# Tier B: soft-required — pipeline runs, but specific features get disabled
SOFT_REQUIRED_COLUMNS = {
    "Cost": "Profit and Profit Margin KPIs will be unavailable.",
    "Region": "Region Analyzer will be skipped in the Investigation Engine.",
}

# Minimum number of distinct weeks needed for Historical/Seasonality analyzers
MIN_WEEKS_FOR_HISTORY = 4
MIN_WEEKS_FOR_SEASONALITY = 52  # roughly a year

# Anomaly Detection Engine — business filter thresholds
# A Store x Category group must clear BOTH to be checked for anomalies at all.
MIN_WEEKS_FOR_GROUP = MIN_WEEKS_FOR_HISTORY  # reuse the same 4-week bar used elsewhere
MIN_VOLUME_PERCENTILE = 10  # groups below the 10th percentile of avg weekly Revenue are skipped

# Anomaly Detection Engine — Isolation Forest
# Rough prior for what fraction of group-weeks are genuinely anomalous.
ANOMALY_CONTAMINATION = 0.05
ISOLATION_FOREST_RANDOM_STATE = 42

# Anomaly Detection Engine — correlation step
# Minimum number of anomalous groups sharing a Category (or Store) in the same
# week before it's treated as a correlated pattern rather than an isolated one.
MIN_CORRELATED_GROUPS = 2

# Investigation Engine — Tier-1 analyzer weights (frozen, from architecture doc)
ANALYZER_WEIGHTS = {
    "Product": 0.21,
    "Category": 0.18,
    "Store": 0.15,
    "Historical": 0.13,
    "Region": 0.11,
    "Price": 0.11,
    "Top Contributor": 0.08,
    "Seasonality": 0.03,
}

# Product Analyzer — uniqueness normalization: a product's revenue-share
# deviation (this week vs its own historical average) at or above this
# threshold is treated as maximally "unique" (uniqueness score = 1.0).
PRODUCT_UNIQUENESS_SATURATION = 0.5  # 50 percentage points of share deviation

# Shared across analyzers — magnitude normalization: a metric deviation at or
# beyond this many standard deviations from the group's own history is
# treated as maximal magnitude (magnitude score = 1.0).
MAGNITUDE_SATURATION_STD = 3.0
# Investigation Engine — Product Analyzer sufficiency guards
# A Store+Category+Week must clear both before the Product Analyzer trusts
# its own product-level breakdown enough to score it.
MIN_PRODUCT_TRANSACTIONS = 3   # transactions in the anomalous week itself
MIN_DISTINCT_PRODUCTS = 2      # need >=2 products to say anything is "concentrated"

# Category Analyzer — same idea as Product Analyzer, one level up: instead of
# products within a Store+Category, this looks at categories within a Store.
CATEGORY_UNIQUENESS_SATURATION = 0.5  # 50 percentage points of share deviation
MIN_CATEGORY_TRANSACTIONS = 3   # transactions for the store in the anomalous week
MIN_DISTINCT_CATEGORIES = 2     # need >=2 categories to say anything is "concentrated"

# Store Analyzer — same idea as Category Analyzer, one level up: instead of
# categories within a Store, this looks at stores within a Category.
STORE_UNIQUENESS_SATURATION = 0.5  # 50 percentage points of share deviation
MIN_STORE_TRANSACTIONS = 3   # transactions for this category, across all stores, this week
MIN_DISTINCT_STORES = 2      # need >=2 stores to say anything is "isolated"

# Store Analyzer — same idea as Category Analyzer, one level up: instead of
# categories within a Store, this looks at stores within a Category.
STORE_UNIQUENESS_SATURATION = 0.5  # 50 percentage points of share deviation
MIN_STORE_TRANSACTIONS = 3   # transactions for this category, across all stores, this week
MIN_DISTINCT_STORES = 2      # need >=2 stores to say anything is "isolated"

# Region Analyzer — same idea, one level up again: instead of stores within a
# Category, this looks at regions within a Category. Region is soft-required,
# so this analyzer must also handle the column being entirely absent.
REGION_UNIQUENESS_SATURATION = 0.5  # 50 percentage points of share deviation
MIN_REGION_TRANSACTIONS = 3   # transactions for this category, across all regions, this week
MIN_DISTINCT_REGIONS = 2      # need >=2 regions to say anything is "isolated"

# Region Analyzer — same idea, one level up again: instead of stores within a
# Category, this looks at regions within a Category. Region is soft-required,
# so this analyzer must also handle the column being entirely absent.
REGION_UNIQUENESS_SATURATION = 0.5  # 50 percentage points of share deviation
MIN_REGION_TRANSACTIONS = 3   # transactions for this category, across all regions, this week
MIN_DISTINCT_REGIONS = 2      # need >=2 regions to say anything is "isolated"

# Price Analyzer — different shape from the others: instead of comparing
# this group against peers, it checks whether unit price moved AND whether
# quantity responded in the opposite direction (elasticity signature), plus
# a direct Discount-column check if that column happens to exist.
MIN_PRICE_TRANSACTIONS = 3
PRICE_ELASTICITY_SATURATION_STD = MAGNITUDE_SATURATION_STD  # reuse same z-score saturation
PRICE_DISCOUNT_SATURATION = 0.10  # a 10-percentage-point avg discount shift saturates the signal

# Historical Analyzer — checks precedent, not just deviation size. A z-score
# beyond this threshold counts as "comparably extreme" when scanning history
# for similar past occurrences.
HISTORICAL_PRECEDENT_Z_THRESHOLD = 1.0
MIN_HISTORICAL_TRANSACTIONS = 3   # transactions this week

# Top Contributor Analyzer — ranks products by absolute impact (revenue/units
# lost or gained vs their own historical norm), not by share deviation like
# Product Analyzer. Distinct value: "which specific products should I act
# on", complementing Product Analyzer's "is this store+category's product
# mix behaving oddly overall".
MIN_CONTRIBUTOR_TRANSACTIONS = 3
MIN_DISTINCT_CONTRIBUTOR_PRODUCTS = 2
TOP_CONTRIBUTOR_N = 3  # how many top-impact products define "concentration"

# Seasonality Analyzer — requires full-year history minimum to find the
# seasonal pattern for this calendar week. Much stricter threshold than
# other analyzers since without prior years, the comparison makes no sense.
MIN_SEASONALITY_WEEKS = 52  # need roughly a year to establish a seasonal baseline
MIN_SEASONALITY_TRANSACTIONS = 3   # this specific week
SEASONALITY_CONSISTENCY_SATURATION = 0.3  # normalized std dev of prior years