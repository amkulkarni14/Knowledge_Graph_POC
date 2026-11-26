"""Bounded in-process build execution with pollable status."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from threading import BoundedSemaphore
from time import monotonic
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import STAGE_FUNCTIONS, execute, require, require_build_ontology, rules_for
from backend.app.services.graph_publication import persist
from backend.app.services.graphml_import import read_graphml

BUILD_STAGES = tuple(stage for stage in sorted(STAGE_FUNCTIONS) if stage >= 10)
PERSISTENCE_STAGE = 16


def execution_result(session, stage, result):
    """Small, durable summaries. Detailed reports stay on their existing endpoints."""
    if stage == 10:
        return {"entity_types": len(result["nodes"]), "relationship_types": len(result["edges"])}
    if stage == 11:
        return {"tables": result["tables"], "total_rows": result["total_rows"]}
    if stage == 12:
        tables = result["tables"]
        return {"tables": {
                    name: {**{key: value for key, value in table.items() if key != "duplicate_entities"},
                           "duplicate_entity_groups": len(table["duplicate_entities"])}
                    for name, table in tables.items()
                },
                "findings": dict(Counter(item["severity"] for item in result["findings"])),
                "checks": dict(Counter(item["check"] for item in result["findings"])),
                "business_rules_applied": sum(map(len, result["business_rules"].values()))}
    if stage == 15:
        return {**result, "errors": len(result["errors"]), "warnings": len(result["warnings"]),
                "checks": {"passed": sum(1 for check in result["checks"] if check["result"].endswith("pass")),
                            "total": len(result["checks"])}}
    if stage == PERSISTENCE_STAGE:
        return {"destination": "Neo4j", **(session.published_build or {}), **result}
    return result


def mark_step(job, stage, status, result=None):
    now = datetime.now(timezone.utc)
    steps = []
    for step in job["steps"]:
        if step["stage"] == stage:
            step = {**step, "status": status}
            if status == "running":
                step["started_at"] = now.isoformat()
            else:
                step["finished_at"] = now.isoformat()
                if step.get("started_at") and status != "interrupted":
                    step["duration_ms"] = max(0, round((now - datetime.fromisoformat(step["started_at"])).total_seconds() * 1000))
                if result is not None:
                    step["result"] = result
        steps.append(step)
    job["steps"] = steps
    severity, message = {
        "running": ("info", "Stage started."),
        "completed": ("success", "Stage completed."),
        "failed": ("error", "Stage stopped before completion."),
        "interrupted": ("warning", "Stage interrupted."),
        "skipped": ("warning", "Stage skipped."),
    }[status]
    job["events"] = [*job["events"], {"time": now.isoformat(), "stage": stage,
                                     "severity": severity, "message": message}]
    if status == "completed" and result:
        findings = result.get("findings")
        warnings = (findings.get("warn", 0) + findings.get("quarantine", 0)
                    if isinstance(findings, dict) else result.get("warnings"))
        if isinstance(warnings, int) and warnings > 0:
            job["events"] = [*job["events"], {"time": now.isoformat(), "stage": stage, "severity": "warning",
                                             "message": "Review the findings in the stage results."}]


def stage_result(session, stage):
    ctx = session.ctx
    if stage == 10:
        return ctx.build_plan
    if stage == 11:
        return {"tables": ctx.extraction.tables, "watermarks": ctx.extraction.watermarks,
                "total_rows": ctx.extraction.total_rows}
    if stage == 12:
        return {k: v for k, v in ctx.dq_report.items() if k != "rules"}
    if stage == 13:
        return {"stats": ctx.clean.stats, "merged": len(ctx.clean.merges),
                "quarantined": len(ctx.clean.quarantine), "records": len(ctx.clean.records)}
    if stage == 14:
        return {"nodes": ctx.graph.number_of_nodes(), "edges": ctx.graph.number_of_edges(),
                "stats": {k: v for k, v in ctx.build_stats.items() if k != "quarantine"},
                "quarantined": len(ctx.build_stats.get("quarantine", []))}
    if stage == 15:
        return ctx.graph_report
    raise ApiError(404, "stage_not_found", "This stage is not a build stage")


def run_stage(session, stage, body):
    if stage not in STAGE_FUNCTIONS or stage < 10:
        raise ApiError(404, "stage_not_found", "Choose a build stage from 10 through 15")
    kwargs = {}
    if stage == 11:
        kwargs["batch_size"] = body.batch_size

        def progress(i, total, table, rows):
            with session.status_lock:
                if session.job:
                    session.job["progress"] = {"table_index": i, "tables": total, "table": table, "rows": rows}
        kwargs["progress"] = progress
    if stage == 12:
        kwargs["business_rules"] = rules_for(session, body)
    execute(session, stage, STAGE_FUNCTIONS[stage], **kwargs)
    session.build_request = body.model_dump(mode="json")
    return jsonable_encoder(stage_result(session, stage))


class BuildRunner:
    def __init__(self, max_jobs):
        self.pool = ThreadPoolExecutor(max_workers=max_jobs, thread_name_prefix="kg-build")
        self.slots = BoundedSemaphore(max_jobs)

    def start(self, session, body, *, publish_as=None):
        return self._submit(session, body, publish_as)

    def start_publication(self, session, actor):
        return self._submit(session, None, actor)

    def start_graphml(self, session, actor, upload):
        return self._submit(session, None, actor, graphml=upload)

    def cancel(self, session, job_id):
        with session.status_lock:
            job = session.job
            if not job or job["id"] != str(job_id):
                raise ApiError(404, "job_not_found", "Build job does not exist")
            if job["status"] in ("queued", "running"):
                job["status"] = "cancelling"
            elif job["status"] != "cancelling":
                raise ApiError(409, "job_not_cancellable", "This build can no longer be cancelled")
            session.checkpoint()
            return dict(job)

    @staticmethod
    def _check_cancelled(session):
        if session.job["status"] == "cancelling":
            raise ApiError(409, "build_cancelled", "Build was cancelled")

    def _submit(self, session, body, actor, *, graphml=None):
        if not session.lock.acquire(blocking=False):
            raise ApiError(409, "session_busy", "Wait for the current operation")
        acquired = False
        try:
            if graphml is None and body is not None:
                require(session, 2, 3)
            require_build_ontology(session)
            if graphml is None and body is None:
                require(session, 14, 15)
            elif body is not None:
                rules_for(session, body)
            if not self.slots.acquire(blocking=False):
                raise ApiError(503, "build_capacity", "Build capacity reached; try again later")
            acquired = True
            started_at = datetime.now(timezone.utc)
            with session.status_lock:
                stages = BUILD_STAGES if body is not None else ()
                if actor is not None:
                    stages += (PERSISTENCE_STAGE,)
                session.job = {"id": str(uuid4()), "status": "queued", "stage": None, "progress": None,
                               "error": None, "started_at": started_at.isoformat(),
                               "steps": [{"stage": stage, "status": "pending"} for stage in stages],
                               "events": [{"time": started_at.isoformat(), "stage": None,
                                           "severity": "info", "message": "Execution queued."}]}
                initial = dict(session.job)
                if body is not None:
                    session.build_request = body.model_dump(mode="json")
                session.checkpoint()
            self.pool.submit(self._run, session, body, actor, initial["id"], started_at, graphml)
            return initial
        except Exception:
            if acquired:
                self.slots.release()
            session.lock.release()
            raise

    def _run(self, session, body, actor, version, started_at, graphml=None):
        status, error = "failed", None
        try:
            for stage in BUILD_STAGES if body is not None else ():
                with session.status_lock:
                    self._check_cancelled(session)
                    session.job.update(status="running", stage=stage, progress=None)
                    mark_step(session.job, stage, "running")
                    session.checkpoint()
                result = run_stage(session, stage, body)
                success = session.ctx.is_done(stage)
                with session.status_lock:
                    mark_step(session.job, stage, "completed" if success else "failed", execution_result(session, stage, result))
                session.checkpoint()
                if not success:
                    status = "blocked"
                    break
            else:
                if actor is not None:
                    with session.status_lock:
                        self._check_cancelled(session)
                        session.job.update(status="running", stage=PERSISTENCE_STAGE, progress=None)
                        mark_step(session.job, PERSISTENCE_STAGE, "running")
                        session.checkpoint()
                    def report(phase, processed):
                        with session.status_lock:
                            self._check_cancelled(session)
                            session.job.update(status="running", stage=PERSISTENCE_STAGE,
                                               progress={"phase": phase, "processed": processed})

                    def commit():
                        with session.status_lock:
                            self._check_cancelled(session)
                            session.job["status"] = "publishing"
                            session.checkpoint()

                    if graphml is None:
                        persist(session, actor, version, report, commit, started_at)
                        graph = session.ctx.graph
                    else:
                        report("validate_graphml", 0)
                        payload, label_key, relationship_key = graphml
                        ontology = require_build_ontology(session)
                        graph = read_graphml(payload, ontology, label_key, relationship_key)
                        context = replace(session.ctx, graph=graph, completed=set(session.ctx.completed),
                                          graph_report={"ok": True, "errors": [], "warnings": []},
                                          build_stats={"quarantine": []})
                        persist(session, actor, version, report, commit, started_at, context=context)
                    session.published_build = {"project_id": str(session.id), "version_id": version}
                    with session.status_lock:
                        mark_step(session.job, PERSISTENCE_STAGE, "completed",
                                  execution_result(session, PERSISTENCE_STAGE, {
                                      "nodes": graph.number_of_nodes(), "relationships": graph.number_of_edges(),
                                  }))
                with session.status_lock:
                    self._check_cancelled(session)
                    status = "completed"
        except ApiError as exc:
            status = "cancelled" if exc.code == "build_cancelled" else "failed"
            error = {"code": exc.code, "message": exc.message}
        except Exception:
            error = {"code": "build_failed", "message": "Build failed"}
        finally:
            try:
                with session.status_lock:
                    session.sync()
                    for step in session.job["steps"]:
                        if step["status"] == "running":
                            mark_step(session.job, step["stage"], "failed" if status == "failed" else "skipped")
                        elif step["status"] == "pending":
                            mark_step(session.job, step["stage"], "skipped")
                    session.job.update(status=status, error=error, finished_at=datetime.now(timezone.utc).isoformat())
                session.checkpoint()
            finally:
                session.touched = monotonic()
                session.lock.release()
                self.slots.release()

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=False)
