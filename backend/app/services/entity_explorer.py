"""Read-only identity lookup and bounded traversal shared by both graph stores."""
from collections import deque
from itertools import chain
from time import monotonic

from fastapi.encoders import jsonable_encoder
from backend.app.exceptions.handlers import ApiError
from backend.app.services.graphs import hidden_properties
from backend.app.services.neo_graph import NODE_MATCH

MATCH_LIMIT = 20
TYPE_LIMIT = 250
NODE_LIMIT = 100
EDGE_LIMIT = 300

PUBLISHED_TYPES = NODE_MATCH + """
RETURN DISTINCT n.label AS label ORDER BY label LIMIT $limit
"""
PUBLISHED_SEARCH = NODE_MATCH + """
WHERE ($label = '' OR n.label = $label)
  AND (n.id = $term OR ($prefix AND n.id STARTS WITH $term) OR
       (n.source_key IS NOT NULL AND
        (n.id = n.label + ':' + $term OR ($prefix AND n.id STARTS WITH (n.label + ':' + $term)))))
RETURN n.id AS id, properties(n) AS properties ORDER BY n.id LIMIT $limit
"""
PUBLISHED_NODE = NODE_MATCH + """
WHERE n.id = $id
RETURN n.id AS id, properties(n) AS properties,
       COUNT { (m:KGEntity {projectId: $project, graphVersionId: $version})
               -[r {projectId: $project, graphVersionId: $version}]->(n) } AS incoming,
       COUNT { (n)-[r {projectId: $project, graphVersionId: $version}]->
               (m:KGEntity {projectId: $project, graphVersionId: $version}) } AS outgoing
"""
PUBLISHED_EDGES = NODE_MATCH + """
WHERE n.id IN $frontier
MATCH (n)-[r {projectId: $project, graphVersionId: $version}]-
      (m:KGEntity {projectId: $project, graphVersionId: $version})
WHERE NOT m.id IN $expanded
RETURN {id: m.id, properties: properties(m)} AS neighbor,
       {source: startNode(r).id, target: endNode(r).id, key: r.key,
        properties: r {.*, type: type(r)}} AS edge
LIMIT $limit
"""


def mapped_identity(node, properties):
    prefix = f"{properties.get('label')}:"
    if properties.get("source_key") is not None and node.startswith(prefix):
        return node[len(prefix):]
    return node


def identity_result(row):
    properties = row["properties"]
    return {"id": row["id"], "label": properties.get("label", ""),
            "identifier": mapped_identity(row["id"], properties),
            "display_name": next((str(properties[key]) for key in ("display_name", "name", "title")
                                  if properties.get(key)), row["id"])}


def ontology_types(metadata):
    return [item["name"] for item in metadata.get("classes", [])]


def property_filter(session, metadata):
    hidden = {key.casefold() for key in hidden_properties(session) | set(metadata.get("hidden_properties", ()))}

    def clean(properties):
        return jsonable_encoder({key: value for key, value in properties.items() if key.casefold() not in hidden})

    return clean


def search_result(rows, types=()):
    return {"types": list(types)[:TYPE_LIMIT],
            "matches": [identity_result(row) for row in rows[:MATCH_LIMIT]],
            "truncated": len(rows) > MATCH_LIMIT or len(types) > TYPE_LIMIT}


def local_search(graph, clean, term, label, prefix, metadata):
    deadline = monotonic() + 2
    if not term:
        labels = set(ontology_types(metadata))
        for _, props in graph.nodes(data=True):
            if monotonic() > deadline:
                raise ApiError(503, "entity_schema_timeout", "The graph schema could not be read in time.")
            if props.get("label"):
                labels.add(props["label"])
        return search_result([], sorted(labels))
    rows = []
    for node, props in graph.nodes(data=True):
        if monotonic() > deadline:
            raise ApiError(503, "entity_lookup_timeout", "Entity search took too long. Try a typed identifier.")
        if label and label != props.get("label"):
            continue
        keys = (str(node), mapped_identity(str(node), props))
        if not any(key == term or (prefix and key.startswith(term)) for key in keys):
            continue
        rows.append({"id": str(node), "properties": clean(props)})
        if len(rows) > MATCH_LIMIT:
            break
    return search_result(rows)


def local_node(graph, clean, node):
    if node not in graph:
        return None
    return {"id": node, "properties": clean(graph.nodes[node]),
            "incoming": graph.in_degree(node), "outgoing": graph.out_degree(node)}


def local_edges(graph, clean, frontier, expanded, limit):
    rows = []
    deadline = monotonic() + 2
    for node in frontier:
        for source, target, key, props in chain(graph.out_edges(node, keys=True, data=True),
                                                graph.in_edges(node, keys=True, data=True)):
            if monotonic() > deadline:
                raise ApiError(503, "entity_traversal_timeout", "Traversal took too long. Try a smaller depth.")
            neighbor = target if source == node else source
            if neighbor in expanded:
                continue
            rows.append({"neighbor": {"id": neighbor, "properties": clean(graph.nodes[neighbor])},
                         "edge": {"source": source, "target": target, "key": key, "properties": clean(props)}})
            if len(rows) == limit:
                return rows
    return rows


def neighborhood(root, hops, adjacent, metadata, *, node_count, edge_count):
    if root is None:
        raise ApiError(404, "node_not_found", "The entity does not exist in the selected graph")
    nodes = {root["id"]: {"id": root["id"], "properties": root["properties"]}}
    edges, expanded = {}, set()
    frontier = deque(nodes)
    truncated = False
    for _ in range(hops):
        if not frontier:
            break
        batch, frontier = list(frontier), deque()
        rows = adjacent(batch, list(expanded), EDGE_LIMIT + 1)
        truncated |= len(rows) > EDGE_LIMIT
        for row in rows[:EDGE_LIMIT]:
            neighbor, edge = row["neighbor"], row["edge"]
            key = (edge["source"], edge["target"], edge["key"])
            if key not in edges and len(edges) == EDGE_LIMIT:
                truncated = True
                continue
            if neighbor["id"] not in nodes:
                if len(nodes) == NODE_LIMIT:
                    truncated = True
                    continue
                nodes[neighbor["id"]] = neighbor
                frontier.append(neighbor["id"])
            edges[key] = edge
        expanded.update(batch)
    return {"root": {**root, "identifier": mapped_identity(root["id"], root["properties"])},
            "ontology": {key: value for key, value in metadata.items() if key != "hidden_properties"}
            if metadata else None,
            "graph": {"nodes": list(nodes.values()), "edges": list(edges.values()),
                      "truncated": truncated, "total_nodes": node_count, "total_edges": edge_count}}
