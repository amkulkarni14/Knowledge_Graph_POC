from typing import Literal
from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
import networkx as nx
from kg_pipeline.graph_builder.loaders import s16_graph_persistence as persistence
from backend.app.core.dependencies import CurrentSession, CurrentUser
from backend.app.dto.models import Result, GraphView, Page, SnapshotRequest, Identifier, BuildId
from backend.app.dto.graph_questions import GraphAnswer, GraphQuestionRequest
from backend.app.exceptions.handlers import ApiError
from backend.app.services import graphs as service
from backend.app.services import entity_explorer as entities
from backend.app.services import graph_questions as questions
from backend.app.services.graph_intelligence import structural_insights
from backend.app.services.graph_exports import graphml_response
from backend.app.services.graphml_import import MAX_GRAPHML_BYTES, read_graphml, summarize
from backend.app.services.workflow import current_build_ontology, execute, operation, require

router = APIRouter(prefix="/sessions/{session_id}/graphs", tags=["graphs"])


@router.get("/entities", response_model=Result[dict])
def entity_search(session: CurrentSession, ontology_id: Identifier | None = None, build_id: BuildId | None = None,
                  q: str = Query("", max_length=300), label: str = Query("", max_length=63), prefix: bool = False):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        metadata = graph.graph.get("entity_ontology", {})
        return {"data": entities.local_search(graph, entities.property_filter(session, metadata),
                                              q.strip(), label, prefix, metadata)}


@router.get("/entity-neighborhood", response_model=Result[dict])
def entity_neighborhood(session: CurrentSession, node_id: str = Query(min_length=1, max_length=300),
                        ontology_id: Identifier | None = None, build_id: BuildId | None = None,
                        hops: int = Query(1, ge=0, le=3)):
    with operation(session):
        graph = service.select_graph(session, ontology_id, build_id)
        metadata = graph.graph.get("entity_ontology", {})
        clean = entities.property_filter(session, metadata)
        root = entities.local_node(graph, clean, node_id)
        return {"data": entities.neighborhood(
            root, hops, lambda batch, expanded, limit: entities.local_edges(graph, clean, batch, expanded, limit),
            metadata, node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges())}


@router.get("/questions/suggestions", response_model=Result[list[str]])
def question_suggestions(session: CurrentSession, ontology_id: Identifier | None = None, build_id: BuildId | None = None):
    with operation(session):
        return {"data": questions.followups(questions.graph_schema(session, service.select_graph(session, ontology_id, build_id)))}


@router.get("/questions/provider", response_model=Result[dict])
def question_provider(session: CurrentSession):
    return {"data": questions.availability()}


@router.post("/questions", response_model=Result[GraphAnswer])
def ask_graph(body: GraphQuestionRequest, session: CurrentSession):
    if not questions.SLOTS.acquire(blocking=False):
        raise ApiError(503, "graph_question_busy", "Graph AI is busy. Try again shortly.")
    try:
        with operation(session):
            graph = service.select_graph(session, body.ontology_id, body.build_id)
            schema = questions.graph_schema(session, graph, include_properties=body.ontology_id is None)
        # Preserve the default Groq transport and scope Ollama to this feature.
        name = questions.provider()
        notice = None
        complete = questions.ollama_provider.complete if name == "ollama" else questions.model_completion
        def rule_plan():
            return questions.plan_question(body, schema, lambda *_: questions.rules(body, schema))
        if name == "rules":
            plan = rule_plan()
        else:
            try:
                plan = questions.plan_question(body, schema, complete)
            except ApiError as error:
                if name != "ollama" or error.status < 500:
                    raise
                name = "rules"
                notice = error.message + " Using predefined graph questions."
                plan = rule_plan()
        with operation(session):
            if body.ontology_id is None and session.ctx.graph is not graph:
                raise ApiError(409, "graph_changed", "The workspace graph changed. Ask your question again.")
            result = questions.execute(graph, plan, schema)
        if name != "rules" and plan.operation not in {"path", "insights"}:
            result = questions.explain(result, complete)
        return {"data": {**result, "provider": name, "notice": notice}}
    finally:
        questions.SLOTS.release()


def graphml_upload(file, label_key, relationship_key):
    payload = file.file.read(MAX_GRAPHML_BYTES + 1)
    if len(payload) > MAX_GRAPHML_BYTES:
        raise ApiError(413, "graphml_too_large", "GraphML uploads are limited to 4 MiB")
    return payload, label_key, relationship_key


@router.post("/graphml/preview", response_model=Result[dict])
def preview_graphml(session: CurrentSession, file: UploadFile = File(),
                    label_key: str = Form("label", min_length=1, max_length=63),
                    relationship_key: str = Form("type", min_length=1, max_length=63)):
    payload, label_key, relationship_key = graphml_upload(file, label_key, relationship_key)
    with operation(session):
        ontology = current_build_ontology(session)
        graph = read_graphml(payload, ontology, label_key, relationship_key)
        return {"data": {"project": session.name, "ontology_validated": ontology is not None,
                         **summarize(graph)}}


@router.post("/graphml/publish", status_code=202, response_model=Result[dict])
def publish_graphml(session: CurrentSession, user: CurrentUser, request: Request, file: UploadFile = File(),
                    label_key: str = Form("label", min_length=1, max_length=63),
                    relationship_key: str = Form("type", min_length=1, max_length=63)):
    upload = graphml_upload(file, label_key, relationship_key)
    return {"data": request.app.state.builds.start_graphml(session, user.username, upload)}


@router.get("/intelligence", response_model=Result[dict])
def local_intelligence(session: CurrentSession, node_id: str = Query(min_length=1, max_length=300),
                       target_label: str = Query("", max_length=63)):
    with operation(session):
        graph = service.select_graph(session)
        view = service.graph_view(session, graph, limit=160, edge_limit=200, focus=node_id, hops=2)
        return {"data": structural_insights(view, node_id, target_label)}


@router.get("/graphml/neighborhood")
def local_neighborhood_graphml(session: CurrentSession, node_id: str = Query(min_length=1, max_length=300)):
    with operation(session):
        graph = service.select_graph(session)
        return graphml_response(service.graph_view(session, graph, limit=160, edge_limit=200, focus=node_id, hops=2))


@router.post("/snapshots", response_model=Result[dict],
             responses={202: {"model": Result[dict], "description": "Neo4j publication queued"}})
def save_snapshot(body: SnapshotRequest, session: CurrentSession, user: CurrentUser,
                  request: Request, response: Response):
    if body.load_neo4j:
        job = request.app.state.builds.start_publication(session, user.username)
        response.status_code = 202
        return {"data": job}
    with operation(session):
        require(session, 14)
        if session.ctx.graph_report is None:
            raise ApiError(409, "no_graph_validation", "Validate the graph before saving")
        result = execute(session, 16, persistence.run)
        session.recovered_snapshot = {"ontology_id": result["ontology_id"], "build_id": result["build_id"]}
        session.saved_graph_report = session.ctx.graph_report
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
        search_text = search.casefold()
        searchable = {"name", "title", "display_name"} - service.hidden_properties(session)
        matched = (n for n, props in graph.nodes(data=True) if (not label or props.get("label") == label)
                   and (search_text in str(n).casefold() or any(
                       isinstance(props.get(key), str) and search_text in props[key].casefold()
                       for key in searchable)))
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
