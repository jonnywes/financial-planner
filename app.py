import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI Financial Planner", layout="wide")

st.title("AI Financial Planner")
st.caption("Iteration 4 — SQLite persistence with SQLAlchemy.")

# Lazy imports for app sections
from src.storage import initialize as init_storage, dataframe_to_transactions, fetch_all_transactions, upsert_transactions
from src.db import get_session

# Initialize DB once per app startup
@st.cache_resource
def _init_db_once():
    init_storage()
    return True

_init_db_once()

# Tabs
TAB_DASHBOARD, TAB_UPLOAD, TAB_AI = st.tabs(["Dashboard", "Data Upload", "AI Advice"]) 

with TAB_DASHBOARD:
    st.header("Dashboard")
    st.info("Visualization and insights will appear here in later iterations (5).")

with TAB_UPLOAD:
    st.header("Data Upload")
    st.subheader("Upload CSV and/or PDF statements and save to database")

    uploaded_csv = st.file_uploader("Upload a CSV file with transactions", type=["csv"], key="csv_uploader")
    uploaded_pdf = st.file_uploader("Upload a PDF bank statement", type=["pdf"], key="pdf_uploader")

    combined_frames = []

    if uploaded_csv is not None:
        from src.ingestion import load_transactions_from_csv
        try:
            df_csv: pd.DataFrame = load_transactions_from_csv(uploaded_csv)
            st.success(f"CSV: parsed {len(df_csv)} transactions.")
            combined_frames.append(df_csv)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to parse CSV: {exc}")

    if uploaded_pdf is not None:
        from src.ingestion import load_transactions_from_pdf
        try:
            df_pdf: pd.DataFrame = load_transactions_from_pdf(uploaded_pdf)
            st.success(f"PDF: parsed {len(df_pdf)} transactions.")
            combined_frames.append(df_pdf)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to parse PDF: {exc}")

    if combined_frames:
        df_all = pd.concat(combined_frames, ignore_index=True)
        df_all = df_all.drop_duplicates(subset=["date", "description", "amount"]).sort_values("date").reset_index(drop=True)
        st.subheader("Preview Parsed Transactions")
        st.dataframe(df_all, use_container_width=True)

        if st.button("Save to Database", type="primary"):
            with get_session() as session:
                records = dataframe_to_transactions(df_all)
                inserted = upsert_transactions(session, records)
            st.success(f"Saved {inserted} new transactions to the database.")
    else:
        st.info("Upload CSV and/or PDF to preview parsed transactions.")

    st.divider()
    st.subheader("Stored Transactions")
    with get_session() as session:
        df_persisted = fetch_all_transactions(session)
    st.dataframe(df_persisted, use_container_width=True)

with TAB_AI:
    st.header("AI Advice")
    st.info("AI-driven financial recommendations will be added in iteration 6.")