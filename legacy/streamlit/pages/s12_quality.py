import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.preprocessing import s12_data_quality as s12

ctx = stage_header(12)
SEV = {"block": "⛔ block", "quarantine": "🟠 quarantine", "warn": "🟡 warn"}

if guard(ctx, 11):
    st.markdown("**Business rules applied**")
    rules = {t: r for t, r in s12.DEFAULT_BUSINESS_RULES.items() if t in ctx.catalog.tables}
    enabled = {}
    cols = st.columns(max(len(rules), 1))
    for col, (t, rs) in zip(cols, rules.items()):
        keep = [r for r in rs if col.checkbox(f"{t}: {r[0]} {r[1]}", value=True, key=f"rule_{t}_{r[0]}")]
        if keep:
            enabled[t] = keep
    if st.button("Run data quality checks", type="primary"):
        run_stage(s12.run, ctx, business_rules=enabled)

    rep = ctx.dq_report
    if rep:
        f = rep["findings"]
        m = st.columns(4)
        m[0].metric("Blocking", sum(x["severity"] == "block" for x in f))
        m[1].metric("Quarantine", sum(x["severity"] == "quarantine" for x in f))
        m[2].metric("Warnings", sum(x["severity"] == "warn" for x in f))
        m[3].metric("Rows profiled", sum(t["rows"] for t in rep["tables"].values()))
        if any(x["severity"] == "block" for x in f):
            st.error("Build blocked: duplicate primary keys must be fixed in the source.")
        st.subheader("Findings and the action taken")
        table([{"severity": SEV[x["severity"]], "table": x["table"], "check": x["check"], "detail": x["detail"],
                "sample keys": ", ".join(x["sample_keys"])} for x in f])
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Per class profile")
            table([{"table": t, "class": p["class"], "rows": p["rows"], "distinct keys": p["distinct_keys"],
                    "nulls": ", ".join(f"{k}={v}" for k, v in p["null_counts"].items()) or "-",
                    "duplicate PK": p["duplicate_primary_keys"], "duplicate entities": len(p["duplicate_entities"]),
                    "type errors": p["type_errors"], "rule failures": p["rule_failures"]}
                   for t, p in rep["tables"].items()])
        with c2:
            st.subheader("Referential integrity per relationship")
            table([{"relationship": r["relationship"], "table": r["table"], "empty links": r["null_references"],
                    "orphans": ("❗ " if r["orphan_references"] else "") + str(r["orphan_references"])}
                   for r in rep["referential_integrity"]])
        with st.expander("SQL push-down equivalents for large tables"):
            st.code("""-- duplicate entities by normalised business key
SELECT lower(trim(email)) AS k, array_agg(customer_id) FROM public.customers GROUP BY 1 HAVING count(*) > 1;
-- orphan references for an undeclared FK
SELECT o.order_id, o.customer_id FROM public.orders o
LEFT JOIN public.customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL;
-- business rule
SELECT product_id, unit_price FROM public.products WHERE unit_price < 0;""", language="sql")
activity(ctx, 12)
next_stage(12)
