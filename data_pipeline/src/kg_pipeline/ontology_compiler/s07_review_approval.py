"""Stage 7 - Review the AI suggestions and build the hybrid draft.

What : for each suggestion the user chooses approve / edit / reject. Approved and edited
       items are merged with the manual draft into a NEW draft; manual tweaks can be added.
Why  : people are responsible for meaning; the AI can be confidently wrong. Each item
       records its origin (manual / ai / hybrid) for audit.
Rules: invalid items cannot be approved unless edited; duplicates are informational;
       the input ontology is never modified (copy-on-write).
Out  : ctx.hybrid_draft. Final approval by a reviewer happens in Stage 9 after Stage 8.
"""
from __future__ import annotations

from typing import Optional

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import AttributeDef
from kg_pipeline.core.ontology_models import ClassDef
from kg_pipeline.core.ontology_models import ClassMapping
from kg_pipeline.core.ontology_models import DataType
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.ontology_models import Origin
from kg_pipeline.core.ontology_models import RelationshipDef
from kg_pipeline.core.ontology_models import RelationshipMapping
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.ontology_compiler.s06_ai_suggestions import ReviewItem


def default_decisions(items: list[ReviewItem]) -> dict[str, dict]:
    """Suggested starting point for the review screen: approve valid, reject invalid."""
    return {i.item_id: {"action": "approve" if i.status == "valid" else "reject"}
            for i in items if i.kind != "duplicate"}


def apply_decisions(onto: Ontology, items: list[ReviewItem], decisions: dict[str, dict], actor: str,
                    catalog: Optional[SchemaCatalog] = None) -> Ontology:
    """decisions = {item_id: {"action": "approve"|"reject"|"edit", "payload": {...}}}"""
    new = onto.model_copy(deep=True)
    applied = []
    by_id = {i.item_id: i for i in items}
    for item_id, d in decisions.items():
        item = by_id[item_id]
        if d["action"] == "reject" or item.kind == "duplicate":
            continue
        if item.status == "invalid" and d["action"] != "edit":
            raise ValueError(f"{item_id} is invalid; it must be edited before approval")
        payload = d.get("payload") or item.payload
        origin = Origin.HYBRID if d["action"] == "edit" else Origin.AI
        if item.kind == "class":
            new.classes.append(ClassDef(
                name=payload["name"], description=payload["description"], origin=origin,
                mapping=ClassMapping(source_table=payload["source_table"], key_columns=payload["key_columns"]),
                attributes=[AttributeDef(name=a["name"], data_type=a["data_type"], required=a["required"],
                                         source_column=a["source_column"], origin=origin)
                            for a in payload["attributes"]]))
        elif item.kind == "relationship":
            table = payload["mapping_table"]

            def col_type(c):
                if catalog and catalog.table(table) and c in catalog.tables[table].columns:
                    return catalog.tables[table].columns[c].data_type
                return DataType.STRING

            new.relationships.append(RelationshipDef(
                name=payload["name"], source_class=payload["source_class"], target_class=payload["target_class"],
                cardinality=payload["cardinality"], origin=origin, description=payload.get("rationale", ""),
                properties=[AttributeDef(name=c.lower(), source_column=c, origin=origin, data_type=col_type(c))
                            for c in payload["property_columns"]],
                mapping=RelationshipMapping(kind=payload["mapping_kind"], table=table,
                                            source_key_columns=payload["source_key_columns"],
                                            target_key_columns=payload["target_key_columns"],
                                            property_columns=payload["property_columns"])))
        elif item.kind == "attribute":
            cls = new.class_by_name(payload["class_name"])
            a = payload["attribute"]
            cls.attributes.append(AttributeDef(name=a["name"], data_type=a["data_type"], required=a["required"],
                                               source_column=a["source_column"], origin=origin))
        applied.append(item_id)
    new.change_note = f"AI-assisted update by {actor}: applied {', '.join(applied) or 'nothing'}"
    new.created_by = actor
    return new


def apply_manual_edits(onto: Ontology, acyclic_relationships: list[str] | None = None,
                       watermark_column: str | None = None) -> Ontology:
    """Typical human edits on top of the AI output (what makes the result 'hybrid')."""
    new = onto.model_copy(deep=True)
    for r in new.relationships:
        if r.key in (acyclic_relationships or []):
            r.allow_cycles = False
    if watermark_column:
        for c in new.classes:
            if c.mapping and not c.mapping.watermark_column:
                c.mapping.watermark_column = watermark_column
    return new


def run(ctx: PipelineContext, decisions: dict[str, dict], actor: str,
        acyclic_relationships: list[str] | None = None, watermark_column: str | None = "updated_at") -> Ontology:
    if ctx.manual_ontology is None:
        raise RuntimeError("Stage 5 must run first")
    if not ctx.is_done(6):
        raise RuntimeError("Stage 6 must run (or be skipped) first")
    draft = apply_decisions(ctx.manual_ontology, ctx.ai_items, decisions, actor, ctx.catalog)
    draft = apply_manual_edits(draft, acyclic_relationships, None)
    if watermark_column and ctx.catalog:
        # enable incremental loads only where the watermark column really exists
        for c in draft.classes:
            if c.mapping and not c.mapping.watermark_column and \
                    ctx.catalog.has_column(c.mapping.source_table, watermark_column):
                c.mapping.watermark_column = watermark_column
    ctx.invalidate_from(7)
    ctx.hybrid_draft = draft
    approved = sum(d["action"] in ("approve", "edit") for d in decisions.values())
    rejected = sum(d["action"] == "reject" for d in decisions.values())
    ctx.log(7, f"Review by {actor}: {approved} accepted, {rejected} rejected -> hybrid draft with "
               f"{len(draft.classes)} classes and {len(draft.relationships)} relationships")
    ctx.mark_done(7)
    return draft
