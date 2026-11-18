"""Page layout: theme CSS, stage header cards, prerequisite guard, activity log, navigation."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from components.bootstrap import get_ctx
from kg_pipeline.core.context import PARTS
from kg_pipeline.core.context import STAGES
from kg_pipeline.core.context import PipelineContext

PAGE_FILES = {s["no"]: f"pages/s{s['no']:02d}_{s['key']}.py" for s in STAGES}
BY_NO = {s["no"]: s for s in STAGES}
PART_COLORS = {"A": "#1F4E79", "B": "#6B4C9A", "C": "#2E7D4F"}

# What / Why / Input / Output / Tools shown at the top of every stage page.
STAGE_DOCS: dict[int, dict] = {
    1: dict(what="Agree the business questions, the tables in scope, the sensitive columns and the users.",
            why="The questions decide which tables and links matter. A frozen scope stops the graph growing "
                "into something slow that nobody uses.",
            input="Business owner + database owner knowledge", output="Scope sheet", tools="Shared document"),
    2: dict(what="Open a READ-ONLY connection (ideally to a read replica) with a statement timeout, or load "
                 "several CSV files at once as read-only in-memory tables.",
            why="The pipeline must never change business data or slow down live applications. Uploaded files "
                "are checked (size, rows, encoding) and never written to disk.",
            input="Host, database, read-only user (password from env / vault) - or several CSV files",
            output="Live DataSource handle (+ keys and links inferred from files)",
            tools="psycopg 3, psycopg_pool, csv"),
    3: dict(what="Read tables, columns, types, primary keys, foreign keys and row estimates from pg_catalog.",
            why="Keys and links already describe most of the graph. The catalog feeds the editor, the AI, "
                "validation and the SQL whitelist. No business data is read here.",
            input="Database connection", output="SchemaCatalog (storage/catalog/catalog.json)",
            tools="pg_catalog SQL"),
    4: dict(what="Classify each table (entity / event / bridge / lookup / log) and find undeclared foreign keys.",
            why="Different table kinds become different graph things. A bridge table must become edges, "
                "not a node type.",
            input="SchemaCatalog", output="Table types + relationship candidates", tools="Python rules"),
    5: dict(what="Define classes, attributes (types, required, PII), relationships (direction, cardinality) "
                 "and the mapping to tables/columns.",
            why="The ontology is the rulebook: it fixes exactly what the graph contains, so every build has "
                "the same shape.",
            input="SchemaCatalog (drop-downs)", output="Draft ontology", tools="Pydantic model"),
    6: dict(what="Send the schema STRUCTURE (+ optional masked samples, never PII) to Groq and get missing "
                 "classes, relationships, attributes and duplicates.",
            why="The AI drafts in seconds and notices links people miss. Every suggestion is checked against "
                "the real schema; nothing is applied automatically.",
            input="Draft ontology + SchemaCatalog", output="Labelled suggestions (valid / needs review / invalid)",
            tools="Groq structured outputs (strict JSON schema)"),
    7: dict(what="Approve, edit or reject each suggestion and merge the result with the manual work.",
            why="People are responsible for meaning. The origin of every item (manual / ai / hybrid) is "
                "recorded for audit.",
            input="Draft + suggestions", output="Hybrid draft", tools="Review screen"),
    8: dict(what="Structural checks (names, duplicates, references, cycles) and semantic checks against the "
                 "real database and the approved version.",
            why="A broken rulebook builds a broken graph. Catching it here costs seconds.",
            input="Hybrid draft + SchemaCatalog", output="Validation report (errors block approval)",
            tools="Validator"),
    9: dict(what="Save the draft as a new immutable version and approve it with a second person (four-eyes).",
            why="We must always know which rulebook produced a graph, and be able to roll back.",
            input="Validated draft", output="Approved ontology version", tools="Ontology repository + audit log"),
    10: dict(what="Show exactly which table, key and columns feed every node type and edge type.",
             why="Everyone sees what will be read before it happens. The builder needs nothing else, so table "
                 "names are never hard-coded.",
             input="Approved ontology", output="Build plan", tools="Python"),
    11: dict(what="Read only the planned columns, in keyset batches, and record checkpoints and watermarks.",
             why="Batches keep memory and database load flat. Only-needed columns keep sensitive data out.",
             input="Build plan + connection", output="Staged rows + extraction stats", tools="psycopg keyset SQL"),
    12: dict(what="Check nulls, duplicate keys, duplicate entities, types, business rules and referential "
                  "integrity.",
             why="In a graph bad data becomes wrong structure: an orphan FK is an edge to nothing, a duplicate "
                 "customer splits one person in two.",
             input="Staged rows + ontology", output="Data quality report (block / quarantine / warn)",
             tools="Python (SQL / DuckDB push-down for big tables)"),
    13: dict(what="Trim and fix case, convert types, give every entity a stable id and merge records that share "
                  "a business key.",
             why="Duplicates and spelling variants give wrong counts, wrong central nodes and wrong groups.",
             input="Staged rows + DQ rules", output="Clean records, alias map, merges, quarantine",
             tools="Python (fuzzy matching later)"),
    14: dict(what="Pass 1 adds one node per clean record. Pass 2 adds one edge per relationship row.",
             why="This is where tables become a graph, following the approved ontology only.",
             input="Clean records + relationship rows", output="NetworkX MultiDiGraph", tools="NetworkX"),
    15: dict(what="Reconcile the graph with the source row counts and check it against the ontology rules.",
             why="Proves nothing was lost or wired wrongly before anyone uses the graph.",
             input="Graph + build stats", output="Pass / fail report", tools="NetworkX"),
    16: dict(what="Write a versioned snapshot (JSON + GraphML + manifest + quarantine) and move CURRENT only "
                  "if valid. Optionally push to Neo4j.",
             why="A NetworkX graph lives only in memory. Snapshots give restart, rollback and audit.",
             input="Validated graph", output="Graph store version (CURRENT)", tools="node-link JSON, GraphML, Neo4j"),
}

CSS = """
<style>
.block-container {padding-top: 1.6rem; max-width: 1350px;}
.kg-hero {background: linear-gradient(120deg,#0E2A47 0%,#1F4E79 55%,#2E7D9A 100%); color:#fff;
          border-radius:16px; padding:22px 28px; margin-bottom:18px;}
.kg-hero h1 {color:#fff; font-size:1.75rem; margin:0 0 6px 0;}
.kg-hero p {color:#DCE8F5; margin:0; font-size:0.98rem;}
.kg-badge {display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.75rem; font-weight:600;
           margin-right:6px; background:rgba(255,255,255,0.18); color:#fff;}
.kg-card {background:#fff; border:1px solid #E3E8EF; border-radius:12px; padding:14px 16px; height:100%;
          box-shadow:0 1px 2px rgba(16,24,40,0.04);}
.kg-card h4 {margin:0 0 6px 0; font-size:0.78rem; letter-spacing:.06em; text-transform:uppercase; color:#5B6B7F;}
.kg-card p {margin:0; font-size:0.92rem; color:#1B2430;}
.kg-why {border-left:4px solid #2E7D4F; background:#F1F8F3;}
.kg-chip {display:inline-block; background:#EEF3F9; color:#1F4E79; border-radius:6px; padding:2px 8px;
          font-size:0.78rem; margin:2px 4px 2px 0;}
.kg-flow {display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 4px 0;}
.kg-step {border-radius:10px; padding:6px 10px; font-size:0.8rem; border:1px solid #D5DDE8; background:#fff;}
.kg-step.done {background:#E8F5EC; border-color:#7BC596;}
.kg-step.cur {background:#1F4E79; color:#fff; border-color:#1F4E79; font-weight:600;}
.kg-log {font-family: Consolas, monospace; font-size:0.82rem; padding:2px 0;}
.kg-log .warning {color:#B26A00;} .kg-log .error {color:#C62828;} .kg-log .info {color:#1B2430;}
div[data-testid="stMetric"] {background:#fff; border:1px solid #E3E8EF; border-radius:12px; padding:10px 14px;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _esc(s: str) -> str:
    return html.escape(str(s))


def flow_strip(ctx: PipelineContext, current: int | None = None) -> None:
    items = []
    for s in STAGES:
        cls = "cur" if s["no"] == current else ("done" if ctx.is_done(s["no"]) else "")
        mark = "✓ " if ctx.is_done(s["no"]) and s["no"] != current else ""
        items.append(f'<span class="kg-step {cls}">{mark}{s["no"]}. {_esc(s["title"])}</span>')
    st.markdown(f'<div class="kg-flow">{"".join(items)}</div>', unsafe_allow_html=True)


def stage_header(no: int) -> PipelineContext:
    ctx = get_ctx()
    s, d = BY_NO[no], STAGE_DOCS[no]
    status = "✅ completed" if ctx.is_done(no) else "⏳ not run yet"
    st.markdown(
        f'<div class="kg-hero" style="background:linear-gradient(120deg,#0E2A47 0%,{PART_COLORS[s["part"]]} 70%);">'
        f'<span class="kg-badge">Part {s["part"]} · {PARTS[s["part"]]}</span>'
        f'<span class="kg-badge">Stage {no} of {len(STAGES)}</span><span class="kg-badge">{status}</span>'
        f'<h1>{s["icon"]} {_esc(s["title"])}</h1><p>{_esc(d["what"])}</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2.2, 1.2, 1.2])
    c1.markdown(f'<div class="kg-card kg-why"><h4>Why we need it</h4><p>{_esc(d["why"])}</p></div>',
                unsafe_allow_html=True)
    c2.markdown(f'<div class="kg-card"><h4>Input</h4><p>{_esc(d["input"])}</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kg-card"><h4>Output</h4><p>{_esc(d["output"])}</p>'
                f'<div style="margin-top:6px">{"".join(f"<span class=kg-chip>{_esc(t.strip())}</span>" for t in d["tools"].split(","))}'
                f'</div></div>', unsafe_allow_html=True)
    flow_strip(ctx, no)
    return ctx


def guard(ctx: PipelineContext, *stages: int) -> bool:
    """Shows which earlier stage is missing (with a link) and returns False if any is."""
    missing = ctx.require(*stages)
    if missing is None:
        return True
    s = BY_NO[missing]
    st.warning(f"This stage needs **Stage {missing} · {s['title']}** first.")
    st.page_link(PAGE_FILES[missing], label=f"Go to Stage {missing} · {s['title']}", icon=s["icon"])
    return False


def activity(ctx: PipelineContext, stage: int, expanded: bool = True) -> None:
    events = [e for e in ctx.events if e["stage"] == stage]
    if not events:
        return
    with st.expander(f"📜 What happened in this stage ({len(events)} events)", expanded=expanded):
        icon = {"info": "•", "warning": "⚠", "error": "✖"}
        rows = "".join(f'<div class="kg-log"><span class="{e["level"]}">{e["time"]} {icon[e["level"]]} '
                       f'{_esc(e["message"])}</span></div>' for e in events[-40:])
        st.markdown(rows, unsafe_allow_html=True)


def next_stage(no: int) -> None:
    st.divider()
    cols = st.columns(2)
    if no > 1:
        p = BY_NO[no - 1]
        cols[0].page_link(PAGE_FILES[no - 1], label=f"← Stage {no - 1} · {p['title']}", icon=p["icon"])
    if no < len(STAGES):
        n = BY_NO[no + 1]
        cols[1].page_link(PAGE_FILES[no + 1], label=f"Stage {no + 1} · {n['title']} →", icon=n["icon"])


def table(rows, height: int | None = None, **kw) -> None:
    if rows is None or (hasattr(rows, "__len__") and len(rows) == 0):
        st.caption("(nothing to show)")
        return
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    for c in df.columns:                  # lists/dicts render poorly; show them as text
        if df[c].map(lambda v: isinstance(v, (list, dict, set, tuple))).any():
            df[c] = df[c].map(lambda v: ", ".join(map(str, v)) if isinstance(v, (list, set, tuple))
                              else (str(v) if isinstance(v, dict) else v))
    st.dataframe(df, width="stretch", hide_index=True, height=height or "auto", **kw)


def run_stage(fn, *args, success: str | None = None, **kwargs):
    """Runs a stage function and turns exceptions into a visible error instead of a crash."""
    try:
        with st.spinner("Running..."):
            result = fn(*args, **kwargs)
        if success:
            st.toast(success, icon="✅")
        return result
    except Exception as e:  # noqa: BLE001 - shown to the user
        st.error(f"{type(e).__name__}: {e}")
        return None


def sidebar_status(ctx: PipelineContext) -> None:
    with st.sidebar:
        done = len(ctx.completed)
        st.progress(done / len(STAGES), text=f"Pipeline progress: {done}/{len(STAGES)} stages")
        info = ctx.source_info
        if info:
            st.caption(f"🔌 {info.get('mode')} · {info.get('name')}")
        if ctx.approved_ontology is not None:
            st.caption(f"📘 ontology {ctx.approved_ontology.ontology_id} v{ctx.approved_ontology.version}")
        if ctx.graph is not None:
            st.caption(f"🕸️ graph {ctx.graph.number_of_nodes()} nodes · {ctx.graph.number_of_edges()} edges")
