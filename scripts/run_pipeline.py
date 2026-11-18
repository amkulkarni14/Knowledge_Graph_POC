"""Run all 16 stages headless (same code the UI calls).

    python scripts/run_pipeline.py                 # in-memory sample data, offline AI fixture
    python scripts/run_pipeline.py --postgres      # PG* settings from env / .env
    python scripts/run_pipeline.py --use-groq      # real Groq call (needs GROQ_API_KEY)
    python scripts/run_pipeline.py --csv-dir data/samples/customer360   # every .csv in a folder, ontology drafted by rules
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_pipeline" / "src"))

from kg_pipeline.core.context import PipelineContext  # noqa: E402
from kg_pipeline.pipeline import run_all  # noqa: E402
from kg_pipeline.preprocessing.connectors.csv_source import CsvImportError
from kg_pipeline.preprocessing.connectors.csv_source import read_directory  # noqa: E402
from kg_pipeline.preprocessing import s02_connect  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--postgres", action="store_true")
    ap.add_argument("--use-groq", action="store_true")
    ap.add_argument("--csv-dir", help="folder with CSV files: each file becomes a table, the ontology is drafted")
    ap.add_argument("--project", default=None, help="project name (default: the folder name)")
    ap.add_argument("--author", default="data.modeller")
    ap.add_argument("--reviewer", default="reviewer.lead")
    args = ap.parse_args()

    csv_files, project = None, args.project or "Uploaded files"
    if args.csv_dir:
        try:
            csv_files = read_directory(args.csv_dir)
        except CsvImportError as e:
            print(f"Cannot read CSV files: {e}")
            return 2
        project = args.project or Path(args.csv_dir).resolve().name.replace("_", " ").title()
    try:
        ctx = run_all(PipelineContext(), postgres=s02_connect.env_defaults() if args.postgres else None,
                      use_groq=args.use_groq, author=args.author, reviewer=args.reviewer,
                      csv_files=csv_files, project=project)
    except CsvImportError as e:
        print(f"Cannot use the CSV files:\n{e}")
        return 2
    except ValueError as e:
        if not csv_files:
            raise
        print(f"Cannot build a graph from the CSV files:\n{e}")
        return 2
    for e in ctx.events:
        print(f"[{e['time']}] S{e['stage']:02d} {e['level']:7s} {e['message']}")
    if ctx.ontology_report is not None and not ctx.ontology_report.ok:
        for i in ctx.ontology_report.issues:
            print(" ", i.level, i.code, i.path, i.message)
    gr = ctx.graph_report
    if gr is None:
        print("\nPipeline stopped early; see the log above.")
        return 1
    print("\nnodes_by_class:", gr["nodes_by_class"])
    print("edges_by_type:", gr["edges_by_type"])
    print("errors:", gr["errors"])
    print("snapshot:", ctx.snapshot["path"], "published:", ctx.snapshot["published"])
    return 0 if gr["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
