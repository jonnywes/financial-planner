from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional, Set, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session, init_db
from .models import Transaction


def initialize() -> None:
    init_db()


def dataframe_to_transactions(df: pd.DataFrame) -> List[Transaction]:
    records: List[Transaction] = []
    for _, row in df.iterrows():
        d = row.get("date")
        if pd.isna(d):
            continue
        if isinstance(d, pd.Timestamp):
            d = d.date()
        desc = str(row.get("description", "")).strip()
        amt = row.get("amount")
        if pd.isna(amt):
            continue
        records.append(Transaction(date=d, description=desc, amount=float(amt), category=None))
    return records


def upsert_transactions(session: Session, records: Iterable[Transaction]) -> int:
    """Insert transactions while avoiding duplicates by (date, description, amount).
    Avoids duplicates both already in DB and within the given batch.
    """
    # Prefetch existing keys
    existing_keys: Set[Tuple] = set(
        session.execute(
            select(Transaction.date, Transaction.description, Transaction.amount)
        ).all()
    )

    inserted_count = 0
    batch_keys: Set[Tuple] = set()

    for rec in records:
        key = (rec.date, rec.description, rec.amount)
        if key in existing_keys or key in batch_keys:
            continue
        session.add(rec)
        batch_keys.add(key)
        inserted_count += 1

    session.commit()
    return inserted_count


def fetch_all_transactions(session: Session) -> pd.DataFrame:
    rows = session.execute(select(Transaction).order_by(Transaction.date.asc(), Transaction.id.asc())).scalars().all()
    if not rows:
        return pd.DataFrame(columns=["id", "date", "description", "category", "amount"])  # empty schema
    data = [
        {
            "id": r.id,
            "date": r.date,
            "description": r.description,
            "category": r.category,
            "amount": float(r.amount),
        }
        for r in rows
    ]
    return pd.DataFrame(data)