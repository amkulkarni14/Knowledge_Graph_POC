"""Bounded in-process build execution with pollable status."""
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from time import monotonic
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import STAGE_FUNCTIONS, execute, require, rules_for


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

    def start(self, session, body):
        if not session.lock.acquire(blocking=False):
            raise ApiError(409, "session_busy", "Wait for the current operation")
        acquired = False
        try:
            require(session, 3, 9)
            rules_for(session, body)
            if not self.slots.acquire(blocking=False):
                raise ApiError(503, "build_capacity", "Build capacity reached; try again later")
            acquired = True
            with session.status_lock:
                session.job = {"id": str(uuid4()), "status": "queued", "stage": None, "progress": None, "error": None}
                initial = dict(session.job)
            self.pool.submit(self._run, session, body)
            return initial
        except Exception:
            if acquired:
                self.slots.release()
            session.lock.release()
            raise

    def _run(self, session, body):
        try:
            for stage in range(10, 16):
                with session.status_lock:
                    session.job.update(status="running", stage=stage, progress=None)
                run_stage(session, stage, body)
                if not session.ctx.is_done(stage):
                    with session.status_lock:
                        session.job["status"] = "blocked"
                    break
            else:
                with session.status_lock:
                    session.job["status"] = "completed"
        except ApiError as exc:
            with session.status_lock:
                session.job.update(status="failed", error={"code": exc.code, "message": exc.message})
        except Exception:
            with session.status_lock:
                session.job.update(status="failed", error={"code": "build_failed", "message": "Build failed"})
        finally:
            session.sync()
            session.touched = monotonic()
            session.lock.release()
            self.slots.release()

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=False)
