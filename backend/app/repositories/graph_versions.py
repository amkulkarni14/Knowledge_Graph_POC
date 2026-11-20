"""PostgreSQL registry and atomic publication for persistent graph versions."""
import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.app.exceptions.handlers import ApiError


@contextmanager
def registry():
    dsn = os.getenv("KG_META_DSN")
    if not dsn:
        raise ApiError(503, "registry_unconfigured", "Set KG_META_DSN in the backend environment before publishing")
    try:
        with psycopg.connect(dsn, connect_timeout=5, row_factory=dict_row,
                             options="-c statement_timeout=10000") as connection:
            yield connection
    except (psycopg.errors.UndefinedTable, psycopg.errors.InvalidSchemaName):
        raise ApiError(503, "registry_schema_missing",
                       "Apply the PostgreSQL metadata schema and graph version migration") from None
    except psycopg.Error:
        raise ApiError(503, "registry_unavailable", "The graph version registry is unavailable") from None


def authorize(db, project, actor, lock=False, manage=False):
    sql = "SELECT * FROM kg_meta.graph_project AS p WHERE p.project_id = %s AND "
    parameters = (project, actor)
    if manage or lock:
        sql += "p.owner_name = %s"
    else:
        sql += """(p.owner_name = %s OR EXISTS (
            SELECT 1 FROM kg_meta.graph_project_member m
            JOIN kg_meta.app_user u ON u.username = m.username AND u.active
            WHERE m.project_id = p.project_id AND m.username = %s
        ))"""
        parameters += (actor,)
    row = db.execute(sql + (" FOR UPDATE" if lock else ""), parameters).fetchone()
    if row is None:
        raise ApiError(404, "project_not_found", "Graph project does not exist")
    return row


def register(db, session, actor, version, ctx, analytics, started_at):
    db.execute("""
        INSERT INTO kg_meta.graph_project (project_id, owner_name, name)
        VALUES (%s, %s, %s) ON CONFLICT (project_id) DO NOTHING
        """, (session.id, actor, session.name))
    authorize(db, session.id, actor, lock=True)
    graph = ctx.graph
    onto = ctx.approved_ontology
    validation = {key: len(ctx.graph_report[key]) for key in ("errors", "warnings")}
    source_id = (f"graphml:{graph.graph['import_digest']}" if graph.graph.get("import_origin") == "graphml"
                 else f"{session.id}:{session.source_version}")
    db.execute("""
        INSERT INTO kg_meta.graph_build
            (build_id, project_id, actor, ontology_id, ontology_version, mode, status,
             source_watermarks, node_count, edge_count, validation, rejected_count, source_id, analytics, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'staging', %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
        """, (version, session.id, actor, onto.ontology_id, onto.version, graph.graph.get("build_mode", "full"),
              Jsonb(graph.graph.get("source_watermarks", {})), graph.number_of_nodes(), graph.number_of_edges(),
              Jsonb(validation), len(ctx.build_stats.get("quarantine", [])),
              source_id, Jsonb(analytics), started_at))


def event(db, project, version, actor, action):
    db.execute("""
        INSERT INTO kg_meta.graph_version_event (project_id, build_id, actor, action)
        VALUES (%s, %s, %s, %s)
        """, (project, version, actor, action))


def list_projects(db, actor):
    return db.execute("""
        SELECT project_id, name, current_build_id FROM kg_meta.graph_project
        WHERE owner_name = %s OR project_id IN (
            SELECT m.project_id FROM kg_meta.graph_project_member m
            JOIN kg_meta.app_user u ON u.username = m.username AND u.active WHERE m.username = %s
        )
        ORDER BY name, project_id
        """, (actor, actor)).fetchall()


def list_versions(db, project, actor, offset, limit):
    entry = authorize(db, project, actor)
    versions = db.execute("""
        SELECT build_id, ontology_id, ontology_version, status, mode, actor, source_id, source_watermarks,
               node_count, edge_count, rejected_count, validation, started_at, finished_at, error_code
        FROM kg_meta.graph_build WHERE project_id = %s
        ORDER BY started_at DESC, build_id DESC OFFSET %s LIMIT %s
        """, (project, offset, limit)).fetchall()
    return {"current": entry["current_build_id"], "can_manage": entry["owner_name"] == actor, "versions": versions}


def user_password_hash(username):
    if not os.getenv("KG_META_DSN"):
        return None
    try:
        with registry() as db:
            row = db.execute("SELECT password_hash FROM kg_meta.app_user WHERE username = %s AND active",
                             (username,)).fetchone()
            return row["password_hash"] if row else None
    except ApiError:
        return None


def select_version(db, project, actor, version=None):
    entry = authorize(db, project, actor)
    row = db.execute("""
        SELECT * FROM kg_meta.graph_build WHERE project_id = %s AND build_id = %s AND status = 'ready'
        """, (project, version or entry["current_build_id"])).fetchone()
    if row is None:
        raise ApiError(404, "version_not_found", "Published graph version does not exist")
    return row


def publish(db, project, version, actor, *, restore=False):
    authorize(db, project, actor, lock=True)
    if restore:
        select_version(db, project, actor, version)
    else:
        result = db.execute("""
            UPDATE kg_meta.graph_build SET status = 'ready', finished_at = now()
            WHERE project_id = %s AND build_id = %s AND status = 'staging'
            """, (project, version))
        if result.rowcount != 1:
            raise ApiError(409, "version_state", "Graph version is no longer staging")
    db.execute("UPDATE kg_meta.graph_project SET current_build_id = %s WHERE project_id = %s", (version, project))
    event(db, project, version, actor, "restored" if restore else "published")


def fail(db, project, version, actor):
    result = db.execute("""
        UPDATE kg_meta.graph_build SET status = 'failed', finished_at = now(), error_code = 'persistence_failed'
        WHERE project_id = %s AND build_id = %s AND status = 'staging'
        """, (project, version))
    if result.rowcount:
        event(db, project, version, actor, "failed")


@contextmanager
def publication_guard(version):
    # Session locks survive the staging commit and release when the worker disconnects.
    with registry() as db:
        db.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (version,))
        db.commit()
        yield


def recover_interrupted():
    if not os.getenv("KG_META_DSN"):
        return
    try:
        with registry() as db:
            rows = db.execute("""
                SELECT project_id, build_id, actor FROM kg_meta.graph_build
                WHERE status = 'staging' AND project_id IS NOT NULL
                ORDER BY started_at LIMIT 100
                """).fetchall()
            for row in rows:
                claim = db.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS acquired",
                                   (row["build_id"],)).fetchone()
                if claim["acquired"]:
                    result = db.execute("""
                        UPDATE kg_meta.graph_build
                        SET status = 'failed', finished_at = now(), error_code = 'publication_interrupted'
                        WHERE project_id = %s AND build_id = %s AND status = 'staging'
                        """, (row["project_id"], row["build_id"]))
                    if result.rowcount:
                        event(db, row["project_id"], row["build_id"], row["actor"], "publication_interrupted")
    except ApiError:
        # The next maintenance pass can retry when metadata is available.
        return


def queue_delete(db, project, version, actor, retention_days):
    entry = authorize(db, project, actor, lock=True)
    if entry["current_build_id"] == version:
        raise ApiError(409, "current_version", "Restore another version before deleting the current graph")
    row = db.execute("""
        UPDATE kg_meta.graph_build SET status = 'deleting'
        WHERE project_id = %s AND build_id = %s AND (
            status IN ('deleting', 'delete_failed') OR
            (status IN ('ready', 'failed') AND finished_at < now() - make_interval(days => %s))
        )
        RETURNING build_id
        """, (project, version, retention_days)).fetchone()
    if row is None:
        raise ApiError(409, "retained_version", "This version is unavailable for deletion or is within the retention period")
    event(db, project, version, actor, "deletion_requested")


def finish_delete(db, project, version, actor, deleted):
    status = "deleted" if deleted else "delete_failed"
    db.execute("""
        UPDATE kg_meta.graph_build SET status = %s, analytics = CASE WHEN %s THEN NULL ELSE analytics END
        WHERE project_id = %s AND build_id = %s AND status = 'deleting'
        """, (status, deleted, project, version))
    if deleted:
        db.execute("DELETE FROM kg_meta.graph_workspace_item WHERE project_id = %s AND build_id = %s",
                   (project, version))
    event(db, project, version, actor, status)
