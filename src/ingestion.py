from __future__ import annotations

from io import BytesIO, StringIO
from typing import Iterable, Optional, List
import tempfile
import os

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
            parsed = pd.to_datetime(df[c], errors="coerce", utc=False, dayfirst=False)
            if parsed.notna().sum() >= max(1, int(len(df) * 0.5)):
                return parsed.dt.date
        raise ValueError("Could not infer date column.")
    parsed = pd.to_datetime(df[date_col], errors="coerce", utc=False, dayfirst=False)
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


# --------------------------
# PDF ingestion
# --------------------------

def _normalize_extracted_table(raw_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Attempt to normalize a raw extracted PDF table to date/description/amount."""
    if raw_df is None or raw_df.empty:
        return None

    candidates: List[pd.DataFrame] = []

    # Strategy 1: assume current columns are headers
    df1 = raw_df.copy()
    df1.columns = _standardize_columns(df1.columns)
    candidates.append(df1)

    # Strategy 2: first row as header
    if len(raw_df) > 1:
        header = _standardize_columns(list(raw_df.iloc[0].astype(str)))
        df2 = raw_df.iloc[1:].copy()
        df2.columns = header
        candidates.append(df2)

    # Try each candidate
    for trial in candidates:
        try:
            date_series = _infer_date(trial)
            description_series = _infer_description(trial)
            amount_series = _infer_amount(trial)
            normalized = pd.DataFrame({
                "date": pd.to_datetime(date_series, errors="coerce").dt.date,
                "description": description_series.fillna("").astype(str).str.strip(),
                "amount": pd.to_numeric(amount_series, errors="coerce"),
            })
            normalized = normalized.dropna(subset=["date", "amount"]).reset_index(drop=True)
            if not normalized.empty:
                return normalized
        except Exception:
            continue
    return None


def _extract_with_camelot(pdf_path: str) -> List[pd.DataFrame]:
    try:
        import camelot  # type: ignore
    except Exception:
        return []
    frames: List[pd.DataFrame] = []
    try:
        for flavor in ("stream", "lattice"):
            try:
                tables = camelot.read_pdf(pdf_path, pages="all", flavor=flavor)
                for t in tables:
                    frames.append(t.df)
                if frames:
                    break
            except Exception:
                continue
    except Exception:
        return []
    return frames


def _extract_with_tabula(pdf_path: str) -> List[pd.DataFrame]:
    try:
        import tabula  # type: ignore
    except Exception:
        return []
    frames: List[pd.DataFrame] = []
    try:
        dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, lattice=True, stream=True)
        if isinstance(dfs, list):
            frames.extend(dfs)
    except Exception:
        try:
            dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
            if isinstance(dfs, list):
                frames.extend(dfs)
        except Exception:
            return []
    return frames


def load_transactions_from_pdf(file_like: BytesIO) -> pd.DataFrame:
    """
    Parse a PDF file-like object containing bank statement tables into a standardized DataFrame
    with columns [date, description, amount]. Tries Camelot first, then Tabula.
    """
    # Persist to temp file, as extractors expect a path
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_like.read())
        tmp_path = tmp.name

    try:
        extracted_frames: List[pd.DataFrame] = []
        # Try Camelot
        extracted_frames.extend(_extract_with_camelot(tmp_path))
        # Fallback to Tabula if nothing
        if not extracted_frames:
            extracted_frames.extend(_extract_with_tabula(tmp_path))

        normalized_frames: List[pd.DataFrame] = []
        for raw in extracted_frames:
            norm = _normalize_extracted_table(raw)
            if norm is not None and not norm.empty:
                normalized_frames.append(norm)

        if not normalized_frames:
            raise RuntimeError("No transaction-like tables found in PDF.")

        result = pd.concat(normalized_frames, ignore_index=True)
        # Deduplicate
        result = result.drop_duplicates(subset=["date", "description", "amount"]).reset_index(drop=True)
        # Sort
        result = result.sort_values("date").reset_index(drop=True)
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass