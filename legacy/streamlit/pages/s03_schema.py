import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.metadata_extractor import s03_schema_extraction as s3

ctx = stage_header(3)
if guard(ctx, 1, 2):
    if st.button("Read database structure", type="primary"):
        run_stage(s3.run, ctx, success="Schema catalog created")
    with st.expander("SQL used (pg_catalog, no business data)"):
        from kg_pipeline.preprocessing.connectors.postgres_source import COLUMNS_SQL
        from kg_pipeline.preprocessing.connectors.postgres_source import CONSTRAINTS_SQL
        st.code(COLUMNS_SQL.strip() + "\n\n" + CONSTRAINTS_SQL.strip(), language="sql")

    cat = ctx.catalog
    if cat:
        c = st.columns(4)
        c[0].metric("Tables", len(cat.tables))
        c[1].metric("Columns", sum(len(t.columns) for t in cat.tables.values()))
        c[2].metric("Declared FKs", sum(len(t.foreign_keys) for t in cat.tables.values()))
        c[3].metric("Rows (estimate)", sum(t.row_estimate or 0 for t in cat.tables.values()))
        st.subheader("Tables")
        table(s3.catalog_rows(cat))
        st.subheader("Columns of a table")
        t = st.selectbox("Table", list(cat.tables))
        if t:
            table(s3.column_rows(cat, t))
        elif not cat.tables:
            st.warning("No tables found. Check that the connected user has access to the configured schemas.")
        st.caption("`ontology type` is how the column will be read into the graph (used by validation).")
activity(ctx, 3)
next_stage(3)
