from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from groq import AuthenticationError

from backend.app.core.config import ApiSettings  # initializes pipeline import path
from backend.app.exceptions.handlers import ApiError
from backend.app.services import graph_intelligence
from backend.app.services.graph_exports import graphml_rows
from backend.app.services.graph_intelligence import draft_query, grounded_answer, structural_insights
from backend.app.services.graphml_import import read_graphml, summarize
from kg_pipeline.core.ontology_models import Cardinality, DataType


def test_provider_auth_rejection_is_actionable_without_exposing_provider_details(monkeypatch):
    monkeypatch.setenv("KG_GRAPH_AI_ENABLED", "true")
    monkeypatch.setenv("KG_GRAPH_AI_MODEL", "test-model")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")

    def rejected_client(**_):
        response = httpx.Response(401, request=httpx.Request("POST", "https://example.test"))
        raise AuthenticationError("private provider detail", response=response, body=None)

    monkeypatch.setattr(graph_intelligence, "Groq", rejected_client)
    with pytest.raises(ApiError) as failure:
        graph_intelligence.model_completion("Return JSON", {})
    assert failure.value.code == "graph_ai_auth_rejected"
    assert "GROQ_API_KEY" in failure.value.message
    assert "private provider detail" not in failure.value.message


@pytest.fixture
def ontology():
    name = SimpleNamespace(name="name", data_type=DataType.STRING, required=True)
    quantity = SimpleNamespace(name="quantity", data_type=DataType.INTEGER, required=False)
    cls = SimpleNamespace(name="Person", attributes=[name])
    rel = SimpleNamespace(name="KNOWS", source_class="Person", target_class="Person",
                          properties=[quantity], allow_cycles=False, multi_edge=False,
                          cardinality=Cardinality.MANY_TO_MANY)
    return SimpleNamespace(ontology_id="sample", version=1, classes=[cls], relationships=[rel])


def test_graphml_roundtrip(ontology):
    nodes = [{"id": node, "properties": {"label": "Person", "name": node, "projectId": "ignored"}}
             for node in ("A & Bob", "B")]
    edges = [{"source": "A & Bob", "target": "B", "key": "k",
              "properties": {"type": "KNOWS", "quantity": 4}}]
    data = "".join(graphml_rows(nodes, edges)).encode()
    graph = read_graphml(data, ontology)
    assert summarize(graph)["types"] == {"KNOWS": 1}
    assert graph.nodes["A & Bob"] == {"label": "Person", "name": "A & Bob"}
    assert graph["A & Bob"]["B"]["k"]["quantity"] == 4


def test_graphml_rejects_dtd_and_duplicate_or_dangling_topology(ontology):
    with pytest.raises(ApiError, match="without DTDs"):
        read_graphml(b'<!DOCTYPE graphml [<!ENTITY x SYSTEM "file:///a">]><graphml/>', ontology)
    node = {"id": "a", "properties": {"label": "Person", "name": "A"}}
    duplicate = "".join(graphml_rows([node, node], [])).encode()
    with pytest.raises(ApiError, match="unique"):
        read_graphml(duplicate, ontology)
    dangling = "".join(graphml_rows([node], [{"source": "a", "target": "b", "key": "x", "properties": {"type": "KNOWS"}}])).encode()
    with pytest.raises(ApiError, match="endpoints"):
        read_graphml(dangling, ontology)


def test_structural_model_ranks_held_out_two_hop_entity():
    view = {"nodes": [{"id": n, "properties": {"label": "A" if n != "middle" else "B"}} for n in ("start", "middle", "hidden")],
            "edges": [{"source": "start", "target": "middle"}, {"source": "hidden", "target": "middle"}],
            "truncated": False}
    result = structural_insights(view, "start", "A")
    prediction = result["link_predictions"][0]
    assert prediction["node_id"] == "hidden"
    assert prediction["supporting_node_ids"] == ["middle"]
    assert result["recommendations"][0]["score"] == 1.0
    assert sum(value ** 2 for value in result["embedding"]) == pytest.approx(1)


def test_draft_rejects_unsafe_or_unknown_graph_patterns():
    schema = {"labels": [{"label": "Person"}], "relationship_directions": []}
    assert "RETURN" in draft_query("List people", schema, complete=lambda *_: {"cypher": "MATCH (n:Person) RETURN n"})
    with pytest.raises(ApiError, match="outside"):
        draft_query("List unknown", schema, complete=lambda *_: {"cypher": "MATCH (n:Unknown) RETURN n"})
    with pytest.raises(ApiError):
        draft_query("Delete", schema, complete=lambda *_: {"cypher": "MATCH (n:Person) DELETE n RETURN n"})


def test_rag_verifies_citation_ids():
    facts = [{"source": "A", "target": "B", "relationship": "KNOWS"}]
    result = grounded_answer("Who knows B?", facts, complete=lambda *_: {"answer": "A", "citations": [1, 99, True]})
    assert result["citations"] == [1]
    assert result["evidence"][0]["target"] == "B"
    invalid = grounded_answer("Who knows B?", facts, complete=lambda *_: {"answer": "C", "citations": [42]})
    assert invalid["answer"] != "C"
