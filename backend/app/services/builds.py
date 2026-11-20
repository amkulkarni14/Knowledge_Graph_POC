"""Bounded in-process build execution with pollable status."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from threading import BoundedSemaphore
from time import monotonic
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import STAGE_FUNCTIONS, execute, require, rules_for
from backend.app.services.graph_publication import persist
from backend.app.services.graphml_import import read_graphml


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
            if graphml is not None:
                require(session, 9)
            elif body is None:
                require(session, 9, 14, 15)
            else:
                require(session, 3, 9)
                rules_for(session, body)
            if not self.slots.acquire(blocking=False):
                raise ApiError(503, "build_capacity", "Build capacity reached; try again later")
            acquired = True
            started_at = datetime.now(timezone.utc)
            with session.status_lock:
                session.job = {"id": str(uuid4()), "status": "queued", "stage": None, "progress": None,
                               "error": None, "started_at": started_at.isoformat()}
                initial = dict(session.job)
            self.pool.submit(self._run, session, body, actor, initial["id"], started_at, graphml)
            return initial
        except Exception:
            if acquired:
                self.slots.release()
            session.lock.release()
            raise

    def _run(self, session, body, actor, version, started_at, graphml=None):
        try:
            for stage in range(10, 16) if body is not None else ():
                with session.status_lock:
                    self._check_cancelled(session)
                    session.job.update(status="running", stage=stage, progress=None)
                run_stage(session, stage, body)
                if not session.ctx.is_done(stage):
                    with session.status_lock:
                        session.job["status"] = "blocked"
                    break
            else:
                if actor is not None:
                    def report(phase, processed):
                        with session.status_lock:
                            self._check_cancelled(session)
                            session.job.update(status="running", stage=16,
                                               progress={"phase": phase, "processed": processed})

                    def commit():
                        with session.status_lock:
                            self._check_cancelled(session)
                            session.job["status"] = "publishing"

                    if graphml is None:
                        persist(session, actor, version, report, commit, started_at)
                    else:
                        report("validate_graphml", 0)
                        payload, label_key, relationship_key = graphml
                        ontology = session.ctx.approved_ontology
                        if ontology is None:
                            raise ApiError(409, "ontology_required", "Approve an ontology before publishing GraphML")
                        graph = read_graphml(payload, ontology, label_key, relationship_key)
                        context = replace(session.ctx, graph=graph, completed=set(session.ctx.completed),
                                          graph_report={"ok": True, "errors": [], "warnings": []},
                                          build_stats={"quarantine": []})
                        persist(session, actor, version, report, commit, started_at, context=context)
                with session.status_lock:
                    self._check_cancelled(session)
                    session.job["status"] = "completed"
        except ApiError as exc:
            with session.status_lock:
                status = "cancelled" if exc.code == "build_cancelled" else "failed"
                session.job.update(status=status, error={"code": exc.code, "message": exc.message})
        except Exception:
            with session.status_lock:
                session.job.update(status="failed", error={"code": "build_failed", "message": "Build failed"})
        finally:
            with session.status_lock:
                session.job["finished_at"] = datetime.now(timezone.utc).isoformat()
            session.sync()
            session.touched = monotonic()
            session.lock.release()
            self.slots.release()

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=False)
