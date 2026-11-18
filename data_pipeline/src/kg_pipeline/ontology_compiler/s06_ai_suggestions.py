"""Stage 6 - Groq AI ontology suggestions.

What : send the schema STRUCTURE (+ optional masked samples, never PII) and the current
       ontology to Groq; get missing classes / relationships / attributes / duplicates.
Why  : large schemas are slow to model by hand; the AI drafts in seconds and notices
       links people miss. The human still decides (Stage 7).
How  : strict JSON-schema structured output -> Pydantic re-parse -> backend review of
       every suggestion against the real SchemaCatalog (hallucination guard).
Out  : ctx.ai_items (labelled ReviewItems: valid / needs_review / invalid). Nothing is applied.

Without GROQ_API_KEY (or when the user chooses "offline"), a recorded fixture is used,
so the stage is always demonstrable. The graph build never depends on the AI.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ValidationError

from kg_pipeline.config import FIXTURE_DIR
from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import AttributeDef
from kg_pipeline.core.ontology_models import Cardinality
from kg_pipeline.core.ontology_models import ClassDef
from kg_pipeline.core.ontology_models import DataType
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.schema_models import COMPATIBLE
from kg_pipeline.core.schema_models import SchemaCatalog

SENSITIVE_COLUMN_RE = re.compile(
    r"(email|phone|mobile|name|address|ssn|pan|aadhaar|dob|birth|password|token)", re.I)

SYSTEM_PROMPT = """You are a knowledge-graph ontology architect.
You receive a PostgreSQL schema (tables, columns, types, primary keys, foreign keys)
and the user's existing ontology. Suggest IMPROVEMENTS ONLY:
- new classes (PascalCase) for tables that represent real entities (not pure join tables),
- new relationships (UPPER_SNAKE_CASE verbs) derived from foreign keys or join tables,
- attributes missing from existing classes,
- classes that look like duplicates.
Rules:
- Use ONLY table and column names that appear in the schema. Never invent columns.
- Do not repeat classes, attributes or relationships that already exist.
- Relationship mapping: mapping_table is the table whose rows are edges;
  source_key_columns/target_key_columns are columns IN THAT TABLE that identify the
  source/target node keys.
- Attribute names are snake_case. confidence is 0..1.
Return JSON matching the provided schema."""


# --------------------------------------------------------------------------- 1. context
def mask_value(value: Any) -> Any:
    """Keeps the SHAPE of a value (useful to the LLM) but not its content."""
    if value is None:
        return None
    s = str(value)
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return re.sub(r"\d", "9", s)
    return re.sub(r"[A-Za-z]", "x", s)[:24]


def build_schema_context(catalog: SchemaCatalog, ontology: Optional[Ontology] = None,
                         samples: Optional[dict[str, list[dict]]] = None,
                         allowed_tables: Optional[set[str]] = None,
                         sensitive_columns: Optional[set[str]] = None) -> dict:
    pii = set(sensitive_columns or set())
    if ontology:
        for c in ontology.classes:
            if c.mapping:
                pii |= {f"{c.mapping.source_table}.{a.source_column}" for a in c.attributes if a.pii}
    tables = []
    for name, t in catalog.tables.items():
        if allowed_tables and name not in allowed_tables:
            continue
        entry = {"table": name, "row_estimate": t.row_estimate, "primary_key": t.primary_key,
                 "columns": [{"name": c.name, "type": c.pg_type, "nullable": c.nullable} for c in t.columns.values()],
                 "foreign_keys": [fk.model_dump() for fk in t.foreign_keys]}
        if samples and name in samples:
            safe = [c for c in t.columns if f"{name}.{c}" not in pii and not SENSITIVE_COLUMN_RE.search(c)]
            entry["masked_samples"] = [{c: mask_value(r.get(c)) for c in safe} for r in samples[name][:3]]
        tables.append(entry)
    existing = None
    if ontology:
        existing = {
            "classes": [{"name": c.name, "source_table": c.mapping.source_table if c.mapping else None,
                         "attributes": [a.name for a in c.attributes]} for c in ontology.classes],
            "relationships": [{"name": r.name, "source": r.source_class, "target": r.target_class,
                               "cardinality": r.cardinality.value} for r in ontology.relationships],
        }
    return {"tables": tables, "existing_ontology": existing}


# --------------------------------------------------------------------------- 2. strict schema
_ATTR = {"type": "object", "additionalProperties": False,
         "required": ["name", "data_type", "source_column", "required"],
         "properties": {"name": {"type": "string"},
                        "data_type": {"type": "string", "enum": [d.value for d in DataType]},
                        "source_column": {"type": "string"}, "required": {"type": "boolean"}}}
_STR_ARR = {"type": "array", "items": {"type": "string"}}
SUGGESTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["classes", "relationships", "missing_attributes", "possible_duplicates"],
    "properties": {
        "classes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["name", "description", "source_table", "key_columns", "attributes", "confidence", "rationale"],
            "properties": {"name": {"type": "string"}, "description": {"type": "string"},
                           "source_table": {"type": "string"}, "key_columns": _STR_ARR,
                           "attributes": {"type": "array", "items": _ATTR},
                           "confidence": {"type": "number"}, "rationale": {"type": "string"}}}},
        "relationships": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["name", "source_class", "target_class", "cardinality", "mapping_kind", "mapping_table",
                         "source_key_columns", "target_key_columns", "property_columns", "confidence", "rationale"],
            "properties": {"name": {"type": "string"}, "source_class": {"type": "string"},
                           "target_class": {"type": "string"},
                           "cardinality": {"type": "string", "enum": [c.value for c in Cardinality]},
                           "mapping_kind": {"type": "string", "enum": ["foreign_key", "join_table"]},
                           "mapping_table": {"type": "string"}, "source_key_columns": _STR_ARR,
                           "target_key_columns": _STR_ARR, "property_columns": _STR_ARR,
                           "confidence": {"type": "number"}, "rationale": {"type": "string"}}}},
        "missing_attributes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["class_name", "attribute", "confidence", "rationale"],
            "properties": {"class_name": {"type": "string"}, "attribute": _ATTR,
                           "confidence": {"type": "number"}, "rationale": {"type": "string"}}}},
        "possible_duplicates": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["class_a", "class_b", "reason", "confidence"],
            "properties": {"class_a": {"type": "string"}, "class_b": {"type": "string"},
                           "reason": {"type": "string"}, "confidence": {"type": "number"}}}},
    },
}


class AttrSuggestion(BaseModel):
    name: str
    data_type: str
    source_column: str
    required: bool


class ClassSuggestion(BaseModel):
    name: str
    description: str
    source_table: str
    key_columns: list[str]
    attributes: list[AttrSuggestion]
    confidence: float
    rationale: str


class RelSuggestion(BaseModel):
    name: str
    source_class: str
    target_class: str
    cardinality: str
    mapping_kind: Literal["foreign_key", "join_table"]
    mapping_table: str
    source_key_columns: list[str]
    target_key_columns: list[str]
    property_columns: list[str]
    confidence: float
    rationale: str


class MissingAttrSuggestion(BaseModel):
    class_name: str
    attribute: AttrSuggestion
    confidence: float
    rationale: str


class DuplicateSuggestion(BaseModel):
    class_a: str
    class_b: str
    reason: str
    confidence: float


class SuggestionSet(BaseModel):
    classes: list[ClassSuggestion]
    relationships: list[RelSuggestion]
    missing_attributes: list[MissingAttrSuggestion]
    possible_duplicates: list[DuplicateSuggestion]


class ReviewItem(BaseModel):
    item_id: str
    kind: Literal["class", "relationship", "attribute", "duplicate"]
    label: str
    payload: dict
    confidence: float
    rationale: str
    status: Literal["valid", "invalid", "needs_review"]
    problems: list[str] = []


# --------------------------------------------------------------------------- 2b. call Groq
def _log_request(path: Path, **entry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def request_suggestions(context: dict, actor: str, use_groq: bool, model: str | None = None,
                        max_retries: int = 4) -> tuple[SuggestionSet, dict]:
    model = model or settings.groq_model
    user_content = json.dumps(context, default=str)
    prompt_hash = hashlib.sha256((SYSTEM_PROMPT + user_content).encode()).hexdigest()[:16]
    tables_shared = [t["table"] for t in context["tables"]]
    samples_shared = any("masked_samples" in t for t in context["tables"])
    base = dict(actor=actor, prompt_hash=prompt_hash, tables_shared=tables_shared, samples_shared=samples_shared)

    if not use_groq:
        data = json.loads((FIXTURE_DIR / "groq_offline_fixture.json").read_text(encoding="utf-8"))
        _log_request(settings.ai_log_path, model="offline-fixture", outcome="ok", **base)
        return SuggestionSet.model_validate(data), {"model": "offline-fixture", "attempts": 1, "latency_s": 0.0,
                                                    "prompt_hash": prompt_hash}

    from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

    client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=60, max_retries=0)
    for attempt in range(1, max_retries + 1):
        started = time.monotonic()
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0.1,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_content}],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "ontology_suggestions", "strict": True, "schema": SUGGESTION_SCHEMA}},
            )
            result = SuggestionSet.model_validate_json(resp.choices[0].message.content or "{}")
            latency = round(time.monotonic() - started, 2)
            _log_request(settings.ai_log_path, model=model, attempt=attempt, outcome="ok", latency_s=latency, **base)
            return result, {"model": model, "attempts": attempt, "latency_s": latency, "prompt_hash": prompt_hash}
        except RateLimitError as e:
            retry_after = float(e.response.headers.get("retry-after", 0) or 0)
            wait = max(retry_after, 2 ** attempt + random.random())
            _log_request(settings.ai_log_path, model=model, attempt=attempt, outcome="rate_limited", **base)
        except (APIConnectionError, ValidationError, json.JSONDecodeError) as e:
            wait = 2 ** attempt + random.random()
            _log_request(settings.ai_log_path, model=model, attempt=attempt,
                         outcome=f"retryable:{type(e).__name__}", **base)
        except APIStatusError as e:
            if e.status_code < 500:              # 4xx (bad request / auth): do not retry
                _log_request(settings.ai_log_path, model=model, attempt=attempt,
                             outcome=f"fatal:{e.status_code}", **base)
                raise
            wait = 2 ** attempt + random.random()
            _log_request(settings.ai_log_path, model=model, attempt=attempt,
                         outcome=f"server_error:{e.status_code}", **base)
        time.sleep(wait)
    raise RuntimeError("Groq unavailable after retries; continue with manual ontology editing")


# --------------------------------------------------------------------------- 3. review (never trust the LLM)
def _check_attr(a: AttrSuggestion, table: str, catalog: SchemaCatalog, problems: list[str]) -> bool:
    if a.data_type not in {d.value for d in DataType}:
        problems.append(f"attribute {a.name}: unknown data type {a.data_type}")
        return False
    t = catalog.table(table)
    col = t.columns.get(a.source_column) if t else None
    if col is None:
        problems.append(f"column {table}.{a.source_column} does not exist (hallucination)")
        return False
    if col.data_type not in COMPATIBLE[DataType(a.data_type)]:
        problems.append(f"attribute {a.name}: {a.data_type} incompatible with {col.pg_type}")
        return False
    return True


def review_suggestions(s: SuggestionSet, catalog: SchemaCatalog, onto: Ontology,
                       min_confidence: float = 0.6) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    existing_classes = {c.name.lower() for c in onto.classes}
    existing_tables = {c.mapping.source_table: c.name for c in onto.classes if c.mapping}
    suggested: dict[str, ClassSuggestion] = {}

    def finish(kind, label, payload, conf, rationale, problems):
        status = "invalid" if problems else ("needs_review" if conf < min_confidence else "valid")
        items.append(ReviewItem(item_id=f"{kind[:3]}-{len(items) + 1:03d}", kind=kind, label=label,
                                payload=payload, confidence=conf, rationale=rationale, status=status,
                                problems=problems))

    for c in s.classes:
        problems: list[str] = []
        if c.name.lower() in existing_classes:
            problems.append(f"class {c.name} already exists")
        t = catalog.table(c.source_table)
        if t is None:
            problems.append(f"table {c.source_table} does not exist (hallucination)")
        else:
            if c.source_table in existing_tables:
                problems.append(f"table already mapped by class {existing_tables[c.source_table]} "
                                "(possible duplicate class)")
            if sorted(c.key_columns) != sorted(t.primary_key):
                problems.append(f"key {c.key_columns} is not the primary key {t.primary_key}")
            c.attributes = [a for a in c.attributes if _check_attr(a, c.source_table, catalog, problems)]
        if not problems:
            try:
                ClassDef(name=c.name, attributes=[AttributeDef(name=a.name, data_type=a.data_type)
                                                  for a in c.attributes])
            except ValidationError as e:
                problems.append(f"naming: {e.errors()[0]['msg']}")
        if not problems:
            suggested[c.name] = c
        finish("class", c.name, c.model_dump(), c.confidence, c.rationale, problems)

    known = {c.name for c in onto.classes} | set(suggested)
    existing_rels = {(r.name, r.source_class, r.target_class) for r in onto.relationships}
    for r in s.relationships:
        problems = []
        for cls in (r.source_class, r.target_class):
            if cls not in known:
                problems.append(f"class {cls} is neither existing nor a valid suggestion")
        if (r.name, r.source_class, r.target_class) in existing_rels:
            problems.append("relationship already exists")
        t = catalog.table(r.mapping_table)
        if t is None:
            problems.append(f"table {r.mapping_table} does not exist (hallucination)")
        else:
            for col in r.source_key_columns + r.target_key_columns + r.property_columns:
                if col not in t.columns:
                    problems.append(f"column {r.mapping_table}.{col} does not exist (hallucination)")
        if r.cardinality not in {c.value for c in Cardinality}:
            problems.append(f"invalid cardinality {r.cardinality}")
        finish("relationship", f"{r.source_class}-[{r.name}]->{r.target_class}", r.model_dump(),
               r.confidence, r.rationale, problems)

    for m in s.missing_attributes:
        problems = []
        cls = onto.class_by_name(m.class_name)
        if cls is None or cls.mapping is None:
            problems.append(f"class {m.class_name} not found or unmapped")
        else:
            if any(a.name == m.attribute.name or a.source_column == m.attribute.source_column for a in cls.attributes):
                problems.append(f"{m.class_name} already has {m.attribute.name}")
            _check_attr(m.attribute, cls.mapping.source_table, catalog, problems)
        finish("attribute", f"{m.class_name}.{m.attribute.name}", m.model_dump(), m.confidence, m.rationale,
               problems)

    for d in s.possible_duplicates:
        items.append(ReviewItem(item_id=f"dup-{len(items) + 1:03d}", kind="duplicate",
                                label=f"{d.class_a} ~ {d.class_b}", payload=d.model_dump(),
                                confidence=d.confidence, rationale=d.reason, status="needs_review"))
    return items


# --------------------------------------------------------------------------- stage entry point
def skip(ctx: PipelineContext) -> None:
    """The AI step is optional: a purely manual ontology is a valid path."""
    ctx.invalidate_from(6)
    ctx.ai_items, ctx.ai_meta = [], {"model": "skipped"}
    ctx.log(6, "AI suggestions skipped; continuing with the manual ontology only")
    ctx.mark_done(6)


def run(ctx: PipelineContext, actor: str, use_groq: bool = False, include_samples: bool = False,
        allowed_tables: Optional[set[str]] = None) -> list[ReviewItem]:
    if ctx.manual_ontology is None or ctx.catalog is None:
        raise RuntimeError("Stages 3 and 5 must run first")
    if not use_groq and ctx.source_info.get("mode") == "csv":
        raise ValueError("The recorded offline response only fits the built-in sample database, not uploaded "
                         "files. Call Groq live (set GROQ_API_KEY) or use 'Skip AI (manual only)'.")
    samples = None
    if include_samples:
        samples = {t: ctx.source.sample_rows(t, 3) for t in ctx.catalog.tables
                   if not allowed_tables or t in allowed_tables}
    sensitive = set(ctx.scope.sensitive_columns) if ctx.scope else set()
    context = build_schema_context(ctx.catalog, ctx.manual_ontology, samples, allowed_tables, sensitive)
    suggestions, meta = request_suggestions(context, actor=actor, use_groq=use_groq)
    items = review_suggestions(suggestions, ctx.catalog, ctx.manual_ontology)
    ctx.invalidate_from(6)
    ctx.ai_items = items
    ctx.ai_meta = {**meta, "context": context}
    counts = {s: sum(i.status == s for i in items) for s in ("valid", "needs_review", "invalid")}
    ctx.log(6, f"AI ({meta['model']}) returned {len(items)} suggestions: {counts['valid']} valid, "
               f"{counts['needs_review']} need review, {counts['invalid']} invalid (blocked by backend checks)")
    ctx.mark_done(6)
    return items
