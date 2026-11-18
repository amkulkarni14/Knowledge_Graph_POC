import os

import streamlit as st

from components.layout import activity, guard, run_stage, stage_header, table
from kg_pipeline.config import settings
from kg_pipeline.graph_builder.loaders import s16_graph_persistence as s16

ctx = stage_header(16)
if guard(ctx, 14) and ctx.graph_report is None:
    st.warning("Run Stage 15 (graph validation) first: its result decides whether the build is published.")
elif ctx.is_done(14):
    st.markdown("Snapshot layout: `storage/graphs/<ontology>/<build_id>/` → `graph.json.gz` (primary), "
                "`graph.graphml` (Gephi / yEd / Neo4j import), `quarantine.json`, `manifest.json` (checksums); "
                "`CURRENT` points at the active build.")
    neo = None
    with st.expander("Optional: also load into Neo4j (phase-2 graph database)"):
        use_neo = st.checkbox("Push to Neo4j after saving")
        c1, c2, c3 = st.columns(3)
        uri = c1.text_input("URI", os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
        user = c2.text_input("User", os.environ.get("NEO4J_USER", "neo4j"))
        pwd = c3.text_input("Password", os.environ.get("NEO4J_PASSWORD", ""), type="password")
        st.caption("Needs `pip install neo4j`. Uses MERGE, so re-loading the same snapshot is idempotent.")
        if use_neo:
            neo = {"uri": uri, "user": user, "password": pwd}
    if st.button("💾 Save graph version", type="primary"):
        run_stage(s16.run, ctx, neo4j=neo, success="Graph stored")

    snap = ctx.snapshot
    if snap:
        (st.success if snap["published"] else st.warning)(
            f"Build **{snap['build_id']}** " + ("saved and marked **CURRENT**" if snap["published"]
                                                else "saved but NOT published (validation failed)"))
        m = st.columns(4)
        m[0].metric("Nodes", snap["nodes"])
        m[1].metric("Edges", snap["edges"])
        m[2].metric("Ontology version", snap["ontology_version"])
        m[3].metric("Reload check", "✅ identical" if snap.get("reload_check") else "-")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Manifest")
            st.json({k: v for k, v in snap.items() if k != "path"}, expanded=False)
        with c2:
            st.subheader("Downloads")
            from pathlib import Path
            p = Path(snap["path"])
            for f, mime in (("graph.json.gz", "application/gzip"), ("graph.graphml", "application/xml"),
                            ("manifest.json", "application/json"), ("quarantine.json", "application/json")):
                st.download_button(f"⬇ {f}", (p / f).read_bytes(), file_name=f, mime=mime, key=f"dl_{f}")
            st.caption(f"Location: `{p}`")

oid = ctx.approved_ontology.ontology_id if ctx.approved_ontology else None
if oid:
    builds = s16.list_builds(oid)
    if builds:
        st.subheader("Graph versions in the store")
        table(builds)
        valid = [b["build_id"] for b in builds if b["valid"] and not b["current"]]
        if valid:
            c1, c2 = st.columns([2, 1])
            target = c1.selectbox("Roll back / promote CURRENT to", valid)
            if c2.button("Set as CURRENT"):
                run_stage(s16.set_current, oid, target, success=f"CURRENT -> {target}")
                st.rerun()
st.caption(f"Graph store root: `{settings.graph_store_dir}`")
activity(ctx, 16)
st.page_link("pages/explorer.py", label="Open the Graph Store Explorer →", icon="🧭")
