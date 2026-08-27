import streamlit as st
import plotly.express as px
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from dashboard.data_access import get_analytics_data

st.set_page_config(page_title="DecisionLens — Analytics", page_icon="📈", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("DecisionLens")
    st.caption("Retail KPI Root Cause Investigation")
    st.divider()
    if st.button("🏠 Overview", use_container_width=True):
        st.switch_page("pages/1_Overview.py")
    if st.button("📋 Events", use_container_width=True):
        st.switch_page("pages/2_Events.py")
    if st.button("🔬 Investigation Detail", use_container_width=True):
        st.switch_page("pages/3_Investigation_Detail.py")
    if st.button("📈 Analytics", use_container_width=True, type="primary"):
        st.switch_page("pages/4_Analytics.py")
    if st.button("🧪 Try It Yourself", use_container_width=True):
        st.switch_page("pages/5_Try_It_Yourself.py")
    st.divider()

# ── Content ──────────────────────────────────────────────────────────────────
st.title("📈 Analytics")
st.caption("Cross-investigation insights across all 214 flagged anomalies")
st.divider()

data = get_analytics_data(source="superstore")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Analyzer by Frequency")
    st.caption("Which analyzer ranked #1 most often")
    analyzer_df = pd.DataFrame(data["top_analyzers"])
    if not analyzer_df.empty:
        fig = px.bar(
            analyzer_df, x="count", y="analyzer", orientation="h",
            color="count", color_continuous_scale="Purples",
            labels={"count": "Times Ranked #1", "analyzer": "Analyzer"},
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0, r=0, t=10, b=0), height=320)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Priority Breakdown")
    st.caption("Distribution of recommendation priorities")
    priority_df = pd.DataFrame(data["priority_breakdown"])
    if not priority_df.empty:
        fig = px.pie(
            priority_df, names="priority", values="count",
            color="priority",
            color_discrete_map={
                "immediate": "#e74c3c", "short-term": "#f39c12",
                "monitor": "#2ecc71", "none": "#95a5a6",
            },
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Confidence Score Distribution")
st.caption("How confident the system is across all 214 investigations")
scores = data["confidence_scores"]
if scores:
    fig = px.histogram(
        x=scores, nbins=20,
        labels={"x": "Confidence Score"},
        color_discrete_sequence=["#7c3aed"],
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, bargap=0.1)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("Store Rollup")
    store_df = pd.DataFrame(data["store_rollup"])
    if not store_df.empty:
        store_df["avg_confidence"] = store_df["avg_confidence"].apply(lambda x: f"{x:.1%}")
        store_df.columns = ["Store", "Investigations", "Avg Confidence"]
        st.dataframe(store_df, use_container_width=True, hide_index=True)

with col4:
    st.subheader("Category Rollup")
    cat_df = pd.DataFrame(data["category_rollup"])
    if not cat_df.empty:
        cat_df["avg_confidence"] = cat_df["avg_confidence"].apply(lambda x: f"{x:.1%}")
        cat_df.columns = ["Category", "Investigations", "Avg Confidence"]
        st.dataframe(cat_df, use_container_width=True, hide_index=True)