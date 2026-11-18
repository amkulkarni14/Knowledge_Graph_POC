"""Visual helpers shared by the UI: PyVis HTML for instance graphs, ontology schema
diagrams and table-relationship diagrams. The browser only ever receives a bounded
(sub)graph, never the full graph of a large build."""
from __future__ import annotations

import html
import json

import networkx as nx

PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756", "#72B7B2", "#EECA3B", "#FF9DA6",
           "#9D755D", "#BAB0AC"]
LABEL_FIELDS = ("full_name", "product_name", "org_name", "city", "name", "title")


def color_map(labels) -> dict[str, str]:
    return {lbl: PALETTE[i % len(PALETTE)] for i, lbl in enumerate(sorted(set(labels)))}


def node_caption(nid: str, d: dict) -> str:
    for f in LABEL_FIELDS:
        if d.get(f):
            return f"{d[f]}"
    return nid


def _network(height: str, directed: bool = True):
    from pyvis.network import Network
    net = Network(height=height, width="100%", directed=directed, cdn_resources="in_line", bgcolor="#FFFFFF")
    net.set_options(json.dumps({
        "physics": {"solver": "forceAtlas2Based", "stabilization": {"iterations": 150},
                    "forceAtlas2Based": {"gravitationalConstant": -60, "springLength": 110}},
        "interaction": {"hover": True, "navigationButtons": True, "tooltipDelay": 120},
        "edges": {"smooth": {"type": "dynamic"}, "font": {"size": 10, "align": "middle", "color": "#555"},
                  "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}}},
        "nodes": {"font": {"size": 13, "face": "Segoe UI"}, "borderWidth": 2},
    }))
    return net


def graph_html(G: nx.MultiDiGraph, height: str = "620px", hide: set[str] | None = None,
               highlight: set[str] | None = None) -> str:
    """Interactive picture of an instance (sub)graph. `hide` = attribute names not shown (PII)."""
    hide = hide or set()
    highlight = highlight or set()
    colors = color_map(d.get("label", "?") for _, d in G.nodes(data=True))
    net = _network(height)
    for n, d in G.nodes(data=True):
        # tooltips are rendered as HTML by vis-network: escape every source value
        props = "\n".join(html.escape(f"{k}: {v}") for k, v in d.items() if k not in hide and not k.startswith("_"))
        net.add_node(n, label=f"{node_caption(n, d)}\n{n}", title=props, color=colors.get(d.get("label"), "#999"),
                     shape="dot", size=26 if n in highlight else 16,
                     borderWidth=4 if n in highlight else 2)
    for u, v, k, d in G.edges(keys=True, data=True):
        extra = {x: y for x, y in d.items() if x not in ("type", "source_table")}
        net.add_edge(u, v, label=d.get("type", k), title="\n".join(html.escape(f"{x}: {y}") for x, y in extra.items()),
                     width=1 + min(d.get("weight", 1), 5) * 0.6)
    return net.generate_html(notebook=False)


def ontology_html(onto, height: str = "460px") -> str:
    """Class-level diagram: one node per class, one arrow per relationship type."""
    colors = color_map(c.name for c in onto.classes)
    net = _network(height)
    for c in onto.classes:
        attrs = "\n".join(f"{'*' if a.required else ' '} {a.name}: {a.data_type.value}"
                          + (" (PII)" if a.pii else "") for a in c.attributes)
        src = c.mapping.source_table if c.mapping else "unmapped"
        net.add_node(c.name, label=f"{c.name}\n[{src}]", title=html.escape(f"{c.name} ({c.origin.value})\n{attrs}"),
                     color=colors[c.name], shape="box", font={"color": "#FFFFFF", "size": 14})
    for r in onto.relationships:
        if r.source_class in colors and r.target_class in colors:
            net.add_edge(r.source_class, r.target_class, label=f"{r.name} ({r.cardinality.value})",
                         title=html.escape(f"{r.description}\norigin: {r.origin.value}"),
                         dashes=r.origin.value != "manual")
    return net.generate_html(notebook=False)


def schema_html(catalog, analysis: list[dict] | None = None, height: str = "460px") -> str:
    """Table-level diagram: declared FKs (solid) and undeclared FK candidates (dashed red)."""
    kinds = {a["table"]: a["type"] for a in analysis or []}
    kcolor = {"entity": "#4C78A8", "event": "#F58518", "bridge": "#54A24B", "lookup": "#B279A2", "log": "#999999"}
    net = _network(height)
    for t in catalog.tables.values():
        k = kinds.get(t.name, "entity")
        cols = "\n".join(c for c in t.columns)
        net.add_node(t.name, label=f"{t.name}\n({k})", title=html.escape(cols), shape="box",
                     color=kcolor.get(k, "#4C78A8"), font={"color": "#FFFFFF"})
    for t in catalog.tables.values():
        for fk in t.foreign_keys:
            net.add_edge(t.name, fk.ref_table, label=",".join(fk.columns))
    for a in analysis or []:
        for c in a["undeclared_fk"]:
            net.add_edge(c["table"], c["probably_references"], label=f"{c['column']} (no FK!)",
                         color="#E45756", dashes=True)
    return net.generate_html(notebook=False)


def ego(G: nx.MultiDiGraph, node: str, radius: int = 1) -> nx.MultiDiGraph:
    radius = max(1, min(radius, 3))
    keep = nx.ego_graph(G.to_undirected(as_view=True), node, radius=radius).nodes
    return G.subgraph(keep).copy()


def limit_graph(G: nx.MultiDiGraph, max_nodes: int = 300, labels: set[str] | None = None) -> nx.MultiDiGraph:
    nodes = [n for n, d in G.nodes(data=True) if not labels or d.get("label") in labels]
    if len(nodes) > max_nodes:
        nodes = sorted(nodes, key=lambda n: G.degree(n), reverse=True)[:max_nodes]
    return G.subgraph(nodes).copy()
