"""Normalized domain models shared by all data providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


DemandPattern = Literal[
    "stable",
    "increasing",
    "decreasing",
    "weekly_seasonal",
    "spike",
    "intermittent",
    "zero_periods",
]


@dataclass(frozen=True)
class Store:
    store_id: str
    name: str
    location: str


@dataclass(frozen=True)
class Category:
    category_id: str
    name: str


@dataclass(frozen=True)
class InventoryItem:
    item_id: str
    item_code: str
    name: str
    category_id: str
    unit: str
    min_stock: float
    safety_stock: float
    supplier_lead_time_days: int
    demand_pattern: DemandPattern


@dataclass(frozen=True)
class StockBalance:
    item_id: str
    store_id: str
    usable_qty: float
    as_of_date: date


@dataclass(frozen=True)
class ConsumptionRecord:
    item_id: str
    store_id: str
    date: date
    quantity: float
    is_missing: bool = False


@dataclass(frozen=True)
class BatchLot:
    batch_id: str
    item_id: str
    store_id: str
    available_qty: float
    expiry_date: date
    received_date: date


@dataclass(frozen=True)
class IncomingReceipt:
    receipt_id: str
    item_id: str
    store_id: str
    expected_qty: float
    expected_date: date


@dataclass
class DatasetMetadata:
    provider_name: str
    generated_at: datetime
    history_start: date
    history_end: date
    item_count: int
    store_count: int
    category_count: int
    missing_observation_count: int
    insufficient_history_item_count: int
    seed: int
    assumptions: list[str] = field(default_factory=list)


@dataclass
class InventorySnapshot:
    """Complete normalized inventory dataset returned by a provider."""

    stores: list[Store]
    categories: list[Category]
    items: list[InventoryItem]
    balances: list[StockBalance]
    consumption: list[ConsumptionRecord]
    batches: list[BatchLot]
    incoming: list[IncomingReceipt]
    metadata: DatasetMetadata