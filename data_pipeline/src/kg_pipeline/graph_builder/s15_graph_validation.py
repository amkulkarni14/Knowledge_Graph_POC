"""Stage 15 - Check the graph before anyone can use it.

Reconciliation (proves nothing was lost silently):
    per class        : source rows = nodes + merged + quarantined
    per relationship : rows read   = edges created + duplicates + null refs + dangling + quarantined
Ontology conformance: known classes, required attributes, allowed (type, source, target)
triples, cardinality, forbidden cycles. Isolated nodes are listed for review.
Out : ctx.graph_report {ok, errors, warnings, checks[], nodes_by_class, edges_by_type}
"""
from __future__ import annotations

from collections import Counter

import networkx as nx

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import Cardinality


def validate_graph(G: nx.MultiDiGraph, onto, source, stats: dict) -> dict:
    errors, warnings, checks = [], [], []
    labels = Counter(d.get("label") for _, d in G.nodes(data=True))
    classes = {c.name: c for c in onto.classes}

    def check(name: str, passed: bool, detail: str):
        checks.append({"check": name, "result": "✅ pass" if passed else "❌ fail", "detail": detail})

    for cls in onto.classes:
        if not cls.mapping:
            continue
        s = stats["classes"].get(cls.name, {})
        src_rows = source.count(cls.mapping.source_table)
        nodes, merged, quar = labels.get(cls.name, 0), s.get("merged", 0), s.get("quarantined", 0)
        ok = src_rows == nodes + merged + quar
        check(f"Node reconciliation: {cls.name}", ok,
              f"{src_rows} source rows = {nodes} nodes + {merged} merged + {quar} quarantined")
        if not ok:
            errors.append(f"{cls.name}: source={src_rows} but nodes+merged+quarantined={nodes + merged + quar}")

    for name, s in stats["relationships"].items():
        accounted = s["created"] + s["duplicates"] + s["null_refs"] + s["dangling"] + s["quarantined"]
        ok = accounted == s["rows"]
        check(f"Edge reconciliation: {name}", ok,
              f"{s['rows']} rows = {s['created']} edges + {s['duplicates']} duplicates + {s['null_refs']} empty "
              f"+ {s['dangling']} dangling + {s['quarantined']} quarantined")
        if not ok:
            errors.append(f"{name}: rows={s['rows']} but accounted={accounted}")
        if s["dangling"]:
            warnings.append(f"{name}: {s['dangling']} reference(s) to missing nodes were quarantined")

    bad_nodes = []
    for nid, d in G.nodes(data=True):
        cls = classes.get(d.get("label"))
        if cls is None:
            bad_nodes.append(f"{nid}: unknown class {d.get('label')}")
            continue
        missing = [a.name for a in cls.attributes if a.required and a.name not in d]
        if missing:
            bad_nodes.append(f"{nid}: missing required attributes {missing}")
    check("Every node has a known class and its required attributes", not bad_nodes,
          f"{len(bad_nodes)} problem(s)" if bad_nodes else f"{G.number_of_nodes()} nodes checked")
    errors.extend(bad_nodes)

    allowed = {(r.name, r.source_class, r.target_class) for r in onto.relationships}
    bad_edges = [f"invalid edge {u}-[{d.get('type')}]->{v}" for u, v, d in G.edges(data=True)
                 if (d.get("type"), G.nodes[u]["label"], G.nodes[v]["label"]) not in allowed]
    check("Every edge type is allowed between its classes", not bad_edges,
          f"{len(bad_edges)} invalid" if bad_edges else f"{G.number_of_edges()} edges checked")
    errors.extend(bad_edges)

    for r in onto.relationships:
        sub = [(u, v) for u, v, d in G.edges(data=True) if d["type"] == r.name
               and G.nodes[u]["label"] == r.source_class and G.nodes[v]["label"] == r.target_class]
        out_deg, in_deg = Counter(u for u, _ in sub), Counter(v for _, v in sub)
        problems = []
        if r.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
            bad = [n for n, c in out_deg.items() if c > 1]
            if bad:
                problems.append(f"{len(bad)} source node(s) have >1 edge")
        if r.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.ONE_TO_MANY):
            bad = [n for n, c in in_deg.items() if c > 1]
            if bad:
                problems.append(f"{len(bad)} target node(s) have >1 edge")
        check(f"Cardinality {r.cardinality.value}: {r.key}", not problems, "; ".join(problems) or "holds")
        errors.extend(f"{r.name}: {p} but cardinality is {r.cardinality.value}" for p in problems)
        if not r.allow_cycles:
            H = nx.DiGraph(sub)
            acyclic = nx.is_directed_acyclic_graph(H)
            check(f"No cycles: {r.key}", acyclic, "acyclic" if acyclic else f"cycle {nx.find_cycle(H)}")
            if not acyclic:
                errors.append(f"{r.name}: cycle found {nx.find_cycle(H)}")

    orphans = list(nx.isolates(G))
    check("Isolated nodes (review only)", True, f"{len(orphans)} isolated: {orphans[:10]}" if orphans else "none")
    if orphans:
        warnings.append(f"{len(orphans)} isolated node(s): {orphans[:10]}")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "checks": checks,
            "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
            "nodes_by_class": dict(labels),
            "edges_by_type": dict(Counter(d["type"] for _, _, d in G.edges(data=True))),
            "components": nx.number_weakly_connected_components(G) if G.number_of_nodes() else 0}


def run(ctx: PipelineContext) -> dict:
    if ctx.graph is None or not ctx.is_done(14):
        raise RuntimeError("Stage 14 must run first")
    report = validate_graph(ctx.graph, ctx.approved_ontology, ctx.extraction.staged, ctx.build_stats)
    ctx.invalidate_from(15)
    ctx.graph_report = report
    ctx.log(15, f"Graph validation {'PASSED' if report['ok'] else 'FAILED'}: {len(report['errors'])} error(s), "
                f"{len(report['warnings'])} warning(s)", "info" if report["ok"] else "error")
    if report["ok"]:
        ctx.mark_done(15)
    return report
