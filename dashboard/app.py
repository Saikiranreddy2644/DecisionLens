# dashboard/app.py
import streamlit as st

st.set_page_config(
    page_title="DecisionLens",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.switch_page("pages/1_Overview.py")