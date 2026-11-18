"""In-memory source with the same interface as PostgresSource (demo and tests)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.preprocessing.connectors import sample_data


def _sortable(values) -> tuple:
    """Sort key where NULL sorts last and is never compared with a real value (keys may contain NULL)."""
    return tuple((v is None, 0 if v is None else v) for v in values)


class SampleSource:
    def __init__(self, catalog: Optional[SchemaCatalog] = None, rows: Optional[dict[str, list[dict]]] = None):
        self.catalog = catalog or sample_data.build_catalog()
        self.rows = rows if rows is not None else sample_data.build_rows()
        self.name = self.catalog.source_name or "sample://retail"
        for t, info in self.catalog.tables.items():
            info.row_estimate = len(self.rows.get(t, []))

    def ping(self) -> dict:
        return {"server_version": "in-memory sample (no database)", "user": "demo", "read_only": True}

    def introspect_schema(self) -> SchemaCatalog:
        cat = self.catalog.model_copy(deep=True)
        cat.extracted_at = datetime.now(timezone.utc).isoformat()
        return cat

    def iter_batches(self, table: str, columns: list[str], key_columns: list[str],
                     batch_size: int = 5000, since: Any = None,
                     watermark_column: Optional[str] = None,
                     start_after: Optional[tuple] = None) -> Iterator[list[dict]]:
        if table not in self.catalog.tables:
            raise ValueError(f"unknown table {table}")
        unknown = [c for c in list(columns) + list(key_columns) if c not in self.catalog.tables[table].columns]
        if unknown:
            raise ValueError(f"unknown columns {unknown} in {table}")

        def key(r):
            return tuple(r[k] for k in key_columns)

        data = sorted(self.rows.get(table, []), key=lambda r: _sortable(key(r)))
        if since is not None and watermark_column:
            data = [r for r in data if r.get(watermark_column) is not None and r[watermark_column] >= since]
        if start_after is not None:
            data = [r for r in data if _sortable(key(r)) > _sortable(tuple(start_after))]
        wanted = list(dict.fromkeys(list(key_columns) + list(columns)))
        for i in range(0, len(data), batch_size):
            yield [{c: r.get(c) for c in wanted} for r in data[i:i + batch_size]]

    def count(self, table: str) -> int:
        return len(self.rows.get(table, []))

    def sample_rows(self, table: str, limit: int = 5) -> list[dict]:
        return [dict(r) for r in self.rows.get(table, [])[:limit]]

    def close(self) -> None:
        pass
