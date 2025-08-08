from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import os

import pandas as pd

# --------------------------
# Summaries
# --------------------------

def build_spending_summary(df: pd.DataFrame) -> str:
    if df.empty:
        return "No transactions available."

    df2 = df.copy()
    df2["date"] = pd.to_datetime(df2["date"])  # normalize

    total_income = float(df2.loc[df2["amount"] > 0, "amount"].sum())
    total_expense = float(df2.loc[df2["amount"] < 0, "amount"].sum())
    net = total_income + total_expense

    # Top categories by absolute spend
    if "category" not in df2.columns:
        df2["category"] = "Uncategorized"
    cat = df2[df2["amount"] < 0].groupby("category")["amount"].sum().abs().sort_values(ascending=False).head(7)

    # Recent monthly trend (last 6 months)
    df2["month"] = df2["date"].dt.to_period("M").dt.to_timestamp()
    trend = df2.groupby("month")["amount"].sum().tail(6)

    lines = [
        f"Total income: ${total_income:,.2f}",
        f"Total expense: ${abs(total_expense):,.2f}",
        f"Net: ${net:,.2f}",
        "",
        "Top spending categories:",
    ]
    for name, val in cat.items():
        lines.append(f"- {name}: ${float(val):,.2f}")

    lines.append("")
    lines.append("Monthly net spending (recent):")
    for idx, val in trend.items():
        lines.append(f"- {idx.strftime('%Y-%m')}: ${float(val):,.2f}")

    return "\n".join(lines)


# --------------------------
# Providers
# --------------------------

@dataclass
class OpenAISettings:
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    timeout_seconds: float = 30


@dataclass
class LlamaSettings:
    model_path: str = ""  # path to GGUF file
    temperature: float = 0.2
    max_tokens: int = 512


def generate_with_openai(prompt: str, settings: Optional[OpenAISettings] = None) -> str:
    settings = settings or OpenAISettings()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set.")
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openai package not installed.") from exc

    client = OpenAI(api_key=api_key)
    client = client.with_options(timeout=settings.timeout_seconds)

    response = client.chat.completions.create(
        model=settings.model,
        temperature=settings.temperature,
        messages=[
            {"role": "system", "content": "You are a concise, practical AI financial planner. Provide actionable budgeting, savings, and debt advice."},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise RuntimeError("No content returned from OpenAI.")
    return content.strip()


def generate_with_llama(prompt: str, settings: Optional[LlamaSettings] = None) -> str:
    settings = settings or LlamaSettings()
    try:
        from llama_cpp import Llama  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("llama-cpp-python not installed.") from exc
    if not settings.model_path:
        raise RuntimeError("No model_path provided for llama-cpp.")

    llm = Llama(model_path=settings.model_path, n_ctx=4096)
    result = llm(
        prompt=f"System: You are a concise, practical AI financial planner.\nUser: {prompt}\nAssistant:",
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        echo=False,
    )
    text = result.get("choices", [{}])[0].get("text")
    if not text:
        raise RuntimeError("No content returned from llama model.")
    return str(text).strip()


# --------------------------
# Public API
# --------------------------

def build_advice_prompt(df: pd.DataFrame, user_notes: str = "") -> str:
    summary = build_spending_summary(df)
    extra = ("\n\nUser notes:\n" + user_notes.strip()) if user_notes and user_notes.strip() else ""
    return (
        "Analyze the following spending summary and provide 5-8 concrete recommendations "
        "to improve budgeting, savings, and debt payoff. Include category-level insights and monthly trend considerations.\n\n"
        f"Summary:\n{summary}{extra}"
    )


def generate_advice(
    df: pd.DataFrame,
    provider: str = "none",
    user_notes: str = "",
    openai_settings: Optional[OpenAISettings] = None,
    llama_settings: Optional[LlamaSettings] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return (advice_text, error_message). Never raises; safe for UI use."""
    if df.empty:
        return None, "No transactions available for analysis."

    prompt = build_advice_prompt(df, user_notes=user_notes)

    try:
        if provider == "openai":
            return generate_with_openai(prompt, openai_settings), None
        elif provider == "llama":
            return generate_with_llama(prompt, llama_settings), None
        else:
            return None, "AI provider not selected."
    except Exception as exc:  # noqa: BLE001
        return None, f"AI generation failed: {exc}"