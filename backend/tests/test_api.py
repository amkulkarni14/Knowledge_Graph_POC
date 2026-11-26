"""API contract and offline integration tests; no live database/provider calls."""
import json
import sys
from pathlib import Path
import time
from unittest.mock import Mock
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import ApiSettings
from backend.app.main import create_app
from backend.tests.helpers import make_settings, login_headers
from backend.app.services import workflow
from kg_pipeline.config import settings as pipeline_settings


@pytest.fixture
def app(tmp_path):
    return create_app(make_settings(storage_root=tmp_path / "sessions"))


@pytest.fixture
def client(app):
    """Signed-in client: all routes except /login and /health require a bearer token."""
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers.update(login_headers(client))
        yield client


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"]


def session(client):
    return ok(client.post("/api/v1/sessions", json={"name": "API test"}), 201)["id"]


def scoped(client):
    sid = session(client)
    base = f"/api/v1/sessions/{sid}"
    ok(client.put(base + "/scope", json={"project": "Test", "business_questions": ["How are records connected?"]}))
    return base


@pytest.mark.parametrize("state", ["active", "recovered", "legacy"])
def test_delete_workspace_preserves_artifacts_and_other_workspaces(client, app, state):
    from backend.app.repositories.library import catalog
    sid, other = session(client), session(client)
    repo = app.state.sessions
    root = repo.settings.storage_root
    artifact = root / sid / "graphs" / "manifest.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}")
    outside = root.parent / "shared.json"
    outside.write_text("shared")
    (root / sid / "shared-reference").write_text(str(outside))
    draft = root / sid / "working_drafts" / "draft.json"
    draft.parent.mkdir()
    draft.write_text("{}")
    active = repo._sessions[UUID(sid)]
    active.published_build = {"build_id": "external"}
    active.checkpoint()
    if state != "active":
        repo.close()
    if state == "legacy":
        with catalog(root) as db:
            db.execute("DELETE FROM workspace_recovery WHERE workspace_id=?", (sid,))
    if state == "recovered":
        # A valid checkpoint is authoritative and bypasses legacy draft discovery.
        ok(client.post(f"/api/v1/workspaces/{sid}/reopen"))
    path = f"/api/v1/workspaces/{sid}"
    assert client.delete(path, headers={"Authorization": ""}).status_code == 401
    assert client.delete(path).status_code == 204
    assert client.delete(path).status_code == 404
    assert client.post(path + "/reopen").status_code == 404
    assert client.get(f"/api/v1/sessions/{sid}").status_code == 404
    assert {item["id"] for item in ok(client.get("/api/v1/workspaces"))} == {other}
    with catalog(root) as db:
        assert db.execute("SELECT 1 FROM workspace_recovery WHERE workspace_id=?", (sid,)).fetchone() is None
    assert artifact.read_text() == draft.read_text() == "{}"
    assert outside.read_text() == "shared"


def test_delete_workspace_refuses_cross_user_and_running_jobs(client, app):
    repo = app.state.sessions
    foreign = repo.create("Other account", "another-user")
    missing = client.delete(f"/api/v1/workspaces/{foreign.id}")
    assert missing.status_code == 404
    assert repo.get(foreign.id, "another-user") is foreign
    sid = UUID(session(client))
    path = f"/api/v1/workspaces/{sid}"
    active = repo._sessions[sid]
    for status in ("queued", "running", "cancelling", "publishing"):
        active.job = {"status": status}
        assert client.delete(path).status_code == 409
    active.job = None
    with active.lock:
        assert client.delete(path).status_code == 409
    assert client.delete(path).status_code == 204


def test_workspace_delete_rolls_back_catalog_failure(client, app):
    from backend.app.repositories.library import catalog

    sid = session(client)
    path = f"/api/v1/workspaces/{sid}"
    with catalog(app.state.sessions.settings.storage_root) as db:
        db.execute("""CREATE TRIGGER reject_checkpoint_delete BEFORE DELETE ON workspace_recovery
                      BEGIN SELECT RAISE(ABORT, 'fixture failure'); END""")
    assert client.delete(path).status_code == 500
    assert ok(client.get(f"/api/v1/sessions/{sid}"))["id"] == sid
    assert ok(client.get("/api/v1/workspaces"))[0]["id"] == sid
    with catalog(app.state.sessions.settings.storage_root) as db:
        db.execute("DROP TRIGGER reject_checkpoint_delete")
    assert client.delete(path).status_code == 204


def upload_csv(client, base):
    folder = ROOT / "data/samples/customer360"
    return client.post(base + "/sources/upload",
                       files=[("files", (p.name, p.read_bytes(), "text/csv")) for p in sorted(folder.glob("*.csv"))])


def prepared(client):
    base = scoped(client)
    ok(upload_csv(client, base))
    ok(client.post(base + "/metadata/extract"))
    ok(client.post(base + "/metadata/analyze"))
    return base


def test_confirmed_source_schema_lists_only_selected_assets_before_extraction(client):
    base = "/api/v1/sessions/" + session(client)
    path = base + "/sources/schema"
    assert client.get(path).status_code == 409
    candidate = ok(client.post(base + "/sources/connections", json={
        "source": "sample", "name": "Retail sample", "configuration": {},
    }))
    assert client.get(path).status_code == 409
    table = "public.customers"
    ok(client.post(base + f"/sources/connections/{candidate['id']}/select", json={"assets": [table]}))
    schema = ok(client.get(path))
    assert list(schema) == [table]
    assert schema[table]
    assert ok(client.get(base))["completed_stages"] == [2]
    assert client.get(base + "/metadata").status_code == 409
    assert client.get(path, headers={"Authorization": ""}).status_code == 401
    assert client.delete(base + "/sources").status_code == 204
    assert client.get(path).status_code == 409


def approved(client):
    base = prepared(client)
    ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))
    ok(client.post(base + "/ontology/draft/save"))
    ok(client.post(base + "/ontology/suggestions/skip"))
    ok(client.post(base + "/ontology/review", json={"actor": "data.modeller"}))
    report = ok(client.post(base + "/ontology/validate"))
    assert report["ok"], report
    ok(client.post(base + "/ontology/approve", json={"author": "data.modeller", "reviewer": "reviewer.lead"}))
    return base


def build(client, base):
    for stage in range(10, 16):
        ok(client.post(base + f"/builds/stages/{stage}", json={}))
    return ok(client.get(base + "/builds/stages/15"))


def test_health_openapi_and_stage_registry(client):
    assert ok(client.get("/api/v1/health"))["status"] == "ok"
    stages = ok(client.get("/api/v1/stages"))
    assert [s["no"] for s in stages] == list(range(1, 17))
    spec = client.get("/openapi.json").json()
    assert "/api/v1/sessions/{session_id}/graphs/data" in spec["paths"]


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "  "}, {"name": "x", "unknown": 1}, {}])
def test_invalid_session_requests(client, body):
    assert client.post("/api/v1/sessions", json=body).status_code == 422


def test_sessions_are_isolated_and_close(client):
    first, second = scoped(client), scoped(client)
    ok(upload_csv(client, first))
    assert ok(client.get(first))["completed_stages"] == [1, 2]
    assert ok(client.get(second))["completed_stages"] == [1]
    assert client.delete(first).status_code == 204
    assert client.get(first).status_code == 404


def test_workspace_list_only_shows_active_sessions_owned_by_the_user(app, client):
    first = session(client)
    second = session(client)
    app.state.sessions.create("Other user's workspace", owner="other")
    assert {view["id"] for view in ok(client.get("/api/v1/sessions"))} == {first, second}
    assert client.delete(f"/api/v1/sessions/{first}").status_code == 204
    assert [view["id"] for view in ok(client.get("/api/v1/sessions"))] == [second]


def test_csv_can_connect_before_scope_and_updates_workspace_summary(client):
    base = "/api/v1/sessions/" + session(client)
    assert client.post(base + "/sources/sample").status_code == 404
    ok(upload_csv(client, base))
    view = ok(client.get(base))
    assert view["completed_stages"] == [2]
    assert view["summary"]["source_type"] == "csv"
    assert view["summary"]["source_files"] == 7
    assert client.post(base + "/metadata/extract").status_code == 409
    ok(client.put(base + "/scope", json={"project": "Test", "business_questions": ["What is connected?"]}))
    ok(client.post(base + "/metadata/extract"))
    ok(client.post(base + "/metadata/analyze"))
    ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))
    summary = ok(client.get(base))["summary"]
    assert summary["tables"] == sum(summary["table_types"].values()) == 7
    assert summary["ontology"]["classes"] > 0


def test_postgres_connects_before_scope(client, monkeypatch):
    from kg_pipeline.preprocessing.connectors import postgres_source

    source = Mock(name="postgres_source")
    source.name = "postgres://test"
    source.schemas = ["public"]
    source.ping.return_value = {"read_only": True}
    monkeypatch.setattr(postgres_source, "PostgresSource", Mock(return_value=source))
    base = "/api/v1/sessions/" + session(client)
    missing = client.post(base + "/metadata/extract")
    assert missing.json()["error"]["message"] == "Complete Data Sources first"
    ok(client.post(base + "/sources/postgres", json={
        "host": "localhost", "dbname": "test", "user": "reader", "password": "test"}))
    assert ok(client.get(base))["completed_stages"] == [2]
    missing = client.post(base + "/metadata/extract")
    assert missing.json()["error"]["message"] == "Complete Goal & Scope first"


def test_domain_template_persists_and_populates_scope(app, client):
    from backend.app.repositories.library import list_domains

    payload = {"name": "Customer domain", "project": "Customer 360", "scope_notes": "Account relationships",
               "business_questions": ["Which accounts belong to each customer?"],
               "tables_in_scope": ["csv.customers"], "columns_in_scope": ["csv.customers.cust_id"],
               "sensitive_columns": ["csv.customers.email"], "users": ["Analysts"], "later_list": ["Loans"]}
    saved = ok(client.post("/api/v1/domains", json=payload), 201)
    assert ok(client.get("/api/v1/domains")) == [saved]
    assert list_domains(app.state.config.storage_root, "other") == []
    scope = {key: saved[key] for key in payload if key != "name"}
    base = "/api/v1/sessions/" + session(client)
    ok(upload_csv(client, base))
    ok(client.put(base + "/scope", json=scope))
    assert ok(client.get(base + "/scope")) == scope


def test_saved_ontologies_include_versions_after_workspace_closes(app, client):
    from backend.app.repositories.library import list_ontologies

    base = approved(client)
    ok(client.post(base + "/ontology/versions/1/rollback", params={"ontology_id": "knowledge-graph"},
                   json={"actor": "data.modeller"}))
    assert client.delete(base).status_code == 204
    (saved,) = ok(client.get("/api/v1/ontologies"))
    assert saved["ontology_id"] == "knowledge-graph"
    assert [(row["version"], row["status"]) for row in saved["versions"]] == [
        (2, "draft"), (1, "approved"), (None, "draft")]
    assert list_ontologies(app.state.config.storage_root, "other") == []


def test_stage_advice_uses_aggregate_context_without_changing_workflow(client, monkeypatch):
    from backend.app.services import stage_advice

    base = prepared(client)
    before = ok(client.get(base))["completed_stages"]
    completion = Mock(return_value={"suggestions": ["Compare inferred keys with the schema."]})
    monkeypatch.setattr(stage_advice, "model_completion", completion)
    response = ok(client.post(base + "/stage-advice/3", json={"question": "How do I review keys?"}))
    assert response["mode"] == "ai"
    assert response["facts"]["table_count"] == 7
    payload = completion.call_args.args[1]
    assert payload["question"] == "How do I review keys?"
    assert set(payload) == {"stage", "facts", "checklist", "question"}
    assert "csv.customers" not in str(payload)
    assert ok(client.get(base))["completed_stages"] == before


def test_every_workflow_stage_has_a_fallback_when_ai_fails(client, monkeypatch):
    from backend.app.services import stage_advice
    from backend.app.exceptions.handlers import ApiError

    base = "/api/v1/sessions/" + session(client)
    failed = Mock(side_effect=ApiError(502, "graph_ai_failed", "provider failure"))
    monkeypatch.setattr(stage_advice, "model_completion", failed)
    for stage in range(1, 20):
        response = ok(client.post(base + f"/stage-advice/{stage}", json={}))
        assert response["mode"] == "guide" and len(response["suggestions"]) == 2
    assert client.post(base + "/stage-advice/20", json={}).status_code == 404
    assert client.post(base + "/stage-advice/2", json={"question": "x" * 601}).status_code == 422


def test_graphml_preview_can_check_structure_before_approval(client):
    base = "/api/v1/sessions/" + session(client)
    data = b"""<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
      <key id="label" for="node" attr.name="label" attr.type="string"/>
      <graph edgedefault="directed"><node id="n1"><data key="label">A</data></node></graph>
    </graphml>"""
    files = {"file": ("graph.graphml", data, "application/xml")}
    preview = ok(client.post(base + "/graphs/graphml/preview", files=files))
    assert preview["ontology_validated"] is False
    assert preview["nodes"] == 1 and preview["labels"] == {"A": 1}
    assert client.post(base + "/graphs/graphml/publish", files=files).status_code == 409
    assert client.post(approved(client) + "/graphs/graphml/preview", files=files).status_code == 422


def test_expired_session_is_closed(app, client):
    base = scoped(client)
    from uuid import UUID
    obj = app.state.sessions.get(UUID(base.rsplit("/", 1)[1]))
    obj.touched -= 4000
    assert client.get(base).status_code == 404


def test_capacity_and_busy_session(app, client):
    base = scoped(client)
    from uuid import UUID
    obj = app.state.sessions.get(UUID(base.rsplit("/", 1)[1]))
    obj.lock.acquire()
    try:
        assert upload_csv(client, base).status_code == 409
        assert client.delete(base).status_code == 409
    finally:
        obj.lock.release()


@pytest.mark.parametrize("route", ["/metadata/extract", "/metadata/analyze",
                                  "/ontology/validate", "/ontology/draft/save"])
def test_missing_prerequisites(client, route):
    base = "/api/v1/sessions/" + session(client)
    assert client.post(base + route).status_code == 409


def test_source_change_invalidates_all_results(client):
    base = approved(client)
    build(client, base)
    ok(upload_csv(client, base))
    assert ok(client.get(base))["completed_stages"] == [1, 2]
    assert client.get(base + "/graphs/data").status_code == 409
    assert client.get(base + "/ontology/draft").status_code == 409
    assert client.get(base + "/builds/stages/15").status_code == 409


def test_scope_change_keeps_source_but_invalidates_results(client):
    base = prepared(client)
    ok(client.put(base + "/scope", json={"project": "Changed", "business_questions": ["New question"]}))
    assert ok(client.get(base))["completed_stages"] == [1, 2]
    assert client.get(base + "/metadata").status_code == 409


def test_bad_upload_preserves_connection(client):
    base = prepared(client)
    previous = ok(client.get(base + "/sources"))
    result = client.post(base + "/sources/upload", files=[("files", ("bad.csv", b"\x00\x01", "text/csv"))])
    assert result.status_code == 422
    assert ok(client.get(base + "/sources")) == previous
    assert ok(client.get(base))["completed_stages"] == [1, 2, 3, 4]


@pytest.mark.parametrize("filename", ["../bad.csv", r"..\bad.csv", "workbook.xlsx", "data.tsv", "data.txt", ""])
def test_upload_filename_and_type_validation(client, filename):
    base = scoped(client)
    response = client.post(base + "/sources/upload", files=[("files", (filename, b"id\n1\n", "text/csv"))])
    assert response.status_code in (400, 422)


def test_upload_limit_before_parser(tmp_path):
    app = create_app(make_settings(storage_root=tmp_path, max_request_bytes=512))
    with TestClient(app) as client:
        response = client.post("/api/v1/sessions", content=b"x" * 513,
                               headers={"Content-Type": "application/json", **login_headers(client)})
        assert response.status_code == 413


def test_credentials_never_echoed(client, monkeypatch):
    base = scoped(client)
    password = "SENSITIVE_TEST_PASSWORD"
    invalid = client.post(base + "/sources/postgres", json={
        "host": "localhost", "port": 99999, "dbname": "test", "user": "reader", "password": password})
    assert invalid.status_code == 422 and password not in invalid.text
    monkeypatch.setattr(workflow.s02_connect, "connect_postgres",
                        Mock(side_effect=Exception("connection failed password=" + password)))
    failed = client.post(base + "/sources/postgres", json={
        "host": "localhost", "dbname": "test", "user": "reader", "password": password})
    assert failed.status_code == 502 and password not in failed.text
    assert password not in client.get(base + "/events").text


def test_table_whitelist_and_preview_limits(client):
    base = prepared(client)
    assert client.get(base + "/metadata/preview", params={"table": "csv.not_real"}).status_code == 404
    assert client.get(base + "/metadata/preview", params={"table": "csv.customers", "limit": 101}).status_code == 422
    assert client.get(base + "/metadata/preview", params={"table": "csv.customers;DROP TABLE x"}).status_code == 422
    rows = ok(client.get(base + "/metadata/preview", params={"table": "csv.customers", "limit": 2}))
    assert len(rows) == 2


def test_complete_workflow_snapshots_and_graphs(client):
    base = approved(client)
    report = build(client, base)
    assert (report["nodes"], report["edges"]) == (54, 64)
    assert report["ok"]
    graph = ok(client.get(base + "/graphs/data", params={"limit": 5, "edge_limit": 4}))
    assert len(graph["nodes"]) <= 5 and len(graph["edges"]) <= 4 and graph["truncated"]
    node_id = graph["nodes"][0]["id"]
    assert ok(client.get(base + "/graphs/node", params={"node_id": node_id}))["id"] == node_id
    assert ok(client.get(base + "/graphs/path", params={"source": node_id, "target": node_id}))["connected"]
    snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
    assert snapshot["published"] and "path" not in snapshot
    oid = snapshot["ontology_id"]
    items = ok(client.get(base + "/graphs/snapshots", params={"ontology_id": oid}))
    assert items[0]["current"]
    download = client.get(base + f"/graphs/snapshots/{snapshot['build_id']}/download/graph.json.gz",
                          params={"ontology_id": oid})
    assert download.status_code == 200 and download.content[:2] == b"\x1f\x8b"
    reloaded = ok(client.get(base + "/graphs/data", params={"ontology_id": oid}))
    assert reloaded["total_nodes"] == report["nodes"]
    other = scoped(client)
    assert client.get(other + "/graphs/data", params={"ontology_id": oid}).status_code == 404


def test_four_eyes_and_mapping_validation(client):
    base = prepared(client)
    draft = ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))["ontology"]
    draft["classes"][0]["mapping"]["key_columns"] = ["not_a_column"]
    assert client.put(base + "/ontology/draft", json={"ontology": draft}).status_code == 422
    assert client.post(base + "/ontology/approve", json={"author": "Same", "reviewer": "same"}).status_code == 422


def test_editor_mutation_invalidates_approval(client):
    base = approved(client)
    onto = ok(client.get(base + "/ontology/draft"))
    name = onto["classes"][0]["name"]
    ok(client.patch(base + f"/ontology/classes/{name}", json={"name": "RenamedClass"}))
    assert 9 not in ok(client.get(base))["completed_stages"]
    assert client.post(base + "/builds", json={}).status_code == 409


def test_unknown_review_suggestion_and_empty_ai_allowlist(client):
    base = prepared(client)
    ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))
    ok(client.post(base + "/ontology/draft/save"))
    assert client.post(base + "/ontology/suggestions", json={"actor": "author", "allowed_tables": []}).status_code == 422
    ok(client.post(base + "/ontology/suggestions/skip"))
    assert client.post(base + "/ontology/review", json={
        "actor": "author", "decisions": {"nonexistent": {"action": "approve"}}}).status_code == 422


def test_build_job_status_and_storage_restoration(client):
    base = approved(client)
    previous = pipeline_settings.storage_dir
    job = ok(client.post(base + "/builds", json={}), 202)
    assert job["status"] == "queued"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = ok(client.get(base + "/builds/status"))
        if status["status"] in ("completed", "blocked", "failed"):
            break
        time.sleep(0.01)
    assert status["status"] == "completed", status
    pipeline = ok(client.get(base + "/builds/pipeline"))
    assert [step["stage"] for step in status["steps"]] == [item["stage"] for item in pipeline["steps"]]
    assert all(step["status"] == "completed" and step["duration_ms"] >= 0 and step["result"]
               for step in status["steps"])
    assert [item["time"] for item in status["events"]] == sorted(item["time"] for item in status["events"])
    assert sum(event["severity"] == "success" for event in status["events"]) == len(status["steps"])
    assert pipeline_settings.storage_dir == previous
    assert ok(client.get(base + "/builds/stages/15"))["ok"]


def test_snapshot_path_and_artifact_validation(client):
    base = scoped(client)
    assert client.get(base + "/graphs/data", params={"ontology_id": "../outside"}).status_code == 422
    assert client.get(base + "/graphs/data", params={"ontology_id": "knowledge-graph", "build_id": "../../outside"}).status_code == 422


def test_build_monitor_keeps_completed_steps_when_extraction_fails(client, monkeypatch):
    from threading import Event
    from backend.app.exceptions.handlers import ApiError
    from backend.app.services import builds

    base = approved(client)
    entered, release = Event(), Event()
    run_stage = builds.run_stage

    def fail_extraction(active, stage, body):
        if stage != 11:
            return run_stage(active, stage, body)
        entered.set()
        assert release.wait(10)
        raise ApiError(502, "source_failure", "Could not read the source")

    monkeypatch.setattr(builds, "run_stage", fail_extraction)
    try:
        ok(client.post(base + "/builds", json={}), 202)
        assert entered.wait(5)
        live = ok(client.get(base + "/builds/status"))
        assert [step["status"] for step in live["steps"][:3]] == ["completed", "running", "pending"]
        assert live["steps"][0]["result"]["entity_types"]
        assert client.post(base + "/builds", json={}).status_code == 409
    finally:
        release.set()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = ok(client.get(base + "/builds/status"))
        if job["status"] == "failed":
            break
        time.sleep(.01)
    assert job["status"] == "failed"
    assert [step["status"] for step in job["steps"]] == ["completed", "failed", "skipped", "skipped", "skipped", "skipped"]
    assert job["error"]["message"] == "Could not read the source"
    assert all(job["error"]["message"] not in event["message"] for event in job["events"])


def test_cors_explicit_origin(client):
    response = client.options("/api/v1/sessions", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/v1/sessions", headers={
        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in response.headers


def test_nested_unknown_fields_are_rejected(client):
    base = prepared(client)
    draft = ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))["ontology"]
    draft["classes"][0]["mapping"]["unrecognized"] = True
    assert client.put(base + "/ontology/draft", json={"ontology": draft}).status_code == 422


def test_saved_draft_can_be_reverted_after_edit(client):
    base = prepared(client)
    original = ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))["ontology"]
    ok(client.post(base + "/ontology/draft/save"))
    old = original["classes"][0]["name"]
    ok(client.patch(base + f"/ontology/classes/{old}", json={"name": "NewName"}))
    reverted = ok(client.post(base + "/ontology/draft/revert"))
    assert reverted == original
    assert 5 not in ok(client.get(base))["completed_stages"]


def test_manual_review_preview_matches_applied_review(client):
    base = prepared(client)
    ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))
    ok(client.post(base + "/ontology/draft/save"))
    assert client.post(base + "/ontology/validate").status_code == 409
    ok(client.post(base + "/ontology/suggestions/skip"))
    body = {"actor": "data.modeller"}
    preview = ok(client.post(base + "/ontology/review/preview", json=body))
    applied = ok(client.post(base + "/ontology/review", json=body))
    assert preview == applied
    assert ok(client.post(base + "/ontology/validate"))["ok"]
    assert client.post(base + "/builds/stages/10", json={}).status_code == 409
    assert client.post(base + "/ontology/approve",
                       json={"author": "data.modeller", "reviewer": "data.modeller"}).status_code == 422
    ok(client.post(base + "/ontology/approve", json={"author": "data.modeller", "reviewer": "reviewer.lead"}))
    report = build(client, base)
    assert (report["nodes"], report["edges"]) == (54, 64)


def test_versions_audit_and_rollback(client):
    base = approved(client)
    rows = ok(client.get(base + "/ontology/versions", params={"ontology_id": "knowledge-graph"}))
    assert len(rows) == 1 and rows[0]["status"] == "approved"
    history = ok(client.get(base + "/ontology/audit", params={"ontology_id": "knowledge-graph"}))
    assert history["total"] >= 3
    original = ok(client.get(base + "/ontology/versions/1", params={"ontology_id": "knowledge-graph"}))
    rolled = ok(client.post(base + "/ontology/versions/1/rollback",
                            params={"ontology_id": "knowledge-graph"}, json={"actor": "data.modeller"}))
    assert rolled["version"] == 2 and rolled["status"] == "draft"
    assert rolled["classes"] == original["classes"]
    ok(client.post(base + "/ontology/use-approved", params={"ontology_id": "knowledge-graph"}))
    assert 9 in ok(client.get(base))["completed_stages"]


def test_failed_pipeline_call_restores_storage_and_state(app, client, monkeypatch):
    base = scoped(client)
    ok(upload_csv(client, base))
    previous = pipeline_settings.storage_dir
    monkeypatch.setattr(workflow.s03_schema_extraction, "run", Mock(side_effect=OSError("private/path")))
    result = client.post(base + "/metadata/extract")
    assert result.status_code == 502 and "private/path" not in result.text
    assert pipeline_settings.storage_dir == previous
    assert ok(client.get(base))["completed_stages"] == [1, 2]


def test_neo4j_is_not_called_unless_requested(client, monkeypatch):
    from kg_pipeline.graph_builder.loaders import s16_graph_persistence
    mocked = Mock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr(s16_graph_persistence, "push_to_neo4j", mocked)
    base = approved(client)
    build(client, base)
    ok(client.post(base + "/graphs/snapshots", json={}))
    mocked.assert_not_called()


def test_corrupt_export_is_not_downloaded(app, client):
    from uuid import UUID
    base = approved(client)
    build(client, base)
    snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
    obj = app.state.sessions.get(UUID(base.rsplit("/", 1)[1]))
    artifact = obj.root / "graphs" / snapshot["ontology_id"] / snapshot["build_id"] / "graph.graphml"
    artifact.write_text("corrupt", encoding="utf-8")
    response = client.get(base + f"/graphs/snapshots/{snapshot['build_id']}/download/graph.graphml",
                          params={"ontology_id": snapshot["ontology_id"]})
    assert response.status_code == 409


def test_sensitive_columns_are_hidden_from_previews(client):
    base = scoped(client)
    ok(client.put(base + "/scope", json={"project": "Privacy", "business_questions": ["Connections"],
                                       "sensitive_columns": ["csv.customers.email"]}))
    ok(upload_csv(client, base))
    ok(client.post(base + "/metadata/extract"))
    rows = ok(client.get(base + "/metadata/preview", params={"table": "csv.customers"}))
    assert rows and all("email" not in row for row in rows)


def test_rule_and_batch_validation(client):
    base = approved(client)
    assert client.post(base + "/builds", json={"batch_size": 0}).status_code == 422
    response = client.post(base + "/builds", json={
        "business_rules": {"csv.nonexistent": [{"column": "id", "rule": "non_negative"}]}})
    assert response.status_code == 422
    response = client.post(base + "/builds", json={
        "business_rules": {"csv.customers": [{"column": "id", "rule": "allowed_values"}]}})
    assert response.status_code == 422


def test_validation_only_workflow_builds_without_approval(tmp_path):
    from backend.app.services.workflow_policy import VALIDATION_ONLY

    app = create_app(make_settings(storage_root=tmp_path, workflow_policy=VALIDATION_ONLY))
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers.update(login_headers(client))
        stages = {stage["no"]: stage for stage in ok(client.get("/api/v1/stages"))}
        assert set(stages) == set(range(1, 17)) - {6, 7, 9}
        assert stages[8]["prerequisites"] == [5]
        assert stages[10]["prerequisites"] == [3, 8]

        base = prepared(client)
        draft = ok(client.post(base + "/ontology/draft",
                               json={"mode": "schema", "name": "Customer 360 Ontology"}))["ontology"]
        assert draft["name"] == "Customer 360 Ontology"
        from copy import deepcopy

        invalid = deepcopy(draft)
        invalid["classes"][0]["attributes"].append({"name": "label", "data_type": "string"})
        ok(client.put(base + "/ontology/draft", json={"ontology": invalid}))
        ok(client.post(base + "/ontology/draft/save"))
        assert not ok(client.post(base + "/ontology/validate"))["ok"]
        assert client.post(base + "/builds/stages/10", json={}).status_code == 409
        assert client.post(base + "/builds", json={}).status_code == 409

        ok(client.put(base + "/ontology/draft", json={"ontology": draft}))
        ok(client.post(base + "/ontology/draft/save"))
        assert ok(client.post(base + "/ontology/validate"))["ok"]
        workspace = ok(client.get(base))
        assert workspace["summary"]["ontology"]["status"] == "validated"
        assert set(workspace["completed_stages"]).isdisjoint({6, 7, 9})
        assert client.post(base + "/ontology/suggestions/skip").json()["error"]["code"] == "stage_disabled"
        assert client.post(base + "/ontology/review", json={"actor": "data.modeller"}).json()["error"]["code"] == "stage_disabled"
        assert client.post(base + "/ontology/approve",
                           json={"author": "data.modeller", "reviewer": "reviewer.lead"}).json()["error"]["code"] == "stage_disabled"
        assert ok(client.get(base + "/ontology/versions", params={"ontology_id": draft["ontology_id"]})) == []

        job = ok(client.post(base + "/builds", json={}), 202)
        assert job["status"] in {"queued", "running"}
        for _ in range(150):
            job = ok(client.get(base + "/builds/status"))
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(0.02)
        assert job["status"] == "completed", job
        result = ok(client.get(base + "/builds/stages/15"))
        assert result["ok"], result
        assert set(ok(client.get(base))["completed_stages"]).isdisjoint({6, 7, 9})
        snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
        assert snapshot["ontology_id"] == draft["ontology_id"]

        saved = ok(client.get(base + "/ontology/draft"))
        completed = ok(client.get(base))["completed_stages"]
        report = ok(client.get(base + "/ontology/validation"))
        for name in ("   ", "x" * 201):
            assert client.post(base + "/ontology/draft/save", json={"name": name}).status_code == 422
        renamed = ok(client.post(base + "/ontology/draft/save",
                                 json={"name": "  Retail Customer Ontology  "}))
        assert renamed == {**saved, "name": "Retail Customer Ontology"}
        assert ok(client.get(base + "/ontology/draft")) == renamed
        workspace = ok(client.get(base))
        assert workspace["summary"]["ontology"]["name"] == renamed["name"]
        assert workspace["summary"]["ontology"]["status"] == "validated"
        assert workspace["completed_stages"] == completed
        assert ok(client.get(base + "/ontology/validation")) == report
        assert ok(client.get(base + "/builds/stages/15")) == result
        paths = list((tmp_path / base.rsplit("/", 1)[-1] / "working_drafts").glob("*.json"))
        assert [path.stem for path in paths] == [draft["ontology_id"]]
        assert json.loads(paths[0].read_text(encoding="utf-8")) == renamed
        (library_entry,) = ok(client.get("/api/v1/ontologies"))
        assert library_entry["name"] == renamed["name"]
        ok(client.post(base + "/builds/stages/10", json={}))

        draft["classes"][0]["description"] = "Edited class"
        ok(client.put(base + "/ontology/draft", json={"ontology": draft}))
        assert not set(ok(client.get(base))["completed_stages"]).intersection({5, 8, 10, 14, 15, 16})
        assert client.post(base + "/builds/stages/10", json={}).status_code == 409
        assert client.post(base + "/builds", json={}).status_code == 409
        ok(client.post(base + "/ontology/draft/save"))
        assert client.post(base + "/builds/stages/10", json={}).status_code == 409
        assert ok(client.post(base + "/ontology/validate"))["ok"]
        ok(client.post(base + "/builds/stages/10", json={}))


def test_workflow_policy_cannot_enable_validation_only_in_production():
    with pytest.raises(ValueError, match="cannot be used in production"):
        make_settings(workflow_policy="poc_validation_only", deployment_environment="production")
    with pytest.raises(ValueError, match="KG_WORKFLOW_POLICY"):
        make_settings(workflow_policy="unknown")


def test_connector_candidate_selection_and_disconnect(client):
    base = scoped(client)
    other = scoped(client)
    payload = {"source": "sample", "name": "Retail candidate"}
    assert ok(client.post(base + "/sources/test", json=payload))["asset_count"] == 0
    data = ok(client.post(base + "/sources/connections", json=payload))
    link = "/sources/connections/" + data["id"]
    assert ok(client.get(base))["completed_stages"] == [1]
    assert ok(client.get(base + "/sources/connections/candidate"))["id"] == data["id"]
    assert client.get(other + link + "/assets").status_code == 404
    assert ok(client.get(base + link + "/assets", params={"limit": 1}))["total"] > 1
    assert client.post(base + link + "/select", json={"assets": ["missing"]}).status_code == 422
    asset = "public.customers"
    ok(client.put(base + "/scope", json={"project": "Test", "business_questions": ["How many?"],
                                      "sensitive_columns": [asset + ".email"]}))
    preview = ok(client.post(base + link + "/preview", json={"asset": asset, "limit": 2}))
    assert len(preview["rows"]) == 2
    assert "email" not in preview["rows"][0]
    ok(client.post(base + link + "/select", json={"assets": [asset]}))
    assert ok(client.get(base))["completed_stages"] == [1, 2]
    assert list(ok(client.post(base + "/metadata/extract"))["tables"]) == [asset]
    assert client.delete(base + "/sources").status_code == 204
    assert ok(client.get(base))["completed_stages"] == [1]


def test_network_policy_protects_legacy_and_guided_connections(client):
    base = scoped(client)
    postgres = {"host": "not-allowlisted.invalid", "dbname": "test", "user": "reader", "password": "fixture-secret"}
    legacy = client.post(base + "/sources/postgres", json=postgres)
    guided = client.post(base + "/sources/test", json={"source": "postgres", "name": "Denied", "configuration": postgres})
    for response in (legacy, guided):
        assert response.status_code == 403
        assert postgres["password"] not in response.text
    assert ok(client.get(base))["completed_stages"] == [1]


def test_s3_sdk_selection_through_graph_validation(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from urllib.parse import urlsplit

    pytest.importorskip("boto3")
    content = b"customer_id,name\n1,First\n2,Second\n"
    requests = []

    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            path = urlsplit(self.path).path
            requests.append(path)
            if path == "/fixture":
                data = (f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                        f'<Name>fixture</Name><IsTruncated>false</IsTruncated>'
                        f'<Contents><Key>retail/customers.csv</Key><Size>{len(content)}</Size></Contents>'
                        f'</ListBucketResult>').encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
            elif path == "/fixture/retail/customers.csv":
                data = content
                self.send_response(206)
                self.send_header("Content-Range", f"bytes 0-{len(data) - 1}/{len(data)}")
            else:
                self.send_error(404)
                return
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    with ThreadingHTTPServer(("127.0.0.1", 0), Fixture) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}"
            monkeypatch.setenv("KG_SOURCE_S3_ENDPOINTS", endpoint)
            app = create_app(make_settings(storage_root=tmp_path, workflow_policy="poc_validation_only"))
            with TestClient(app) as client:
                client.headers.update(login_headers(client))
                base = scoped(client)
                body = {"source": "s3", "name": "S3 fixture", "configuration": {
                    "authentication": "key", "access_key": "local-fixture", "secret_key": "local-fixture",
                    "region": "us-east-1", "bucket": "fixture", "endpoint": endpoint, "prefix": "retail/"}}
                assert ok(client.post(base + "/sources/test", json=body))["asset_count"] == 0
                data = ok(client.post(base + "/sources/connections", json=body))
                link = base + "/sources/connections/" + data["id"]
                asset = ok(client.get(link + "/assets"))["items"][0]
                assert asset["name"] == "retail/customers.csv"
                assert all(path == "/fixture" for path in requests)
                assert len(ok(client.post(link + "/preview", json={"asset": asset["id"]}))["rows"]) == 2
                ok(client.post(link + "/select", json={"assets": [asset["id"]]}))
                catalog = ok(client.post(base + "/metadata/extract"))
                assert list(catalog["tables"]) == [asset["id"]]
                assert catalog["tables"][asset["id"]]["relationship_origin"] == "inferred"
                ok(client.post(base + "/metadata/analyze"))
                ok(client.post(base + "/ontology/draft", json={"mode": "schema"}))
                ok(client.post(base + "/ontology/draft/save"))
                assert ok(client.post(base + "/ontology/validate"))["ok"]
                assert build(client, base)["ok"]
        finally:
            server.shutdown()
            thread.join()


def test_bigquery_preview_checks_scan_budget(monkeypatch):
    from types import SimpleNamespace
    from kg_pipeline.core.schema_models import ColumnInfo, SchemaCatalog, TableInfo
    from kg_pipeline.preprocessing.connectors.bigquery_source import BigQuerySource

    bigquery = pytest.importorskip("google.cloud.bigquery")
    remote = Mock()
    job = Mock()
    job.done.return_value = True
    job.result.return_value = SimpleNamespace(pages=[[{"customer_id": 1}]])
    cap = 64 * 1024 * 1024
    remote.query.side_effect = [SimpleNamespace(total_bytes_processed=cap + 1),
                                SimpleNamespace(total_bytes_processed=123), job]
    monkeypatch.setattr(bigquery, "Client", Mock(return_value=remote))
    source = BigQuerySource("fixture-project", "retail")
    name = "retail.customers"
    source.catalog = SchemaCatalog(tables={name: TableInfo(
        name=name, source_path="fixture-project." + name,
        columns={"customer_id": ColumnInfo(name="customer_id", pg_type="bigint")})})
    try:
        with pytest.raises(ValueError, match="scan cap"):
            source.sample_rows(name, 1)
        assert remote.query.call_count == 1
        assert source.sample_rows(name, 1) == [{"customer_id": 1}]
        calls = remote.query.call_args_list
        assert calls[0].kwargs["job_config"].dry_run
        assert calls[-1].kwargs["job_config"].maximum_bytes_billed == cap
        assert calls[-1].args[0].endswith("LIMIT 1")
    finally:
        source.close()


def test_business_insights_customer360_workspace_quality_and_graph(client, app):
    base = approved(client)
    endpoint = base + "/insights"
    table = next(name for name in ok(client.get(endpoint))["tables"] if name.endswith(".accounts"))
    source = ok(client.get(endpoint, params={"table": table}))
    assert source["graph"] is None
    assert source["scanned"] > 0
    assert source["quality"] == []
    assert ok(client.get(endpoint, params={"table": table})) == source
    assert ok(client.get(endpoint, params={"table": table, "refresh": True}))["refreshed_at"] != source["refreshed_at"]
    assert client.get(endpoint, params={"table": "public.not_owned"}).status_code == 422
    assert client.get(endpoint, params={"table": table, "measure": "account_id"}).status_code == 422

    from backend.app.core.security import create_access_token
    token = create_access_token(app.state.config, "another-user")
    assert client.get(endpoint, headers={"Authorization": f"Bearer {token}"}).status_code == 404
    assert client.get(endpoint, headers={"Authorization": ""}).status_code == 401

    report = build(client, base)
    assert report["ok"]
    result = ok(client.get(endpoint, params={"table": table}))
    graph = result["graph"]
    assert graph["topology"]["total_nodes"] > 0
    assert all(row["id"].startswith("Entity ") and set(row["properties"]) == {"label"}
               for row in graph["topology"]["nodes"])
    assert graph["relationships"] and graph["most_connected"] and graph["communities"]
    assert result["quality"]
    assert all(set(row) == {"dataset", "issue", "count", "severity"} for row in result["quality"])
    filtered = ok(client.get(endpoint, params={"entity_type": graph["entity_types"][0]}))
    assert len(filtered["graph"]["entities"]) == 1
    snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
    from_snapshot = ok(client.get(endpoint, params={"ontology_id": snapshot["ontology_id"], "build_id": snapshot["build_id"]}))
    assert from_snapshot["graph"]["topology"]["total_nodes"] == graph["topology"]["total_nodes"]


def test_business_insights_supply_chain_filters_and_bounded_profile(client, monkeypatch):
    base = scoped(client)
    rows = ["shipment_id,status,ship_date,units,supplier_name"]
    for index in range(12):
        status = "Late" if index < 6 else "On time"
        month = "01" if index % 2 == 0 else "02"
        rows.append(f"{index + 1},{status},2026-{month}-01,{index + 10},Private Name")
    ok(client.post(base + "/sources/upload", files=[("files", ("shipments.csv", "\n".join(rows), "text/csv"))]))
    endpoint = base + "/insights"
    initial = ok(client.get(endpoint))
    assert initial["scanned"] == 12
    assert initial["graph"] is None
    assert "Private Name" not in json.dumps(initial)
    assert {field["name"] for field in initial["fields"]} == {"status", "ship_date", "units"}
    assert {item["label"]: item["records"] for item in initial["distribution"]} == {"Late": 6, "On time": 6}
    assert [item["label"] for item in initial["trends"]] == ["2026-01", "2026-02"]
    result = ok(client.get(endpoint, params={
        "category": "Late", "start": "2026-01-01", "end": "2026-01-31", "minimum": 10,
    }))
    assert next(metric["value"] for metric in result["metrics"] if metric["label"] == "Matching records") == 3
    assert result["distribution"][0]["total"] == 36
    sparse = ok(client.get(endpoint, params={"minimum": 21}))
    assert sparse["distribution"] == []
    assert next(metric["value"] for metric in sparse["metrics"] if metric["label"] == "Matching records") is None
    assert client.get(endpoint, params={"start": "2026-03-01", "end": "2026-01-01"}).status_code == 422
    monkeypatch.setenv("KG_INSIGHTS_ROWS", "4")
    bounded = ok(client.get(endpoint, params={"refresh": True}))
    assert bounded["truncated"] and bounded["scanned"] == 4
    assert next(metric["value"] for metric in bounded["metrics"] if metric["label"] == "Total records") is None


def test_business_insights_generic_and_empty_datasets(client, app, monkeypatch):
    from uuid import UUID
    base = scoped(client)
    endpoint = base + "/insights"
    assert ok(client.get(endpoint))["tables"] == []
    ok(client.post(base + "/sources/upload", files=[("files", ("generic.csv", "id,note\n1,text\n2,other\n3,more", "text/csv"))]))
    result = ok(client.get(endpoint))
    assert result["scanned"] == 3
    assert result["fields"] == result["distribution"] == result["trends"] == []
    source = app.state.sessions.get(UUID(base.rsplit("/", 1)[1])).ctx.source
    monkeypatch.setattr(source, "iter_batches", lambda *args: iter(()))
    empty = ok(client.get(endpoint, params={"refresh": True}))
    assert empty["scanned"] == 0 and not empty["truncated"]
    monkeypatch.setattr(source, "iter_batches", Mock(side_effect=RuntimeError("Secret provider details")))
    failure = client.get(endpoint, params={"refresh": True})
    assert failure.status_code == 502 and "Secret provider details" not in failure.text


def test_business_insights_does_not_combine_currencies(client):
    base = scoped(client)
    csv = "id,currency,amount\n1,USD,10\n2,USD,20\n3,USD,30\n4,EUR,5\n5,EUR,15\n6,EUR,25"
    ok(client.post(base + "/sources/upload", files=[("files", ("transactions.csv", csv, "text/csv"))]))
    mixed = ok(client.get(base + "/insights"))
    assert next(metric["value"] for metric in mixed["metrics"] if metric["label"] == "Total amount") is None
    assert all(group["total"] is None for group in mixed["distribution"])
    single = ok(client.get(base + "/insights", params={"category": "USD"}))
    metric = next(metric for metric in single["metrics"] if metric["label"] == "Total amount")
    assert (metric["value"], metric["unit"]) == (60, "USD")


def test_workspace_graph_questions_validate_plans_run_read_only_and_exclude_results_from_ai(client, app, monkeypatch):
    from backend.app.services import graph_questions
    from backend.app.core.security import create_access_token
    monkeypatch.setenv("KG_GRAPH_AI_ENABLED", "true")
    monkeypatch.setenv("KG_GRAPH_AI_PROVIDER", "groq")
    base = approved(client)
    assert build(client, base)["ok"]
    endpoint = base + "/graphs/questions"
    assert ok(client.get(endpoint + "/suggestions"))
    mock = Mock(side_effect=[{"operation": "count_entities", "label": "Account"}, {"fact_ids": [2, 1]}])
    monkeypatch.setattr(graph_questions, "model_completion", mock)
    result = ok(client.post(endpoint, json={"question": "How many accounts?", "previous_question": "Show accounts"}))
    assert result["count"] > 0 and result["plan"]["operation"] == "count_entities"
    assert result["explanation_source"] == "ai_evidence_selection"
    assert mock.call_args_list[0].args[1]["previous_question"] == "Show accounts"
    assert set(mock.call_args_list[1].args[1]) == {"facts"}
    assert all(row["entity"] not in str(mock.call_args_list[1].args[1]) for row in result["rows"])
    assert client.post(endpoint, json={"question": "Show accounts"}, headers={
        "Authorization": "Bearer " + create_access_token(app.state.config, "another-user"),
    }).status_code == 404
    for plan in ({"operation": "delete", "label": "Account"},
                 {"operation": "entities", "label": "Unknown"},
                 {"operation": "entities", "label": "Account", "property": "password", "contains": "secret"}):
        monkeypatch.setattr(graph_questions, "model_completion", Mock(return_value=plan))
        assert client.post(endpoint, json={"question": "Show accounts"}).status_code == 422
    monkeypatch.setattr(graph_questions, "model_completion", Mock(return_value={"operation": "clarify"}))
    result = ok(client.post(endpoint, json={"question": "What about them?"}))
    assert result["plan"]["operation"] == "clarify" and result["rows"] == []
    monkeypatch.setattr(graph_questions, "MAX_NODES", 0)
    assert client.post(endpoint, json={"question": "Show accounts"}).status_code == 422


def test_graph_question_filters_are_literal_and_provider_failure_does_not_change_graph(client, monkeypatch):
    import networkx as nx
    from backend.app.dto.graph_questions import GraphQueryPlan
    from backend.app.services import graph_questions
    graph = nx.MultiDiGraph()
    graph.add_edge("first", "second", key="contains", type="Contains")
    graph.nodes["first"].update(label="Container", name="a [label]")
    graph.nodes["second"].update(label="Item")
    match = GraphQueryPlan(operation="relationships", label="Container", relationship="Contains",
                           target_label="Item", property="name", contains="[label]")
    assert graph_questions.run_plan(graph, match) == (1, [("first", "second", "contains")])
    assert graph_questions.run_plan(graph, match.model_copy(update={"contains": "unknown"})) == (0, [])
    base = approved(client)
    assert build(client, base)["ok"]
    monkeypatch.setenv("KG_GRAPH_AI_ENABLED", "false")
    response = client.post(base + "/graphs/questions", json={"question": "Show accounts"})
    assert response.status_code == 503 and response.json()["error"]["code"] == "graph_ai_unconfigured"
    assert ok(client.get(base + "/graphs/data"))["total_nodes"] > 0


def test_graph_questions_rules_and_ollama_fallback(client, monkeypatch):
    from backend.app.exceptions.handlers import ApiError
    from backend.app.services import graph_questions
    monkeypatch.setenv("KG_GRAPH_AI_ENABLED", "true")
    monkeypatch.setenv("KG_GRAPH_AI_PROVIDER", "rules")
    base = approved(client)
    assert build(client, base)["ok"]
    endpoint = base + "/graphs/questions"
    assert ok(client.get(endpoint + "/provider"))["ready"]
    question = ok(client.get(endpoint + "/suggestions"))[0]
    answer = ok(client.post(endpoint, json={"question": question}))
    assert answer["provider"] == "rules" and answer["count"] > 0
    overview = ok(client.post(endpoint, json={"question": "Summarize graph insights."}))
    assert overview["rows"][0]["metric"] == "Entities"
    edge = ok(client.get(base + "/graphs/data"))["edges"][0]
    path = ok(client.post(endpoint, json={"question": f'Find the shortest path from "{edge["source"]}" to "{edge["target"]}".'}))
    assert path["count"] == 1 and path["graph"]["edges"]
    monkeypatch.setenv("KG_GRAPH_AI_PROVIDER", "ollama")
    unavailable = Mock(side_effect=ApiError(503, "ollama_unreachable", "Cannot reach Ollama."))
    monkeypatch.setattr(graph_questions.ollama_provider, "check", unavailable)
    assert ok(client.get(endpoint + "/provider"))["fallback"]
    fallback = ok(client.post(endpoint, json={"question": question}))
    assert fallback["provider"] == "rules" and "Cannot reach Ollama" in fallback["notice"]
    unsupported = ok(client.post(endpoint, json={"question": "Predict next year's sales."}))
    assert unsupported["plan"]["operation"] == "clarify" and unsupported["rows"] == []
    completion = Mock(side_effect=[{"operation": "count_entities", "label": answer["plan"]["label"]}, {"fact_ids": [1, 2]}])
    monkeypatch.setattr(graph_questions.ollama_provider, "complete", completion)
    generated = ok(client.post(endpoint, json={"question": "How many of those?", "previous_question": question}))
    assert generated["provider"] == "ollama" and generated["count"] == answer["count"]


def test_ollama_transport_checks_tag_and_uses_local_json(monkeypatch):
    from backend.app.exceptions.handlers import ApiError
    from backend.app.services import ollama_provider
    monkeypatch.setenv("KG_GRAPH_AI_MODEL", "test-model:7b")
    request = Mock(side_effect=[{"models": [{"name": "test-model:7b"}]},
                                {"message": {"content": '{"operation":"clarify"}'}}])
    monkeypatch.setattr(ollama_provider, "request", request)
    assert ollama_provider.complete("instruction", {"question": "question"}) == {"operation": "clarify"}
    assert request.call_args_list[0].args == ("/api/tags",)
    payload = request.call_args_list[1].args[1]
    assert payload["model"] == "test-model:7b" and payload["format"] == "json" and not payload["stream"]
    request.side_effect = None
    request.return_value = {"models": []}
    with pytest.raises(ApiError) as error:
        ollama_provider.check()
    assert error.value.code == "ollama_model_missing"


def test_durable_workspace_reopens_saved_progress_and_snapshot(tmp_path, monkeypatch):
    from backend.app.core.security import create_access_token
    from backend.app.services.builds import BuildRunner

    settings = make_settings(storage_root=tmp_path, workflow_policy="poc_validation_only")
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        client.headers.update(login_headers(client))
        base = prepared(client)
        sid = base.rsplit("/", 1)[-1]
        domain = ok(client.post("/api/v1/domains", json={
            "name": "Recovery template", "project": "Recovery", "business_questions": ["What is connected?"]
        }), 201)
        ok(client.put(base + "/scope", json={
            "domain_id": domain["id"], "project": "Recovery", "business_questions": ["What is connected?"]
        }))
        ok(client.post(base + "/metadata/extract"))
        ok(client.post(base + "/metadata/analyze"))
        ok(client.post(base + "/ontology/draft", json={"mode": "schema", "name": "Recovery graph"}))
        ok(client.post(base + "/ontology/draft/save"))
        assert ok(client.post(base + "/ontology/validate"))["ok"]
        assert build(client, base)["ok"]
        snapshot = ok(client.post(base + "/graphs/snapshots", json={}))
        completed = ok(client.get(base))["completed_stages"]

    replay = Mock(side_effect=AssertionError("Recovery must not submit jobs"))
    monkeypatch.setattr(BuildRunner, "_submit", replay)
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        client.headers.update(login_headers(client))
        assert client.get(base).status_code == 404
        [inactive] = ok(client.get("/api/v1/workspaces"))
        assert inactive["historical_stages"] == completed and not inactive["active"]
        path = "/api/v1/workspaces/" + sid + "/reopen"
        other = {"Authorization": "Bearer " + create_access_token(settings, "another-user")}
        assert ok(client.get("/api/v1/workspaces", headers=other)) == []
        assert client.post(path, headers=other).status_code == 404
        recovered = ok(client.post(path))
        assert recovered["domain_id"] == domain["id"]
        assert recovered["reconnect_required"]
        assert recovered["historical_stages"] == completed
        assert set(recovered["completed_stages"]) == {1, 3, 4, 5, 8, 10}
        assert ok(client.get(base + "/ontology/draft"))["name"] == "Recovery graph"
        assert ok(client.get(base + "/ontology/validation"))["ok"]
        assert client.post(base + "/builds/stages/11", json={}).status_code == 409
        assert client.post(base + "/builds/stages/12", json={}).status_code == 409
        params = recovered["snapshot"]
        assert params == {key: snapshot[key] for key in ("ontology_id", "build_id")}
        assert client.get(base + "/graphs/data", params=params, headers=other).status_code == 404
        assert ok(client.get(base + "/graphs/data", params=params))["total_nodes"] == snapshot["nodes"]
        entities = base + "/graphs/entities"
        neighborhood = base + "/graphs/entity-neighborhood"
        assert {"Customer", "Account", "Bank"} <= set(ok(client.get(entities, params=params))["types"])
        for value, label in [("C001", "Customer"), ("A100", "Account"), ("HDFC", "Bank")]:
            [match] = ok(client.get(entities, params={**params, "q": value}))["matches"]
            assert match["label"] == label
            view = ok(client.get(neighborhood, params={**params, "node_id": match["id"], "hops": 3}))
            assert view["ontology"]["name"] == "Recovery graph"
            assert view["root"]["incoming"] + view["root"]["outgoing"] > 0
            assert view["graph"]["edges"]
        assert ok(client.get(entities, params={**params, "q": "c001"}))["matches"] == []
        assert client.get(neighborhood, params={**params, "node_id": "Missing"}).status_code == 404
        assert client.get(entities, params=params, headers=other).status_code == 404
        assert ok(client.post(path))["snapshot"] == params
        assert not replay.called

        ok(upload_csv(client, base))
        assert not ok(client.get(base))["reconnect_required"]
        assert 8 not in ok(client.get(base))["completed_stages"]
        ok(client.post(base + "/metadata/extract"))
        ok(client.post(base + "/metadata/analyze"))
        assert ok(client.get(base + "/ontology/draft"))["name"] == "Recovery graph"
        assert ok(client.get(base + "/graphs/data", params=params))["total_nodes"] == snapshot["nodes"]

    (tmp_path / sid / "graphs" / snapshot["ontology_id"] / snapshot["build_id"] / "graph.json.gz").write_bytes(b"bad")
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        client.headers.update(login_headers(client))
        recovered = ok(client.post(path))
        assert recovered["snapshot"] is None
        assert any("integrity" in issue for issue in recovered["recovery_issues"])
        files = {
            artifact: artifact.read_bytes()
            for folder in ("working_drafts", "graphs")
            for artifact in (tmp_path / sid / folder).rglob("*")
            if artifact.is_file()
        }
        assert any(file.name == "manifest.json" for file in files)
        assert any(file.parent.name == "working_drafts" for file in files)
        delete_path = path.removesuffix("/reopen")
        assert client.delete(delete_path, headers=other).status_code == 404
        assert client.delete(delete_path).status_code == 204
        assert ok(client.get("/api/v1/workspaces")) == []
        assert ok(client.get("/api/v1/ontologies")) == []
        assert [item["id"] for item in ok(client.get("/api/v1/domains"))] == [domain["id"]]
        assert {file: file.read_bytes() for file in files} == files


def test_interrupted_jobs_and_legacy_artifacts_across_processes(tmp_path):
    import subprocess
    from pathlib import Path
    from uuid import UUID, uuid4
    from backend.app.repositories.library import register_workspace, save_working_draft
    from kg_pipeline.core.ontology_models import Ontology

    settings = make_settings(storage_root=tmp_path, workflow_policy="poc_validation_only")
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers.update(login_headers(client))
        sid = session(client)
        active = app.state.sessions.get(UUID(sid), "admin")
        active.job = {"id": "kept-job", "status": "publishing", "steps": [
            {"stage": 16, "status": "running", "started_at": "2026-11-25T08:00:00+00:00"},
        ], "events": []}
        active.ctx.source_info = {"mode": "postgres", "password": "must-not-persist"}
        active.checkpoint()
    legacy = uuid4()
    register_workspace(tmp_path, legacy, "admin", "Legacy workspace")
    save_working_draft(tmp_path / str(legacy), Ontology(
        ontology_id="legacy", name="Legacy draft", namespace="urn:legacy", created_by="admin",
    ))
    script = """
import json
import sys
from pathlib import Path
from uuid import UUID
from backend.tests.helpers import make_settings
from backend.app.repositories.sessions import SessionRepository
root, sid, legacy = sys.argv[1:]
repo = SessionRepository(make_settings(storage_root=Path(root), workflow_policy="poc_validation_only"))
session = repo.reopen(UUID(sid), "admin")
assert repo.reopen(UUID(sid), "admin") is session
draft = repo.reopen(UUID(legacy), "admin")
print(json.dumps({"job": session.job, "source": session.ctx.source_info, "draft": draft.saved_draft.name,
                  "stages": list(draft.ctx.completed), "issues": draft.recovery_issues}))
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), sid, str(legacy)],
                            cwd=ROOT, capture_output=True, text=True, check=True, timeout=45)
    output = json.loads(result.stdout)
    assert output["job"]["status"] == "interrupted" and output["job"]["id"] == "kept-job"
    [interrupted] = output["job"]["steps"]
    assert interrupted["status"] == "interrupted" and "duration_ms" not in interrupted
    assert output["job"]["events"][-1]["severity"] == "warning"
    assert output["source"] == {"mode": "postgres", "credential_reference": None}
    assert output["draft"] == "Legacy draft" and not output["stages"] and output["issues"]
    assert b"must-not-persist" not in (tmp_path / "library.sqlite3").read_bytes()
