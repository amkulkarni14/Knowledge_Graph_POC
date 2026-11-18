"""Stage 10 - Confirm the build plan (PostgreSQL -> ontology mapping).

What : derive a readable plan from the APPROVED ontology: which table, key and
       columns feed each class; which table's rows become each relationship's edges.
Why  : everyone sees what will be read before it happens; the builder needs nothing
       else, so table names are never hard-coded in Python.
Out  : ctx.build_plan = {"nodes": [...], "edges": [...], "tables": {table: [columns]}}
"""
from __future__ import annotations

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import Ontology


def make_plan(onto: Ontology) -> dict:
    nodes, edges, tables = [], [], {}

    def need(table: str, cols):
        cur = tables.setdefault(table, [])
        for c in cols:
            if c and c not in cur:
                cur.append(c)

    for c in onto.classes:
        if not c.mapping:
            continue
        m = c.mapping
        cols = [a.source_column for a in c.attributes if a.source_column]
        need(m.source_table, m.key_columns + cols + m.resolution_columns +
             ([m.watermark_column] if m.watermark_column else []))
        nodes.append({
            "class": c.name, "table": m.source_table, "node id": f"{c.name}:<{'|'.join(m.key_columns)}>",
            "columns": ", ".join(cols), "merge duplicates by": ", ".join(m.resolution_columns) or "-",
            "incremental by": m.watermark_column or "full read",
            "rule": f"one node per row of {m.source_table}"
                    + (f", merged when {', '.join(m.resolution_columns)} match" if m.resolution_columns else ""),
        })
    for r in onto.relationships:
        if not r.mapping:
            continue
        mp = r.mapping
        need(mp.table, mp.source_key_columns + mp.target_key_columns + mp.property_columns)
        edges.append({
            "relationship": r.key, "cardinality": r.cardinality.value, "rows of": mp.table,
            "source key": ", ".join(mp.source_key_columns), "target key": ", ".join(mp.target_key_columns),
            "edge properties": ", ".join(mp.property_columns) or "-",
            "rule": f"one edge per row of {mp.table} whose source and target keys are both set",
            "acyclic": not r.allow_cycles,
        })
    return {"nodes": nodes, "edges": edges, "tables": tables}


def run(ctx: PipelineContext) -> dict:
    if ctx.approved_ontology is None:
        raise RuntimeError("Stage 9 must run first: only an APPROVED ontology can be built")
    plan = make_plan(ctx.approved_ontology)
    ctx.invalidate_from(10)
    ctx.build_plan = plan
    ctx.log(10, f"Build plan: {len(plan['nodes'])} node types and {len(plan['edges'])} edge types "
                f"from {len(plan['tables'])} tables")
    ctx.mark_done(10)
    return plan
