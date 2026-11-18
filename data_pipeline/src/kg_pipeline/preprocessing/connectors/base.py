"""The read-only interface every data source implements."""
from __future__ import annotations

from typing import Any, Iterator, Optional, Protocol

from kg_pipeline.core.schema_models import SchemaCatalog


class DataSource(Protocol):
    name: str

    def introspect_schema(self) -> SchemaCatalog: ...

    def iter_batches(self, table: str, columns: list[str], key_columns: list[str],
                     batch_size: int = 5000, since: Any = None,
                     watermark_column: Optional[str] = None,
                     start_after: Optional[tuple] = None) -> Iterator[list[dict]]: ...

    def count(self, table: str) -> int: ...

    def sample_rows(self, table: str, limit: int = 5) -> list[dict]: ...

    def close(self) -> None: ...
