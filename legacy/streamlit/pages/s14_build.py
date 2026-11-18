import streamlit as st

from components.graph_view import show_graph
from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from components import viz
from kg_pipeline.graph_builder import s14_graph_builder as s14

ctx = stage_header(14)
if guard(ctx, 13):
    with st.expander("How table things become graph things", expanded=False):
        st.markdown("""
| PostgreSQL | Graph | Example |
|---|---|---|
| table of real things | node type (class) | customers → Customer |
| row | node | Priya Sharma → `Customer:2` |
| primary key | node id | customer_id 2 → `Customer:2` |
| column | node property | segment = Silver |
| foreign key | edge | orders.customer_id → Customer PLACED Order |
| link-table row | edge with properties | order_items → Order CONTAINS Product {quantity} |
| link to same table | edge between same class | referred_by → Customer REFERRED Customer |

Graph type: **`nx.MultiDiGraph`** (directed + several relationship types per pair; edge key = relationship name).
""")
    if st.button("Build the NetworkX graph", type="primary"):
        run_stage(s14.run, ctx, success="Graph built")

    G = ctx.graph
    if G is not None:
        m = st.columns(4)
        m[0].metric("Nodes", G.number_of_nodes())
        m[1].metric("Edges", G.number_of_edges())
        m[2].metric("Node types", len({d["label"] for _, d in G.nodes(data=True)}))
        m[3].metric("Dangling edges set aside", sum(s["dangling"] for s in ctx.build_stats["relationships"].values()))
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Pass 1 · nodes")
            table([{"class": k, **v} for k, v in ctx.build_stats["classes"].items()])
        with c2:
            st.subheader("Pass 2 · edges")
            table([{"relationship": k, **v} for k, v in ctx.build_stats["relationships"].items()])

        st.subheader("The graph")
        labels = sorted({d["label"] for _, d in G.nodes(data=True)})
        f1, f2, f3, f4 = st.columns([2, 1.4, 1, 1])
        show = set(f1.multiselect("Node types", labels, default=labels))
        focus = f2.selectbox("Focus on a node (ego view)", ["(whole graph)"] + sorted(G.nodes))
        radius = f3.slider("Hops", 1, 3, 2, disabled=focus == "(whole graph)")
        hide_pii = f4.toggle("Hide PII", value=True)
        pii = {a.name for c in ctx.approved_ontology.classes for a in c.attributes if a.pii} if hide_pii else set()
        sub = viz.ego(G, focus, radius) if focus != "(whole graph)" else G
        sub = viz.limit_graph(sub, 300, show)
        st.caption(f"Showing {sub.number_of_nodes()} nodes / {sub.number_of_edges()} edges "
                   "(the browser only gets a bounded subgraph). Hover for properties; drag to rearrange.")
        show_graph(sub, 600, hide=pii, highlight={focus})
        st.subheader("Inspect a node")
        n = st.selectbox("Node", sorted(G.nodes), key="inspect")
        c1, c2 = st.columns(2)
        c1.json({k: v for k, v in G.nodes[n].items() if k not in pii})
        c2.markdown("**Relationships**")
        rows = [{"direction": "→ out", "type": d["type"], "other node": v, "props":
                 {k: x for k, x in d.items() if k not in ("type", "source_table")}}
                for _, v, d in G.out_edges(n, data=True)]
        rows += [{"direction": "← in", "type": d["type"], "other node": u, "props":
                  {k: x for k, x in d.items() if k not in ("type", "source_table")}}
                 for u, _, d in G.in_edges(n, data=True)]
        with c2:
            table(rows)
activity(ctx, 14)
next_stage(14)
