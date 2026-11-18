"""Stage 12 - Check data quality (driven by the approved ontology).

What : nulls, duplicate primary keys, duplicate entities (same business key),
       type validity, business rules, referential integrity of every relationship.
Why  : in a graph bad data becomes wrong STRUCTURE: an orphan FK -> edge to nothing,
       a duplicate customer -> one person split into two nodes.
Policy: each finding is  block (stop the build) | quarantine (set row aside) | warn.
Out  : ctx.dq_report

For very large tables push these checks into SQL / DuckDB and bring back aggregates.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable

from kg_pipeline.core.context import PipelineContext
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.preprocessing.transform import CoercionError
from kg_pipeline.preprocessing.transform import canon_key
from kg_pipeline.preprocessing.transform import coerce
from kg_pipeline.preprocessing.transform import normalize

RULES: dict[str, Callable[[Any, Any], bool]] = {
    "non_negative": lambda v, _: v is None or float(v) >= 0,
    "allowed_values": lambda v, allowed: v is None or str(v).strip().upper() in allowed,
}

# table -> [(column, rule, optional argument)]
DEFAULT_BUSINESS_RULES: dict[str, list[tuple]] = {
    "public.products": [("unit_price", "non_negative")],
    "public.orders": [("status", "allowed_values", {"PLACED", "SHIPPED", "DELIVERED", "CANCELLED"})],
}


def profile(onto: Ontology, source, batch_size: int = 5000,
            business_rules: dict[str, list[tuple]] | None = None) -> dict:
    business_rules = business_rules or {}
    report: dict = {"tables": {}, "referential_integrity": [], "findings": []}
    keysets: dict[str, set] = {}

    def finding(severity, table, check, detail, keys=None):
        report["findings"].append({"severity": severity, "table": table, "check": check, "detail": detail,
                                   "sample_keys": [str(k) for k in (keys or [])[:5]]})

    for cls in onto.classes:
        if not cls.mapping:
            continue
        m = cls.mapping
        cols = [a.source_column for a in cls.attributes if a.source_column] + m.resolution_columns
        nulls, pk_seen, dup_pk = Counter(), Counter(), []
        res_groups = defaultdict(list)
        bad_type, rule_fail = defaultdict(list), defaultdict(list)
        rows = 0
        for batch in source.iter_batches(m.source_table, cols, m.key_columns, batch_size):
            for r in batch:
                rows += 1
                key = canon_key(r[k] for k in m.key_columns)
                pk_seen[key] += 1
                if pk_seen[key] == 2:
                    dup_pk.append(key)
                for a in cls.attributes:
                    v = r.get(a.source_column)
                    if v is None:
                        nulls[a.name] += 1
                        continue
                    try:
                        coerce(normalize(v, a.normalize), a.data_type)
                    except CoercionError:
                        bad_type[a.name].append(key)
                if m.resolution_columns:
                    rk = tuple(normalize(r.get(c), "lower") for c in m.resolution_columns)
                    if all(x is not None for x in rk):
                        res_groups[rk].append(key)
                for col, rule, *arg in business_rules.get(m.source_table, []):
                    if not RULES[rule](r.get(col), arg[0] if arg else None):
                        rule_fail[f"{col}:{rule}"].append(key)
        keysets[cls.name] = set(pk_seen)
        dup_entities = {"|".join(k): [x[0] if len(x) == 1 else x for x in v]
                        for k, v in res_groups.items() if len(v) > 1}
        report["tables"][m.source_table] = {
            "class": cls.name, "rows": rows, "distinct_keys": len(pk_seen),
            "null_counts": dict(nulls), "duplicate_primary_keys": len(dup_pk),
            "duplicate_entities": dup_entities, "type_errors": sum(len(v) for v in bad_type.values()),
            "rule_failures": sum(len(v) for v in rule_fail.values()),
        }
        if dup_pk:
            finding("block", m.source_table, "duplicate_primary_key", f"{len(dup_pk)} keys appear twice", dup_pk)
        for a in cls.attributes:
            if a.required and nulls[a.name]:
                finding("quarantine", m.source_table, "required_null", f"{a.name}: {nulls[a.name]} rows")
        for attr, keys in bad_type.items():
            finding("quarantine", m.source_table, "type_invalid", attr, keys)
        for rule, keys in rule_fail.items():
            finding("quarantine", m.source_table, "business_rule", rule, keys)
        if dup_entities:
            finding("warn", m.source_table, "duplicate_entity",
                    f"{len(dup_entities)} group(s) share {m.resolution_columns}; merged in Stage 13",
                    list(dup_entities.values()))

    for rel in onto.relationships:
        src, tgt = onto.class_by_name(rel.source_class), onto.class_by_name(rel.target_class)
        if not (rel.mapping and src and tgt and src.name in keysets and tgt.name in keysets):
            continue
        mp = rel.mapping
        pk = source.introspect_schema().table(mp.table).primary_key or mp.source_key_columns + mp.target_key_columns
        null_fk, orphans = 0, []
        for batch in source.iter_batches(mp.table, mp.source_key_columns + mp.target_key_columns, pk, batch_size):
            for r in batch:
                s = canon_key(r[c] for c in mp.source_key_columns)
                t = canon_key(r[c] for c in mp.target_key_columns)
                if s is None or t is None:
                    null_fk += 1
                    continue
                if s not in keysets[src.name] or t not in keysets[tgt.name]:
                    orphans.append({"source": "|".join(s), "target": "|".join(t)})
        entry = {"relationship": rel.key, "table": mp.table, "null_references": null_fk,
                 "orphan_references": len(orphans)}
        report["referential_integrity"].append(entry)
        if orphans:
            finding("quarantine", mp.table, "orphan_reference", rel.key, orphans)
    return report


def run(ctx: PipelineContext, business_rules: dict[str, list[tuple]] | None = None) -> dict:
    if ctx.extraction is None:
        raise RuntimeError("Stage 11 must run first")
    rules = DEFAULT_BUSINESS_RULES if business_rules is None else business_rules
    rules = {t: r for t, r in rules.items() if t in ctx.catalog.tables}
    report = profile(ctx.approved_ontology, ctx.extraction.staged, business_rules=rules)
    report["business_rules"] = {t: [f"{c} {rule}" + (f" {sorted(a[0])}" if a else "") for c, rule, *a in r]
                                for t, r in rules.items()}
    report["rules"] = rules
    ctx.invalidate_from(12)
    ctx.dq_report = report
    sev = Counter(f["severity"] for f in report["findings"])
    ctx.log(12, f"Data quality: {sev.get('block', 0)} blocking, {sev.get('quarantine', 0)} quarantine, "
                f"{sev.get('warn', 0)} warning finding(s)",
            "error" if sev.get("block") else ("warning" if report["findings"] else "info"))
    if sev.get("block"):
        ctx.log(12, "Build blocked: fix the source data (duplicate primary keys) and re-run", "error")
        return report
    ctx.mark_done(12)
    return report
