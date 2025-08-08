import streamlit as st

st.set_page_config(page_title="AI Financial Planner", layout="wide")

st.title("AI Financial Planner")
st.caption("Iteration 1 — Project setup. Placeholder sections below.")

# Basic navigation via tabs
TAB_DASHBOARD, TAB_UPLOAD, TAB_AI = st.tabs(["Dashboard", "Data Upload", "AI Advice"]) 

with TAB_DASHBOARD:
    st.header("Dashboard")
    st.info("Visualization and insights will appear here in later iterations (5).")

with TAB_UPLOAD:
    st.header("Data Upload")
    st.info("CSV/PDF upload and parsing will be implemented in iterations 2 and 3.")

with TAB_AI:
    st.header("AI Advice")
    st.info("AI-driven financial recommendations will be added in iteration 6.")