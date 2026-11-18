"""Stage 13 - Clean the data and merge duplicates (entity resolution).

What : trim / case rules, type coercion to the ontology data type, required-value and
       business-rule checks, deterministic node ids, and merging of records that share
       an agreed business key (e.g. the same e-mail after cleaning).
Why  : graph algorithms count connections; duplicates and spelling variants give wrong
       counts, wrong "most important" nodes and wrong groups. Stable ids make builds
       comparable over time.
Out  : ctx.clean = CleanResult
         records[node_id] -> node attributes (ready for NetworkX)
         alias[class][source key] -> canonical node id (used to redirect edges)
         merges, changes (before/after), quarantine, per-class stats
"""
from __future__ import annotations

from dataclasses import dataclass, field

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.preprocessing.transform import CoercionError
from kg_pipeline.preprocessing.transform import canon_key
from kg_pipeline.preprocessing.transform import coerce
from kg_pipeline.preprocessing.transform import node_id
from kg_pipeline.preprocessing.transform import normalize
from kg_pipeline.preprocessing.s12_data_quality import RULES


@dataclass
class CleanResult:
    records: dict = field(default_factory=dict)
    alias: dict = field(default_factory=dict)
    merges: list = field(default_factory=list)
    changes: list = field(default_factory=list)
    quarantine: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def run(ctx: PipelineContext, max_changes_shown: int = 500) -> CleanResult:
    if not ctx.is_done(12):
        raise RuntimeError("Stage 12 must pass first (no blocking data quality findings)")
    onto, source = ctx.approved_ontology, ctx.extraction.staged
    rules = ctx.dq_report.get("rules", {})
    res = CleanResult()

    for cls in onto.classes:
        if not cls.mapping:
            continue
        m = cls.mapping
        st = res.stats.setdefault(cls.name, dict(rows=0, nodes=0, merged=0, quarantined=0, values_changed=0))
        alias = res.alias.setdefault(cls.name, {})
        canonical: dict[tuple, str] = {}
        cols = [a.source_column for a in cls.attributes if a.source_column] + m.resolution_columns
        for batch in source.iter_batches(m.source_table, cols, m.key_columns):
            for row in batch:
                st["rows"] += 1
                key = canon_key(row[k] for k in m.key_columns)
                nid = node_id(cls.name, key)
                try:
                    props = {}
                    for a in cls.attributes:
                        raw = row.get(a.source_column) if a.source_column else None
                        val = coerce(normalize(raw, a.normalize), a.data_type)
                        if a.required and val is None:
                            raise CoercionError(f"required attribute '{a.name}' is NULL")
                        if val is not None:
                            props[a.name] = val
                        if isinstance(raw, str) and val != raw:
                            st["values_changed"] += 1
                            if len(res.changes) < max_changes_shown:
                                res.changes.append({"node": nid, "attribute": a.name, "before": repr(raw),
                                                    "after": repr(val), "rule": a.normalize or "trim"})
                    for col, rule, *arg in rules.get(m.source_table, []):
                        if not RULES[rule](row.get(col), arg[0] if arg else None):
                            raise CoercionError(f"business rule {rule} failed on {col}={row.get(col)!r}")
                except CoercionError as e:
                    st["quarantined"] += 1
                    res.quarantine.append({"stage": "node", "class": cls.name, "table": m.source_table,
                                           "key": "|".join(key), "reason": str(e)})
                    continue

                if m.resolution_columns:
                    rk = tuple(normalize(row.get(c), "lower") for c in m.resolution_columns)
                    if None not in rk:
                        target = canonical.get(rk)
                        if target and target != nid:
                            alias[key] = target
                            node = res.records[target]
                            node.setdefault("merged_ids", []).append(nid)
                            filled = [k for k in props if k not in node]
                            for k in filled:                     # attribute fusion: first non-null wins
                                node[k] = props[k]
                            st["merged"] += 1
                            res.merges.append({"class": cls.name, "merged": nid, "into": target,
                                               "because": f"{', '.join(m.resolution_columns)} = {'|'.join(rk)}",
                                               "attributes filled": ", ".join(filled) or "-"})
                            continue
                        canonical[rk] = nid
                        props["_resolution_key"] = "|".join(rk)
                alias[key] = nid
                res.records[nid] = {"label": cls.name, "source_table": m.source_table,
                                    "source_key": "|".join(key), **props}
                st["nodes"] += 1

    ctx.invalidate_from(13)
    ctx.clean = res
    ctx.log(13, f"Cleaning: {len(res.records)} canonical records, {len(res.merges)} merged duplicate(s), "
                f"{len(res.quarantine)} row(s) quarantined, "
                f"{sum(s['values_changed'] for s in res.stats.values())} value(s) normalised")
    for mg in res.merges:
        ctx.log(13, f"Entity resolution: {mg['merged']} merged into {mg['into']} ({mg['because']})")
    ctx.mark_done(13)
    return res
