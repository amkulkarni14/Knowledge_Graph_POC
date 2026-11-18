"""Stage 3 - Read the database structure (schema extraction).

What : read tables, columns, types, PK, FK, unique constraints, row estimates
       from pg_catalog into a SchemaCatalog. No business data is read.
Why  : keys and links already describe most of the graph; the catalog feeds the
       ontology drop-downs, the AI prompt, validation and the SQL whitelist.
Out  : ctx.catalog (+ storage/catalog/catalog.json).
"""
from __future__ import annotations

from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.schema_models import SchemaCatalog


def run(ctx: PipelineContext) -> SchemaCatalog:
    if ctx.source is None:
        raise RuntimeError("Stage 2 (connect) must run first")
    catalog = ctx.source.introspect_schema()
    in_scope = set(ctx.scope.tables_in_scope) if ctx.scope and ctx.scope.tables_in_scope else None
    if in_scope:
        missing = sorted(in_scope - set(catalog.tables))
        if missing:
            ctx.log(3, f"Scope tables not found in the database: {missing}", "warning")
        catalog.tables = {k: v for k, v in catalog.tables.items() if k in in_scope}
        if not catalog.tables:
            raise ValueError("None of the tables in the Stage 1 scope exist in this source "
                             f"(source tables: {sorted(ctx.source.introspect_schema().tables)}). "
                             "Clear 'Tables in scope' in Stage 1 to use all tables, or fix the names.")

    ctx.invalidate_from(3)
    ctx.catalog = catalog
    settings.catalog_dir.mkdir(parents=True, exist_ok=True)
    (settings.catalog_dir / "catalog.json").write_text(catalog.model_dump_json(indent=2), encoding="utf-8")

    n_cols = sum(len(t.columns) for t in catalog.tables.values())
    n_fk = sum(len(t.foreign_keys) for t in catalog.tables.values())
    ctx.log(3, f"Schema catalog: {len(catalog.tables)} tables, {n_cols} columns, {n_fk} declared foreign keys")
    ctx.mark_done(3)
    return catalog


def catalog_rows(catalog: SchemaCatalog) -> list[dict]:
    """Flat table summary for display."""
    return [{"table": t.name, "columns": len(t.columns), "primary_key": ", ".join(t.primary_key) or "-",
             "foreign_keys": "; ".join(f"{','.join(fk.columns)} → {fk.ref_table}" for fk in t.foreign_keys) or "-",
             "rows (estimate)": t.row_estimate} for t in catalog.tables.values()]


def column_rows(catalog: SchemaCatalog, table: str) -> list[dict]:
    t = catalog.tables[table]
    fk_cols = {c: fk.ref_table for fk in t.foreign_keys for c in fk.columns}
    rows = [{"column": c.name, "pg_type": c.pg_type, "ontology type": c.data_type.value,
             "nullable": c.nullable, "PK": c.name in t.primary_key, "FK →": fk_cols.get(c.name, ""),
             "file header": c.source_header} for c in t.columns.values()]
    if not any(r["file header"] for r in rows):          # only uploaded files have original headers
        for r in rows:
            del r["file header"]
    return rows
