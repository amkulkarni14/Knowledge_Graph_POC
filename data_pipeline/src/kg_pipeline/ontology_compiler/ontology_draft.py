"""Drafts an ontology from a SchemaCatalog by rules only (no AI).

    table (entity / event / lookup)  -> class      (key = primary key, one attribute per column)
    foreign key                      -> relationship  owner --HAS_<HOLDER>--> holder   (rows of the holder table)
    bridge table (M:N)               -> relationship  A --<BRIDGE_TABLE>--> B          (rows of the bridge table)
    self reference                   -> relationship  holder --<COLUMN>--> owner

A draft is a starting point, not an answer: everything the rules are unsure about, or had to leave out, is
returned as a note so the person editing it knows where to look. The draft is checked by the same Stage 8
validator as a hand-made ontology.
"""
from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel

from kg_pipeline.core.naming import NAME_LIMIT
from kg_pipeline.core.naming import split_words
from kg_pipeline.core.naming import to_class_name
from kg_pipeline.core.naming import to_snake
from kg_pipeline.core.naming import to_upper_snake
from kg_pipeline.core.naming import unique_name
from kg_pipeline.core.ontology_models import AttributeDef
from kg_pipeline.core.ontology_models import Cardinality
from kg_pipeline.core.ontology_models import ClassDef
from kg_pipeline.core.ontology_models import ClassMapping
from kg_pipeline.core.ontology_models import DataType
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.ontology_models import OntologyStatus
from kg_pipeline.core.ontology_models import RelationshipDef
from kg_pipeline.core.ontology_models import RelationshipMapping
from kg_pipeline.core.schema_models import ForeignKey
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.core.schema_models import TableInfo

# Names the graph builder writes itself on nodes / edges; an ontology attribute with one of these would overwrite it.
RESERVED_NODE_ATTRIBUTES = frozenset({"label", "source_table", "source_key", "merged_ids", "_resolution_key"})
RESERVED_EDGE_PROPERTIES = frozenset({"type", "weight", "key", "source_table"})

_SENSITIVE_WORDS = frozenset({"pan", "aadhaar", "aadhar", "ssn", "passport", "phone", "mobile", "email", "salary",
                              "income", "password", "tax", "national", "dob", "birth"})
_WATERMARK_NAMES = ("updated_at", "modified_at", "last_updated", "last_modified", "updated_on", "modified_on")
_TIME_TYPES = (DataType.DATE, DataType.DATETIME)


class OntologyDraft(BaseModel):
    ontology: Ontology
    notes: list[str]


def _attribute_name(column: str, used: set[str], reserved: frozenset[str]) -> str:
    name = to_snake(column)
    if name in reserved:
        name = f"{name}_value"
    return unique_name(name, used)


def _attributes(table: TableInfo, sensitive: set[str], used: set[str] | None = None) -> list[AttributeDef]:
    used = used if used is not None else set()
    attrs = []
    for col in table.columns.values():
        words = set(split_words(col.name))
        attrs.append(AttributeDef(
            name=_attribute_name(col.name, used, RESERVED_NODE_ATTRIBUTES),
            data_type=col.data_type, source_column=col.name,
            required=col.name in table.primary_key or not col.nullable,
            normalize="lower" if "email" in words else None,
            pii=bool(words & _SENSITIVE_WORDS) or f"{table.name}.{col.name}" in sensitive))
    return attrs


def _watermark(table: TableInfo) -> str | None:
    return next((n for n in _WATERMARK_NAMES if n in table.columns and table.columns[n].data_type in _TIME_TYPES),
                None)


def _in_owner_key_order(fk: ForeignKey, owner: TableInfo) -> list[str] | None:
    """The FK columns, ordered like the owner's primary key (so they line up with the owner's node ids)."""
    if set(fk.ref_columns) != set(owner.primary_key) or len(fk.columns) != len(owner.primary_key):
        return None
    by_ref = dict(zip(fk.ref_columns, fk.columns))
    return [by_ref[k] for k in owner.primary_key]


def draft_from_catalog(catalog: SchemaCatalog, kinds: dict[str, str], *, ontology_id: str, namespace: str,
                       name: str, author: str = "data.modeller",
                       sensitive_columns: Iterable[str] = ()) -> OntologyDraft:
    """`kinds` is the Stage 4 table type per table (entity / event / bridge / lookup / log)."""
    sensitive = set(sensitive_columns)
    notes: list[str] = []
    class_of: dict[str, str] = {}
    class_names: set[str] = set()
    classes: list[ClassDef] = []

    for t in catalog.tables.values():
        kind = kinds.get(t.name, "entity")
        if kind == "bridge":
            continue                                         # becomes a relationship below
        if not t.primary_key:
            notes.append(f"{t.name}: no primary key, so it was left out (a class needs a key that identifies a row)")
            continue
        if kind == "log":
            notes.append(f"{t.name}: looks like a log / very large event table, so it was left out")
            continue
        cname = unique_name(to_class_name(t.name), class_names)
        class_of[t.name] = cname
        classes.append(ClassDef(
            name=cname, description=f"Drafted from table {t.name}",
            attributes=_attributes(t, sensitive),
            mapping=ClassMapping(source_table=t.name, key_columns=list(t.primary_key),
                                 watermark_column=_watermark(t))))
        if kind == "lookup":
            notes.append(f"{t.name}: small code table. It became class {cname}; if it only describes other "
                         "records, delete the class and keep the code as a property instead")

    relationships: list[RelationshipDef] = []
    taken: set[tuple[str, str, str]] = set()

    def add(base: str, source: str, target: str, **kw) -> None:
        rel_name, n = base[:NAME_LIMIT], 2
        while (rel_name, source, target) in taken:
            suffix = f"_{n}"
            rel_name, n = base[: NAME_LIMIT - len(suffix)] + suffix, n + 1
        taken.add((rel_name, source, target))
        relationships.append(RelationshipDef(name=rel_name, source_class=source, target_class=target, **kw))

    for t in catalog.tables.values():
        kind = kinds.get(t.name, "entity")
        if kind == "bridge":
            _draft_bridge(t, catalog, class_of, notes, add)
            continue
        if t.name not in class_of:
            continue
        per_owner: dict[str, int] = {}
        for fk in t.foreign_keys:
            per_owner[fk.ref_table] = per_owner.get(fk.ref_table, 0) + 1
        for fk in t.foreign_keys:
            owner = catalog.tables.get(fk.ref_table)
            if owner is None or fk.ref_table not in class_of:
                notes.append(f"{t.name}.{', '.join(fk.columns)} → {fk.ref_table}: the referenced table is not a "
                             "class, so no relationship was drafted")
                continue
            cols = _in_owner_key_order(fk, owner)
            if cols is None:
                notes.append(f"{t.name}.{', '.join(fk.columns)} → {fk.ref_table}: the foreign key does not point at "
                             "the primary key of that table, so no relationship was drafted")
                continue
            holder_cls, owner_cls = class_of[t.name], class_of[owner.name]
            unique_fk = catalog.is_unique(t.name, cols)
            if owner.name == t.name:                          # self reference: row --COLUMN--> referenced row
                base = to_upper_snake(cols[0].removesuffix("_id").removesuffix("_no") or cols[0])
                add(base, holder_cls, owner_cls,
                    cardinality=Cardinality.ONE_TO_ONE if unique_fk else Cardinality.MANY_TO_ONE,
                    description=f"Drafted from the self-reference {t.name}.{', '.join(cols)}",
                    mapping=RelationshipMapping(kind="foreign_key", table=t.name,
                                                source_key_columns=list(t.primary_key), target_key_columns=cols))
                notes.append(f"{base} ({holder_cls} → {holder_cls}) is a self reference; mark it 'forbid cycles' in "
                             "Stage 5 if it must not loop (for example a management chain)")
                continue
            base = "HAS_" + to_upper_snake(holder_cls)
            if per_owner[fk.ref_table] > 1:                   # two links between the same pair: say which column
                base = f"{base}_{to_upper_snake(cols[0].removesuffix('_id'))}"
            add(base, owner_cls, holder_cls,
                cardinality=Cardinality.ONE_TO_ONE if unique_fk else Cardinality.ONE_TO_MANY,
                description=f"Drafted from the foreign key {t.name}.{', '.join(cols)} → {owner.name}",
                mapping=RelationshipMapping(kind="foreign_key", table=t.name, source_key_columns=cols,
                                            target_key_columns=list(t.primary_key)))

    onto = Ontology(ontology_id=ontology_id, namespace=namespace, name=name, created_by=author,
                    status=OntologyStatus.DRAFT, classes=classes, relationships=relationships,
                    change_note="Drafted from the schema by rules (no AI)")
    if not classes:
        notes.append("No class could be drafted: no table has a primary key that identifies its rows")
    return OntologyDraft(ontology=onto, notes=notes)


def _draft_bridge(t: TableInfo, catalog: SchemaCatalog, class_of: dict[str, str], notes: list[str], add) -> None:
    if len(t.foreign_keys) < 2:
        return
    a_fk, b_fk = t.foreign_keys[0], t.foreign_keys[1]
    a, b = catalog.tables.get(a_fk.ref_table), catalog.tables.get(b_fk.ref_table)
    if a is None or b is None or a.name not in class_of or b.name not in class_of:
        notes.append(f"{t.name}: bridge table, but one side is not a class, so no relationship was drafted")
        return
    a_cols, b_cols = _in_owner_key_order(a_fk, a), _in_owner_key_order(b_fk, b)
    if a_cols is None or b_cols is None:
        notes.append(f"{t.name}: bridge table whose foreign keys do not point at primary keys, so no "
                     "relationship was drafted")
        return
    used_cols = set(a_cols) | set(b_cols)
    props = [c for c in t.columns if c not in used_cols]
    used: set[str] = set()
    properties = [AttributeDef(name=_attribute_name(c, used, RESERVED_EDGE_PROPERTIES),
                               data_type=t.columns[c].data_type, source_column=c) for c in props]
    add(to_upper_snake(to_class_name(t.name)), class_of[a.name], class_of[b.name],
        cardinality=Cardinality.MANY_TO_MANY, properties=properties,
        description=f"Drafted from the bridge table {t.name}",
        mapping=RelationshipMapping(kind="join_table", table=t.name, source_key_columns=a_cols,
                                    target_key_columns=b_cols, property_columns=props))
    if len(t.foreign_keys) > 2:
        notes.append(f"{t.name}: bridge table with {len(t.foreign_keys)} foreign keys; only the first two were "
                     "used. Add the others by hand if you need them")
