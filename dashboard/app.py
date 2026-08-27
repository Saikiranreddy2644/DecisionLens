import streamlit as st
import os
from database.db_manager import initialize_schema

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "decisionlens.db")

initialize_schema(DB_PATH)

st.set_page_config(
    page_title="DecisionLens",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.switch_page("pages/1_Overview.py")