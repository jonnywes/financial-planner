from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

import pandas as pd
import plotly.express as px


# --------------------------
# Data aggregation
# --------------------------

def spending_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "amount"])
    tmp = df.copy()
    # Consider only expenses (negative amounts)
    tmp = tmp[tmp["amount"] < 0]
    grouped = tmp.groupby("category", dropna=False)["amount"].sum().reset_index()
    grouped["amount"] = grouped["amount"].abs()  # show positive slice sizes
    grouped["category"] = grouped["category"].fillna("Uncategorized")
    return grouped.sort_values("amount", ascending=False)


def monthly_spending(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "spending"])  # empty
    tmp = df.copy()
    tmp["month"] = pd.to_datetime(tmp["date"]).dt.to_period("M").dt.to_timestamp()
    monthly = tmp.groupby("month")["amount"].sum().reset_index()
    monthly.rename(columns={"amount": "spending"}, inplace=True)
    return monthly.sort_values("month")


# --------------------------
# Plot builders
# --------------------------

def pie_spending_by_category(df: pd.DataFrame):
    agg = spending_by_category(df)
    if agg.empty:
        return None
    fig = px.pie(agg, names="category", values="amount", title="Spending by Category")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig


def line_monthly_trend(df: pd.DataFrame):
    monthly = monthly_spending(df)
    if monthly.empty:
        return None
    fig = px.line(monthly, x="month", y="spending", title="Monthly Net Spending")
    fig.update_layout(xaxis_title="Month", yaxis_title="Net Amount")
    return fig


# --------------------------
# Calculators
# --------------------------

@dataclass
class DebtPlan:
    months: int
    total_interest: float
    payoff_date: date


def debt_payoff_schedule(balance: float, apr_percent: float, monthly_payment: float, start_month: pd.Timestamp | None = None) -> DebtPlan:
    if monthly_payment <= 0 or balance <= 0:
        return DebtPlan(months=0, total_interest=0.0, payoff_date=date.today())
    apr = apr_percent / 100.0
    monthly_rate = apr / 12.0

    months = 0
    total_interest = 0.0
    remaining = float(balance)

    while remaining > 1e-6 and months < 1200:  # cap at 100 years
        interest = remaining * monthly_rate
        principal = monthly_payment - interest
        if principal <= 0:
            # Payment too small to cover interest
            break
        remaining -= principal
        total_interest += interest
        months += 1

    payoff_month = (start_month or pd.Timestamp.today()).to_period("M").to_timestamp() + pd.offsets.MonthBegin(months)
    return DebtPlan(months=months, total_interest=round(total_interest, 2), payoff_date=payoff_month.date())


@dataclass
class SavingsPlan:
    months: int
    goal_date: date


def savings_goal_months(current_savings: float, monthly_contribution: float, goal_amount: float, start_month: pd.Timestamp | None = None) -> SavingsPlan:
    if monthly_contribution <= 0 or goal_amount <= current_savings:
        return SavingsPlan(months=0, goal_date=date.today())
    remaining = goal_amount - current_savings
    months = int((remaining + monthly_contribution - 1) // monthly_contribution)  # ceil division
    goal_month = (start_month or pd.Timestamp.today()).to_period("M").to_timestamp() + pd.offsets.MonthBegin(months)
    return SavingsPlan(months=months, goal_date=goal_month.date())