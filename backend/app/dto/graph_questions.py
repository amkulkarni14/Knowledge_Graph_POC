from typing import Literal

from pydantic import Field

from backend.app.dto.models import BuildId, GraphView, Identifier, StrictModel


class GraphQuestionRequest(StrictModel):
    question: str = Field(min_length=1, max_length=600)
    previous_question: str | None = Field(default=None, max_length=600)
    ontology_id: Identifier | None = None
    build_id: BuildId | None = None


class GraphQueryPlan(StrictModel):
    operation: Literal["entities", "relationships", "count_entities", "count_relationships", "path", "insights", "clarify"]
    label: str | None = Field(default=None, max_length=100)
    relationship: str | None = Field(default=None, max_length=100)
    target_label: str | None = Field(default=None, max_length=100)
    property: str | None = Field(default=None, max_length=100)
    contains: str | None = Field(default=None, min_length=1, max_length=150)
    source_id: str | None = Field(default=None, max_length=180)
    target_id: str | None = Field(default=None, max_length=180)


class GraphAnswer(StrictModel):
    plan: GraphQueryPlan
    count: int
    explanation: str
    explanation_source: Literal["ai_evidence_selection", "calculated"]
    graph: GraphView
    rows: list[dict]
    followups: list[str]
    provider: Literal["groq", "ollama", "rules"] = "groq"
    notice: str | None = None
