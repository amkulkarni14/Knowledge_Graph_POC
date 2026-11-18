import streamlit as st

from components.layout import activity, next_stage, run_stage, stage_header
from kg_pipeline.core import s01_scope

ctx = stage_header(1)
base = ctx.scope or s01_scope.default_scope()

# If catalog exists and scope has no tables, suggest all discovered tables
_catalog_tables = list(ctx.catalog.tables) if ctx.catalog else []
_default_tables = base.tables_in_scope or _catalog_tables

st.subheader("Scope sheet")
if _catalog_tables and not base.tables_in_scope:
    st.info(f"Catalog detected {len(_catalog_tables)} tables — pre-filled below. Clear to use all.")
with st.form("scope"):
    project = st.text_input("Project", base.project)
    c1, c2 = st.columns(2)
    questions = c1.text_area("Business questions (one per line)", "\n".join(base.business_questions), height=150)
    tables = c2.text_area("Tables in scope (schema.table, one per line; empty = all)",
                          "\n".join(_default_tables), height=150)
    c3, c4 = st.columns(2)
    sensitive = c3.text_area("Sensitive columns (schema.table.column) — never sent to the AI",
                             "\n".join(base.sensitive_columns), height=110)
    users = c4.text_area("Users of the result", "\n".join(base.users), height=110)
    later = st.text_input("Later list (not in this version)", ", ".join(base.later_list))
    submitted = st.form_submit_button("Freeze scope", type="primary")


def lines(s: str) -> list[str]:
    return [x.strip() for x in s.splitlines() if x.strip()]


if submitted:
    scope = s01_scope.ScopeSheet(project=project, business_questions=lines(questions), tables_in_scope=lines(tables),
                                 sensitive_columns=lines(sensitive), users=lines(users),
                                 later_list=[x.strip() for x in later.split(",") if x.strip()])
    run_stage(s01_scope.run, ctx, scope, success="Scope frozen")

if ctx.scope:
    st.subheader("Result")
    c = st.columns(3)
    c[0].metric("Business questions", len(ctx.scope.business_questions))
    c[1].metric("Tables in scope", len(ctx.scope.tables_in_scope) or "all")
    c[2].metric("Sensitive columns", len(ctx.scope.sensitive_columns))
    st.json(ctx.scope.model_dump(), expanded=False)
activity(ctx, 1)
next_stage(1)
