"""Authenticated operations on durable graph projects."""
import os
from time import perf_counter
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import StreamingResponse
from neo4j.exceptions import DriverError, Neo4jError
from psycopg.types.json import Jsonb
from pydantic import Field

from backend.app.core.dependencies import CurrentSession, CurrentUser
from backend.app.dto.models import BuildRequest, Result, StrictModel
from backend.app.exceptions.handlers import ApiError
from backend.app.repositories import graph_versions as registry
from backend.app.services import entity_explorer as entities
from backend.app.services.cypher_subset import compile_query
from backend.app.services.graph_exports import CONTENT_TYPES, graphml_response, stream_graph
from backend.app.services.graph_intelligence import draft_query, grounded_answer, structural_insights
from backend.app.services.neo_graph import EDGE_MATCH, NODE_MATCH, NeoGraphStore

router = APIRouter(tags=["graph versions"])
BASE = "/graph-projects/{project}"
TOOLS = BASE + "/versions/{version}"

NODE_SEARCH = NODE_MATCH + """
WHERE ($label = '' OR n.label = $label)
  AND ($search = '' OR toLower(n.id) CONTAINS toLower($search)
       OR any(key IN keys(n) WHERE (key IN ['name', 'title'] OR key ENDS WITH '_name')
              AND toLower(toString(n[key])) CONTAINS toLower($search)))
  AND ($property = '' OR toString(n[$property]) = $value)
RETURN n.id AS id, properties(n) AS properties ORDER BY n.id SKIP $offset LIMIT $limit
"""
NEIGHBORS = {
    hops: NODE_MATCH + f"""
    WHERE n.id = $id
    MATCH p = (n)-[*1..{hops}]-(m:KGEntity {{projectId: $project, graphVersionId: $version}})
    WHERE all(x IN nodes(p) WHERE x.projectId = $project AND x.graphVersionId = $version)
      AND all(r IN relationships(p) WHERE r.projectId = $project AND r.graphVersionId = $version
              AND ($kind = '' OR type(r) = $kind))
    RETURN [x IN nodes(p) | {{id: x.id, properties: properties(x)}}] AS nodes,
           [r IN relationships(p) | {{source: startNode(r).id, target: endNode(r).id,
                                     key: r.key, properties: properties(r)}}] AS edges
    LIMIT $limit
    """ for hops in (1, 2)
}
SHORTEST = NODE_MATCH + """
WHERE n.id = $source
MATCH (m:KGEntity {projectId: $project, graphVersionId: $version, id: $target})
WHERE n <> m
MATCH p = allShortestPaths((n)-[*1..12]-(m))
WHERE all(x IN nodes(p) WHERE x.projectId = $project AND x.graphVersionId = $version)
  AND all(r IN relationships(p) WHERE r.projectId = $project AND r.graphVersionId = $version)
RETURN [x IN nodes(p) | {id: x.id, properties: properties(x)}] AS nodes,
       [r IN relationships(p) | {source: startNode(r).id, target: endNode(r).id,
                                 key: r.key, properties: properties(r)}] AS edges
LIMIT $limit
"""
TEMPLATES = {
    "entities": NODE_SEARCH,
    "relationships": EDGE_MATCH + """
        WHERE ($kind = '' OR type(r) = $kind)
        RETURN {id: a.id, properties: properties(a)} AS source,
               {id: b.id, properties: properties(b)} AS target,
               r.key AS key, properties(r) AS properties LIMIT $limit
    """,
    "labels": NODE_MATCH + """
        UNWIND keys(n) AS property
        RETURN n.label AS label, collect(DISTINCT property) AS properties, count(DISTINCT n) AS count
        ORDER BY label LIMIT $limit
    """,
    "types": EDGE_MATCH + """
        UNWIND keys(r) AS property
        RETURN a.label AS source, type(r) AS type, b.label AS target,
               collect(DISTINCT property) AS properties, count(DISTINCT r) AS count
        ORDER BY source, type, target LIMIT $limit
    """,
}


class WorkspaceItem(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["query", "scene"]
    template: Literal["entities", "relationships", "labels", "types"] = "entities"
    search: str = Field(default="", max_length=200)
    label: str = Field(default="", max_length=63)
    relationship: str = Field(default="", max_length=63)
    focus: str = Field(default="", max_length=300)
    hops: int = Field(default=1, ge=1, le=2)
    layout: Literal["cose", "breadthfirst", "circle", "grid", "concentric"] = "cose"
    cypher: str = Field(default="", max_length=2000)
    property: str = Field(default="", max_length=63)
    value: str = Field(default="", max_length=200)


class CypherRequest(StrictModel):
    cypher: str = Field(min_length=1, max_length=2000)


class GraphQuestion(StrictModel):
    question: str = Field(min_length=1, max_length=1000)


class AnchoredQuestion(GraphQuestion):
    node_id: str = Field(min_length=1, max_length=300)


class MemberRequest(StrictModel):
    username: str = Field(min_length=1, max_length=100)


def read_graph(project, version, statement, **parameters):
    try:
        with NeoGraphStore(read=True) as store:
            return store.read(statement, project, version, **parameters)
    except (DriverError, Neo4jError):
        raise ApiError(502, "graph_read_failed", "The graph database could not complete the read") from None


def resolve(project, version, user):
    with registry.registry() as db:
        return registry.select_version(db, project, user.username, str(version))


@router.get(TOOLS + "/entities", response_model=Result[dict])
def entity_search(project: UUID, version: UUID, user: CurrentUser, q: str = Query("", max_length=300),
                  label: str = Query("", max_length=63), prefix: bool = False):
    version_row = resolve(project, version, user)
    term = q.strip()
    if not term:
        ontology = (version_row.get("validation") or {}).get("entity_ontology", {})
        observed = read_graph(project, str(version), entities.PUBLISHED_TYPES, limit=entities.TYPE_LIMIT + 1)
        types = sorted(set(entities.ontology_types(ontology)) | {row["label"] for row in observed if row["label"]})
        return {"data": entities.search_result([], types)}
    rows = read_graph(project, str(version), entities.PUBLISHED_SEARCH, label=label, term=term,
                      prefix=prefix, limit=entities.MATCH_LIMIT + 1)
    return {"data": entities.search_result(rows)}


@router.get(TOOLS + "/entity-neighborhood", response_model=Result[dict])
def entity_neighborhood(project: UUID, version: UUID, user: CurrentUser,
                        node_id: str = Query(min_length=1, max_length=300), hops: int = Query(1, ge=0, le=3)):
    row = resolve(project, version, user)
    def adjacent(batch, expanded, limit):
        return read_graph(project, str(version), entities.PUBLISHED_EDGES, frontier=batch,
                          expanded=expanded, limit=limit)
    nodes = read_graph(project, str(version), entities.PUBLISHED_NODE, id=node_id)
    return {"data": entities.neighborhood(
        nodes[0] if nodes else None, hops, adjacent, (row.get("validation") or {}).get("entity_ontology"),
        node_count=row["node_count"], edge_count=row["edge_count"])}


@router.get("/graph-projects", response_model=Result[list[dict]])
def projects(user: CurrentUser):
    with registry.registry() as db:
        return {"data": registry.list_projects(db, user.username)}


@router.get(BASE + "/versions", response_model=Result[dict])
def versions(project: UUID, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    with registry.registry() as db:
        return {"data": registry.list_versions(db, project, user.username, offset, limit)}


@router.get(BASE + "/members", response_model=Result[list[dict]])
def members(project: UUID, user: CurrentUser):
    with registry.registry() as db:
        registry.authorize(db, project, user.username, manage=True)
        return {"data": db.execute("""
            SELECT username, role FROM kg_meta.graph_project_member WHERE project_id = %s ORDER BY username
            """, (project,)).fetchall()}


@router.put(BASE + "/members", response_model=Result[dict])
def grant_viewer(project: UUID, user: CurrentUser, body: MemberRequest):
    with registry.registry() as db:
        registry.authorize(db, project, user.username, lock=True)
        registered = db.execute("SELECT username FROM kg_meta.app_user WHERE username = %s AND active",
                                (body.username,)).fetchone()
        if registered is None:
            raise ApiError(404, "user_not_found", "Active application user does not exist")
        db.execute("""
            INSERT INTO kg_meta.graph_project_member (project_id, username, role) VALUES (%s, %s, 'viewer')
            ON CONFLICT (project_id, username) DO NOTHING
            """, (project, body.username))
    return {"data": {"username": body.username, "role": "viewer"}}


@router.delete(BASE + "/members", response_model=Result[dict])
def revoke_viewer(project: UUID, user: CurrentUser, username: str = Query(min_length=1, max_length=100)):
    with registry.registry() as db:
        registry.authorize(db, project, user.username, lock=True)
        db.execute("DELETE FROM kg_meta.graph_project_member WHERE project_id = %s AND username = %s",
                   (project, username))
    return {"data": {"username": username}}


@router.put(TOOLS + "/current", response_model=Result[dict])
def restore(project: UUID, version: UUID, user: CurrentUser):
    with registry.registry() as db:
        registry.publish(db, project, str(version), user.username, restore=True)
    return {"data": {"current": version}}


def purge_version(project, version, actor):
    try:
        with registry.registry() as db:
            locked = db.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0)) AS acquired",
                                (version,)).fetchone()
            if not locked["acquired"]:
                return
            row = db.execute("""
                SELECT status FROM kg_meta.graph_build WHERE project_id = %s AND build_id = %s
                """, (project, version)).fetchone()
            if row is None or row["status"] != "deleting":
                return
            db.commit()
            deleted = False
            try:
                with NeoGraphStore() as store:
                    store.delete_version(project, version)
                deleted = True
            except (ApiError, DriverError, Neo4jError):
                pass
            registry.finish_delete(db, project, version, actor, deleted)
    except ApiError:
        # An interrupted purge remains eligible for another idempotent attempt.
        return


@router.delete(TOOLS, status_code=202, response_model=Result[dict])
def delete(project: UUID, version: UUID, user: CurrentUser, tasks: BackgroundTasks):
    try:
        days = max(0, int(os.getenv("KG_GRAPH_RETENTION_DAYS", "30")))
    except ValueError:
        raise ApiError(503, "retention_invalid", "Graph retention is misconfigured") from None
    with registry.registry() as db:
        registry.queue_delete(db, project, str(version), user.username, days)
    tasks.add_task(purge_version, project, str(version), user.username)
    return {"data": {"status": "deleting", "version": version}}


@router.get(TOOLS + "/analytics", response_model=Result[dict])
def analytics(project: UUID, version: UUID, user: CurrentUser):
    return {"data": resolve(project, version, user)["analytics"] or {}}


@router.get(TOOLS + "/communities/{index}", response_model=Result[dict])
def community(project: UUID, version: UUID, index: int, user: CurrentUser):
    metadata = resolve(project, version, user)
    groups = (metadata["analytics"] or {}).get("communities", [])
    if not 0 <= index < len(groups):
        raise ApiError(404, "community_not_found", "Community does not exist for this graph version")
    members = groups[index]["members"]
    nodes = read_graph(project, str(version), NODE_MATCH + """
        WHERE n.id IN $ids RETURN n.id AS id, properties(n) AS properties LIMIT 100
        """, ids=members)
    edges = read_graph(project, str(version), EDGE_MATCH + """
        WHERE a.id IN $ids AND b.id IN $ids
        RETURN a.id AS source, b.id AS target, r.key AS key, properties(r) AS properties LIMIT 251
        """, ids=members)
    return {"data": {"nodes": nodes, "edges": edges[:250], "total_nodes": metadata["node_count"],
                     "total_edges": metadata["edge_count"], "truncated": len(edges) > 250 or len(nodes) < groups[index]["size"]}}


@router.get(TOOLS + "/export/{format_name}")
def export(project: UUID, version: UUID, user: CurrentUser,
           format_name: Literal["json", "graphml", "nodes.csv", "relationships.csv"]):
    resolve(project, version, user)
    read_graph(project, str(version), "RETURN 1 AS ok")
    return StreamingResponse(stream_graph(project, str(version), format_name),
                             media_type=CONTENT_TYPES[format_name],
                             headers={"Content-Disposition": f'attachment; filename="graph-{version}.{format_name}"'})


@router.get(TOOLS + "/schema", response_model=Result[dict])
def schema(project: UUID, version: UUID, user: CurrentUser):
    resolve(project, version, user)
    result = {name: read_graph(project, str(version), TEMPLATES[name], limit=200) for name in ("labels", "types")}
    try:
        with NeoGraphStore(read=True) as store:
            result.update(store.schema_objects())
    except (DriverError, Neo4jError):
        result["schema_metadata"] = "Index and constraint metadata is unavailable to the read identity."
    return {"data": result}


@router.get(BASE + "/health", response_model=Result[dict])
def health(project: UUID, user: CurrentUser):
    with registry.registry() as db:
        entry = registry.authorize(db, project, user.username)
        events = db.execute("""
            SELECT build_id, action, actor, occurred_at FROM kg_meta.graph_version_event
            WHERE project_id = %s ORDER BY event_id DESC LIMIT 30
            """, (project,)).fetchall()
    status = "available"
    try:
        with NeoGraphStore(read=True) as store:
            store.read("RETURN 1 AS ok", project, entry["current_build_id"])
    except (ApiError, DriverError, Neo4jError):
        status = "unavailable"
    return {"data": {"metadata_postgresql": "available", "neo4j_read": status,
                     "current": entry["current_build_id"], "events": events}}


@router.get(TOOLS + "/compare", response_model=Result[dict])
def compare(project: UUID, version: UUID, baseline: UUID, user: CurrentUser):
    current = resolve(project, version, user)
    previous = resolve(project, baseline, user)
    nodes = read_graph(project, str(version), NODE_MATCH + """
        OPTIONAL MATCH (before:KGEntity {projectId: $project, graphVersionId: $baseline, id: n.id})
        WITH n, before, [key IN keys(n) WHERE key <> 'graphVersionId'] AS fields
        RETURN count(before) AS matched,
               sum(CASE WHEN before IS NOT NULL AND
                         (size(keys(n)) <> size(keys(before)) OR
                          any(key IN fields WHERE before[key] IS NULL OR n[key] <> before[key]))
                        THEN 1 ELSE 0 END) AS updated
        """, baseline=str(baseline))
    edges = read_graph(project, str(version), EDGE_MATCH + """
        OPTIONAL MATCH (:KGEntity {projectId: $project, graphVersionId: $baseline, id: a.id})
                       -[before {projectId: $project, graphVersionId: $baseline, key: r.key}]->
                       (:KGEntity {projectId: $project, graphVersionId: $baseline, id: b.id})
        WHERE type(before) = type(r)
        RETURN count(before) AS matched
        """, baseline=str(baseline))
    return {"data": {
        "previous_nodes": previous["node_count"], "current_nodes": current["node_count"],
        "added_nodes": current["node_count"] - nodes[0]["matched"],
        "removed_nodes": previous["node_count"] - nodes[0]["matched"],
        "updated_nodes": nodes[0]["updated"],
        "added_relationships": current["edge_count"] - edges[0]["matched"],
        "removed_relationships": previous["edge_count"] - edges[0]["matched"],
        "ontology_changed": any(current[key] != previous[key] for key in ("ontology_id", "ontology_version")),
        "source_changed": current["source_id"] != previous["source_id"],
        "current_duration_s": (current["finished_at"] - current["started_at"]).total_seconds(),
        "previous_duration_s": (previous["finished_at"] - previous["started_at"]).total_seconds(),
        "current_validation": current["validation"], "previous_validation": previous["validation"],
    }}


@router.get(TOOLS + "/query", response_model=Result[dict])
def query(project: UUID, version: UUID, user: CurrentUser,
          template: Literal["entities", "relationships", "labels", "types"],
          search: str = Query("", max_length=200), label: str = Query("", max_length=63),
          kind: str = Query("", max_length=63), offset: int = Query(0, ge=0, le=100000),
          property: str = Query("", max_length=63), value: str = Query("", max_length=200),
          limit: int = Query(50, ge=1, le=200), log_run: bool = False):
    resolve(project, version, user)
    started = perf_counter()
    rows = read_graph(project, str(version), TEMPLATES[template], search=search,
                      label=label, kind=kind, offset=offset, limit=limit, property=property, value=value)
    duration = round((perf_counter() - started) * 1000)
    if log_run:
        with registry.registry() as db:
            save_item(db, project, str(version), user.username, "query_run", str(uuid4()),
                      {"template": template, "duration_ms": duration, "row_count": len(rows)})
    return {"data": {"template": template, "rows": rows, "duration_ms": duration}}


@router.post(TOOLS + "/query", response_model=Result[dict])
def execute_cypher(project: UUID, version: UUID, user: CurrentUser, body: CypherRequest):
    resolve(project, version, user)
    compiled = compile_query(body.cypher)
    started = perf_counter()
    records = read_graph(project, str(version), compiled.statement, **compiled.parameters)
    duration = round((perf_counter() - started) * 1000)
    rows = [{column: row[f"value{index}"] for index, column in enumerate(compiled.columns)} for row in records]
    with registry.registry() as db:
        save_item(db, project, str(version), user.username, "query_run", str(uuid4()),
                  {"template": "cypher", "duration_ms": duration, "row_count": len(rows)})
    return {"data": {"template": "cypher", "rows": rows, "duration_ms": duration}}


def save_item(db, project, version, actor, kind, name, settings):
    db.execute("""
        INSERT INTO kg_meta.graph_workspace_item (project_id, build_id, actor, kind, name, settings)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (project_id, build_id, actor, kind, name)
        DO UPDATE SET settings = EXCLUDED.settings, updated_at = now()
        """, (project, version, actor, kind, name, Jsonb(settings)))


@router.put(TOOLS + "/workspace-items", response_model=Result[dict])
def store_item(project: UUID, version: UUID, user: CurrentUser, body: WorkspaceItem):
    if body.cypher:
        compile_query(body.cypher)
    with registry.registry() as db:
        registry.select_version(db, project, user.username, str(version))
        save_item(db, project, str(version), user.username, body.kind, body.name,
                  body.model_dump(exclude={"kind", "name"}))
    return {"data": {"name": body.name, "kind": body.kind}}


@router.get(TOOLS + "/workspace-items", response_model=Result[list[dict]])
def workspace_items(project: UUID, version: UUID, user: CurrentUser,
                    kind: Literal["query", "scene", "query_run"]):
    with registry.registry() as db:
        registry.select_version(db, project, user.username, str(version))
        rows = db.execute("""
            SELECT name, settings, updated_at FROM kg_meta.graph_workspace_item
            WHERE project_id = %s AND build_id = %s AND actor = %s AND kind = %s
            ORDER BY updated_at DESC, name LIMIT 50
            """, (project, str(version), user.username, kind)).fetchall()
    return {"data": rows}


@router.get(TOOLS + "/neighborhood", response_model=Result[dict])
def neighborhood(project: UUID, version: UUID, user: CurrentUser,
                 node_id: str = Query(min_length=1, max_length=300),
                 hops: int = Query(1, ge=1, le=2), kind: str = Query("", max_length=63),
                 limit: int = Query(50, ge=1, le=100)):
    metadata = resolve(project, version, user)
    root = read_graph(project, str(version), NODE_MATCH + """
        WHERE n.id = $id RETURN n.id AS id, properties(n) AS properties
        """, id=node_id)
    if not root:
        raise ApiError(404, "node_not_found", "The entity does not exist in this version")
    paths = read_graph(project, str(version), NEIGHBORS[hops], id=node_id, kind=kind, limit=limit + 1)
    return {"data": graph_view(metadata, paths, limit, root)}


def graph_view(metadata, paths, limit, root=()):
    nodes = {node["id"]: node for node in root}
    edges = {}
    for path in paths[:limit]:
        nodes.update((node["id"], node) for node in path["nodes"])
        edges.update(((edge["source"], edge["target"], edge["key"]), edge) for edge in path["edges"])
    return {"nodes": list(nodes.values()), "edges": list(edges.values()),
            "total_nodes": metadata["node_count"], "total_edges": metadata["edge_count"],
            "truncated": len(paths) > limit}


@router.post(TOOLS + "/query-draft", response_model=Result[dict])
def query_draft(project: UUID, version: UUID, user: CurrentUser, body: GraphQuestion):
    resolve(project, version, user)
    labels = read_graph(project, str(version), TEMPLATES["labels"], limit=60)
    types = read_graph(project, str(version), TEMPLATES["types"], limit=60)
    text = draft_query(body.question, {"labels": labels, "relationship_directions": types})
    return {"data": {"cypher": text, "requires_confirmation": True}}


@router.get(TOOLS + "/intelligence", response_model=Result[dict])
def intelligence(project: UUID, version: UUID, user: CurrentUser,
                 node_id: str = Query(min_length=1, max_length=300),
                 target_label: str = Query("", max_length=63)):
    view = neighborhood(project, version, user, node_id=node_id, hops=2, kind="", limit=100)["data"]
    return {"data": structural_insights(view, node_id, target_label)}


@router.get(TOOLS + "/graphml/neighborhood")
def neighborhood_graphml(project: UUID, version: UUID, user: CurrentUser,
                         node_id: str = Query(min_length=1, max_length=300)):
    view = neighborhood(project, version, user, node_id=node_id, hops=2, kind="", limit=100)["data"]
    return graphml_response(view)


def investigate(project, version, user, body, include_rankings=False):
    view = neighborhood(project, version, user, node_id=body.node_id, hops=2, kind="", limit=60)["data"]
    analysis = structural_insights(view, body.node_id) if include_rankings else None
    evidence_edges = view["edges"][:40]
    evidence = [{"source": edge["source"], "relationship": edge["properties"].get("type", "Relationship"),
                 "target": edge["target"]} for edge in evidence_edges]
    result = grounded_answer(body.question, evidence)
    by_id = {node["id"]: node["properties"] for node in view["nodes"]}
    for fact, edge in zip(result["evidence"], evidence_edges):
        fact["source_table"] = edge["properties"].get("source_table")
        fact["source_record"] = by_id.get(fact["source"], {}).get("source_key")
        fact["target_record"] = by_id.get(fact["target"], {}).get("source_key")
    result["graph"] = view
    if include_rankings:
        result["analysis"] = analysis
        result["trace"] = [
            {"tool": "explore_neighborhood", "status": "completed", "nodes": len(view["nodes"])},
            {"tool": "rank_structural_candidates", "status": "completed"},
            {"tool": "answer_from_graph_evidence", "status": "completed", "facts": len(evidence)},
        ]
        with registry.registry() as db:
            save_item(db, project, str(version), user.username, "query_run", str(uuid4()),
                      {"template": "graph_investigation", "steps": len(result["trace"]), "facts": len(evidence)})
    return {"data": result}


@router.post(TOOLS + "/graph-rag", response_model=Result[dict])
def graph_rag(project: UUID, version: UUID, user: CurrentUser, body: AnchoredQuestion):
    return investigate(project, version, user, body)


@router.post(TOOLS + "/investigate", response_model=Result[dict])
def investigation(project: UUID, version: UUID, user: CurrentUser, body: AnchoredQuestion):
    return investigate(project, version, user, body, include_rankings=True)


@router.get(TOOLS + "/paths", response_model=Result[dict])
def paths(project: UUID, version: UUID, user: CurrentUser,
          source: str = Query(min_length=1, max_length=300),
          target: str = Query(min_length=1, max_length=300),
          limit: int = Query(1, ge=1, le=10)):
    metadata = resolve(project, version, user)
    root = []
    matches = []
    if source == target:
        root = read_graph(project, str(version), NODE_MATCH + """
            WHERE n.id = $id RETURN n.id AS id, properties(n) AS properties
            """, id=source)
    else:
        matches = read_graph(project, str(version), SHORTEST,
                             source=source, target=target, limit=limit + 1)
    return {"data": graph_view(metadata, matches, limit, root)}


@router.post("/sessions/{session_id}/builds/published", status_code=202, response_model=Result[dict])
def reconcile(body: BuildRequest, session: CurrentSession, request: Request, user: CurrentUser):
    return {"data": request.app.state.builds.start(session, body, publish_as=user.username)}
