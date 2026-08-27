# anomaly_detection/business_event.py

import pandas as pd


def _pattern_for_row(row) -> str:
    if row["is_category_correlated"] and row["is_store_correlated"]:
        return "both"
    if row["is_category_correlated"]:
        return "category_wide"
    if row["is_store_correlated"]:
        return "store_wide"
    return "isolated"


def build_business_events(tagged_df: pd.DataFrame) -> list:
    """
    Packages flagged, correlation-tagged anomalies into Business Events —
    the object the Investigation Engine consumes next.

    Grouping rule (documented simplification — see README-style note below):
      - category_wide / both -> one event per (Year, Week, Category),
        bundling every anomalous Store in that category that week
      - store_wide / both    -> one event per (Year, Week, Store),
        bundling every anomalous Category in that store that week
      - isolated              -> one event per anomalous row, standalone

    A row tagged "both" appears in BOTH its category-wide event and its
    store-wide event rather than one merged cross-dimension event. Properly
    merging (e.g. via connected-component clustering across shared
    Year/Week/Store/Category edges) is a real enhancement but adds real
    complexity for a pattern that should be rare in practice — documented
    here as a known limitation/future enhancement, same treatment the
    README already gives the removed Holiday/Event Analyzer.

    Returns a list of event dicts:
        {
            "event_id": int,
            "year": int, "week": int,
            "pattern": "category_wide" | "store_wide" | "isolated",
            "dimension": "Category" | "Store" | None,
            "dimension_value": <the shared Category or Store name>,
            "affected_groups": [(Store, Category), ...],
            "anomaly_rows": [<row dict>, ...],
        }
    """
    anomalies = tagged_df[tagged_df["is_anomaly"]].copy()
    anomalies["pattern"] = anomalies.apply(_pattern_for_row, axis=1)

    events = []
    event_id = 1

    # Category-wide events (includes "both" rows)
    cat_rows = anomalies[anomalies["pattern"].isin(["category_wide", "both"])]
    for (year, week, category), group in cat_rows.groupby(["Year", "Week", "Category"]):
        events.append({
            "event_id": event_id,
            "year": int(year),
            "week": int(week),
            "pattern": "category_wide",
            "dimension": "Category",
            "dimension_value": category,
            "affected_groups": list(zip(group["Store"], group["Category"])),
            "anomaly_rows": group.to_dict("records"),
        })
        event_id += 1

    # Store-wide events (includes "both" rows)
    store_rows = anomalies[anomalies["pattern"].isin(["store_wide", "both"])]
    for (year, week, store), group in store_rows.groupby(["Year", "Week", "Store"]):
        events.append({
            "event_id": event_id,
            "year": int(year),
            "week": int(week),
            "pattern": "store_wide",
            "dimension": "Store",
            "dimension_value": store,
            "affected_groups": list(zip(group["Store"], group["Category"])),
            "anomaly_rows": group.to_dict("records"),
        })
        event_id += 1

    # Isolated — one event per row
    isolated_rows = anomalies[anomalies["pattern"] == "isolated"]
    for _, row in isolated_rows.iterrows():
        events.append({
            "event_id": event_id,
            "year": int(row["Year"]),
            "week": int(row["Week"]),
            "pattern": "isolated",
            "dimension": None,
            "dimension_value": None,
            "affected_groups": [(row["Store"], row["Category"])],
            "anomaly_rows": [row.to_dict()],
        })
        event_id += 1

    return events


def print_business_event_summary(events: list):
    by_pattern = {}
    for e in events:
        by_pattern[e["pattern"]] = by_pattern.get(e["pattern"], 0) + 1

    print("\nBusiness Event Summary")
    print(f"  Total events: {len(events)}")
    for pattern, count in by_pattern.items():
        print(f"  {pattern}: {count}")
    print()

_PATTERN_LABELS = {
    "category_wide": "Category-wide",
    "store_wide": "Store-wide",
    "isolated": "Isolated",
}


def format_events_table(events: list) -> pd.DataFrame:
    """
    Turns the event dict list into a compact, human-readable table:
        Event ID | Type | Week | Affected

    "Affected" is phrased per pattern:
      - category_wide -> "<Category> in <N> stores"
      - store_wide     -> "<Store> across <N> categories"
      - isolated        -> "<Store> - <Category>"

    This is a DISPLAY view — event_id here is just a zero-padded label
    (E001, E002, ...) for readability, not a stable identifier; use the
    event dict's own "event_id" for anything programmatic.
    """
    rows = []
    for e in events:
        event_label = f"E{e['event_id']:03d}"
        week_label = f"{e['year']}-W{e['week']:02d}"

        if e["pattern"] == "category_wide":
            n_stores = len({store for store, _ in e["affected_groups"]})
            affected = f"{e['dimension_value']} in {n_stores} store{'s' if n_stores != 1 else ''}"
        elif e["pattern"] == "store_wide":
            n_categories = len({category for _, category in e["affected_groups"]})
            affected = f"{e['dimension_value']} across {n_categories} categor{'ies' if n_categories != 1 else 'y'}"
        else:  # isolated
            store, category = e["affected_groups"][0]
            affected = f"{store} - {category}"

        rows.append({
            "Event ID": event_label,
            "Type": _PATTERN_LABELS.get(e["pattern"], e["pattern"]),
            "Week": week_label,
            "Affected": affected,
        })

    return pd.DataFrame(rows)


def print_events_table(events: list, limit: int = None):
    """Console-friendly print of format_events_table(), optionally capped to the first `limit` rows."""
    df = format_events_table(events)
    if limit:
        df = df.head(limit)
    print(df.to_string(index=False))