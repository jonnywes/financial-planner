import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI Financial Planner", layout="wide")

st.title("AI Financial Planner")
st.caption("Iteration 5 — Categorization and dashboard visuals.")

# Lazy imports for app sections
from src.storage import initialize as init_storage, dataframe_to_transactions, fetch_all_transactions, upsert_transactions
from src.db import get_session
from src.categorization import apply_categories
from src.dashboard import pie_spending_by_category, line_monthly_trend, debt_payoff_schedule, savings_goal_months

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

    with get_session() as session:
        df_tx = fetch_all_transactions(session)

    if df_tx.empty:
        st.info("No transactions stored yet. Upload data in the Data Upload tab.")
    else:
        df_tx = apply_categories(df_tx)
        col1, col2 = st.columns(2)
        with col1:
            fig_pie = pie_spending_by_category(df_tx)
            if fig_pie is not None:
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Not enough expense data for category pie chart.")
        with col2:
            fig_line = line_monthly_trend(df_tx)
            if fig_line is not None:
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Not enough data for monthly trend chart.")

    st.divider()
    st.subheader("Debt Payoff Calculator")
    c1, c2, c3 = st.columns(3)
    with c1:
        debt_balance = st.number_input("Current debt balance", min_value=0.0, value=1000.0, step=50.0)
    with c2:
        debt_apr = st.number_input("APR %", min_value=0.0, value=18.0, step=0.1)
    with c3:
        debt_payment = st.number_input("Monthly payment", min_value=0.0, value=100.0, step=10.0)

    plan = debt_payoff_schedule(debt_balance, debt_apr, debt_payment)
    if plan.months == 0 and debt_balance > 0 and debt_payment <= 0:
        st.warning("Increase monthly payment to be greater than monthly interest.")
    st.write(f"Months to payoff: {plan.months}")
    st.write(f"Total interest paid: ${plan.total_interest:,.2f}")
    st.write(f"Estimated payoff date: {plan.payoff_date}")

    st.divider()
    st.subheader("Savings Goal Tracker")
    s1, s2, s3 = st.columns(3)
    with s1:
        current_savings = st.number_input("Current savings", min_value=0.0, value=500.0, step=50.0)
    with s2:
        monthly_contrib = st.number_input("Monthly contribution", min_value=0.0, value=250.0, step=25.0)
    with s3:
        savings_goal = st.number_input("Goal amount", min_value=0.0, value=5000.0, step=100.0)

    splan = savings_goal_months(current_savings, monthly_contrib, savings_goal)
    st.write(f"Months to reach goal: {splan.months}")
    st.write(f"Estimated goal date: {splan.goal_date}")

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