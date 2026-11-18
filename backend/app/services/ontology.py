"""Ontology editor and repository adapters with catalog and state validation."""
from copy import copy
from pydantic import ValidationError
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.ontology_compiler import s05_manual_ontology as manual
from kg_pipeline.ontology_compiler import s06_ai_suggestions as ai
from kg_pipeline.ontology_compiler import s07_review_approval as review
from kg_pipeline.ontology_compiler import s08_ontology_validation as validation
from kg_pipeline.ontology_compiler import s09_ontology_repository as versions
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import clear_from, require


def repository(session):
    return versions.OntologyRepository(session.root / "ontology_repo")


def editor(session):
    require(session, 3, 4)
    if session.editor is None:
        raise ApiError(409, "no_editor", "Create or load an ontology draft first")
    return session.editor


def check_mappings(session, onto):
    require(session, 3)
    catalog = session.ctx.catalog
    if len({c.name for c in onto.classes}) != len(onto.classes):
        raise ApiError(422, "duplicate_class", "Class names must be unique")
    if len({r.key for r in onto.relationships}) != len(onto.relationships):
        raise ApiError(422, "duplicate_relationship", "Relationship keys must be unique")
    for cls in onto.classes:
        if len({a.name for a in cls.attributes}) != len(cls.attributes):
            raise ApiError(422, "duplicate_attribute", "Attribute names must be unique")
        if not cls.mapping:
            continue
        mapping = cls.mapping
        columns = mapping.key_columns + mapping.resolution_columns
        columns += [a.source_column for a in cls.attributes if a.source_column]
        columns += [mapping.watermark_column] if mapping.watermark_column else []
        if mapping.source_table not in catalog.tables or any(
                not catalog.has_column(mapping.source_table, c) for c in columns):
            raise ApiError(422, "invalid_mapping", "Class mapping references an unknown table or column")
    for rel in onto.relationships:
        if not onto.class_by_name(rel.source_class) or not onto.class_by_name(rel.target_class):
            raise ApiError(422, "invalid_relationship", "Relationship endpoints must be existing classes")
        if rel.mapping:
            m = rel.mapping
            cols = m.source_key_columns + m.target_key_columns + m.property_columns
            cols += [m.watermark_column] if m.watermark_column else []
            cols += [a.source_column for a in rel.properties if a.source_column]
            if m.table not in catalog.tables or any(not catalog.has_column(m.table, c) for c in cols):
                raise ApiError(422, "invalid_mapping", "Relationship mapping references an unknown table or column")


def update_editor(session, onto):
    # Re-parse copies because domain assignment itself does not validate fields.
    onto = Ontology.model_validate(onto.model_dump(mode="json"))
    check_mappings(session, onto)
    clear_from(session.ctx, 5)
    session.editor = onto
    session.sync()
    return onto


def review_args(session, body):
    require(session, 5, 6)
    by_id = {item.item_id: item for item in session.ctx.ai_items}
    decisions = body.model_dump()["decisions"]
    if set(decisions) - set(by_id):
        raise ApiError(422, "unknown_suggestion", "A decision references an unknown suggestion")
    for item_id, decision in decisions.items():
        item = by_id[item_id]
        if item.kind == "duplicate" and decision["action"] != "reject":
            raise ApiError(422, "informational_suggestion", "Duplicate suggestions are informational")
        if item.status == "invalid" and decision["action"] == "approve":
            raise ApiError(422, "invalid_suggestion", "Invalid suggestions must be edited before approval")
        if decision["action"] == "edit":
            model = {"class": ai.ClassSuggestion, "relationship": ai.RelSuggestion,
                     "attribute": ai.MissingAttrSuggestion}.get(item.kind)
            if model is None:
                raise ApiError(422, "invalid_edit", "This suggestion cannot be edited")
            try:
                decision["payload"] = model.model_validate(decision["payload"]).model_dump()
            except ValidationError:
                raise ApiError(422, "invalid_edit", "Edited suggestion does not match its contract") from None
    args = {"decisions": decisions, "actor": body.actor,
            "acyclic_relationships": body.acyclic_relationships, "watermark_column": body.watermark_column}
    # Validate the final reviewed model before any workflow state is published.
    try:
        candidate = copy(session.ctx)
        candidate.completed = set(candidate.completed)
        candidate.events = list(candidate.events)
        onto = review.run(candidate, **args)
        check_mappings(session, onto)
        if set(body.acyclic_relationships) - {r.key for r in onto.relationships}:
            raise ApiError(422, "unknown_relationship", "Cycle rule references an unknown relationship")
    except ApiError:
        raise
    except (ValueError, KeyError, AttributeError, TypeError):
        raise ApiError(422, "invalid_review", "Review decisions cannot be applied") from None
    return args
