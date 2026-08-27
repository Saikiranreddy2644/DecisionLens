import streamlit as st
import plotly.express as px
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from dashboard.data_access import get_overview_stats

st.set_page_config(page_title="DecisionLens", page_icon="🔍", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("DecisionLens")
    st.caption("Retail KPI Root Cause Investigation")
    st.divider()
    if st.button("🏠 Overview", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Overview.py")
    if st.button("📋 Events", use_container_width=True):
        st.switch_page("pages/2_Events.py")
    if st.button("🔬 Investigation Detail", use_container_width=True):
        st.switch_page("pages/3_Investigation_Detail.py")
    if st.button("📈 Analytics", use_container_width=True):
        st.switch_page("pages/4_Analytics.py")
    if st.button("🧪 Try It Yourself", use_container_width=True):
        st.switch_page("pages/5_Try_It_Yourself.py")
    st.divider()
    st.caption("Phases 1–7 pipeline output")
    st.caption("Superstore dataset · 2014–2017")

# ── Content ──────────────────────────────────────────────────────────────────
st.title("🔍 DecisionLens — Business Overview")
st.caption("Pre-computed investigation results from the Superstore dataset (2014–2017)")
st.divider()

stats = get_overview_stats(source="superstore")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Investigations", stats["total_investigations"])
with col2:
    st.metric("Anomalous Weeks", stats["total_events"])
with col3:
    st.metric("Recommendations", stats["total_recommendations"])
with col4:
    st.metric("High Priority", stats["high_priority_count"])
    st.caption("🔴 Requires immediate action")
with col5:
    st.metric("Avg Confidence", f"{stats['avg_confidence']:.1%}")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Investigations by Store")
    store_df = pd.DataFrame(stats["store_breakdown"])
    if not store_df.empty:
        fig = px.bar(
            store_df, x="count", y="store", orientation="h",
            color="count", color_continuous_scale="Blues",
            labels={"count": "Investigations", "store": "Store"},
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0, r=0, t=10, b=0), height=400)
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Investigations by Category")
    cat_df = pd.DataFrame(stats["category_breakdown"])
    if not cat_df.empty:
        fig = px.pie(cat_df, names="category", values="count",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=400)
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.info("💡 Go to **Events** in the sidebar to explore individual investigations.")