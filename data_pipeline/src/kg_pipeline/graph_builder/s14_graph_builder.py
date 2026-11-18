"""Stage 14 - Build the knowledge graph in NetworkX (ontology-driven).

What : PASS 1 adds one node per clean record; PASS 2 adds one edge per relationship row.
Why  : this is where tables become a graph. Nodes first, because an edge needs both ends.
       Nothing here knows "Customer" or "PLACED": the loops read the approved ontology.
Graph: nx.MultiDiGraph
       * directed - relationships have a meaning direction (Customer PLACED Order)
       * multi    - several relationship types between the same pair are kept
       * edge key = relationship name -> re-loading a row is idempotent
Out  : ctx.graph, ctx.build_stats (+ dangling references added to the quarantine)
"""
from __future__ import annotations

from datetime import datetime, timezone

import networkx as nx

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.preprocessing.transform import CoercionError
from kg_pipeline.preprocessing.transform import canon_key
from kg_pipeline.preprocessing.transform import coerce


def run(ctx: PipelineContext) -> nx.MultiDiGraph:
    if ctx.clean is None or not ctx.is_done(13):
        raise RuntimeError("Stage 13 must run first")
    onto, source, clean = ctx.approved_ontology, ctx.extraction.staged, ctx.clean
    G = nx.MultiDiGraph()
    stats = {"classes": {}, "relationships": {}}
    quarantine = list(clean.quarantine)

    # PASS 1 - nodes
    for nid, attrs in clean.records.items():
        G.add_node(nid, **attrs)
    for name, s in clean.stats.items():
        stats["classes"][name] = {"rows": s["rows"], "created": s["nodes"], "merged": s["merged"],
                                  "quarantined": s["quarantined"]}
    ctx.log(14, f"Pass 1: {G.number_of_nodes()} nodes added")

    # PASS 2 - edges
    for rel in onto.relationships:
        if not rel.mapping:
            continue
        mp = rel.mapping
        st = stats["relationships"].setdefault(rel.key, dict(rows=0, created=0, duplicates=0, null_refs=0,
                                                             dangling=0, quarantined=0))
        table = ctx.catalog.table(mp.table)
        row_key_cols = table.primary_key or (mp.source_key_columns + mp.target_key_columns)
        prop_defs = {p.source_column: p for p in rel.properties}
        src_alias = clean.alias.get(rel.source_class, {})
        tgt_alias = clean.alias.get(rel.target_class, {})
        for batch in source.iter_batches(mp.table, mp.source_key_columns + mp.target_key_columns +
                                         mp.property_columns, row_key_cols):
            for row in batch:
                st["rows"] += 1
                s = canon_key(row[c] for c in mp.source_key_columns)
                t = canon_key(row[c] for c in mp.target_key_columns)
                if s is None or t is None:
                    st["null_refs"] += 1                    # optional link not set: no edge (correct)
                    continue
                u, v = src_alias.get(s), tgt_alias.get(t)
                if u is None or v is None:
                    st["dangling"] += 1
                    quarantine.append({"stage": "edge", "class": rel.key, "table": mp.table,
                                       "key": f"{'|'.join(s)} -> {'|'.join(t)}",
                                       "reason": "source node missing" if u is None else "target node missing"})
                    continue
                try:
                    props = {}
                    for c in mp.property_columns:
                        p = prop_defs.get(c)
                        val = coerce(row.get(c), p.data_type) if p else row.get(c)
                        if val is not None:
                            props[p.name if p else c] = val
                except CoercionError as e:
                    st["quarantined"] += 1
                    quarantine.append({"stage": "edge", "class": rel.key, "table": mp.table,
                                       "key": f"{'|'.join(s)} -> {'|'.join(t)}", "reason": str(e)})
                    continue
                key = rel.name if not rel.multi_edge else \
                    f"{rel.name}#{'|'.join(str(row[c]) for c in row_key_cols)}"
                if G.has_edge(u, v, key):                   # same pair again (e.g. after an entity merge)
                    G.edges[u, v, key]["weight"] += 1
                    st["duplicates"] += 1
                    continue
                G.add_edge(u, v, key=key, type=rel.name, weight=1, source_table=mp.table, **props)
                st["created"] += 1
        ctx.log(14, f"Pass 2: {rel.key}: {st['created']} edges"
                    + (f", {st['dangling']} dangling" if st["dangling"] else "")
                    + (f", {st['duplicates']} merged duplicates" if st["duplicates"] else ""))

    G.graph.update({"ontology_id": onto.ontology_id, "ontology_version": onto.version,
                    "namespace": onto.namespace, "built_at": datetime.now(timezone.utc).isoformat(),
                    "source": ctx.source_info.get("name", ""), "source_watermarks": ctx.extraction.watermarks,
                    "build_mode": ctx.extraction.mode})
    ctx.invalidate_from(14)
    ctx.graph = G
    ctx.build_stats = {**stats, "quarantine": quarantine}
    ctx.log(14, f"NetworkX MultiDiGraph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    ctx.mark_done(14)
    return G
