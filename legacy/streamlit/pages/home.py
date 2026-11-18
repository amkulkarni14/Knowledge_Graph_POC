"""Overview: architecture, the 16 stages, and a one-click demo run."""
import streamlit as st

from components.bootstrap import get_ctx, reset_ctx
from components.layout import BY_NO, PAGE_FILES, STAGE_DOCS, flow_strip, run_stage, table
from kg_pipeline.config import SAMPLE_FILES_DIR
from kg_pipeline.core.context import PARTS
from kg_pipeline.core.context import STAGES
from kg_pipeline.pipeline import run_all
from kg_pipeline.preprocessing.connectors.csv_source import read_directory

ctx = get_ctx()

st.markdown(
    '<div class="kg-hero"><span class="kg-badge">PostgreSQL → Ontology → NetworkX → Graph store</span>'
    '<h1>🕸️ Enterprise Knowledge Graph Studio</h1>'
    '<p>Every stage of turning relational tables into a validated, versioned knowledge graph has its own '
    'screen: what it does, why it is needed, what goes in, what comes out, and what actually happened.</p></div>',
    unsafe_allow_html=True)

st.subheader("Target architecture")
st.graphviz_chart("""
digraph G {
  rankdir=LR; bgcolor="transparent"; node [shape=box style="rounded,filled" fontname="Segoe UI" fontsize=11 color="#9AA8B8"];
  edge [color="#5B6B7F" fontname="Segoe UI" fontsize=9];
  pg   [label="PostgreSQL\\n(read replica,\\nread-only role)\\nStages 1-3" fillcolor="#FFFFFF"];
  prep [label="Preprocessing\\nschema analysis · extraction\\nquality · cleaning · ER\\nStages 4, 11-13" fillcolor="#E6EEF8"];
  onto [label="Hybrid Ontology Studio\\nmanual + Groq AI\\nreview · validate · version\\nStages 5-10" fillcolor="#EEE7F6"];
  groq [label="Groq AI\\nsuggestions only\\n(strict JSON)" fillcolor="#FFF6D6"];
  repo [label="Ontology repository\\nversions · audit" shape=cylinder fillcolor="#DDF0F5"];
  build [label="NetworkX MultiDiGraph\\nontology-driven builder\\nStage 14" fillcolor="#E3F2E7"];
  val  [label="Graph validation gate\\nreconciliation · rules\\nStage 15" fillcolor="#FDECEC"];
  store [label="Graph store\\nJSON + GraphML snapshots\\nCURRENT pointer · (Neo4j)\\nStage 16" shape=cylinder fillcolor="#DDF0F5"];
  use  [label="Query & analytics\\n(next phase)" fillcolor="#FBE7D8" style="rounded,filled,dashed"];
  pg -> prep [label="read-only SQL"]; pg -> onto [label="schema metadata"];
  groq -> onto [label="suggestions"]; onto -> repo [label="approved"]; repo -> build [label="rules"];
  repo -> prep [label="DQ rules" style=dashed]; prep -> build [label="clean rows"];
  build -> val; val -> store [label="publish if valid"]; store -> use;
}""", width="stretch")

c1, c2 = st.columns([1.4, 1])
with c1:
    st.subheader("The 16 stages")
    for part, label in PARTS.items():
        st.markdown(f"**Part {part} · {label}**")
        for s in [s for s in STAGES if s["part"] == part]:
            done = "✅" if ctx.is_done(s["no"]) else "▫️"
            st.page_link(PAGE_FILES[s["no"]], label=f"{done} {s['no']}. {s['title']} — {STAGE_DOCS[s['no']]['output']}",
                         icon=s["icon"])
with c2:
    st.subheader("Quick run")
    st.write("Runs every stage on the built-in sample retail database with default decisions "
             "(the AI uses the recorded offline response). Open any stage afterwards to see its result, "
             "or re-run stages one by one with your own choices.")
    if st.button("▶ Run all 16 stages on sample data", type="primary", width="stretch"):
        reset_ctx()
        ctx = get_ctx()
        if run_stage(run_all, ctx, success="Pipeline finished") is not None:
            st.rerun()
    st.write("Or run every stage on the bundled **Customer 360 CSV files** (7 files: the ontology is drafted "
             "from the files by rules; no AI is needed).")
    if st.button("▶ Run all 16 stages on the Customer 360 CSV files", width="stretch"):
        reset_ctx()
        ctx = get_ctx()
        if run_stage(lambda: run_all(ctx, csv_files=read_directory(SAMPLE_FILES_DIR / "customer360"),
                                     project="Customer 360"), success="Pipeline finished") is not None:
            st.rerun()
    if st.button("↺ Reset session", width="stretch"):
        reset_ctx()
        st.rerun()
    st.markdown("**Two rhythms**")
    st.caption("Stages 1–10 run when the rulebook (ontology) is designed or changed. "
               "Stages 11–16 run on every graph build, for example nightly.")

if ctx.events:
    st.subheader("Progress")
    flow_strip(ctx)
    m = st.columns(4)
    m[0].metric("Stages completed", f"{len(ctx.completed)}/16")
    m[1].metric("Ontology", f"v{ctx.approved_ontology.version}" if ctx.approved_ontology else "-")
    m[2].metric("Nodes", ctx.graph.number_of_nodes() if ctx.graph is not None else "-")
    m[3].metric("Edges", ctx.graph.number_of_edges() if ctx.graph is not None else "-")
    with st.expander("Full activity log", expanded=False):
        table([{"time": e["time"], "stage": f"{e['stage']}. {BY_NO[e['stage']]['title']}", "level": e["level"],
                "message": e["message"]} for e in ctx.events])
