import json

import streamlit as st

from components.graph_view import show_ontology
from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.ontology_compiler import s05_manual_ontology as s5
from kg_pipeline.ontology_compiler import s07_review_approval as s7

ctx = stage_header(7)
ICON = {"valid": "🟢", "needs_review": "🟡", "invalid": "🔴"}

if guard(ctx, 5, 6):
    items = [i for i in ctx.ai_items if i.kind != "duplicate"]
    dups = [i for i in ctx.ai_items if i.kind == "duplicate"]
    defaults = s7.default_decisions(ctx.ai_items)
    decisions: dict[str, dict] = {}

    if items:
        st.subheader("Decide on each suggestion")
        st.caption("Invalid items can only be accepted after editing. Edited items get origin = hybrid.")
        order = {"valid": 0, "needs_review": 1, "invalid": 2}
        for i in sorted(items, key=lambda x: (order[x.status], -x.confidence)):
            with st.container(border=True):
                a, b = st.columns([3, 1.2])
                a.markdown(f"{ICON[i.status]} **{i.label}** · `{i.kind}` · confidence **{i.confidence:.2f}**  \n"
                           f"_{i.rationale}_" + (f"  \n❗ {'; '.join(i.problems)}" if i.problems else ""))
                opts = ["approve", "edit", "reject"] if i.status != "invalid" else ["reject", "edit"]
                default = defaults.get(i.item_id, {"action": "reject"})["action"]
                action = b.radio("Decision", opts, index=opts.index(default) if default in opts else 0,
                                 key=f"dec_{i.item_id}", horizontal=True, label_visibility="collapsed")
                entry = {"action": action}
                if action == "edit":
                    txt = st.text_area("Edit the suggestion (JSON)", json.dumps(i.payload, indent=1),
                                       key=f"edit_{i.item_id}", height=180)
                    try:
                        entry["payload"] = json.loads(txt)
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
                        entry = {"action": "reject"}
                decisions[i.item_id] = entry
        if dups:
            st.info("Possible duplicates (informational): " + "; ".join(f"{d.label} — {d.rationale}" for d in dups))
    else:
        st.info("No AI suggestions: the manual draft goes forward unchanged (you can still add manual edits).")

    st.subheader("Manual edits on top (what makes it hybrid)")
    try:
        preview = s7.apply_decisions(ctx.manual_ontology, ctx.ai_items, decisions, "preview", ctx.catalog) \
            if items else ctx.manual_ontology
    except Exception as e:  # noqa: BLE001 - an edited payload may be incomplete while typing
        st.error(f"Edited suggestion cannot be applied yet: {type(e).__name__}: {e}")
        preview = ctx.manual_ontology
    self_refs = [r.key for r in preview.relationships if r.source_class == r.target_class]
    acyclic = st.multiselect("Relationships that must never form a loop", [r.key for r in preview.relationships],
                             default=self_refs)
    wm = st.text_input("Enable incremental loads with this watermark column where it exists", "updated_at")
    actor = st.text_input("Reviewed by (data modeller)", ctx.manual_ontology.created_by)
    if st.button("Build hybrid draft", type="primary"):
        run_stage(s7.run, ctx, decisions, actor=actor, acyclic_relationships=acyclic, watermark_column=wm or None,
                  success="Hybrid draft created")

    if ctx.hybrid_draft is not None:
        st.subheader("Hybrid draft")
        c1, c2 = st.columns([1, 1.1])
        with c1:
            table(s5.class_rows(ctx.hybrid_draft))
            table(s5.relationship_rows(ctx.hybrid_draft))
        with c2:
            show_ontology(ctx.hybrid_draft, 420)
activity(ctx, 7)
next_stage(7)
