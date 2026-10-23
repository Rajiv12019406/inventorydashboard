"""Synthetic inventory data provider with in-memory snapshot caching."""

from __future__ import annotations

from functools import lru_cache

from app.data.models import InventorySnapshot
from app.data.provider import InventoryDataProvider
from app.data.synthetic_generator import generate_synthetic_snapshot


class SyntheticInventoryDataProvider(InventoryDataProvider):
    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._snapshot: InventorySnapshot | None = None

    def provider_name(self) -> str:
        return "Synthetic Data"

    def load_snapshot(self) -> InventorySnapshot:
        if self._snapshot is None:
            self._snapshot = _cached_snapshot(self._seed)
        return self._snapshot


@lru_cache(maxsize=4)
def _cached_snapshot(seed: int) -> InventorySnapshot:
    return generate_synthetic_snapshot(seed=seed)