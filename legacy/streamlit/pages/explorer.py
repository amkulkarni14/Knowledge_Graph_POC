"""Loads the CURRENT graph from the store (proves persistence) and lets users explore it."""
import networkx as nx
import streamlit as st

from components.graph_view import show_graph
from components.layout import table
from components import viz
from kg_pipeline.config import settings
from kg_pipeline.graph_builder.loaders import s16_graph_persistence as s16

st.markdown('<div class="kg-hero"><span class="kg-badge">Reads from the graph store, not from memory</span>'
            '<h1>🧭 Graph Store Explorer</h1><p>Loads a saved snapshot (checksum verified) and answers simple '
            'connection questions. Full analytics is the next phase.</p></div>', unsafe_allow_html=True)

root = settings.graph_store_dir
oids = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []
if not oids:
    st.info("No graph stored yet. Run Stage 16 (or the quick run on the home page).")
    st.stop()

c1, c2 = st.columns(2)
oid = c1.selectbox("Ontology", oids)
builds = s16.list_builds(oid)
if not builds:
    st.info("No builds for this ontology.")
    st.stop()
labels = [f"{b['build_id']}{'  (CURRENT)' if b['current'] else ''}" for b in builds]
choice = c2.selectbox("Build", labels)
build_id = choice.split()[0]


@st.cache_resource(show_spinner="Loading snapshot...")
def load(o: str, b: str) -> nx.MultiDiGraph:
    return s16.load_graph(o, b)


try:
    G = load(oid, build_id)
except Exception as e:  # noqa: BLE001
    st.error(f"{type(e).__name__}: {e}")
    st.stop()

m = st.columns(4)
m[0].metric("Nodes", G.number_of_nodes())
m[1].metric("Edges", G.number_of_edges())
m[2].metric("Ontology version", G.graph.get("ontology_version"))
m[3].metric("Built", str(G.graph.get("built_at", ""))[:16])

tab1, tab2, tab3 = st.tabs(["Neighbourhood", "Connection between two nodes", "Most connected"])
nodes = sorted(G.nodes)
with tab1:
    a, b = st.columns([2, 1])
    n = a.selectbox("Node", nodes)
    r = b.slider("Hops", 1, 3, 1)
    sub = viz.ego(G, n, r)
    show_graph(viz.limit_graph(sub, 300), 520, hide={"email", "phone"}, highlight={n})
with tab2:
    a, b = st.columns(2)
    x = a.selectbox("From", nodes, key="p_from")
    y = b.selectbox("To", nodes, index=min(len(nodes) - 1, 1), key="p_to")
    U = G.to_undirected(as_view=True)
    if nx.has_path(U, x, y):
        path = nx.shortest_path(U, x, y)
        hops = []
        for p, q in zip(path, path[1:]):
            d = G.get_edge_data(p, q) or G.get_edge_data(q, p)
            hops.append({"from": p, "relationship": ("→ " if G.has_edge(p, q) else "← ") + next(iter(d.values()))["type"],
                         "to": q})
        st.success(f"{len(path) - 1} hop(s)")
        table(hops)
        show_graph(G.subgraph(path).copy(), 360, hide={"email", "phone"}, highlight={x, y})
    else:
        st.warning("These nodes are not connected.")
with tab3:
    S = nx.Graph(G.to_undirected())
    deg = nx.degree_centrality(S)
    table([{"node": k, "class": G.nodes[k]["label"], "degree centrality": round(v, 3), "links": S.degree(k)}
           for k, v in sorted(deg.items(), key=lambda kv: -kv[1])[:15]])
