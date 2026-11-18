import pandas as pd
import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.preprocessing import s13_cleaning_er as s13

ctx = stage_header(13)
if guard(ctx, 12):
    if st.button("Clean, normalise and merge duplicates", type="primary"):
        run_stage(s13.run, ctx, success="Records cleaned")
    res = ctx.clean
    if res:
        m = st.columns(4)
        m[0].metric("Canonical records (future nodes)", len(res.records))
        m[1].metric("Duplicates merged", len(res.merges))
        m[2].metric("Rows quarantined", len(res.quarantine))
        m[3].metric("Values normalised", sum(s["values_changed"] for s in res.stats.values()))
        st.subheader("Per class")
        table([{"class": k, **v} for k, v in res.stats.items()])

        st.subheader("🔗 Entity resolution (one real thing = one node)")
        if res.merges:
            table(res.merges)
            for mg in res.merges:
                st.info(f"Edges that pointed to **{mg['merged']}** will be redirected to **{mg['into']}**; "
                        f"`merged_ids` on the node keeps the alias so the merge can be audited or undone.")
        else:
            st.caption("No duplicates found.")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Before → after (normalisation)")
            table(res.changes)
        with c2:
            st.subheader("Quarantine (set aside, not lost)")
            table(res.quarantine)
        st.subheader("Clean records")
        labels = sorted({r["label"] for r in res.records.values()})
        lbl = st.selectbox("Class", labels)
        rows = [{"node_id": k, **{x: y for x, y in v.items() if x != "label"}}
                for k, v in res.records.items() if v["label"] == lbl]
        st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)
        st.caption("Node id = `<Class>:<key>` so `customers.id = 5` and `products.id = 5` never collide, "
                   "and the same row gets the same id in every build.")
activity(ctx, 13)
next_stage(13)
