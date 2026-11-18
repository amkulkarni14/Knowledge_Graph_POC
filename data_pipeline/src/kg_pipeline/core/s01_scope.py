"""Stage 1 - Agree the goal and scope.

What : business questions, tables in scope, sensitive columns, users.
Why  : the questions decide which tables, columns and links matter; a frozen
       scope stops the graph growing into something nobody uses.
Out  : ScopeSheet (used by Stage 3 to filter tables and by Stage 6 for PII masking).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from kg_pipeline.core.context import PipelineContext


class ScopeSheet(BaseModel):
    project: str = "Retail Knowledge Graph"
    business_questions: list[str] = Field(default_factory=list)
    tables_in_scope: list[str] = Field(default_factory=list)      # empty = all tables in the schema
    sensitive_columns: list[str] = Field(default_factory=list)    # "table.column"
    users: list[str] = Field(default_factory=list)
    later_list: list[str] = Field(default_factory=list)


def default_scope() -> ScopeSheet:
    return ScopeSheet(
        business_questions=[
            "How is a customer connected to an organisation?",
            "Which products are bought together (customers who bought X also bought Y)?",
            "Which customers and products sit at the centre of the network?",
            "Which customers form natural groups?",
        ],
        tables_in_scope=[],
        sensitive_columns=[],
        users=["Data modeller", "Reviewer (domain owner)", "Business analyst"],
        later_list=["S3 / BigQuery sources", "Neo4j serving store", "GraphRAG / NL queries"],
    )


def scope_for_files(project: str, filenames: list[str]) -> ScopeSheet:
    """A neutral scope for a set of uploaded files (the default scope's questions are about the retail sample)."""
    return ScopeSheet(
        project=project,
        business_questions=["How are the records in these files connected to each other?",
                           "Which records sit at the centre of the network?",
                           "Which records are orphaned or duplicated?"],
        tables_in_scope=[], sensitive_columns=[],
        users=["Data modeller", "Reviewer (domain owner)", "Business analyst"],
        later_list=[f"Files: {', '.join(filenames)}"] if filenames else [])


def run(ctx: PipelineContext, scope: ScopeSheet) -> ScopeSheet:
    if not scope.business_questions:
        raise ValueError("at least one business question is required")
    ctx.invalidate_from(1)
    ctx.scope = scope
    ctx.log(1, f"Scope frozen: {len(scope.business_questions)} questions, "
               f"{len(scope.tables_in_scope) or 'all'} tables, {len(scope.sensitive_columns)} sensitive columns")
    ctx.mark_done(1)
    return scope
