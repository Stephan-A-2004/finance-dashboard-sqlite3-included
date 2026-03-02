"""Ticker parsing from manual input and CSV files."""

import re

import pandas as pd


def _normalise(t: str) -> str:
    return t.strip().upper()


def _looks_like_ticker(s: str) -> bool:
    s = s.strip().upper()
    return bool(re.match(r'^[A-Z0-9^=]{1,10}([.\-][A-Z0-9]{1,10})?$', s))


def parse_manual_input(text: str) -> list[str]:
    parts = [p.strip() for p in text.replace("\n", ",").split(",")]
    tickers = [_normalise(p) for p in parts if p.strip() and _looks_like_ticker(p)]
    seen: set[str] = set()
    out: list[str] = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_csv_file(path: str) -> list[str]:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("CSV file is empty.")

    used_fallback = False
    candidates = ["ticker", "symbol", "symbols", "tickers", "asset", "assets"]
    col = None
    lower_cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_cols:
            col = lower_cols[cand]
            break

    if col is None:
        col = df.columns[0]
        used_fallback = True

    tickers: list[str] = []
    for val in df[col].dropna().astype(str).tolist():
        tickers.extend(parse_manual_input(val))

    seen: set[str] = set()
    out: list[str] = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)

    if not out and used_fallback:
        raise ValueError(
            f"No ticker-like values found.\n"
            f"No known ticker column name detected.\n"
            f"Columns in file: {list(df.columns)}\n"
            f"Try naming the ticker column: ticker or symbol."
        )

    return out