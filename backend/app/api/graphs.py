import os
from typing import Literal
from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
import networkx as nx
from kg_pipeline.graph_builder.loaders import s16_graph_persistence as persistence
from backend.app.core.dependencies import CurrentSession
from backend.app.dto.models import Result, GraphView, Page, SnapshotRequest, Identifier, BuildId
from backend.app.exceptions.handlers import ApiError
from backend.app.services import graphs as service
from backend.app.services.workflow import execute, operation, require

router = APIRouter(prefix="/sessions/{session_id}/graphs", tags=["graphs"])


@router.post("/snapshots", response_model=Result[dict])
def save_snapshot(body: SnapshotRequest, session: CurrentSession):
    with operation(session):
        require(session, 14)
        if session.ctx.graph_report is None:
            raise ApiError(409, "no_graph_validation", "Validate the graph before saving")
        neo = None
        if body.load_neo4j:
            uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
            if not all((uri, user, password)):
                raise ApiError(409, "neo4j_not_configured", "Neo4j is not configured on the server")
            neo = {"uri": uri, "user": user, "password": password}
        result = execute(session, 16, persistence.run, neo4j=neo)
        return {"data": {k: v for k, v in result.items() if k != "path"}}


@router.get("/snapshots", response_model=Result[list[dict]])
def snapshots(session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        service.checked_path(session, ontology_id)
        return {"data": persistence.list_builds(ontology_id, root=service.snapshot_root(session))}


@router.post("/snapshots/{build_id}/current", response_model=Result[dict])
def promote(build_id: BuildId, session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        service.load(session, ontology_id, build_id)
        try:
            persistence.set_current(ontology_id, build_id, root=service.snapshot_root(session))
        except ValueError:
            raise ApiError(409, "invalid_snapshot", "Only a valid snapshot can become current") from None
        return {"data": {"build_id": build_id, "current": True}}


@router.get("/snapshots/{build_id}/download/{artifact}")
def download(build_id: BuildId, artifact: Literal["graph.json.gz", "graph.graphml", "manifest.json", "quarantine.json"],
             session: CurrentSession, ontology_id: Identifier):
    with operation(session):
        service.load(session, ontology_id, build_id)
        path = service.checked_path(session, ontology_id, build_id, artifact)
        return FileResponse(path, media_type=service.ARTIFACTS[artifact], filename=artifact)


@router.get("/data", response_model=Result[GraphView])
def data(session: CurrentSession, ontology_id: Identifier | None = None, build_id: BuildId | None = None,
         limit: int = Query(300, ge=1, le=500), edge_limit: int = Query(1000, ge=1, le=2000),
         labels: list[str] | None = Query(None, max_length=100),
         focus: str | None = Query(None, min_length=1, max_length=300), hops: int = Query(1, ge=1, le=3)):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        return {"data": service.graph_view(session, graph, limit, edge_limit, labels, focus, hops)}


@router.get("/nodes", response_model=Result[Page[dict]])
def nodes(session: CurrentSession, ontology_id: Identifier | None = None, build_id: BuildId | None = None,
          search: str = Query("", max_length=200), label: str | None = Query(None, max_length=63),
          offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        matched = (n for n, props in graph.nodes(data=True) if (not label or props.get("label") == label)
                   and search.casefold() in str(n).casefold())
        total, items = 0, []
        for node in matched:
            if offset <= total < offset + limit:
                items.append({"id": str(node), "properties": service.node_properties(session, graph.nodes[node])})
            total += 1
        return {"data": {"items": items, "total": total, "offset": offset, "limit": limit}}


@router.get("/node", response_model=Result[dict])
def node(session: CurrentSession, node_id: str = Query(min_length=1, max_length=300),
         ontology_id: Identifier | None = None, build_id: BuildId | None = None,
         limit: int = Query(100, ge=1, le=500)):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        if node_id not in graph:
            raise ApiError(404, "node_not_found", "Node does not exist")
        from itertools import chain, islice
        edges = chain(graph.out_edges(node_id, keys=True, data=True), graph.in_edges(node_id, keys=True, data=True))
        items = [{"source": str(u), "target": str(v), "key": str(k),
                  "properties": service.node_properties(session, d)} for u, v, k, d in islice(edges, limit)]
        return {"data": {"id": node_id, "properties": service.node_properties(session, graph.nodes[node_id]),
                         "relationships": items, "limit": limit}}


@router.get("/path", response_model=Result[dict])
def path(session: CurrentSession, source: str = Query(min_length=1, max_length=300),
         target: str = Query(min_length=1, max_length=300),
         ontology_id: Identifier | None = None, build_id: BuildId | None = None,
         max_hops: int = Query(20, ge=1, le=100)):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        if source not in graph or target not in graph:
            raise ApiError(404, "node_not_found", "Path endpoints must exist")
        undirected = graph.to_undirected(as_view=True)
        # Use a depth cutoff; no enumeration of all simple paths.
        paths = nx.single_source_shortest_path(undirected, source, cutoff=max_hops)
        found = paths.get(target)
        return {"data": {"connected": found is not None, "nodes": found or [], "max_hops": max_hops}}


@router.get("/metrics", response_model=Result[dict])
def metrics(session: CurrentSession, ontology_id: Identifier | None = None, build_id: BuildId | None = None,
            limit: int = Query(15, ge=1, le=100)):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        simple = nx.Graph(graph.to_undirected())
        degree = nx.degree_centrality(simple)
        rows = [{"node": str(n), "class": graph.nodes[n].get("label"), "degree_centrality": score,
                 "links": simple.degree(n)} for n, score in sorted(degree.items(), key=lambda pair: -pair[1])[:limit]]
        return {"data": {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
                         "components": nx.number_connected_components(simple), "most_connected": rows}}
