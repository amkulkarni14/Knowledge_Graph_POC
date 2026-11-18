"""Stage 8 - Validate the ontology.

STRUCTURAL : is the rulebook well formed by itself? (names, duplicates, references, cycles)
SEMANTIC   : is it true against the real database and compatible with the approved version?
             (tables/columns exist, types fit, keys unique, FK declared, breaking changes)
Errors block approval (Stage 9); warnings are shown to the reviewer.
"""
from __future__ import annotations

from collections import Counter
from typing import Literal, Optional

import networkx as nx
from pydantic import BaseModel

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.ontology_compiler.ontology_draft import RESERVED_EDGE_PROPERTIES
from kg_pipeline.ontology_compiler.ontology_draft import RESERVED_NODE_ATTRIBUTES
from kg_pipeline.core.ontology_models import Cardinality
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.schema_models import COMPATIBLE
from kg_pipeline.core.schema_models import SchemaCatalog


class Issue(BaseModel):
    level: Literal["error", "warning"]
    category: Literal["structural", "semantic"]
    code: str
    path: str
    message: str


class ValidationReport(BaseModel):
    issues: list[Issue] = []

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def errors(self) -> int:
        return sum(i.level == "error" for i in self.issues)

    @property
    def warnings(self) -> int:
        return sum(i.level == "warning" for i in self.issues)

    def add(self, level, category, code, path, message):
        self.issues.append(Issue(level=level, category=category, code=code, path=path, message=message))

    def summary(self) -> str:
        return f"{'VALID' if self.ok else 'INVALID'} ({self.errors} errors, {self.warnings} warnings)"


def validate_structure(onto: Ontology, report: ValidationReport) -> None:
    S = "structural"
    for name, n in Counter(c.name.lower() for c in onto.classes).items():
        if n > 1:
            report.add("error", S, "DUPLICATE_CLASS", name, f"class '{name}' defined {n} times in {onto.namespace}")
    class_names = {c.name for c in onto.classes}
    for c in onto.classes:
        for a, n in Counter(a.name for a in c.attributes).items():
            if n > 1:
                report.add("error", S, "DUPLICATE_ATTRIBUTE", f"{c.name}.{a}", f"attribute defined {n} times")
        for col, n in Counter(a.source_column for a in c.attributes if a.source_column).items():
            if n > 1:
                report.add("warning", S, "COLUMN_MAPPED_TWICE", c.name, f"column '{col}' mapped {n} times")
        for a in c.attributes:
            if a.name in RESERVED_NODE_ATTRIBUTES:
                report.add("error", S, "RESERVED_NAME", f"{c.name}.{a.name}",
                           f"'{a.name}' is written by the graph builder on every node; rename the attribute")
        if c.mapping is None:
            report.add("warning", S, "UNMAPPED_CLASS", c.name, "no PostgreSQL mapping; no nodes will be built")

    for key, n in Counter((r.name, r.source_class, r.target_class) for r in onto.relationships).items():
        if n > 1:
            report.add("error", S, "DUPLICATE_RELATIONSHIP", str(key), f"relationship defined {n} times")
    for r in onto.relationships:
        for side, cls in (("source", r.source_class), ("target", r.target_class)):
            if cls not in class_names:
                report.add("error", S, "MISSING_CLASS", r.key, f"{side} class '{cls}' does not exist")
        for p in r.properties:
            if p.name in RESERVED_EDGE_PROPERTIES:
                report.add("error", S, "RESERVED_NAME", f"{r.key}.{p.name}",
                           f"'{p.name}' is written by the graph builder on every edge; rename the property")
        if r.mapping is None:
            report.add("warning", S, "UNMAPPED_RELATIONSHIP", r.key, "no mapping; no edges will be built")
        elif r.mapping.kind == "join_table" and r.cardinality != Cardinality.MANY_TO_MANY:
            report.add("warning", S, "CARDINALITY_KIND_MISMATCH", r.key,
                       f"join tables normally model M:N, declared {r.cardinality.value}")
        if r.source_class == r.target_class and not r.allow_cycles:
            report.add("warning", S, "SELF_REFERENCE_ACYCLIC", r.key,
                       "self-reference marked acyclic; the instance graph will be checked for cycles")

    acyclic = nx.DiGraph()
    acyclic.add_edges_from((r.source_class, r.target_class) for r in onto.relationships
                           if not r.allow_cycles and r.source_class != r.target_class)
    for cycle in nx.simple_cycles(acyclic):
        report.add("error", S, "PROHIBITED_CYCLE", " -> ".join(cycle + [cycle[0]]),
                   "relationships marked allow_cycles=False form a cycle")


def validate_semantics(onto: Ontology, catalog: SchemaCatalog, report: ValidationReport,
                       approved: Optional[Ontology] = None) -> None:
    S = "semantic"
    for c in onto.classes:
        if not c.mapping:
            continue
        t = catalog.table(c.mapping.source_table)
        if t is None:
            report.add("error", S, "UNKNOWN_TABLE", c.name, f"table {c.mapping.source_table} not found")
            continue
        for col in c.mapping.key_columns + c.mapping.resolution_columns + \
                ([c.mapping.watermark_column] if c.mapping.watermark_column else []):
            if col not in t.columns:
                report.add("error", S, "UNKNOWN_COLUMN", f"{c.name}.mapping", f"column {t.name}.{col} not found")
        if not catalog.is_unique(t.name, c.mapping.key_columns):
            report.add("error", S, "KEY_NOT_UNIQUE", f"{c.name}.mapping",
                       f"key {c.mapping.key_columns} is not the PK/unique key of {t.name} {t.primary_key}")
        for a in c.attributes:
            if not a.source_column:
                continue
            col = t.columns.get(a.source_column)
            if col is None:
                report.add("error", S, "UNKNOWN_COLUMN", f"{c.name}.{a.name}",
                           f"column {t.name}.{a.source_column} not found")
                continue
            if col.data_type not in COMPATIBLE[a.data_type]:
                report.add("error", S, "TYPE_MISMATCH", f"{c.name}.{a.name}",
                           f"{a.data_type.value} cannot be read from {col.pg_type}")
            if a.required and col.nullable:
                report.add("warning", S, "REQUIRED_BUT_NULLABLE", f"{c.name}.{a.name}",
                           f"column {a.source_column} is nullable; NULL rows will be quarantined")

    for r in onto.relationships:
        src, tgt = onto.class_by_name(r.source_class), onto.class_by_name(r.target_class)
        if not (r.mapping and src and tgt and src.mapping and tgt.mapping):
            continue
        t = catalog.table(r.mapping.table)
        if t is None:
            report.add("error", S, "UNKNOWN_TABLE", r.key, f"table {r.mapping.table} not found")
            continue
        for col in r.mapping.source_key_columns + r.mapping.target_key_columns + r.mapping.property_columns:
            if col not in t.columns:
                report.add("error", S, "UNKNOWN_COLUMN", r.key, f"column {t.name}.{col} not found")
        if len(r.mapping.source_key_columns) != len(src.mapping.key_columns) or \
                len(r.mapping.target_key_columns) != len(tgt.mapping.key_columns):
            report.add("error", S, "KEY_ARITY", r.key, "edge key columns must match the class key arity")
        # a foreign key is a set of (column -> referenced column) pairs; the order its columns are listed in is irrelevant
        fk_pairs = [(fk.ref_table, set(zip(fk.columns, fk.ref_columns))) for fk in t.foreign_keys]
        for cols, cls in ((r.mapping.source_key_columns, src), (r.mapping.target_key_columns, tgt)):
            if t.name == cls.mapping.source_table and sorted(cols) == sorted(cls.mapping.key_columns):
                continue          # these columns are the row's own key
            wanted = set(zip(cols, cls.mapping.key_columns))
            if not any(ref == cls.mapping.source_table and pairs == wanted for ref, pairs in fk_pairs):
                report.add("warning", S, "FK_NOT_DECLARED", r.key,
                           f"{t.name}{cols} has no declared FK to {cls.mapping.source_table}; "
                           "referential integrity is checked in Stage 12")
        if r.mapping.kind == "foreign_key" and r.cardinality == Cardinality.ONE_TO_ONE:
            fk_side = r.mapping.target_key_columns if t.name == src.mapping.source_table \
                else r.mapping.source_key_columns
            if not catalog.is_unique(t.name, fk_side):
                report.add("warning", S, "CARDINALITY_NOT_ENFORCED", r.key,
                           "declared 1:1 but the FK column is not UNIQUE in PostgreSQL")

    if approved is not None:
        new_classes = {c.name: c for c in onto.classes}
        for old in approved.classes:
            new = new_classes.get(old.name)
            if new is None:
                report.add("warning", S, "CLASS_REMOVED", old.name,
                           "class exists in the approved version; removing it deletes its nodes")
                continue
            new_attrs = {a.name: a for a in new.attributes}
            for a in old.attributes:
                if a.name not in new_attrs:
                    report.add("warning", S, "ATTRIBUTE_REMOVED", f"{old.name}.{a.name}",
                               "breaking change for consumers")
                elif new_attrs[a.name].data_type != a.data_type:
                    report.add("error", S, "ATTRIBUTE_TYPE_CHANGED", f"{old.name}.{a.name}",
                               f"{a.data_type.value} -> {new_attrs[a.name].data_type.value}; add a new attribute")
    for table, n in Counter(c.mapping.source_table for c in onto.classes if c.mapping).items():
        if n > 1:
            report.add("warning", S, "TABLE_MAPPED_TWICE", table, f"{n} classes read from {table}")


def validate_ontology(onto: Ontology, catalog: Optional[SchemaCatalog] = None,
                      approved: Optional[Ontology] = None) -> ValidationReport:
    report = ValidationReport()
    validate_structure(onto, report)
    if catalog is not None:
        validate_semantics(onto, catalog, report, approved)
    return report


def run(ctx: PipelineContext, approved: Optional[Ontology] = None) -> ValidationReport:
    draft = ctx.hybrid_draft or ctx.manual_ontology
    if draft is None:
        raise RuntimeError("Stage 5/7 must run first")
    report = validate_ontology(draft, ctx.catalog, approved)
    ctx.invalidate_from(8)
    ctx.ontology_report = report
    ctx.log(8, f"Ontology validation: {report.summary()}", "info" if report.ok else "error")
    if report.ok:
        ctx.mark_done(8)
    return report
