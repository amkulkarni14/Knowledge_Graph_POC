import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.ontology_compiler import s09_ontology_repository as s9

ctx = stage_header(9)
repo = s9.OntologyRepository()

st.graphviz_chart("""digraph { rankdir=LR; node [shape=box style="rounded,filled" fontname="Segoe UI" fontsize=10];
 draft [fillcolor="#EEE7F6"]; pending_review [fillcolor="#FFF6D6"]; approved [fillcolor="#E3F2E7"];
 superseded [fillcolor="#DDF0F5"]; rejected [fillcolor="#FDECEC"];
 draft -> pending_review [label="submit (valid)"]; pending_review -> approved [label="approve (reviewer)"];
 pending_review -> rejected [label="reject"]; approved -> superseded [label="newer approved"];
 superseded -> draft [label="rollback = new draft" style=dashed]; }""")

if guard(ctx, 8):
    draft = ctx.hybrid_draft
    with st.form("approve"):
        c1, c2 = st.columns(2)
        author = c1.text_input("Author (saves the version)", draft.created_by)
        reviewer = c2.text_input("Reviewer (approves; must be a different person)", "reviewer.lead")
        go = st.form_submit_button("Save new version & approve", type="primary")
    if go:
        run_stage(s9.run, ctx, author=author, reviewer=reviewer, success="Ontology approved")

oids = repo.ontology_ids()
if oids:
    oid = st.selectbox("Ontology", oids, index=oids.index(ctx.approved_ontology.ontology_id)
                       if ctx.approved_ontology and ctx.approved_ontology.ontology_id in oids else 0)
    st.subheader("Versions")
    table(repo.version_rows(oid))
    c1, c2 = st.columns(2)
    with c1:
        if repo.get_approved(oid) and st.button("Use the approved version for the build (skip editing)"):
            run_stage(s9.use_existing, ctx, oid)
    with c2:
        vs = repo.versions(oid)
        with st.popover("Rollback to an older version"):
            v = st.selectbox("Version", vs)
            who = st.text_input("Requested by", "data.modeller")
            if st.button("Create rollback draft"):
                d = run_stage(repo.rollback, oid, v, who)
                if d:
                    st.success(f"Draft v{d.version} created from v{v}. It must be validated and approved again.")
    st.subheader("Audit history")
    table([{"at": h["at"], "action": h["action"], "version": h["version"], "actor": h["actor"],
            "detail": h["detail"]} for h in reversed(repo.history(oid))])
activity(ctx, 9)
next_stage(9)
