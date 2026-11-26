from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import networkx as nx
import pytest

from backend.app.exceptions.handlers import ApiError
from backend.app.repositories.graph_versions import authorize
from backend.app.services import graph_publication
from backend.app.services.cypher_subset import compile_query
from backend.app.services.neo_graph import properties
from kg_pipeline.core.context import PipelineContext


@pytest.fixture
def session():
    graph = nx.MultiDiGraph()
    graph.add_edge("Person:1", "Person:2", key="KNOWS")
    ontology = SimpleNamespace(ontology_id="people", version=1, relationships=[], classes=[])
    ctx = PipelineContext(graph=graph, graph_report={"ok": True, "warnings": []},
                          approved_ontology=ontology, build_stats={})
    ctx.mark_done = Mock()
    return SimpleNamespace(id=uuid4(), ctx=ctx)


def test_failed_import_does_not_publish(monkeypatch, session):
    registry = Mock()
    registry.registry.return_value = nullcontext("db")
    registry.publication_guard.return_value = nullcontext()
    store = Mock()
    store.import_graph.side_effect = ValueError("internal backend detail")
    monkeypatch.setattr(graph_publication, "versions", registry)
    monkeypatch.setattr(graph_publication, "NeoGraphStore", lambda: nullcontext(store))
    version = str(uuid4())
    with pytest.raises(ApiError) as failure:
        graph_publication.persist(session, "owner", version, Mock(), Mock())
    assert failure.value.code == "publication_failed"
    registry.register.assert_called_once()
    registry.fail.assert_called_once_with("db", session.id, version, "owner")
    registry.publish.assert_not_called()
    session.ctx.mark_done.assert_not_called()


def test_missing_scipy_leaves_other_analytics_available(monkeypatch, session):
    monkeypatch.setattr(nx, "pagerank", Mock(side_effect=ModuleNotFoundError("scipy")))
    analytics = graph_publication.analyze(session.ctx.graph)
    assert "pagerank" in analytics["unavailable_algorithms"]
    assert "pagerank" not in analytics["rankings"]
    assert analytics["rankings"]["betweenness"]


def test_publication_follows_import(monkeypatch, session):
    events = Mock()
    registry, store = events.registry, events.store
    registry.registry.side_effect = lambda: nullcontext("db")
    registry.publication_guard.side_effect = lambda _version: nullcontext()
    monkeypatch.setattr(graph_publication, "versions", registry)
    monkeypatch.setattr(graph_publication, "NeoGraphStore", lambda: nullcontext(store))
    version = str(uuid4())
    graph_publication.persist(session, "owner", version, Mock(), events.commit)
    names = [entry[0] for entry in events.mock_calls]
    assert names.index("registry.register") < names.index("store.import_graph")
    assert names.index("store.import_graph") < names.index("commit") < names.index("registry.publish")
    assert session.ctx.snapshot["build_id"] == version
    session.ctx.mark_done.assert_called_once_with(16)


def test_project_authorization_scopes_owner():
    db = Mock()
    db.execute.return_value.fetchone.return_value = None
    project = uuid4()
    with pytest.raises(ApiError) as failure:
        authorize(db, project, "other-owner", manage=True)
    assert failure.value.status == 404
    statement, parameters = db.execute.call_args.args
    assert "p.project_id = %s AND p.owner_name = %s" in statement
    assert parameters == (project, "other-owner")


def test_properties_hide_sensitive_values_case_insensitively():
    assert properties({"Email": "personal", "name": "Casey", "values": [1, 2], "absent": None},
                      {"email"}) == {"name": "Casey", "values": "[1, 2]"}


def test_cypher_compiles_external_labels_and_relationship_type_to_parameters():
    query = compile_query("MATCH (c:Customer)-[r:PLACED]->(o:Order) RETURN c, r, count(o) LIMIT 900")
    assert query.columns == ["c", "r", "count(o)"]
    assert query.parameters == {"label": "Customer", "kind": "PLACED", "target": "Order", "limit": 200}
    assert "Customer" not in query.statement and "PLACED" not in query.statement
    assert query.statement.count("projectId: $project") == 3
    assert query.statement.count("graphVersionId: $version") == 3


@pytest.mark.parametrize("statement", [
    "MATCH (c:Customer) DETACH DELETE c RETURN c",
    "MATCH (c:Customer) RETURN c UNION MATCH (x) RETURN x",
    "CALL db.labels()",
    "MATCH (c:Customer) RETURN c.name + 1",
    "MATCH (c:Customer) RETURN x.name AS name",
    "MATCH (c:Customer) RETURN properties(c)",
    "MATCH (c:Customer) RETURN x",
])
def test_cypher_rejects_statements_outside_the_grammar(statement):
    with pytest.raises(ApiError) as failure:
        compile_query(statement)
    assert failure.value.status == 422


def test_cypher_compiles_properties_and_counts_without_interpolating_user_identifiers():
    query = compile_query("MATCH (c:Customer) RETURN c.name AS customer, count(*) AS total")
    assert query.columns == ["customer", "total"]
    assert query.parameters["field0"] == "name"
    assert "n[$field0] AS value0, count(*) AS value1" in query.statement
    assert "customer" not in query.statement
