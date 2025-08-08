from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Transaction(id={self.id}, date={self.date}, amount={self.amount}, category={self.category}, description={self.description[:32]!r}...)"