import pandas as pd
import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.config import settings
from kg_pipeline.preprocessing import s11_extraction as s11

ctx = stage_header(11)
if guard(ctx, 10):
    c1, c2 = st.columns([1, 2])
    batch = c1.number_input("Batch size (rows per keyset page)", min_value=1, max_value=100_000,
                            value=min(settings.batch_size, 5000), step=1,
                            help="Try 4 on the sample data to watch several batches per table.")
    c2.code("SELECT <planned columns> FROM <table>\nWHERE (pk) > (:last_key)      -- keyset, not OFFSET\n"
            "ORDER BY pk LIMIT :batch_size", language="sql")
    if st.button("Extract data", type="primary"):
        bar = st.progress(0.0, text="starting")

        def progress(i, n, table_name, rows):
            bar.progress(i / n, text=f"{table_name}: {rows} rows")

        run_stage(s11.run, ctx, batch_size=int(batch), progress=progress, success="Extraction finished")
        bar.empty()

    ex = ctx.extraction
    if ex:
        m = st.columns(3)
        m[0].metric("Rows extracted", ex.total_rows)
        m[1].metric("Tables", len(ex.tables))
        m[2].metric("Batches", sum(t["batches"] for t in ex.tables.values()))
        st.subheader("Per table")
        table([{"table": t, **s} for t, s in ex.tables.items()])
        st.caption("`last_key` is the resume checkpoint; `watermark` is the starting point for the next "
                   "incremental run.")
        st.subheader("Staged rows (exactly what later stages see)")
        t = st.selectbox("Table", list(ex.staged.rows))
        st.dataframe(pd.DataFrame(ex.staged.rows[t]).astype(str), width="stretch", hide_index=True)
activity(ctx, 11)
next_stage(11)
