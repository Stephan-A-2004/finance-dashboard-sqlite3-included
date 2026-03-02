"""yfinance data fetching."""

from typing import Any, Optional

import yfinance as yf

from finance_dashboard.models import AssetStats


def _safe_get(d: dict, key: str) -> Optional[Any]:
    try:
        return d.get(key)
    except Exception:
        return None


def fetch_asset_stats(tickers: list[str]) -> list[AssetStats]:
    out: list[AssetStats] = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            hist = tk.history(period="5d", auto_adjust=False)
            if hist is None or hist.empty:
                raise ValueError("No price data found (invalid ticker or no data available).")

            last_close: Optional[float] = None
            prev_close: Optional[float] = None
            last_adj: Optional[float] = None
            last_volume: Optional[int] = None

            if hist is not None and not hist.empty:
                closes = hist["Close"].dropna()
                if len(closes) >= 1:
                    last_close = float(closes.iloc[-1])
                if len(closes) >= 2:
                    prev_close = float(closes.iloc[-2])

                if "Adj Close" in hist.columns:
                    adj = hist["Adj Close"].dropna()
                    if len(adj) >= 1:
                        last_adj = float(adj.iloc[-1])

                if "Volume" in hist.columns:
                    vol = hist["Volume"].dropna()
                    if len(vol) >= 1:
                        last_volume = int(vol.iloc[-1])

            pct_change_1d: Optional[float] = None
            if last_close is not None and prev_close is not None and prev_close != 0:
                pct_change_1d = (last_close - prev_close) / prev_close * 100.0

            try:
                fast = getattr(tk, "fast_info", {}) or {}
            except Exception:
                fast = {}

            try:
                info = tk.info or {}
            except Exception:
                info = {}

            market_cap = _safe_get(fast, "market_cap") or _safe_get(info, "marketCap")
            currency = _safe_get(fast, "currency") or _safe_get(info, "currency")
            exchange = _safe_get(fast, "exchange") or _safe_get(info, "exchange")
            trailing_pe = _safe_get(info, "trailingPE")
            forward_pe = _safe_get(info, "forwardPE")
            dividend_yield = _safe_get(info, "dividendYield")
            short_name = _safe_get(info, "shortName") or _safe_get(info, "longName")

            row = {
                "Ticker": t,
                "Name": short_name,
                "Close": last_close,
                "Adj Close": last_adj,
                "1D %": pct_change_1d,
                "Volume": last_volume,
                "Market Cap": market_cap,
                "Trailing P/E": trailing_pe,
                "Forward P/E": forward_pe,
                "Dividend Yield": dividend_yield,
                "Currency": currency,
                "Exchange": exchange,
            }
            out.append(AssetStats(ticker=t, row=row))
        except Exception as e:
            out.append(
                AssetStats(
                    ticker=t,
                    row={
                        "Ticker": t,
                        "Name": None,
                        "Close": None,
                        "Adj Close": None,
                        "1D %": None,
                        "Volume": None,
                        "Market Cap": None,
                        "Trailing P/E": None,
                        "Forward P/E": None,
                        "Dividend Yield": None,
                        "Currency": None,
                        "Exchange": None,
                        "Error": str(e),
                    },
                )
            )
    return out