"""Tests for ticker parsing."""

from finance_dashboard.parsing import parse_manual_input, parse_csv_file


def test_basic_parsing() -> None:
    assert parse_manual_input("AAPL, MSFT") == ["AAPL", "MSFT"]


def test_deduplication() -> None:
    assert parse_manual_input("AAPL, MSFT, AAPL") == ["AAPL", "MSFT"]


def test_invalid_tickers_filtered() -> None:
    assert parse_manual_input("AAPL, not-a-ticker, MSFT") == ["AAPL", "MSFT"]


def test_whitespace_handling() -> None:
    assert parse_manual_input("  AAPL  ,  MSFT  ") == ["AAPL", "MSFT"]


def test_empty_input() -> None:
    assert parse_manual_input("") == []