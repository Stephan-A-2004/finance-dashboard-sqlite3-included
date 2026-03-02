"""Configuration constants."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "database" / "asset_queries_history.db"
DEFAULT_COLUMNS: list[str] = [
    "Ticker", "Name", "Close", "Adj Close", "1D %", "Volume",
    "Market Cap", "Trailing P/E", "Forward P/E", "Dividend Yield",
    "Currency", "Exchange", "Error",
]