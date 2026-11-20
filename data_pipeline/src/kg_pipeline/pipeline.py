"""Run the workflow against an explicit CSV or PostgreSQL source."""
from __future__ import annotations

from typing import Sequence

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload
from kg_pipeline.core import s01_scope
from kg_pipeline.preprocessing import s02_connect
from kg_pipeline.metadata_extractor import s03_schema_extraction
from kg_pipeline.metadata_extractor import s04_schema_analysis
from kg_pipeline.ontology_compiler import s05_manual_ontology
from kg_pipeline.ontology_compiler import s06_ai_suggestions
from kg_pipeline.ontology_compiler import s07_review_approval
from kg_pipeline.ontology_compiler import s08_ontology_validation
from kg_pipeline.ontology_compiler import s09_ontology_repository
from kg_pipeline.graph_builder import s10_build_plan
from kg_pipeline.preprocessing import s11_extraction
from kg_pipeline.preprocessing import s12_data_quality
from kg_pipeline.preprocessing import s13_cleaning_er
from kg_pipeline.graph_builder import s14_graph_builder
from kg_pipeline.graph_builder import s15_graph_validation
from kg_pipeline.graph_builder.loaders import s16_graph_persistence


def run_all(ctx: PipelineContext, postgres: dict | None = None, use_groq: bool = False,
            author: str = "data.modeller", reviewer: str = "reviewer.lead",
            csv_files: Sequence[CsvUpload] | None = None, project: str | None = None) -> PipelineContext:
    if bool(csv_files) == bool(postgres):
        raise ValueError("Choose either CSV files or a PostgreSQL connection.")
    if csv_files:
        project = project or "Uploaded files"
        s02_connect.connect_csv(ctx, csv_files)
        scope = s01_scope.scope_for_source(project, [f.filename for f in csv_files])
    else:
        project = project or "PostgreSQL"
        s02_connect.connect_postgres(ctx, **postgres)
        scope = s01_scope.scope_for_source(project)
    s01_scope.run(ctx, scope)
    ctx.mark_done(2)
    s03_schema_extraction.run(ctx)
    s04_schema_analysis.run(ctx)

    draft = s05_manual_ontology.draft_from_schema(ctx, *s05_manual_ontology.default_ids(project), author=author)
    if not draft.ontology.classes:
        problems = [*(ctx.source_info.get("warnings") or []), *draft.notes]
        raise ValueError("Nothing can be built from this source: no table has a column that identifies its rows.\n"
                         + "\n".join(f"- {p}" for p in problems))
    s05_manual_ontology.run(ctx, draft.ontology)
    for note in draft.notes:
        ctx.log(5, note, "warning")
    if use_groq:
        items = s06_ai_suggestions.run(ctx, actor=author, use_groq=True, include_samples=True)
        decisions = {i.item_id: {"action": "approve" if i.status in ("valid", "needs_review") else "reject"}
                     for i in items if i.kind != "duplicate"}
    else:
        s06_ai_suggestions.skip(ctx)
        decisions = {}
    s07_review_approval.run(ctx, decisions, actor=author)
    if not s08_ontology_validation.run(ctx).ok:
        return ctx
    s09_ontology_repository.run(ctx, author=author, reviewer=reviewer)
    s10_build_plan.run(ctx)
    s11_extraction.run(ctx)
    s12_data_quality.run(ctx)
    if not ctx.is_done(12):
        return ctx
    s13_cleaning_er.run(ctx)
    s14_graph_builder.run(ctx)
    s15_graph_validation.run(ctx)
    s16_graph_persistence.run(ctx)
    return ctx
