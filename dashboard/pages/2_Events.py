import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from dashboard.data_access import get_events_table, get_stores, get_categories

st.set_page_config(page_title="DecisionLens — Events", page_icon="📋", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("DecisionLens")
    st.caption("Retail KPI Root Cause Investigation")
    st.divider()
    if st.button("🏠 Overview", use_container_width=True):
        st.switch_page("pages/1_Overview.py")
    if st.button("📋 Events", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Events.py")
    if st.button("🔬 Investigation Detail", use_container_width=True):
        st.switch_page("pages/3_Investigation_Detail.py")
    if st.button("📈 Analytics", use_container_width=True):
        st.switch_page("pages/4_Analytics.py")
    if st.button("🧪 Try It Yourself", use_container_width=True):
        st.switch_page("pages/5_Try_It_Yourself.py")
    st.divider()

    # Filters
    st.subheader("Filters")
    stores = get_stores(source="superstore")
    selected_stores = st.multiselect("Store", options=stores, default=[])
    categories = get_categories(source="superstore")
    selected_categories = st.multiselect("Category", options=categories, default=[])
    conf_range = st.slider("Confidence Score", 0.0, 1.0, (0.0, 1.0), 0.05, format="%.0%%")
    priorities = ["immediate", "short-term", "monitor", "none"]
    selected_priorities = st.multiselect("Priority", options=priorities, default=[])

PRIORITY_ICONS = {"immediate": "🔴", "short-term": "🟡", "monitor": "🟢", "none": "⚪"}

# ── Content ──────────────────────────────────────────────────────────────────
st.title("📋 Events")
st.caption("All flagged Store+Category+Week anomalies — click a row to view its full investigation report")
st.divider()

df = get_events_table(source="superstore")

# Apply filters
filtered = df.copy()
if selected_stores:
    filtered = filtered[filtered["store"].isin(selected_stores)]
if selected_categories:
    filtered = filtered[filtered["category"].isin(selected_categories)]
if selected_priorities:
    filtered = filtered[filtered["priority"].isin(selected_priorities)]
filtered = filtered[
    (filtered["confidence_score"] >= conf_range[0]) &
    (filtered["confidence_score"] <= conf_range[1])
]

st.markdown(f"**{len(filtered)} investigations** matching current filters")

# Format
display_df = filtered.copy()
display_df["confidence_score"] = display_df["confidence_score"].apply(lambda x: f"{x:.1%}")
display_df["priority"] = display_df["priority"].apply(
    lambda x: f"{PRIORITY_ICONS.get(x, '⚪')} {x.title()}"
)
display_df = display_df.rename(columns={
    "investigation_id": "ID", "store": "Store", "category": "Category",
    "period": "Week", "confidence_score": "Confidence",
    "evidence_coverage": "Coverage", "priority": "Priority",
})
display_df = display_df[["ID", "Store", "Category", "Week", "Confidence", "Coverage", "Priority"]]

st.caption("👆 Click any row — then click 'View Selected Investigation' to open its full report")

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

selected_rows = event.selection.rows
if selected_rows:
    selected_index = selected_rows[0]
    selected_id = int(display_df.iloc[selected_index]["ID"])
    selected_row = display_df.iloc[selected_index]

    st.success(
        f"Selected: **{selected_row['Store']}** / {selected_row['Category']} / "
        f"{selected_row['Week']} — Confidence: {selected_row['Confidence']}"
    )

    if st.button("🔬 View Full Investigation Report →", type="primary", use_container_width=True):
        st.session_state["selected_investigation_id"] = selected_id
        st.switch_page("pages/3_Investigation_Detail.py")