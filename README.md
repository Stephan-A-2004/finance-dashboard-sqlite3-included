# Finance Dashboard

Asset viewer with GUI, yfinance integration and SQLite persistence.

## Features
- Fetch stock data from Yahoo Finance (yfinance)
- CSV import with intelligent column detection
- Query history with SQLite storage
- Type checked with mypy strict leaning configuration

## Run
py -m finance_dashboard

## Type check:

cd path_to_root_folder

py -m mypy finance_dashboard

## Test:

py -m pytest tests/