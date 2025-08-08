from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    _SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - sklearn optional
    _SKLEARN_AVAILABLE = False


@dataclass(frozen=True)
class Rule:
    category: str
    keywords: List[str]


_DEFAULT_RULES: List[Rule] = [
    Rule("Income", ["payroll", "salary", "paycheck", "direct deposit", "income"]),
    Rule("Rent", ["rent", "landlord"]),
    Rule("Utilities", ["utility", "electric", "water", "gas bill", "internet", "comcast", "verizon"]),
    Rule("Groceries", ["grocery", "supermarket", "whole foods", "trader joe", "market"]),
    Rule("Dining", ["restaurant", "dining", "eatery", "deli", "bbq", "bistro", "pizza", "burger"]),
    Rule("Coffee", ["coffee", "starbucks", "cafe"]),
    Rule("Transport", ["uber", "lyft", "transit", "metro", "bus", "train", "subway"]),
    Rule("Fuel", ["fuel", "gas station", "shell", "chevron", "bp "]),
    Rule("Shopping", ["amazon", "store", "retail", "shop", "purchase"]),
    Rule("Entertainment", ["movie", "cinema", "netflix", "spotify", "event", "concert"]),
    Rule("Travel", ["airlines", "hotel", "airbnb", "booking", "expedia", "travel"]),
    Rule("Health", ["pharmacy", "drug", "walgreens", "cvs", "doctor", "clinic"]),
    Rule("Transfer", ["transfer", "zelle", "venmo", "cash app", "paypal"]),
    Rule("Fees", ["fee", "charge", "interest"]),
]


def predict_category_rule_based(description: str, amount: float) -> str:
    text = (description or "").lower()
    if amount is not None and amount > 0:
        return "Income"
    for rule in _DEFAULT_RULES:
        if any(kw in text for kw in rule.keywords):
            return rule.category
    return "Uncategorized"


def apply_rule_based_categories(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "category" not in result.columns:
        result["category"] = None
    result["category"] = result.apply(
        lambda r: r.get("category") if pd.notna(r.get("category")) and r.get("category") else predict_category_rule_based(str(r.get("description", "")), float(r.get("amount", 0.0))),
        axis=1,
    )
    return result


def predict_with_ml_if_available(df_labeled: pd.DataFrame, df_unlabeled: pd.DataFrame) -> Optional[List[str]]:
    if not _SKLEARN_AVAILABLE:
        return None
    df_l = df_labeled.dropna(subset=["category"]) if "category" in df_labeled.columns else pd.DataFrame(columns=["description", "category"])  # type: ignore
    if df_l.empty:
        return None
    X_train = df_l["description"].astype(str).values
    y_train = df_l["category"].astype(str).values
    if len(set(y_train)) < 2:
        # Not enough classes to train
        return None
    pipeline: Pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("clf", MultinomialNB()),
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(df_unlabeled["description"].astype(str).values)
    return list(preds)


def apply_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Apply categories using ML if labeled data exists; otherwise fallback to rules."""
    df = df.copy()
    if df.empty:
        return df

    # Split labeled vs unlabeled
    has_category = ("category" in df.columns) & df["category"].notna() & df["category"].astype(str).str.len().gt(0)
    labeled = df[has_category].copy()
    unlabeled = df[~has_category].copy()

    if not unlabeled.empty and not labeled.empty:
        preds = predict_with_ml_if_available(labeled, unlabeled)
        if preds is not None:
            unlabeled.loc[:, "category"] = preds
            df = pd.concat([labeled, unlabeled], ignore_index=True)
            return df

    # Fallback to rule-based
    return apply_rule_based_categories(df)