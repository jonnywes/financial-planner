from __future__ import annotations

from io import BytesIO, StringIO
from typing import Iterable, Optional

import pandas as pd


def _standardize_columns(columns: Iterable[str]) -> list[str]:
    return [str(c).strip().lower().replace("\ufeff", "") for c in columns]


def _find_first(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _coerce_numeric(series: pd.Series) -> pd.Series:
    # Handle parentheses for negatives and commas
    s = series.astype(str).str.replace(",", "", regex=False).str.replace("(", "-", regex=False).str.replace(")", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _infer_amount(df: pd.DataFrame) -> pd.Series:
    # Single amount column
    single_amount = _find_first(df, [
        "amount", "amt", "transaction amount", "value", "amount(usd)", "amount usd",
        "amount ($)", "total"
    ])
    if single_amount:
        return _coerce_numeric(df[single_amount])

    # Debit/Credit columns
    debit_col = _find_first(df, ["debit", "debits", "withdrawal", "outflow", "money out"])  # positive values in column
    credit_col = _find_first(df, ["credit", "credits", "deposit", "inflow", "money in"])   # positive values in column
    if debit_col or credit_col:
        debit = _coerce_numeric(df[debit_col]) if debit_col else 0
        credit = _coerce_numeric(df[credit_col]) if credit_col else 0
        # Convention: credits positive, debits negative
        return credit - debit

    raise ValueError("Could not infer amount columns. Expected 'amount' or 'debit'/'credit'.")


def _infer_description(df: pd.DataFrame) -> pd.Series:
    desc_col = _find_first(df, [
        "description", "memo", "details", "payee", "narrative", "merchant", "transaction description",
        "name"
    ])
    if not desc_col:
        # If there is no clear description, fallback to first non-date, non-amount column
        excluded = {"date"}
        for c in df.columns:
            if c not in excluded and not pd.api.types.is_datetime64_any_dtype(df[c]):
                return df[c].astype(str)
        raise ValueError("Could not infer description column.")
    return df[desc_col].astype(str)


def _infer_date(df: pd.DataFrame) -> pd.Series:
    date_col = _find_first(df, [
        "date", "transaction date", "posted date", "posting date", "date posted", "date_time",
        "value date"
    ])
    if not date_col:
        # Attempt to parse any column that looks like a date
        for c in df.columns:
            parsed = pd.to_datetime(df[c], errors="coerce", utc=False, dayfirst=False, infer_datetime_format=True)
            if parsed.notna().sum() >= max(1, int(len(df) * 0.5)):
                return parsed.dt.date
        raise ValueError("Could not infer date column.")
    parsed = pd.to_datetime(df[date_col], errors="coerce", utc=False, dayfirst=False, infer_datetime_format=True)
    return parsed.dt.date


def load_transactions_from_csv(file_like: BytesIO | StringIO) -> pd.DataFrame:
    """
    Parse a CSV file-like object into a standardized DataFrame with columns:
    - date: datetime.date
    - description: str
    - amount: float (credits positive, debits negative)
    """
    # Try common encodings
    last_error: Optional[Exception] = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            file_like.seek(0)
            df = pd.read_csv(file_like, encoding=encoding)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            df = None  # type: ignore
    if df is None:
        raise RuntimeError(f"Failed to read CSV: {last_error}")

    # Standardize column names
    df.columns = _standardize_columns(df.columns)

    # Infer fields
    date_series = _infer_date(df)
    description_series = _infer_description(df)
    amount_series = _infer_amount(df)

    normalized = pd.DataFrame({
        "date": pd.to_datetime(date_series, errors="coerce").dt.date,
        "description": description_series.fillna("").astype(str).str.strip(),
        "amount": pd.to_numeric(amount_series, errors="coerce"),
    })

    # Drop rows missing critical fields
    normalized = normalized.dropna(subset=["date", "amount"]).reset_index(drop=True)

    # Sort by date
    normalized = normalized.sort_values("date").reset_index(drop=True)

    return normalized