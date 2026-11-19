"""Version-scoped Neo4j writes and server-owned read statements."""
import json
import math
import os
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from itertools import batched
from uuid import UUID

from neo4j import GraphDatabase, Query, READ_ACCESS

from backend.app.exceptions.handlers import ApiError

_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,62}")
CONSTRAINT = """
CREATE CONSTRAINT kg_entity_version_identity IF NOT EXISTS
FOR (n:KGEntity) REQUIRE (n.projectId, n.graphVersionId, n.id) IS UNIQUE
"""
NODE_MATCH = "MATCH (n:KGEntity {projectId: $project, graphVersionId: $version})"
EDGE_MATCH = """
MATCH (a:KGEntity {projectId: $project, graphVersionId: $version})
      -[r {projectId: $project, graphVersionId: $version}]->
      (b:KGEntity {projectId: $project, graphVersionId: $version})
"""


def identifier(value):
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid graph identifier")
    return value


def properties(values, hidden):
    clean = {}
    for key, value in values.items():
        if value is None or key.casefold() in hidden:
            continue
        if isinstance(value, float) and not math.isfinite(value):
            clean[key] = str(value)
        elif isinstance(value, int) and not -(2 ** 63) <= value < 2 ** 63:
            clean[key] = str(value)
        elif isinstance(value, (date, datetime)):
            clean[key] = value.isoformat()
        elif isinstance(value, (Decimal, UUID)):
            clean[key] = str(value)
        else:
            clean[key] = value if isinstance(value, (str, bool, float, int)) else json.dumps(value, default=str)
    return clean


class NeoGraphStore:
    def __init__(self, read=False):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_READ_USER" if read else "NEO4J_USER")
        password = os.getenv("NEO4J_READ_PASSWORD" if read else "NEO4J_PASSWORD")
        if not all((uri, user, password)):
            raise ApiError(503, "neo4j_unconfigured", "The graph database identity is not configured")
        self.driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5,
                                           connection_acquisition_timeout=5, max_transaction_retry_time=10)
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.driver.close()

    def import_graph(self, graph, project, version, hidden, progress, batch_size=1000, *,
                     node_ids=None, edge_key=None):
        scope = {"project": str(project), "version": version}
        node_ids = node_ids or {}
        with self.driver.session(database=self.database) as session:
            session.run(Query(CONSTRAINT, timeout=15)).consume()
            for batch in batched(graph.nodes(data=True), batch_size):
                groups = defaultdict(list)
                for node, props in batch:
                    protected = hidden | {"source_key"} if node in node_ids else hidden
                    groups[identifier(props["label"])].append({
                        "id": node_ids.get(node, str(node)), "props": properties(props, protected),
                    })
                for label, rows in groups.items():
                    query = f"""
                    UNWIND $rows AS row
                    MERGE (n:KGEntity {{projectId: $project, graphVersionId: $version, id: row.id}})
                    SET n = row.props, n.projectId = $project, n.graphVersionId = $version, n.id = row.id
                    SET n:`{label}`
                    """
                    session.run(Query(query, timeout=30), rows=rows, **scope).consume()
                progress("nodes", len(batch))
            for batch in batched(graph.edges(keys=True, data=True), batch_size):
                groups = defaultdict(list)
                for source, target, key, props in batch:
                    groups[identifier(props["type"])].append({
                        "source": node_ids.get(source, str(source)), "target": node_ids.get(target, str(target)),
                        "key": edge_key(key, props) if edge_key else str(key),
                        "props": properties(props, hidden),
                    })
                for kind, rows in groups.items():
                    query = f"""
                    UNWIND $rows AS row
                    MATCH (a:KGEntity {{projectId: $project, graphVersionId: $version, id: row.source}})
                    MATCH (b:KGEntity {{projectId: $project, graphVersionId: $version, id: row.target}})
                    MERGE (a)-[r:`{kind}` {{projectId: $project, graphVersionId: $version, key: row.key}}]->(b)
                    SET r = row.props, r.projectId = $project, r.graphVersionId = $version, r.key = row.key
                    RETURN count(r) AS count
                    """
                    result = session.run(Query(query, timeout=30), rows=rows, **scope).single(strict=True)
                    if result["count"] != len(rows):
                        raise ValueError("Graph import did not resolve all endpoints")
                progress("relationships", len(batch))
            nodes = session.run(Query(NODE_MATCH + " RETURN count(n) AS count", timeout=30), **scope).single()
            edges = session.run(Query(EDGE_MATCH + " RETURN count(r) AS count", timeout=30), **scope).single()
            if (nodes["count"], edges["count"]) != (graph.number_of_nodes(), graph.number_of_edges()):
                raise ValueError("Persisted graph counts differ from validated graph")

    def read(self, statement, project, version, **parameters):
        return list(self.records(statement, project, version, **parameters))

    def records(self, statement, project, version, *, timeout=8, **parameters):
        with self.driver.session(database=self.database, default_access_mode=READ_ACCESS) as session:
            result = session.run(Query(statement, timeout=timeout), project=str(project), version=version, **parameters)
            for record in result:
                yield record.data()

    def schema_objects(self):
        with self.driver.session(database=self.database, default_access_mode=READ_ACCESS) as session:
            objects = {}
            for kind in ("INDEXES", "CONSTRAINTS"):
                statement = (f"SHOW {kind} YIELD name, type, labelsOrTypes, properties "
                             "WHERE 'KGEntity' IN labelsOrTypes RETURN name, type, labelsOrTypes, properties")
                objects[kind.lower()] = [record.data() for record in session.run(Query(statement, timeout=5))]
            return objects

    def delete_version(self, project, version):
        statement = Query(NODE_MATCH + " WITH n LIMIT 1000 DETACH DELETE n RETURN count(*) AS count", timeout=30)
        with self.driver.session(database=self.database) as session:
            while session.run(statement, project=str(project), version=version).single(strict=True)["count"]:
                pass
