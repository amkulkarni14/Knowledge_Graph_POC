import streamlit as st

from components.graph_view import show_ontology
from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.graph_builder import s10_build_plan as s10

ctx = stage_header(10)
if guard(ctx, 9):
    onto = ctx.approved_ontology
    st.caption(f"Plan for approved ontology `{onto.ontology_id}` v{onto.version} (approved by {onto.approved_by})")
    if st.button("Generate build plan", type="primary"):
        run_stage(s10.run, ctx, success="Build plan ready")
    plan = ctx.build_plan
    if plan:
        c = st.columns(3)
        c[0].metric("Node types", len(plan["nodes"]))
        c[1].metric("Edge types", len(plan["edges"]))
        c[2].metric("Tables to read", len(plan["tables"]))
        st.subheader("Nodes: where each node type comes from")
        table(plan["nodes"])
        st.subheader("Edges: which rows become edges")
        table(plan["edges"])
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.subheader("Columns that will be read")
            table([{"table": t, "columns": ", ".join(cols)} for t, cols in plan["tables"].items()])
            st.caption("Only these columns leave the database (Stage 11).")
        with c2:
            st.subheader("Target graph shape")
            show_ontology(onto, 360)
activity(ctx, 10)
next_stage(10)
