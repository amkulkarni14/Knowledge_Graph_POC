import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.graph_builder import s15_graph_validation as s15

ctx = stage_header(15)
if guard(ctx, 14):
    if st.button("Validate the graph", type="primary"):
        run_stage(s15.run, ctx)
    rep = ctx.graph_report
    if rep:
        if rep["ok"]:
            st.success("**PASSED** — every source row is accounted for and the graph follows the ontology. "
                       "It can be published in Stage 16.")
        else:
            st.error("**FAILED** — the graph will not become CURRENT; the previous good version stays in use.")
        m = st.columns(4)
        m[0].metric("Errors", len(rep["errors"]))
        m[1].metric("Warnings", len(rep["warnings"]))
        m[2].metric("Nodes / edges", f"{rep['nodes']} / {rep['edges']}")
        m[3].metric("Connected components", rep["components"])
        st.subheader("Checks")
        table(rep["checks"])
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Nodes by class")
            st.bar_chart(rep["nodes_by_class"], horizontal=True)
        with c2:
            st.subheader("Edges by type")
            st.bar_chart(rep["edges_by_type"], horizontal=True)
        for e in rep["errors"]:
            st.error(e)
        for w in rep["warnings"]:
            st.warning(w)
        st.subheader("Quarantine (rows and links that did not enter the graph)")
        table(ctx.build_stats["quarantine"])
activity(ctx, 15)
next_stage(15)
