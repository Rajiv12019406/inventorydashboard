"""Replaceable inventory data provider abstraction.

Future SQL Server integration:
    Implement SqlServerInventoryDataProvider with the same InventoryDataProvider
    interface. Map hospital tables into the normalized InventorySnapshot models
    in app.data.models. Do not change forecasting or API schemas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings
from app.data.models import InventorySnapshot


class InventoryDataProvider(ABC):
    """Contract for loading normalized inventory data."""

    @abstractmethod
    def load_snapshot(self) -> InventorySnapshot:
        """Return a complete normalized inventory snapshot."""

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""


class SqlServerInventoryDataProvider(InventoryDataProvider):
    """Placeholder adapter contract for a future SQL Server integration.

    Implementation notes (not active in this phase):
    - Read connection settings from environment / secrets manager
    - Query items, stores, balances, consumption, batches, incoming POs
    - Map rows into InventorySnapshot domain models
    - Never expose raw SQL result shapes to the API layer
    """

    def provider_name(self) -> str:
        return "SQL Server"

    def load_snapshot(self) -> InventorySnapshot:
        raise NotImplementedError(
            "SqlServerInventoryDataProvider is not implemented in the synthetic-data phase. "
            "Configure DATA_PROVIDER=synthetic."
        )


@lru_cache
def get_data_provider() -> InventoryDataProvider:
    provider = settings.data_provider.lower().strip()
    if provider == "synthetic":
        from app.data.synthetic_provider import SyntheticInventoryDataProvider

        return SyntheticInventoryDataProvider(seed=settings.synthetic_seed)
    if provider in {"sqlserver", "sql_server", "mssql"}:
        return SqlServerInventoryDataProvider()
    raise ValueError(f"Unknown data provider: {provider}")