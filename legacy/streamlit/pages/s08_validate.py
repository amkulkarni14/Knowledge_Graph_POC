import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.ontology_compiler import s08_ontology_validation as s8
from kg_pipeline.ontology_compiler.s09_ontology_repository import OntologyRepository

ctx = stage_header(8)
if guard(ctx, 7):
    draft = ctx.hybrid_draft
    approved = OntologyRepository().get_approved(draft.ontology_id)
    st.caption(f"Validating the hybrid draft of `{draft.ontology_id}`"
               + (f" against approved v{approved.version} (breaking-change checks)" if approved
                  else " (no approved version yet)"))
    if st.button("Run validation", type="primary"):
        run_stage(s8.run, ctx, approved)
    rep = ctx.ontology_report
    if rep is not None:
        (st.success if rep.ok else st.error)(f"**{rep.summary()}** — "
                                             + ("ready for approval in Stage 9." if rep.ok
                                                else "fix the errors (Stage 5 or 7) before approval."))
        c = st.columns(3)
        c[0].metric("Errors", rep.errors)
        c[1].metric("Warnings", rep.warnings)
        c[2].metric("Checks", "structural + semantic")
        if rep.issues:
            table([{"level": ("🔴 " if i.level == "error" else "🟡 ") + i.level, "kind": i.category, "code": i.code,
                    "where": i.path, "message": i.message} for i in rep.issues])
        else:
            st.info("No issues found.")
    with st.expander("Which checks run"):
        st.markdown("""
| Kind | Check | If it fails |
|---|---|---|
| Structural | duplicate class / attribute / relationship names | error |
| Structural | relationship points to a missing class | error |
| Structural | loop where `allow_cycles = false` | error |
| Semantic | mapped table / column does not exist | error |
| Semantic | attribute type cannot be read from column type | error |
| Semantic | class key is not the PK or a unique key | error |
| Semantic | required attribute on nullable column | warning |
| Semantic | relationship uses a link with no declared FK | warning (checked in Stage 12) |
| Semantic | type changed / class removed vs approved version | error / warning |
""")
activity(ctx, 8)
next_stage(8)
