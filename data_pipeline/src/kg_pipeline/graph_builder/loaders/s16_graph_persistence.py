"""Stage 16 - Store the graph (versioned graph store; optional Neo4j).

What : write each validated graph as an immutable snapshot
           storage/graphs/<ontology_id>/<build_id>/
               graph.json.gz    node-link JSON - primary format, language neutral, lossless
               graph.graphml    interchange (Gephi, yEd, Cytoscape, Neo4j APOC import)
               quarantine.json  rows that did not become nodes/edges, with reasons
               manifest.json    ontology version, counts, watermarks, validation, SHA-256 checksums
           storage/graphs/<ontology_id>/CURRENT  -> active build_id (moved ONLY if validation passed)
       Optionally push the same graph into Neo4j (phase-2 serving store).
Why  : a NetworkX graph lives only in process memory. Snapshots give restart, rollback,
       audit ("which graph produced this report?") and a base for incremental runs.
       Pickle is not used: it is version-specific and unsafe to load from untrusted files.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import networkx as nx

from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext

_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _graphml_safe(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """GraphML stores scalars only: lists/dicts become JSON strings, None is dropped."""
    H = G.copy()

    def fix(d):
        for k, v in list(d.items()):
            if v is None:
                del d[k]
            elif isinstance(v, (list, tuple, set, dict)):
                d[k] = json.dumps(sorted(v) if isinstance(v, set) else v, default=str)
    fix(H.graph)
    for _, d in H.nodes(data=True):
        fix(d)
    for *_, d in H.edges(data=True):
        fix(d)
    return H


def save_graph(G: nx.MultiDiGraph, validation: dict, quarantine: list, root: Path | None = None) -> dict:
    root = Path(root or settings.graph_store_dir)
    build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = root / G.graph["ontology_id"] / build_id
    out.mkdir(parents=True, exist_ok=True)

    with gzip.open(out / "graph.json.gz", "wt", encoding="utf-8") as f:
        json.dump(nx.node_link_data(G, edges="edges"), f, default=str)
    nx.write_graphml(_graphml_safe(G), out / "graph.graphml")
    (out / "quarantine.json").write_text(json.dumps(quarantine, indent=1, default=str), encoding="utf-8")

    manifest = {
        "build_id": build_id, "ontology_id": G.graph["ontology_id"],
        "ontology_version": G.graph["ontology_version"], "build_mode": G.graph.get("build_mode"),
        "built_at": G.graph.get("built_at"), "source": G.graph.get("source"),
        "source_watermarks": G.graph.get("source_watermarks", {}),
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "nodes_by_class": validation.get("nodes_by_class", {}), "edges_by_type": validation.get("edges_by_type", {}),
        "validation": {"ok": validation["ok"], "errors": len(validation["errors"]),
                       "warnings": len(validation["warnings"])},
        "quarantined": len(quarantine),
        "files": {p.name: _sha256(p) for p in sorted(out.iterdir())},
        "published": bool(validation["ok"]),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    if validation["ok"]:
        (root / G.graph["ontology_id"] / "CURRENT").write_text(build_id, encoding="utf-8")
    manifest["path"] = str(out)
    return manifest


def current_build(ontology_id: str, root: Path | None = None) -> Optional[str]:
    p = Path(root or settings.graph_store_dir) / ontology_id / "CURRENT"
    return p.read_text(encoding="utf-8").strip() if p.exists() else None


def list_builds(ontology_id: str, root: Path | None = None) -> list[dict]:
    base = Path(root or settings.graph_store_dir) / ontology_id
    if not base.exists():
        return []
    cur = current_build(ontology_id, root)
    rows = []
    for d in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        mf = d / "manifest.json"
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
            rows.append({"build_id": m["build_id"], "current": m["build_id"] == cur,
                         "ontology_version": m["ontology_version"], "nodes": m["nodes"], "edges": m["edges"],
                         "valid": m["validation"]["ok"], "quarantined": m.get("quarantined", 0),
                         "built_at": (m.get("built_at") or "")[:19]})
    return rows


def set_current(ontology_id: str, build_id: str, root: Path | None = None) -> None:
    """Rollback / promote: point CURRENT at an existing, valid snapshot."""
    base = Path(root or settings.graph_store_dir) / ontology_id
    m = json.loads((base / build_id / "manifest.json").read_text(encoding="utf-8"))
    if not m["validation"]["ok"]:
        raise ValueError("only a validated build can become CURRENT")
    (base / "CURRENT").write_text(build_id, encoding="utf-8")


def load_graph(ontology_id: str, build_id: str | None = None, root: Path | None = None) -> nx.MultiDiGraph:
    base = Path(root or settings.graph_store_dir) / ontology_id
    build_id = build_id or current_build(ontology_id, root)
    if not build_id:
        raise FileNotFoundError(f"no CURRENT build for {ontology_id}")
    manifest = json.loads((base / build_id / "manifest.json").read_text(encoding="utf-8"))
    path = base / build_id / "graph.json.gz"
    if _sha256(path) != manifest["files"]["graph.json.gz"]:
        raise ValueError(f"checksum mismatch for {path}")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, directed=True, multigraph=True, edges="edges")


def push_to_neo4j(G: nx.MultiDiGraph, uri: str, user: str, password: str, batch: int = 5000) -> dict:
    """Optional phase-2 store. Labels / relationship types come from the validated ontology
    (PascalCase / UPPER_SNAKE); they are re-checked here because Cypher cannot parameterise them."""
    from neo4j import GraphDatabase      # optional dependency: pip install neo4j

    def scalar(d):
        return {k: (json.dumps(v, default=str) if isinstance(v, (list, dict)) else v)
                for k, v in d.items() if v is not None}

    counts = {"nodes": 0, "edges": 0}
    with GraphDatabase.driver(uri, auth=(user, password)) as drv, drv.session() as s:
        for label in sorted({d["label"] for _, d in G.nodes(data=True)}):
            if not _LABEL_RE.match(label):
                raise ValueError(f"unsafe label {label!r}")
            s.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:`{label}`) REQUIRE n.id IS UNIQUE")
            rows = [{"id": n, "props": scalar(d)} for n, d in G.nodes(data=True) if d["label"] == label]
            for i in range(0, len(rows), batch):
                s.run(f"UNWIND $rows AS r MERGE (n:`{label}` {{id: r.id}}) SET n += r.props", rows=rows[i:i + batch])
            counts["nodes"] += len(rows)
        for rtype in sorted({d["type"] for *_, d in G.edges(data=True)}):
            if not _LABEL_RE.match(rtype):
                raise ValueError(f"unsafe relationship type {rtype!r}")
            rows = [{"u": u, "v": v, "k": k, "props": scalar(d)}
                    for u, v, k, d in G.edges(keys=True, data=True) if d["type"] == rtype]
            for i in range(0, len(rows), batch):
                s.run(f"UNWIND $rows AS r MATCH (a {{id: r.u}}), (b {{id: r.v}}) "
                      f"MERGE (a)-[e:`{rtype}` {{key: r.k}}]->(b) SET e += r.props", rows=rows[i:i + batch])
            counts["edges"] += len(rows)
    return counts


def run(ctx: PipelineContext, neo4j: dict | None = None) -> dict:
    if ctx.graph is None or ctx.graph_report is None:
        raise RuntimeError("Stages 14 and 15 must run first")
    manifest = save_graph(ctx.graph, ctx.graph_report, ctx.build_stats["quarantine"])
    if manifest["published"]:
        reloaded = load_graph(manifest["ontology_id"], manifest["build_id"])
        manifest["reload_check"] = (reloaded.number_of_nodes() == ctx.graph.number_of_nodes()
                                    and reloaded.number_of_edges() == ctx.graph.number_of_edges())
        ctx.log(16, f"Snapshot {manifest['build_id']} saved and marked CURRENT "
                    f"(reload check {'ok' if manifest['reload_check'] else 'FAILED'})")
    else:
        ctx.log(16, f"Snapshot {manifest['build_id']} saved for investigation but NOT published "
                    "(validation failed); previous CURRENT kept", "warning")
    if neo4j and manifest["published"]:
        manifest["neo4j"] = push_to_neo4j(ctx.graph, **neo4j)
        ctx.log(16, f"Pushed to Neo4j: {manifest['neo4j']}")
    ctx.snapshot = manifest
    ctx.mark_done(16)
    return manifest
