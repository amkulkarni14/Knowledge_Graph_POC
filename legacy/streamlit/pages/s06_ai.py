import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.config import settings
from kg_pipeline.ontology_compiler import s06_ai_suggestions as s6

ctx = stage_header(6)
STATUS_ICON = {"valid": "🟢 valid", "needs_review": "🟡 needs review", "invalid": "🔴 invalid"}

if guard(ctx, 5):
    st.warning("**Rule:** the AI only *suggests*. It never changes an approved ontology; every suggestion is "
               "checked against the real schema and a person decides in Stage 7.")
    c1, c2 = st.columns([1.3, 1])
    with c1:
        live = st.toggle("Call Groq live", value=False, disabled=not settings.groq_available,
                         help="Needs GROQ_API_KEY in the environment / .env. Off = recorded offline response.")
        from_files = ctx.source_info.get("mode") == "csv"
        if from_files and not live:
            st.caption("Uploaded files: the recorded offline response only fits the built-in sample database, so "
                       "it is not offered here. Set GROQ_API_KEY and switch on 'Call Groq live', or skip the AI "
                       "step - the ontology drafted from your files in Stage 5 is complete without it.")
        elif not settings.groq_available:
            st.caption("GROQ_API_KEY not set → the recorded offline response is used "
                       "(it contains deliberate hallucinations to show the backend guard).")
        samples = st.checkbox("Include masked sample values (max 3 rows, PII columns removed)", value=False)
        tables = st.multiselect("Tables the AI may see (allow-list)", list(ctx.catalog.tables),
                                default=list(ctx.catalog.tables))
        actor = st.text_input("Requested by", ctx.manual_ontology.created_by)
        b1, b2 = st.columns(2)
        if b1.button("🤖 Ask AI for suggestions", type="primary", width="stretch",
                     disabled=from_files and not live):
            run_stage(s6.run, ctx, actor=actor, use_groq=live, include_samples=samples,
                      allowed_tables=set(tables), success="Suggestions received")
        if b2.button("Skip AI (manual only)", width="stretch"):
            run_stage(s6.skip, ctx)
    with c2:
        st.markdown("**What is sent to the AI**")
        st.markdown("- table / column names, types, PK, FK, row estimates\n- current ontology (names only)\n"
                    "- optional masked samples: digits → 9, letters → x\n- never: PII columns, real values")
        st.markdown(f"Model: `{settings.groq_model}` · strict JSON schema · temperature 0.1 · retries with backoff")

    items = ctx.ai_items
    if ctx.is_done(6) and items:
        counts = {s: sum(i.status == s for i in items) for s in STATUS_ICON}
        m = st.columns(4)
        m[0].metric("Suggestions", len(items))
        m[1].metric("Valid", counts["valid"])
        m[2].metric("Need review", counts["needs_review"])
        m[3].metric("Invalid (blocked)", counts["invalid"])
        st.subheader("Labelled suggestions (backend review)")
        table([{"id": i.item_id, "kind": i.kind, "suggestion": i.label, "confidence": round(i.confidence, 2),
                "label": STATUS_ICON[i.status], "AI reason": i.rationale, "backend check": "; ".join(i.problems) or "ok"}
               for i in items])
        with st.expander("Exact context sent to the AI (structure only)"):
            st.json(ctx.ai_meta.get("context", {}), expanded=False)
        st.caption(f"Model {ctx.ai_meta.get('model')} · attempts {ctx.ai_meta.get('attempts')} · "
                   f"prompt hash {ctx.ai_meta.get('prompt_hash')} · logged to {settings.ai_log_path.name}")
    elif ctx.is_done(6):
        st.info("AI skipped. Stage 7 will use the manual draft as it is.")
activity(ctx, 6)
next_stage(6)
