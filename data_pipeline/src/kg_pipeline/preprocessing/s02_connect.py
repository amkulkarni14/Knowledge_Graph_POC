"""Connect to CSV files or PostgreSQL.

What : open a READ-ONLY connection (ideally to a read replica) with a statement timeout.
Why  : the pipeline must never change business data or slow down live applications.
Out  : ctx.source (a DataSource) + ctx.source_info (server, user, read-only flag).

Sources:
  * csv      - several uploaded CSV files; each file is a table, keys and links between the
               files are inferred (see kg/sources/csv_source.py). Held in memory only.
  * postgres - real database; credentials come from env/.env or the UI form and are
               never written to disk or logs.
"""
from __future__ import annotations

import os
from typing import Sequence

from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload
from kg_pipeline.preprocessing.connectors.csv_source import UploadLimits
from kg_pipeline.preprocessing.connectors.csv_source import build_csv_source


def env_defaults() -> dict:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "dbname": os.environ.get("PGDATABASE", ""),
        "user": os.environ.get("PGUSER", ""),
        "password": os.environ.get("PGPASSWORD", ""),
        "sslmode": os.environ.get("PGSSLMODE", "prefer"),
        "schemas": settings.pg_schemas,
    }


def _replace_source(ctx: PipelineContext, source) -> None:
    if ctx.source is not None:
        try:
            ctx.source.close()
        except Exception:      # noqa: BLE001 - closing an old pool must not block reconnecting
            pass
    ctx.invalidate_from(2)
    ctx.clear_results_from_schema()
    ctx.source_version += 1
    ctx.source = source


def connect_csv(ctx: PipelineContext, uploads: Sequence[CsvUpload], limits: UploadLimits | None = None) -> dict:
    """Connect to several CSV files at once. All files are checked before anything is replaced: if one is
    unusable the previous connection stays as it was and the error lists every problem."""
    src = build_csv_source(uploads, limits)              # raises CsvImportError (a ValueError) on any bad file
    _replace_source(ctx, src)
    ctx.source_info = {"mode": "csv", "name": src.name, "files": [r.as_row() for r in src.reports],
                       "links": [{"from": r.table, **spec} for r in src.reports for spec in r.link_specs],
                       "warnings": src.warnings, **src.ping()}
    ctx.log(2, f"Connected to {len(src.reports)} uploaded CSV file(s) as read-only in-memory tables "
               "(nothing is written to disk)")
    for r in src.reports:
        key = ", ".join(r.key) if r.key else "no key found"
        ctx.log(2, f"{r.filename} → {r.table}: {r.rows} rows, {r.columns} columns, key: {key}"
                   + (f", links: {'; '.join(r.links)}" if r.links else ""))
    for w in src.warnings:
        ctx.log(2, w, "warning")
    ctx.mark_done(2)
    return ctx.source_info


def connect_postgres(ctx: PipelineContext, host: str, port: int, dbname: str, user: str, password: str,
                     sslmode: str = "prefer", schemas: list[str] | None = None, hostaddr: str | None = None) -> dict:
    from kg_pipeline.preprocessing.connectors.postgres_source import PostgresSource

    src = PostgresSource(host=host, port=port, dbname=dbname, user=user, password=password,
                         sslmode=sslmode, schemas=schemas or ["public"], hostaddr=hostaddr)
    try:
        info = src.ping()
    except Exception:
        src.close()
        raise
    _replace_source(ctx, src)
    ctx.source_info = {"mode": "postgres", "name": src.name, "schemas": src.schemas, **info}
    if not info["read_only"]:
        ctx.log(2, "Session is not read-only by default; read-only is enforced per session", "warning")
    ctx.log(2, "Connected to the PostgreSQL source with a read-only session and statement timeout")
    ctx.mark_done(2)
    return ctx.source_info


def activate_source(ctx: PipelineContext, source, info: dict) -> dict:
    _replace_source(ctx, source)
    ctx.source_info = info
    if source is not None:
        ctx.mark_done(2)
    ctx.log(2, "Data source selection confirmed" if source is not None else "Data source disconnected")
    return info
