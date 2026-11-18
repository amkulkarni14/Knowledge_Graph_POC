"""HTTP contracts; workflow algorithms and domain models remain in kg_pipeline."""
from typing import Annotated, Any, Generic, Literal, TypeVar
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, model_validator
from kg_pipeline.core.ontology_models import (
    AttributeDef, ClassDef, ClassMapping, Ontology, RelationshipDef, RelationshipMapping)
from kg_pipeline.core.s01_scope import ScopeSheet

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")]
Column = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")]
Table = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}\.[A-Za-z_][A-Za-z0-9_]{0,62}$")]
BuildId = Annotated[str, StringConstraints(pattern=r"^[0-9]{8}T[0-9]{12}Z$")]
T = TypeVar("T")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Result(BaseModel, Generic[T]):
    data: T


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class SessionCreate(StrictModel):
    name: Text


class SessionView(BaseModel):
    id: UUID
    name: str
    completed_stages: list[int]
    source_version: int
    job: dict[str, Any] | None
    expires_in_seconds: int


class ScopeRequest(StrictModel):
    project: Text
    business_questions: list[Text] = Field(min_length=1, max_length=100)
    tables_in_scope: list[Table] = Field(default_factory=list, max_length=200)
    sensitive_columns: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=1000)
    users: list[Text] = Field(default_factory=list, max_length=100)
    later_list: list[Text] = Field(default_factory=list, max_length=100)

    def domain(self):
        return ScopeSheet(**self.model_dump())


class PostgresRequest(StrictModel):
    host: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._:-]{1,253}$")]
    port: int = Field(default=5432, ge=1, le=65535, strict=True)
    dbname: Text
    user: Text
    password: SecretStr
    sslmode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = "prefer"
    schemas: list[Column] = Field(default_factory=lambda: ["public"], min_length=1, max_length=20)


class DraftRequest(StrictModel):
    mode: Literal["new", "template", "schema"]
    ontology_id: Identifier = "retail"
    namespace: Text = "com.example.retail"
    name: Text = "Retail Knowledge Graph"
    author: Text = "data.modeller"


class ApiAttribute(AttributeDef):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(default="", max_length=4000)
    source_column: Column | None = None


class ApiClassMapping(ClassMapping):
    model_config = ConfigDict(extra="forbid")
    source_table: Table
    key_columns: list[Column] = Field(min_length=1, max_length=100)
    resolution_columns: list[Column] = Field(default_factory=list, max_length=100)
    watermark_column: Column | None = None


class ApiClass(ClassDef):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(default="", max_length=4000)
    attributes: list[ApiAttribute] = Field(default_factory=list, max_length=500)
    mapping: ApiClassMapping | None = None


class ApiRelationshipMapping(RelationshipMapping):
    model_config = ConfigDict(extra="forbid")
    table: Table
    source_key_columns: list[Column] = Field(min_length=1, max_length=100)
    target_key_columns: list[Column] = Field(min_length=1, max_length=100)
    property_columns: list[Column] = Field(default_factory=list, max_length=500)
    watermark_column: Column | None = None


class ApiRelationship(RelationshipDef):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(default="", max_length=4000)
    properties: list[ApiAttribute] = Field(default_factory=list, max_length=500)
    mapping: ApiRelationshipMapping | None = None


class ApiOntology(Ontology):
    model_config = ConfigDict(extra="forbid")
    ontology_id: Identifier
    namespace: Text
    name: Text
    created_by: Text
    version: int = Field(default=1, ge=1)
    classes: list[ApiClass] = Field(default_factory=list, max_length=500)
    relationships: list[ApiRelationship] = Field(default_factory=list, max_length=2000)
    change_note: str = Field(default="", max_length=4000)


class OntologyRequest(StrictModel):
    ontology: ApiOntology


class ClassRequest(StrictModel):
    definition: ApiClass


class AttributesRequest(StrictModel):
    attributes: list[ApiAttribute] = Field(max_length=500)


class RenameRequest(StrictModel):
    name: Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9_]{0,62}$")]


class RelationshipRequest(StrictModel):
    definition: ApiRelationship


class AIRequest(StrictModel):
    actor: Text
    use_groq: bool = False
    include_samples: bool = False
    allowed_tables: list[Table] | None = Field(default=None, max_length=200)


class Decision(StrictModel):
    action: Literal["approve", "edit", "reject"]
    payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def edit_payload(self):
        if self.action == "edit" and not self.payload:
            raise ValueError("Edited decisions require a payload")
        if self.action != "edit" and self.payload is not None:
            raise ValueError("Only edited decisions accept a payload")
        return self


class ReviewRequest(StrictModel):
    actor: Text
    decisions: dict[Text, Decision] = Field(default_factory=dict, max_length=1000)
    acyclic_relationships: list[Text] = Field(default_factory=list, max_length=500)
    watermark_column: Column | None = None


class ApprovalRequest(StrictModel):
    author: Text
    reviewer: Text

    @model_validator(mode="after")
    def distinct_people(self):
        if self.author.casefold() == self.reviewer.casefold():
            raise ValueError("Reviewer must differ from author")
        return self


class ActorRequest(StrictModel):
    actor: Text


class RejectRequest(ActorRequest):
    reason: Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class Rule(StrictModel):
    column: Column
    rule: Literal["non_negative", "allowed_values"]
    values: list[Text] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def allowed_values(self):
        if self.rule == "allowed_values" and not self.values:
            raise ValueError("Allowed values are required")
        if self.rule == "non_negative" and self.values is not None:
            raise ValueError("This rule takes no values")
        return self


class BuildRequest(StrictModel):
    batch_size: int = Field(default=5000, ge=1, le=100000, strict=True)
    business_rules: dict[Table, list[Rule]] | None = Field(default=None, max_length=200)


class SnapshotRequest(StrictModel):
    load_neo4j: bool = False


class GraphNode(BaseModel):
    id: str
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    key: str
    properties: dict[str, Any]


class GraphView(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int
    truncated: bool
