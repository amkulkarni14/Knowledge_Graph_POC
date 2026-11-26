from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr

from backend.app.dto.models import StrictModel, Text
from kg_pipeline.core.schema_models import ColumnInfo


Connector = Literal["sample", "csv", "postgres", "mssql", "oracle", "s3",
                    "azure_blob", "azure_adls", "gcs", "bigquery"]


class ConnectorSpec(StrictModel):
    required: list[str]
    optional: list[str] = Field(default_factory=list)
    authentication: dict[str, list[str]]
    location: str | None = None
    formats: list[str] = Field(default_factory=list)


class ConnectionRequest(StrictModel):
    source: Connector
    name: Text
    configuration: dict[str, SecretStr] = Field(default_factory=dict, max_length=30)


class ConnectionView(StrictModel):
    id: UUID
    source: Connector
    name: str
    connected_at: str
    duration_ms: int
    database: str | None = None
    endpoint: str | None = None
    authentication: str | None = None
    read_only: bool | None = None
    asset_count: int = 0


class AssetView(StrictModel):
    id: str
    name: str
    kind: str
    columns: int
    size_bytes: int | None = None
    relationship_origin: str


class SelectionRequest(StrictModel):
    assets: list[str] = Field(min_length=1, max_length=200)


class PreviewRequest(StrictModel):
    asset: str = Field(min_length=1, max_length=512)
    columns: list[str] | None = Field(default=None, max_length=200)
    limit: int = Field(default=10, ge=1, le=25)


class PreviewView(StrictModel):
    columns: list[ColumnInfo]
    rows: list[dict]
