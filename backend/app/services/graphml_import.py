"""Parse bounded directed GraphML into an approved ontology's graph."""
import hashlib
import json
import math
from collections import Counter
from xml.etree import ElementTree as ET

import networkx as nx

from backend.app.exceptions.handlers import ApiError
from kg_pipeline.preprocessing.transform import coerce

MAX_GRAPHML_BYTES = 4 * 1024 * 1024
NS = "{http://graphml.graphdrawing.org/xmlns}"
RESERVED = {"projectId", "graphVersionId", "id", "source_key", "source_table"}


def invalid(message):
    return ApiError(422, "invalid_graphml", message)


def read_graphml(payload, ontology, label_key="label", relationship_key="type"):
    if len(payload) > MAX_GRAPHML_BYTES:
        raise ApiError(413, "graphml_too_large", "GraphML uploads are limited to 4 MiB")
    try:
        xml = payload.decode("utf-8-sig")
        if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
            raise ValueError("XML declarations for entities are prohibited")
        root = ET.fromstring(xml)
    except (UnicodeError, ValueError, ET.ParseError):
        raise invalid("Upload valid UTF-8 GraphML without DTDs or entities") from None
    if root.tag != NS + "graphml":
        raise invalid("Upload a GraphML document")
    graphs = root.findall(NS + "graph")
    if len(graphs) != 1 or graphs[0].get("edgedefault") != "directed":
        raise invalid("The file must contain one directed graph")
    document = graphs[0]
    if any(child.tag not in {NS + "node", NS + "edge", NS + "data", NS + "desc"} for child in document):
        raise invalid("Unsupported graph structure")
    nodes, edges = document.findall(NS + "node"), document.findall(NS + "edge")
    if len(nodes) > 10000 or len(edges) > 30000:
        raise invalid("The graph exceeds the import limits for nodes or relationships")
    keys = {}
    for field in root.findall(NS + "key"):
        identifier = field.get("id")
        name = field.get("attr.name")
        if identifier in keys or not identifier or not name:
            raise invalid("GraphML property keys must be unique and named")
        keys[identifier] = name

    def attrs(element, nested):
        values = {}
        record = None
        for child in element:
            if child.tag == NS + "desc":
                continue
            if child.tag != NS + "data" or list(child) or child.get("key") not in keys:
                raise invalid("Unsupported nested GraphML content or unknown property key")
            name = keys[child.get("key")]
            if name in values:
                raise invalid("GraphML contains duplicate attributes")
            values[name] = child.text or ""
            if name == "properties":
                try:
                    candidate = json.loads(values[name])
                except ValueError:
                    continue
                if isinstance(candidate, dict) and isinstance(candidate.get("properties"), dict) and nested in candidate:
                    record = candidate
        return (record["properties"] if record else values), record or {}

    def mapped(source, definitions):
        result = {}
        for item in definitions:
            if item.name in RESERVED:
                continue
            if item.name not in source or source[item.name] is None:
                if item.required:
                    raise invalid("An entity or relationship is missing a required ontology property")
                continue
            try:
                value = coerce(source[item.name], item.data_type)
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Non-finite numeric value")
                result[item.name] = value
            except (ValueError, TypeError, OverflowError):
                raise invalid("A GraphML value does not match its ontology property type") from None
        return result

    graph = nx.MultiDiGraph()
    classes = {cls.name: cls for cls in ontology.classes}
    relationships = {(rel.name, rel.source_class, rel.target_class): rel for rel in ontology.relationships}
    identifiers = {}
    for element in nodes:
        xml_id = element.get("id")
        source, record = attrs(element, "id")
        node_id = record.get("id", xml_id)
        label = source.get(label_key)
        if (not xml_id or xml_id in identifiers or not isinstance(node_id, str) or not node_id.strip()
                or len(node_id) > 300 or node_id in graph or not isinstance(label, str) or label not in classes):
            raise invalid("Node IDs must be unique and each node must have a known ontology label")
        attributes = mapped(source, classes[label].attributes)
        attributes["label"] = label
        graph.add_node(node_id, **attributes)
        identifiers[xml_id] = node_id

    edge_ids = set()
    relation_graphs = {}
    for index, element in enumerate(edges):
        start = identifiers.get(element.get("source"))
        end = identifiers.get(element.get("target"))
        identifier = element.get("id")
        if identifier in edge_ids or not start or not end or element.get("directed") in ("false", "0"):
            raise invalid("Relationship IDs must be unique and endpoints must exist")
        if identifier:
            edge_ids.add(identifier)
        source, record = attrs(element, "key")
        kind = source.get(relationship_key)
        if not isinstance(kind, str):
            raise invalid("Every relationship must have an ontology type")
        signature = (kind, graph.nodes[start]["label"], graph.nodes[end]["label"])
        relation = relationships.get(signature)
        key = record.get("key", source.get("_kg_edge_key", identifier if identifier is not None else f"edge-{index}"))
        if not relation or not isinstance(key, str) or not key or len(key) > 300 or graph.has_edge(start, end, key):
            raise invalid("Relationship conflicts with the approved ontology or duplicates an edge")
        attributes = mapped(source, relation.properties)
        attributes["type"] = kind
        graph.add_edge(start, end, key=key, **attributes)
        per_type = relation_graphs.setdefault(signature, nx.MultiDiGraph())
        if not relation.multi_edge and per_type.has_edge(start, end):
            raise invalid("An ontology relationship disallows parallel edges")
        per_type.add_edge(start, end)

    for signature, part in relation_graphs.items():
        relation = relationships[signature]
        if ((relation.cardinality.value in ("1:1", "N:1") and any(degree > 1 for _, degree in part.out_degree()))
                or (relation.cardinality.value in ("1:1", "1:N") and any(degree > 1 for _, degree in part.in_degree()))
                or (not relation.allow_cycles and not nx.is_directed_acyclic_graph(part))):
            raise invalid("A relationship violates ontology cardinality or cycle rules")
    graph.graph.update(ontology_id=ontology.ontology_id, ontology_version=ontology.version, import_origin="graphml",
                       import_digest=hashlib.sha256(payload).hexdigest())
    return graph


def summarize(graph):
    return {
        "nodes": graph.number_of_nodes(), "relationships": graph.number_of_edges(),
        "labels": dict(Counter(d["label"] for _, d in graph.nodes(data=True))),
        "types": dict(Counter(d["type"] for *_, d in graph.edges(data=True))),
    }
