"""Stage 5 - Create the ontology manually (Ontology Studio).

What : the user defines classes (any business name), attributes with data types,
       relationships with direction and cardinality, and the mapping to tables/columns.
Why  : the ontology fixes exactly what the graph contains and keeps names and types
       stable across builds; domain experts know meanings the database cannot show.
Out  : ctx.manual_ontology (a DRAFT Ontology).

All edit helpers return a NEW ontology (copy-on-write) so a half-finished edit
never corrupts the previous draft.
"""
from __future__ import annotations

import json
import re

from kg_pipeline.config import ONTOLOGY_DIR
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.ontology_compiler.ontology_draft import OntologyDraft
from kg_pipeline.ontology_compiler.ontology_draft import draft_from_catalog
from kg_pipeline.core.ontology_models import AttributeDef
from kg_pipeline.core.ontology_models import ClassDef
from kg_pipeline.core.ontology_models import ClassMapping
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.ontology_models import OntologyStatus
from kg_pipeline.core.ontology_models import RelationshipDef
from kg_pipeline.core.ontology_models import RelationshipMapping
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.metadata_extractor.s04_schema_analysis import classify_table


def default_ids(project: str) -> tuple[str, str, str]:
    """(ontology_id, namespace, name) suggested from the project name, e.g. 'Customer 360' -> customer_360."""
    slug = re.sub(r"[^a-z0-9]+", "_", project.lower()).strip("_") or "ontology"
    if not slug[0].isalpha():
        slug = f"o_{slug}"
    slug = slug[:60]
    return slug, f"com.example.{slug}", f"{project.strip() or 'Knowledge'} Graph".replace("Graph Graph", "Graph")


def draft_from_schema(ctx: PipelineContext, ontology_id: str, namespace: str, name: str,
                      author: str = "data.modeller") -> OntologyDraft:
    """Rule-based draft (class per table, relationship per foreign key / bridge table) from the Stage 3-4 result.

    Nothing is saved: the caller shows the draft and notes, and Stage 5's `run` saves what the user accepts.
    """
    if ctx.catalog is None:
        raise RuntimeError("Stage 3 (schema extraction) must run first")
    kinds = {a["table"]: a["type"] for a in ctx.table_analysis} if ctx.table_analysis else \
        {t.name: classify_table(t, ctx.catalog) for t in ctx.catalog.tables.values()}
    sensitive = set(ctx.scope.sensitive_columns) if ctx.scope else set()
    draft = draft_from_catalog(ctx.catalog, kinds, ontology_id=ontology_id, namespace=namespace, name=name,
                               author=author, sensitive_columns=sensitive)
    ctx.log(5, f"Drafted from the schema: {len(draft.ontology.classes)} classes, "
               f"{len(draft.ontology.relationships)} relationships, {len(draft.notes)} note(s) (not saved yet)")
    return draft


def new_ontology(ontology_id: str, namespace: str, name: str, author: str) -> Ontology:
    return Ontology(ontology_id=ontology_id, namespace=namespace, name=name, created_by=author,
                    status=OntologyStatus.DRAFT, change_note="Manual draft")


def load_template(file_name: str = "retail_manual_draft.json") -> Ontology:
    return Ontology.model_validate(json.loads((ONTOLOGY_DIR / file_name).read_text(encoding="utf-8")))


def attributes_from_table(catalog: SchemaCatalog, table: str, columns: list[str],
                          pii_columns: set[str] | None = None) -> list[AttributeDef]:
    """Default attribute definitions for the chosen columns (type from the column type)."""
    t = catalog.tables[table]
    pii_columns = pii_columns or set()
    return [AttributeDef(name=c.lower(), data_type=t.columns[c].data_type, source_column=c,
                         required=not t.columns[c].nullable, pii=f"{table}.{c}" in pii_columns)
            for c in columns]


def add_class(onto: Ontology, name: str, table: str, key_columns: list[str], attributes: list[AttributeDef],
              description: str = "", resolution_columns: list[str] | None = None,
              watermark_column: str | None = None, category: str | None = None) -> Ontology:
    new = onto.model_copy(deep=True)
    if new.class_by_name(name):
        raise ValueError(f"class {name} already exists")
    new.classes.append(ClassDef(name=name, description=description, category=category, attributes=attributes,
                                mapping=ClassMapping(source_table=table, key_columns=key_columns,
                                                     resolution_columns=resolution_columns or [],
                                                     watermark_column=watermark_column)))
    return new


def remove_class(onto: Ontology, name: str) -> Ontology:
    new = onto.model_copy(deep=True)
    new.classes = [c for c in new.classes if c.name != name]
    new.relationships = [r for r in new.relationships if name not in (r.source_class, r.target_class)]
    return new


def rename_class(onto: Ontology, old: str, new_name: str) -> Ontology:
    new = onto.model_copy(deep=True)
    cls = new.class_by_name(old)
    if cls is None:
        raise ValueError(f"class {old} not found")
    if new.class_by_name(new_name):
        raise ValueError(f"class {new_name} already exists")
    ClassDef(name=new_name)                 # validates naming convention
    cls.name = new_name
    for r in new.relationships:
        if r.source_class == old:
            r.source_class = new_name
        if r.target_class == old:
            r.target_class = new_name
    return new


def add_relationship(onto: Ontology, name: str, source_class: str, target_class: str, cardinality: str,
                     kind: str, table: str, source_key_columns: list[str], target_key_columns: list[str],
                     property_columns: list[str] | None = None, catalog: SchemaCatalog | None = None,
                     description: str = "", allow_cycles: bool = True) -> Ontology:
    new = onto.model_copy(deep=True)
    props = []
    for c in property_columns or []:
        dt = catalog.tables[table].columns[c].data_type if catalog else "string"
        props.append(AttributeDef(name=c.lower(), data_type=dt, source_column=c))
    new.relationships.append(RelationshipDef(
        name=name, source_class=source_class, target_class=target_class, cardinality=cardinality,
        description=description, allow_cycles=allow_cycles, properties=props,
        mapping=RelationshipMapping(kind=kind, table=table, source_key_columns=source_key_columns,
                                    target_key_columns=target_key_columns,
                                    property_columns=property_columns or [])))
    return new


def remove_relationship(onto: Ontology, rel_key: str) -> Ontology:
    new = onto.model_copy(deep=True)
    new.relationships = [r for r in new.relationships if r.key != rel_key]
    return new


def run(ctx: PipelineContext, onto: Ontology) -> Ontology:
    """Accept the user's draft as the Stage 5 result."""
    if not onto.classes:
        raise ValueError("the ontology needs at least one class")
    draft = onto.model_copy(deep=True)
    draft.status = OntologyStatus.DRAFT
    ctx.invalidate_from(5)
    ctx.manual_ontology = draft
    ctx.log(5, f"Manual draft saved: {len(draft.classes)} classes, {len(draft.relationships)} relationships")
    ctx.mark_done(5)
    return draft


def class_rows(onto: Ontology) -> list[dict]:
    return [{"class": c.name, "table": c.mapping.source_table if c.mapping else "-",
             "key": ", ".join(c.mapping.key_columns) if c.mapping else "-",
             "merge by": ", ".join(c.mapping.resolution_columns) if c.mapping else "",
             "attributes": len(c.attributes), "origin": c.origin.value} for c in onto.classes]


def relationship_rows(onto: Ontology) -> list[dict]:
    return [{"relationship": r.key, "cardinality": r.cardinality.value,
             "from table": r.mapping.table if r.mapping else "-",
             "source cols": ", ".join(r.mapping.source_key_columns) if r.mapping else "",
             "target cols": ", ".join(r.mapping.target_key_columns) if r.mapping else "",
             "edge props": ", ".join(r.mapping.property_columns) if r.mapping else "",
             "acyclic": not r.allow_cycles, "origin": r.origin.value} for r in onto.relationships]
