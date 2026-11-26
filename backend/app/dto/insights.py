"""Request and response contracts for workspace-scoped aggregate analytics."""
from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from backend.app.dto.models import BuildId, GraphView, Identifier, StrictModel, Text


class InsightsFilters(StrictModel):
    table: str | None = Field(default=None, max_length=300)
    dimension: Text | None = None
    category: Text | None = None
    measure: Text | None = None
    date_field: Text | None = None
    start: date | None = None
    end: date | None = None
    minimum: float | None = Field(default=None, allow_inf_nan=False)
    maximum: float | None = Field(default=None, allow_inf_nan=False)
    interval: Literal["day", "week", "month", "quarter", "year"] = "month"
    entity_type: Text | None = None
    ontology_id: Identifier | None = None
    build_id: BuildId | None = None
    refresh: bool = False

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("The start date must precede the end date")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("The minimum must not exceed the maximum")
        if (self.ontology_id is None) != (self.build_id is None):
            raise ValueError("Select a specific workspace snapshot")
        return self


class InsightsField(StrictModel):
    name: str
    role: Literal["measure", "date", "category"]
    semantic: str


class InsightsMetric(StrictModel):
    label: str
    value: int | float | None
    definition: str
    unit: str | None = None


class InsightsBucket(StrictModel):
    label: str
    records: int
    total: float | None = None


class InsightsFinding(StrictModel):
    title: str
    explanation: str
    metric: str
    target: Literal["distribution", "trends", "quality", "network"]


class InsightsGraph(StrictModel):
    metrics: list[InsightsMetric]
    entity_types: list[str]
    entities: list[InsightsBucket]
    relationships: list[InsightsBucket]
    communities: list[InsightsBucket]
    topology: GraphView
    dependencies: list[InsightsBucket]
    most_connected: list[InsightsBucket]


class InsightsQuality(StrictModel):
    dataset: str
    issue: str
    count: int
    severity: str


class InsightsResponse(StrictModel):
    refreshed_at: datetime
    source: str | None
    tables: list[str]
    table: str | None
    fields: list[InsightsField]
    scanned: int
    row_limit: int
    truncated: bool
    dimension: str | None
    measure: str | None
    date_field: str | None
    metrics: list[InsightsMetric]
    distribution: list[InsightsBucket]
    trends: list[InsightsBucket]
    quality: list[InsightsQuality]
    graph: InsightsGraph | None
    findings: list[InsightsFinding]
