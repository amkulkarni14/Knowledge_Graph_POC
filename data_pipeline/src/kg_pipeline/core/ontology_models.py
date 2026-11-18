"""Ontology data model (the "rulebook").

One Pydantic model is shared by the UI, the validator, the AI assistant and the
graph builder. The builder reads ONLY this model, so no class or relationship is
hard-coded in Python.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

CLASS_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]{0,62}$")      # PascalCase
ATTR_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")          # snake_case
REL_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,62}$")           # UPPER_SNAKE
ONTOLOGY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")
SQL_IDENT_RE =re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}(\.[A-Za-z_][A-Za-z0-9_]{0,62})?$")


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"


class Cardinality(str, Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "M:N"


class Origin(str, Enum):
    MANUAL = "manual"
    AI = "ai"
    HYBRID = "hybrid"      # AI suggestion edited by a user


class OntologyStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class AttributeDef(BaseModel):
    name: str
    data_type: DataType
    required: bool = False
    source_column: Optional[str] = None
    normalize: Optional[Literal["trim", "lower", "upper", "title"]] = None
    pii: bool = False
    description: str = ""
    origin: Origin = Origin.MANUAL

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not ATTR_NAME_RE.match(v):
            raise ValueError(f"attribute name '{v}' must be snake_case")
        return v


class ClassMapping(BaseModel):
    source_table: str
    key_columns: list[str] = Field(min_length=1)
    resolution_columns: list[str] = []       # deterministic entity resolution keys
    watermark_column: Optional[str] = None   # e.g. updated_at, for incremental loads

    @field_validator("source_table")
    @classmethod
    def _table(cls, v: str) -> str:
        if not SQL_IDENT_RE.match(v):
            raise ValueError(f"invalid table identifier '{v}'")
        return v


class ClassDef(BaseModel):
    name: str
    description: str = ""
    category: Optional[str] = None           # optional upper category (Person, Event, ...)
    attributes: list[AttributeDef] = []
    mapping: Optional[ClassMapping] = None
    origin: Origin = Origin.MANUAL

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not CLASS_NAME_RE.match(v):
            raise ValueError(f"class name '{v}' must be PascalCase")
        return v


class RelationshipMapping(BaseModel):
    """Every relationship is read from ONE table whose rows are edges."""
    kind: Literal["foreign_key", "join_table"]
    table: str
    source_key_columns: list[str] = Field(min_length=1)
    target_key_columns: list[str] = Field(min_length=1)
    property_columns: list[str] = []
    watermark_column: Optional[str] = None


class RelationshipDef(BaseModel):
    name: str
    source_class: str
    target_class: str
    cardinality: Cardinality
    directed: bool = True
    required: bool = False
    allow_cycles: bool = True
    multi_edge: bool = False
    properties: list[AttributeDef] = []
    mapping: Optional[RelationshipMapping] = None
    description: str = ""
    origin: Origin = Origin.MANUAL

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not REL_NAME_RE.match(v):
            raise ValueError(f"relationship name '{v}' must be UPPER_SNAKE_CASE")
        return v

    @property
    def key(self) -> str:
        return f"{self.source_class}-[{self.name}]->{self.target_class}"


class Ontology(BaseModel):
    ontology_id: str
    namespace: str
    name: str
    version: int = 1
    parent_version: Optional[int] = None
    status: OntologyStatus = OntologyStatus.DRAFT
    classes: list[ClassDef] = []
    relationships: list[RelationshipDef] = []
    created_by: str = "system"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_by: Optional[str] = None
    change_note: str = ""

    @field_validator("ontology_id")
    @classmethod
    def _ontology_id(cls, v: str) -> str:
        # the id is used as a folder name in the ontology repository and the graph store
        if not ONTOLOGY_ID_RE.match(v):
            raise ValueError(f"ontology id '{v}' may only use letters, digits, '_' and '-' (max 63 characters)")
        return v

    def class_by_name(self, name: str) -> Optional[ClassDef]:
        return next((c for c in self.classes if c.name == name), None)

    def relationship_by_name(self, name: str) -> Optional[RelationshipDef]:
        return next((r for r in self.relationships if r.name == name), None)
