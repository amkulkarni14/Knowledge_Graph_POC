"""PipelineContext: the hand-off object passed from one stage to the next.

Every stage reads what earlier stages produced and writes its own output here.
The UI keeps one context per browser session; the CLI keeps one per run.
It also records an activity log so the UI can show *what is happening*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

STAGES: list[dict] = [
    # part A - prepare
    {"no": 1, "key": "scope", "title": "Goal & Scope", "part": "A", "icon": "🎯"},
    {"no": 2, "key": "connect", "title": "Connect Safely", "part": "A", "icon": "🔌"},
    {"no": 3, "key": "schema", "title": "Schema Extraction", "part": "A", "icon": "🗂️"},
    {"no": 4, "key": "analysis", "title": "Schema Analysis", "part": "A", "icon": "🔍"},
    # part B - ontology
    {"no": 5, "key": "manual", "title": "Manual Ontology", "part": "B", "icon": "✍️"},
    {"no": 6, "key": "ai", "title": "Groq AI Suggestions", "part": "B", "icon": "🤖"},
    {"no": 7, "key": "review", "title": "Review & Approve", "part": "B", "icon": "✅"},
    {"no": 8, "key": "validate", "title": "Ontology Validation", "part": "B", "icon": "🧪"},
    {"no": 9, "key": "repo", "title": "Ontology Versioning", "part": "B", "icon": "🗃️"},
    {"no": 10, "key": "plan", "title": "Build Plan", "part": "B", "icon": "🗺️"},
    # part C - build
    {"no": 11, "key": "extract", "title": "Data Extraction", "part": "C", "icon": "📥"},
    {"no": 12, "key": "quality", "title": "Data Quality", "part": "C", "icon": "🩺"},
    {"no": 13, "key": "clean", "title": "Clean & Entity Resolution", "part": "C", "icon": "🧹"},
    {"no": 14, "key": "build", "title": "Build NetworkX Graph", "part": "C", "icon": "🕸️"},
    {"no": 15, "key": "gvalidate", "title": "Graph Validation", "part": "C", "icon": "🛡️"},
    {"no": 16, "key": "store", "title": "Store Graph", "part": "C", "icon": "💾"},
]
PARTS = {"A": "Prepare", "B": "Ontology (rulebook)", "C": "Build the graph"}


@dataclass
class PipelineContext:
    # Stage 1
    scope: Any = None
    # Stage 2
    source: Any = None                 # DataSource (PostgresSource or SampleSource)
    source_info: dict = field(default_factory=dict)
    # Stage 3-4
    catalog: Any = None                # SchemaCatalog
    table_analysis: list = field(default_factory=list)
    # Stage 5-10
    manual_ontology: Any = None        # Ontology (draft)
    ai_items: list = field(default_factory=list)
    ai_meta: dict = field(default_factory=dict)
    hybrid_draft: Any = None           # Ontology after review decisions
    ontology_report: Any = None        # ValidationReport
    approved_ontology: Any = None      # Ontology (approved)
    build_plan: Any = None
    # Stage 11-16
    extraction: Any = None             # ExtractionResult
    dq_report: Any = None
    clean: Any = None                  # CleanResult
    graph: Any = None                  # nx.MultiDiGraph
    build_stats: Any = None
    graph_report: Any = None
    snapshot: Any = None               # manifest dict

    source_version: int = 0            # bumped whenever Stage 2 connects to a (new) source

    completed: set = field(default_factory=set)
    events: list = field(default_factory=list)

    def clear_results_from_schema(self) -> None:
        """A different source makes everything derived from the old one meaningless (Stages 3-16)."""
        self.catalog, self.table_analysis = None, []
        self.manual_ontology, self.ai_items, self.ai_meta = None, [], {}
        self.hybrid_draft = self.ontology_report = self.approved_ontology = self.build_plan = None
        self.extraction = self.dq_report = self.clean = self.graph = None
        self.build_stats = self.graph_report = self.snapshot = None

    def log(self, stage: int, message: str, level: str = "info") -> None:
        self.events.append({"time": datetime.now().strftime("%H:%M:%S"), "stage": stage,
                            "level": level, "message": message})

    def mark_done(self, stage: int) -> None:
        self.completed.add(stage)

    def invalidate_from(self, stage: int) -> None:
        """When an upstream stage is re-run, downstream results are no longer valid."""
        self.completed = {s for s in self.completed if s < stage}

    def is_done(self, stage: int) -> bool:
        return stage in self.completed

    def require(self, *stages: int) -> Optional[int]:
        """Returns the first missing prerequisite stage, or None."""
        return next((s for s in stages if s not in self.completed), None)
