import streamlit as st
import plotly.express as px
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from dashboard.data_access import get_investigation_detail, get_events_table

try:
    from dashboard.data_access import get_investigation_detail, get_events_table
    st.write("DEBUG: imports OK")
except Exception as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(page_title="DecisionLens — Investigation", page_icon="🔬", layout="wide")

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
    if st.button("🔬 Investigation Detail", use_container_width=True, type="primary"):
        st.switch_page("pages/3_Investigation_Detail.py")
    if st.button("📈 Analytics", use_container_width=True):
        st.switch_page("pages/4_Analytics.py")
    if st.button("🧪 Try It Yourself", use_container_width=True):
        st.switch_page("pages/5_Try_It_Yourself.py")
    st.divider()

PRIORITY_COLOR = {"immediate": "🔴", "short-term": "🟡", "monitor": "🟢"}
CONFIDENCE_COLOR = {"high": "#2ecc71", "medium": "#f39c12", "low": "#e74c3c"}

def _confidence_label(score):
    if score >= 0.7:
        return "High", CONFIDENCE_COLOR["high"]
    elif score >= 0.4:
        return "Medium", CONFIDENCE_COLOR["medium"]
    else:
        return "Low", CONFIDENCE_COLOR["low"]

# ── Content ──────────────────────────────────────────────────────────────────
st.title("🔬 Investigation Detail")
st.divider()


# Drive navigation purely through session state
# Check both session state keys — _inv_id_override is set by Try It Yourself
# to survive the page switch reliably
if "_inv_id_override" in st.session_state:
    st.session_state["selected_investigation_id"] = st.session_state.pop("_inv_id_override")

if "selected_investigation_id" not in st.session_state:
    st.session_state["selected_investigation_id"] = 1

inv_id = int(st.session_state["selected_investigation_id"])

data = get_investigation_detail(inv_id)
st.write(f"DEBUG: Looking up inv_id={inv_id}, found={data is not None}")
if data:
    st.write(f"DEBUG: source={data['investigation']['source']}")

if data is None:
    st.error(f"Investigation #{inv_id} not found.")
    st.stop()

inv = data["investigation"]
evidence = data["evidence"]
recommendation = data["recommendation"]
summary = data["summary"]

st.divider()

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Store:** {inv['store_name']}")
    st.markdown(f"**Category:** {inv['category_name']}")
    st.markdown(f"**Week:** {inv['investigation_date']}")

conf_score = inv["confidence_score"]
conf_label, conf_color = _confidence_label(conf_score)

with col2:
    st.markdown("**Confidence Score:**")
    st.markdown(
        f"<h2 style='color:{conf_color}'>{conf_score:.1%} ({conf_label})</h2>",
        unsafe_allow_html=True
    )

with col3:
    st.markdown("**Evidence Coverage:**")
    st.markdown(f"<h2>{inv['evidence_coverage']}</h2>", unsafe_allow_html=True)

st.divider()

# ── Insufficient evidence case ────────────────────────────────────────────────
if recommendation is None and summary is None:
    st.warning(
        f"⚠️ **Insufficient Evidence** — All {inv['total_analyzers']} analyzers "
        "returned insufficient data (0/8 coverage). No recommendation was generated."
    )
    st.stop()

# ── Evidence breakdown ────────────────────────────────────────────────────────
st.subheader("📊 Evidence Breakdown")

ev_df = pd.DataFrame(evidence)
ev_df["sufficient"] = ev_df["sufficient_data"].apply(lambda x: "✓" if x else "✗")
ev_df["analyzer_score"] = ev_df["analyzer_score"].fillna(0.0)
ev_df = ev_df.sort_values("rank")

col_chart, col_table = st.columns([2, 1])

with col_chart:
    fig = px.bar(
        ev_df, x="analyzer_score", y="analyzer_name", orientation="h",
        color="analyzer_score",
        color_continuous_scale=["#e74c3c", "#f39c12", "#2ecc71"],
        range_color=[0, 1],
        labels={"analyzer_score": "Score", "analyzer_name": "Analyzer"},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False,
                      margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    display_ev = ev_df[["rank", "analyzer_name", "analyzer_score", "sufficient"]].copy()
    display_ev.columns = ["Rank", "Analyzer", "Score", "Data"]
    display_ev["Score"] = display_ev["Score"].apply(lambda x: f"{x:.3f}")
    st.dataframe(display_ev, use_container_width=True, hide_index=True)

st.divider()

# ── Recommendation ────────────────────────────────────────────────────────────
st.subheader("💡 Recommendation")

priority_icon = PRIORITY_COLOR.get(recommendation["priority"], "⚪")
st.markdown(
    f"""
    <div style='background:#1e1e2e;padding:20px;border-radius:10px;border-left:4px solid #7c3aed'>
    <p style='font-size:18px;margin:0'>{recommendation['action']}</p>
    <p style='margin:8px 0 0 0;color:#aaa'>
        {priority_icon} Priority: <b>{recommendation['priority'].title()}</b>
    </p>
    <p style='margin:8px 0 0 0;color:#aaa;font-size:13px'>{recommendation['rationale']}</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# ── AI Summary ────────────────────────────────────────────────────────────────
st.subheader("🤖 AI Business Summary")

if summary:
    st.info(summary["summary_text"])
    st.caption(f"Generated by: {summary['generated_by']}")
else:
    st.caption("No AI summary available for this investigation.")

st.divider()

# ── Navigation ────────────────────────────────────────────────────────────────
st.divider()
col_prev, col_next, col_jump = st.columns([1, 1, 2])

with col_prev:
    if st.button("← Previous", use_container_width=True, disabled=(inv_id <= 1)):
        st.session_state["selected_investigation_id"] = inv_id - 1
        st.rerun()

with col_next:
    if st.button("Next →", use_container_width=True):
        st.session_state["selected_investigation_id"] = inv_id + 1
        st.rerun()

with col_jump:
    jump_id = st.number_input(
        "Jump to ID", min_value=1, value=inv_id, step=1,
        key=f"jump_input_{inv_id}"  # key changes with inv_id so it resets cleanly
    )
    if jump_id != inv_id:
        st.session_state["selected_investigation_id"] = jump_id
        st.rerun()