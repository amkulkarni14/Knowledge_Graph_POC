import streamlit as st

from components.graph_view import show_html
from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from components import viz
from kg_pipeline.metadata_extractor import s04_schema_analysis as s4

ctx = stage_header(4)
if guard(ctx, 3):
    if st.button("Analyse tables", type="primary"):
        run_stage(s4.run, ctx, success="Tables classified")
    if ctx.table_analysis:
        a = ctx.table_analysis
        st.subheader("Table types and what they become")
        table([{k: r[k] for k in ("table", "type", "becomes", "reason", "rows")} |
               {"referenced by": r["referenced_by"], "undeclared FK": [c["column"] for c in r["undeclared_fk"]]}
               for r in a])
        c1, c2 = st.columns([1.3, 1])
        with c1:
            st.subheader("Table diagram")
            show_html(viz.schema_html(ctx.catalog, a, "440px"), 440)
            st.caption("Blue = entity · orange = event · green = bridge · purple = lookup · "
                       "red dashed = looks like a link but has NO declared foreign key.")
        with c2:
            st.subheader("Relationship candidates")
            table(s4.relationship_candidates(ctx.catalog, a), height=420)
        und = [c for r in a for c in r["undeclared_fk"]]
        if und:
            st.warning("Undeclared links found: "
                       + "; ".join(f"`{c['table']}.{c['column']}` → `{c['probably_references']}`" for c in und)
                       + ". Map them by hand in Stage 5; Stage 12 checks they really hold.")
activity(ctx, 4)
next_stage(4)
