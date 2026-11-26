"""Opt-in API integration using dedicated, disposable PostgreSQL and Neo4j stores."""
import json
import os
from time import monotonic, sleep
from uuid import UUID, uuid4

import bcrypt
import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.repositories import graph_versions
from backend.app.services.neo_graph import NeoGraphStore
from backend.tests.helpers import login_headers, make_settings
from backend.tests.test_api import ok, scoped

SOURCE = os.getenv("KG_TEST_SOURCE")
pytestmark = pytest.mark.skipif(SOURCE is None, reason="Requires disposable live graph database fixtures")


def terminal(client, session):
    deadline = monotonic() + 60
    while monotonic() < deadline:
        job = ok(client.get(session + "/builds/status"))
        if job["status"] in ("completed", "failed", "blocked", "cancelled"):
            return job
        sleep(0.15)
    pytest.fail("Graph job did not reach a terminal state")


def prepare(client, source):
    session = scoped(client)
    ok(client.post(session + "/sources/postgres", json=source))
    ok(client.post(session + "/metadata/extract"))
    ok(client.post(session + "/metadata/analyze"))
    ok(client.post(session + "/ontology/draft", json={"mode": "schema"}))
    ok(client.post(session + "/ontology/draft/save"))
    ok(client.post(session + "/ontology/suggestions/skip"))
    ok(client.post(session + "/ontology/review", json={"actor": "data.modeller"}))
    assert ok(client.post(session + "/ontology/validate"))["ok"]
    ok(client.post(session + "/ontology/approve", json={"author": "data.modeller", "reviewer": "reviewer.lead"}))
    return session


@pytest.fixture
def source_order():
    # Own a separate fixture record instead of editing the seeded retail rows.
    order_id = 1000000 + uuid4().int % 1000000000
    dsn = os.environ["KG_META_DSN"]
    with psycopg.connect(dsn) as db:
        db.execute("""
            INSERT INTO public.orders VALUES (%s,1,'2026-09-02','DELIVERED',91298,'2026-11-01 09:00')
            """, (order_id,))
        db.execute("INSERT INTO public.order_items VALUES (%s,201,1,89999)", (order_id,))
    try:
        yield order_id
    finally:
        with psycopg.connect(dsn) as db:
            db.execute("DELETE FROM public.order_items WHERE order_id = %s", (order_id,))
            db.execute("DELETE FROM public.orders WHERE order_id = %s", (order_id,))


def test_source_to_published_versions(tmp_path, monkeypatch, source_order):
    source = json.loads(SOURCE)
    with TestClient(create_app(make_settings(storage_root=tmp_path))) as client:
        client.headers.update(login_headers(client))
        session = prepare(client, source)
        assert ok(client.get(session + "/sources/health")) == {"status": "available", "mode": "postgres"}
        assert "://" not in ok(client.get(session + "/sources"))["name"]
        project = session.rsplit("/", 1)[1]
        base = f"/api/v1/graph-projects/{project}/versions"
        first = ok(client.post(session + "/builds/published", json={}), 202)["id"]
        assert terminal(client, session)["status"] == "completed"
        assert ok(client.get(base))["current"] == first
        version = base + "/" + first

        rows = ok(client.get(version + "/query", params={"template": "entities", "label": "Order"}))["rows"]
        assert rows
        root = rows[0]["id"]
        cypher = ok(client.post(version + "/query", json={"cypher": "MATCH (o:Order) RETURN o LIMIT 1"}))
        assert len(cypher["rows"]) == 1 and "id" in cypher["rows"][0]["o"]
        graph = ok(client.get(version + "/neighborhood", params={"node_id": root, "hops": 2}))
        assert graph["nodes"][0]["id"] == root and graph["edges"]
        analytics = ok(client.get(version + "/analytics"))
        assert analytics["nodes"] == graph["total_nodes"]
        assert analytics["rankings"]["pagerank"] and analytics["communities"]
        assert ok(client.get(version + "/communities/0"))["nodes"]
        filtered = ok(client.get(version + "/query", params={
            "template": "entities", "property": "id", "value": root,
        }))["rows"]
        assert [row["id"] for row in filtered] == [root]
        schema = ok(client.get(version + "/schema"))
        assert schema["labels"] and schema["types"]
        types = ok(client.get(version + "/entities"))["types"]
        assert "Order" in types
        short_id = root.split(":", 1)[1]
        matches = ok(client.get(version + "/entities", params={"q": short_id, "label": "Order"}))["matches"]
        assert any(match["id"] == root for match in matches)
        entity = ok(client.get(version + "/entity-neighborhood", params={"node_id": root, "hops": 3}))
        assert entity["root"]["id"] == root
        assert entity["ontology"]["classes"] and entity["graph"]["edges"]
        from backend.app.services import graph_intelligence
        with monkeypatch.context() as injected:
            def fixture_provider(_, payload):
                if "schema" in payload:
                    return {"cypher": "MATCH (o:Order) RETURN o LIMIT 1"}
                assert payload["facts"] and "source_record" not in payload["facts"][0]
                return {"answer": "The anchor has a relationship in the retrieved sample.", "citations": [1, 9999]}

            injected.setattr(graph_intelligence, "model_completion", fixture_provider)
            draft = ok(client.post(version + "/query-draft", json={"question": "List an order"}))
            assert draft["requires_confirmation"]
            result = ok(client.post(version + "/investigate", json={"question": "What is connected?", "node_id": root}))
            assert result["citations"] == [1] and len(result["trace"]) == 3
            assert "source_table" in result["evidence"][0]
        target = next(node["id"] for node in graph["nodes"] if node["id"] != root)
        assert ok(client.get(version + "/paths", params={"source": root, "target": target}))["edges"]
        export = client.get(version + "/export/json")
        assert export.status_code == 200
        assert len(export.json()["nodes"]) == graph["total_nodes"]
        for format_name in ("graphml", "nodes.csv", "relationships.csv"):
            assert client.get(f"{version}/export/{format_name}").status_code == 200

        viewer = f"kg_test_{uuid4().hex}"
        password = "disposable-viewer"
        with psycopg.connect(os.environ["KG_META_DSN"]) as db:
            db.execute("INSERT INTO kg_meta.app_user (username, password_hash) VALUES (%s, %s)",
                       (viewer, bcrypt.hashpw(password.encode(), bcrypt.gensalt(4)).decode()))
        project_path = base.removesuffix("/versions")
        try:
            token = client.post("/api/v1/login", json={"username": viewer, "password": password}).json()["access_token"]
            viewer_headers = {"Authorization": f"Bearer {token}"}
            assert client.get(base, headers=viewer_headers).status_code == 404
            assert client.post(version + "/query-draft", json={"question": "List orders"}, headers=viewer_headers).status_code == 404
            ok(client.put(project_path + "/members", json={"username": viewer}))
            assert not ok(client.get(base, headers=viewer_headers))["can_manage"]
            assert client.get(version + "/analytics", headers=viewer_headers).status_code == 200
            assert client.put(version + "/current", headers=viewer_headers).status_code == 404
            assert client.get(session, headers=viewer_headers).status_code == 404
        finally:
            ok(client.delete(project_path + "/members", params={"username": viewer}))
            with psycopg.connect(os.environ["KG_META_DSN"]) as db:
                db.execute("DELETE FROM kg_meta.app_user WHERE username = %s", (viewer,))

        ok(client.put(version + "/workspace-items", json={"name": "Orders", "kind": "scene", "focus": root}))
        items = ok(client.get(version + "/workspace-items", params={"kind": "scene"}))
        assert items[0]["settings"]["focus"] == root
        ok(client.get(version + "/query", params={"template": "labels", "log_run": True}))
        assert ok(client.get(version + "/workspace-items", params={"kind": "query_run"}))

        real_import = NeoGraphStore.import_graph

        def fail_after_writes(self, *args, **kwargs):
            real_import(self, *args, **kwargs)
            raise RuntimeError("Injected failure after Neo4j accepted staged data")

        with monkeypatch.context() as injected:
            injected.setattr(NeoGraphStore, "import_graph", fail_after_writes)
            failed = ok(client.post(session + "/graphs/snapshots", json={"load_neo4j": True}), 202)["id"]
            assert terminal(client, session)["status"] == "failed"
        assert ok(client.get(base))["current"] == first
        assert client.get(f"{base}/{failed}/analytics").status_code == 404
        with graph_versions.publication_guard(failed):
            with psycopg.connect(os.environ["KG_META_DSN"]) as db:
                db.execute("UPDATE kg_meta.graph_build SET status = 'staging' WHERE build_id = %s", (failed,))
            graph_versions.recover_interrupted()
            assert any(row["build_id"] == failed and row["status"] == "staging"
                       for row in ok(client.get(base))["versions"])
        graph_versions.recover_interrupted()
        recovered = next(row for row in ok(client.get(base))["versions"] if row["build_id"] == failed)
        assert recovered["error_code"] == "publication_interrupted"
        assert ok(client.get(base))["current"] == first

        with psycopg.connect(os.environ["KG_META_DSN"]) as db:
            db.execute("DELETE FROM public.order_items WHERE order_id = %s", (source_order,))
            db.execute("DELETE FROM public.orders WHERE order_id = %s", (source_order,))
        second = ok(client.post(session + "/builds/published", json={}), 202)["id"]
        assert terminal(client, session)["status"] == "completed"
        assert ok(client.get(base))["current"] == second
        comparison = ok(client.get(f"{base}/{second}/compare", params={"baseline": first}))
        assert comparison["removed_nodes"] == 1
        assert comparison["removed_relationships"] > 0
        assert client.get(f"/api/v1/graph-projects/{UUID(int=0)}/versions/{second}/analytics").status_code == 404
        ok(client.put(version + "/current"))
        assert ok(client.get(base))["current"] == first
        deletion = client.delete(f"{base}/{second}")
        assert deletion.status_code == 409
        monkeypatch.setenv("KG_GRAPH_RETENTION_DAYS", "0")
        assert client.delete(version).status_code == 409
        ok(client.delete(f"{base}/{second}"), 202)
        assert any(row["build_id"] == second and row["status"] == "deleted"
                   for row in ok(client.get(base))["versions"])
        snapshot = ok(client.post(session + "/graphs/snapshots", json={}))
        local_graphml = client.get(session + f"/graphs/snapshots/{snapshot['build_id']}/download/graph.graphml",
                                   params={"ontology_id": snapshot["ontology_id"]})
        assert local_graphml.status_code == 200
        upload = {"file": ("roundtrip.graphml", local_graphml.content, "application/xml")}
        preview = ok(client.post(session + "/graphs/graphml/preview", files=upload))
        assert preview["nodes"] == snapshot["nodes"]
        imported = ok(client.post(session + "/graphs/graphml/publish", files=upload), 202)["id"]
        assert terminal(client, session)["status"] == "completed"
        assert ok(client.get(base))["current"] == imported
        retained = next(row["id"] for row in rows if row["id"] != f"Order:{source_order}")
        report = ok(client.get(f"{base}/{imported}/intelligence", params={"node_id": retained}))
        assert len(report["embedding"]) == 16
        assert client.get(version + "/graphml/neighborhood", params={"node_id": root}).status_code == 200
        assert client.get(version + "/analytics").status_code == 200
