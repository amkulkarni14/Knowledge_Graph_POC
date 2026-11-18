"""Stage 4 - Understand the structure (schema analysis).

What : classify each table (entity / event / bridge / lookup / log), find FK-based
       relationship candidates and columns that look like UNDECLARED foreign keys.
Why  : different table kinds become different graph things; a bridge table must
       become edges, not a node type, or the graph gets cluttered.
Out  : ctx.table_analysis (list of dicts) - a first guess the data owner confirms.
"""
from __future__ import annotations

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import DataType
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.core.schema_models import TableInfo

BECOMES = {
    "entity": "Node type (class)",
    "event": "Node type (class) with a date",
    "bridge": "Edges (M:N) with properties",
    "lookup": "Node property (usually)",
    "log": "Excluded or aggregated",
}


def _classify(t: TableInfo, catalog: SchemaCatalog) -> tuple[str, str]:
    fk_cols = {c for fk in t.foreign_keys for c in fk.columns}
    pk = set(t.primary_key)
    has_date = any(c.data_type in (DataType.DATE, DataType.DATETIME) and c.name not in ("updated_at", "created_at")
                   for c in t.columns.values())
    if len(t.foreign_keys) >= 2 and pk and pk <= fk_cols:
        return "bridge", "primary key is made of foreign keys"
    if not pk:
        return "log", "no primary key"
    if (t.row_estimate or 0) > 5_000_000 and has_date:
        return "log", "very large, date-based"
    if len(t.columns) <= 3 and catalog.referenced_by(t.name):
        return "lookup", "small code table referenced by others"
    if has_date:
        return "event", "own key and a business date"
    return "entity", "own key and descriptive columns"


def classify_table(t: TableInfo, catalog: SchemaCatalog) -> str:
    """The table type only (entity / event / bridge / lookup / log)."""
    return _classify(t, catalog)[0]


def undeclared_fk_candidates(t: TableInfo, catalog: SchemaCatalog) -> list[dict]:
    """Columns named like another table's single-column PK but with no declared FK."""
    fk_cols = {c for fk in t.foreign_keys for c in fk.columns}
    pk_owner = {o.primary_key[0]: o.name for o in catalog.tables.values() if len(o.primary_key) == 1}
    out = []
    for col in t.columns:
        if col in fk_cols or col in t.primary_key:
            continue
        target = pk_owner.get(col)
        if target and target != t.name:
            out.append({"table": t.name, "column": col, "probably_references": target})
    return out


def run(ctx: PipelineContext) -> list[dict]:
    if ctx.catalog is None:
        raise RuntimeError("Stage 3 (schema extraction) must run first")
    cat = ctx.catalog
    result = []
    for t in cat.tables.values():
        kind, reason = _classify(t, cat)
        cands = undeclared_fk_candidates(t, cat)
        result.append({
            "table": t.name, "type": kind, "becomes": BECOMES[kind], "reason": reason,
            "primary_key": t.primary_key, "foreign_keys": [f"{','.join(fk.columns)} → {fk.ref_table}"
                                                           for fk in t.foreign_keys],
            "referenced_by": cat.referenced_by(t.name), "rows": t.row_estimate,
            "undeclared_fk": cands,
        })
    ctx.invalidate_from(4)
    ctx.table_analysis = result
    counts = {}
    for r in result:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    ctx.log(4, "Table types: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    for r in result:
        for c in r["undeclared_fk"]:
            ctx.log(4, f"{c['table']}.{c['column']} looks like a link to {c['probably_references']} "
                       "but has no declared FK", "warning")
    ctx.mark_done(4)
    return result


def relationship_candidates(catalog: SchemaCatalog, analysis: list[dict]) -> list[dict]:
    """Candidate edges implied by declared FKs, bridges and undeclared FK candidates."""
    kinds = {a["table"]: a["type"] for a in analysis}
    out = []
    for t in catalog.tables.values():
        if kinds.get(t.name) == "bridge":
            a, b = t.foreign_keys[0], t.foreign_keys[1]
            out.append({"from": a.ref_table, "to": b.ref_table, "via": t.name, "pattern": "M:N bridge",
                        "edge properties": [c for c in t.columns if c not in t.primary_key]})
            continue
        for fk in t.foreign_keys:
            pattern = "self reference" if fk.ref_table == t.name else "N:1 foreign key"
            out.append({"from": t.name, "to": fk.ref_table, "via": f"{t.name}.{','.join(fk.columns)}",
                        "pattern": pattern, "edge properties": []})
    for a in analysis:
        for c in a["undeclared_fk"]:
            out.append({"from": c["table"], "to": c["probably_references"], "via": f"{c['table']}.{c['column']}",
                        "pattern": "undeclared FK (verify in Stage 12)", "edge properties": []})
    return out
