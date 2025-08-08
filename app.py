import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI Financial Planner", layout="wide")

st.title("AI Financial Planner")
st.caption("Iteration 2 — CSV ingestion and preview.")

# Tabs
TAB_DASHBOARD, TAB_UPLOAD, TAB_AI = st.tabs(["Dashboard", "Data Upload", "AI Advice"]) 

with TAB_DASHBOARD:
    st.header("Dashboard")
    st.info("Visualization and insights will appear here in later iterations (5).")

with TAB_UPLOAD:
    st.header("Data Upload")
    st.subheader("Upload CSV")

    uploaded_csv = st.file_uploader("Upload a CSV file with transactions", type=["csv"], key="csv_uploader")

    if uploaded_csv is not None:
        from src.ingestion import load_transactions_from_csv
        try:
            df: pd.DataFrame = load_transactions_from_csv(uploaded_csv)
            st.success(f"Parsed {len(df)} transactions.")
            st.dataframe(df, use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to parse CSV: {exc}")
    else:
        st.info("Select a CSV to preview parsed transactions.")

    st.divider()
    st.subheader("Coming soon")
    st.info("PDF ingestion via Camelot/Tabula in iteration 3.")

with TAB_AI:
    st.header("AI Advice")
    st.info("AI-driven financial recommendations will be added in iteration 6.")