"""Stage 11 - Extract the data.

What : read ONLY the tables/columns in the build plan, in keyset batches.
Why  : small batches keep memory and database load flat; only-needed columns means
       less sensitive data in our system; the last key is a resume checkpoint.
Out  : ctx.extraction = ExtractionResult with a *staged source* (same interface as the
       real source) that Stages 12-14 read, plus per-table stats and watermarks.

The prototype stages extracted rows in memory so every later stage can be inspected
on screen. For tables in the tens of millions, stage to DuckDB/Parquet (the "Silver"
layer in the architecture) instead - the interface stays the same.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.preprocessing.connectors.sample_source import SampleSource


@dataclass
class ExtractionResult:
    staged: SampleSource
    tables: dict = field(default_factory=dict)       # table -> stats
    watermarks: dict = field(default_factory=dict)   # table -> max(watermark column) as ISO string
    mode: str = "full"

    @property
    def total_rows(self) -> int:
        return sum(t["rows"] for t in self.tables.values())


def run(ctx: PipelineContext, batch_size: int | None = None, progress=None) -> ExtractionResult:
    if ctx.build_plan is None:
        raise RuntimeError("Stage 10 must run first")
    batch_size = batch_size or settings.batch_size
    onto = ctx.approved_ontology
    wm_cols = {c.mapping.source_table: c.mapping.watermark_column for c in onto.classes
               if c.mapping and c.mapping.watermark_column}
    rows: dict[str, list[dict]] = {}
    stats: dict[str, dict] = {}
    watermarks: dict[str, str] = {}
    plan_tables = ctx.build_plan["tables"]
    for i, (table, cols) in enumerate(plan_tables.items(), start=1):
        info = ctx.catalog.tables[table]
        key_cols = info.primary_key or cols[:1]
        wm = wm_cols.get(table)
        read_cols = list(dict.fromkeys(cols + ([wm] if wm else [])))
        started, batches, last_key = time.perf_counter(), 0, None
        rows[table] = []
        for batch in ctx.source.iter_batches(table, read_cols, key_cols, batch_size):
            batches += 1
            rows[table].extend(batch)
            last_key = tuple(batch[-1][k] for k in key_cols)
            if progress:
                progress(i, len(plan_tables), table, len(rows[table]))
        if wm:
            vals = [r[wm] for r in rows[table] if r.get(wm) is not None]
            if vals:
                watermarks[table] = max(vals).isoformat() if hasattr(max(vals), "isoformat") else str(max(vals))
        stats[table] = {"rows": len(rows[table]), "batches": batches, "columns": len(read_cols),
                        "columns_read": ", ".join(read_cols), "key": ", ".join(key_cols),
                        "last_key (checkpoint)": str(last_key) if last_key else "-",
                        "watermark": watermarks.get(table, "-"),
                        "seconds": round(time.perf_counter() - started, 3)}
        ctx.log(11, f"{table}: {len(rows[table])} rows in {batches} batch(es) of up to {batch_size}")

    staged_catalog = ctx.catalog.model_copy(deep=True)
    result = ExtractionResult(staged=SampleSource(staged_catalog, rows), tables=stats, watermarks=watermarks)
    ctx.invalidate_from(11)
    ctx.extraction = result
    ctx.log(11, f"Extraction finished: {result.total_rows} rows from {len(stats)} tables (full read)")
    ctx.mark_done(11)
    return result
