"""Schema catalog: a technology-neutral description of the PostgreSQL schema.

Produced by Stage 3, consumed by the ontology editor (drop-downs), the AI
assistant (context), validation (whitelist) and extraction (safe SQL).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from kg_pipeline.core.ontology_models import DataType

PG_TYPE_MAP: dict[str, DataType] = {
    "smallint": DataType.INTEGER, "integer": DataType.INTEGER, "bigint": DataType.INTEGER,
    "numeric": DataType.DECIMAL, "decimal": DataType.DECIMAL,
    "real": DataType.FLOAT, "double precision": DataType.FLOAT,
    "boolean": DataType.BOOLEAN,
    "date": DataType.DATE,
    "timestamp without time zone": DataType.DATETIME,
    "timestamp with time zone": DataType.DATETIME,
    "json": DataType.JSON, "jsonb": DataType.JSON,
    "text": DataType.STRING, "character varying": DataType.STRING,
    "character": DataType.STRING, "uuid": DataType.STRING,
}

# which ontology type may be read from which column type
COMPATIBLE: dict[DataType, set[DataType]] = {
    DataType.STRING: set(DataType),
    DataType.INTEGER: {DataType.INTEGER},
    DataType.FLOAT: {DataType.FLOAT, DataType.INTEGER, DataType.DECIMAL},
    DataType.DECIMAL: {DataType.DECIMAL, DataType.INTEGER},
    DataType.BOOLEAN: {DataType.BOOLEAN},
    DataType.DATE: {DataType.DATE, DataType.DATETIME},
    DataType.DATETIME: {DataType.DATETIME},
    DataType.JSON: {DataType.JSON},
}


class ColumnInfo(BaseModel):
    name: str
    pg_type: str
    nullable: bool = True
    source_header: str = ""                     # original CSV header ("Cust ID"), empty for database columns

    @property
    def data_type(self) -> DataType:
        return PG_TYPE_MAP.get(self.pg_type, DataType.STRING)


class ForeignKey(BaseModel):
    columns: list[str]
    ref_table: str
    ref_columns: list[str]


class TableInfo(BaseModel):
    name: str                                   # schema-qualified, e.g. public.customers
    columns: dict[str, ColumnInfo]
    primary_key: list[str] = []
    foreign_keys: list[ForeignKey] = []
    unique_constraints: list[list[str]] = []
    row_estimate: Optional[int] = None


class SchemaCatalog(BaseModel):
    tables: dict[str, TableInfo]
    source_name: str = ""
    extracted_at: str = ""

    def table(self, name: str) -> Optional[TableInfo]:
        return self.tables.get(name)

    def has_column(self, table: str, column: str) -> bool:
        t = self.tables.get(table)
        return bool(t and column in t.columns)

    def is_unique(self, table: str, columns: list[str]) -> bool:
        t = self.tables.get(table)
        if not t:
            return False
        if t.primary_key and sorted(columns) == sorted(t.primary_key):
            return True
        return any(sorted(columns) == sorted(u) for u in t.unique_constraints)

    def referenced_by(self, table: str) -> list[str]:
        return sorted({t.name for t in self.tables.values()
                       for fk in t.foreign_keys if fk.ref_table == table and t.name != table})
