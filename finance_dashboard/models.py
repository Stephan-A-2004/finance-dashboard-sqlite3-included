"""Data models and type definitions."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AssetStats:
    ticker: str
    row: dict[str, Any]