import pandas as pd
import streamlit as st

from components.graph_view import show_ontology
from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.core.ontology_models import AttributeDef
from kg_pipeline.core.ontology_models import Cardinality
from kg_pipeline.core.ontology_models import DataType
from kg_pipeline.ontology_compiler import s05_manual_ontology as s5

ctx = stage_header(5)
if guard(ctx, 3, 4):
    cat = ctx.catalog
    pii = set(ctx.scope.sensitive_columns) if ctx.scope else set()
    if st.session_state.get("onto_edit_source") != ctx.source_version:     # a new source: drop the old editor state
        for k in ("onto_edit", "draft_notes"):
            st.session_state.pop(k, None)
        st.session_state["onto_edit_source"] = ctx.source_version
    if "onto_edit" not in st.session_state:
        st.session_state["onto_edit"] = ctx.manual_ontology

    from_files = ctx.source_info.get("mode") == "csv"
    c0, c1, c2, c3 = st.columns(4)
    with c0.popover("🪄 Draft from the schema (rules)", width="stretch"):
        st.caption("Makes a class for every table that has a key, a relationship for every foreign key / link "
                   "between files and every bridge table. No AI. You review and edit it below before saving.")
        d_id, d_ns, d_nm = s5.default_ids(ctx.scope.project if ctx.scope else "ontology")
        did = st.text_input("Ontology id", d_id, key="dr_id", help="Letters, digits, _ and - only.")
        dns = st.text_input("Namespace", d_ns, key="dr_ns")
        dnm = st.text_input("Name", d_nm, key="dr_nm")
        dau = st.text_input("Author", "data.modeller", key="dr_au")
        if st.button("Create the draft", type="primary", key="dr_go"):
            try:
                draft = s5.draft_from_schema(ctx, did, dns, dnm, dau)
                st.session_state["onto_edit"] = draft.ontology
                st.session_state["draft_notes"] = draft.notes
            except Exception as e:  # noqa: BLE001
                st.error(f"{type(e).__name__}: {e}")
    if c1.button("Load example draft (Customer, Order, PLACED)", width="stretch", disabled=from_files,
                 help="The example maps the built-in retail tables, so it does not fit uploaded files."
                 if from_files else None):
        st.session_state["onto_edit"] = s5.load_template()
    with c2.popover("Start a new empty ontology", width="stretch"):
        oid = st.text_input("Ontology id", "retail")
        ns = st.text_input("Namespace", "com.example.retail")
        nm = st.text_input("Name", "Retail Customer Graph")
        au = st.text_input("Author", "data.modeller")
        if st.button("Create"):
            try:
                st.session_state["onto_edit"] = s5.new_ontology(oid, ns, nm, au)
                st.session_state.pop("draft_notes", None)
            except Exception as e:  # noqa: BLE001
                st.error(f"{type(e).__name__}: {e}")
    if ctx.manual_ontology is not None and c3.button("Revert to last saved draft", width="stretch"):
        st.session_state["onto_edit"] = ctx.manual_ontology

    if st.session_state.get("draft_notes"):
        with st.expander(f"📝 {len(st.session_state['draft_notes'])} note(s) from the draft - read these", expanded=True):
            for note in st.session_state["draft_notes"]:
                st.markdown(f"- {note}")

    onto = st.session_state["onto_edit"]
    if onto is None:
        st.info("Draft the ontology from the schema (🪄), load the example draft, or start a new ontology to begin.")
    else:
        def commit(fn, *a, **kw):
            try:
                st.session_state["onto_edit"] = fn(onto, *a, **kw)
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"{type(e).__name__}: {e}")

        st.markdown(f"**Ontology `{onto.ontology_id}`** · namespace `{onto.namespace}` · author `{onto.created_by}`")
        left, right = st.columns([1, 1.15])
        with left:
            st.subheader("Classes (node types)")
            table(s5.class_rows(onto))
            st.subheader("Relationships (edge types)")
            table(s5.relationship_rows(onto))
        with right:
            st.subheader("Ontology diagram")
            show_ontology(onto, 380)

        tab_c, tab_a, tab_r, tab_m = st.tabs(["➕ Add class", "✏️ Edit attributes", "🔗 Add relationship",
                                              "🧰 Rename / delete"])
        with tab_c:
            tables = list(cat.tables)
            t = st.selectbox("Source table", tables, key="nc_table")
            info = cat.tables[t]
            default_name = "".join(w.capitalize() for w in t.split(".")[-1].rstrip("s").split("_"))
            with st.form("new_class"):
                a1, a2 = st.columns(2)
                name = a1.text_input("Class name (PascalCase, any business name)", default_name)
                category = a2.selectbox("Upper category (optional)",
                                        ["", "Person", "Organization", "Product", "Location", "Event", "Concept"])
                desc = st.text_input("Description", "")
                b1, b2 = st.columns(2)
                keys = b1.multiselect("Identifier (key columns)", list(info.columns), default=info.primary_key)
                cols = b2.multiselect("Attributes (columns)", list(info.columns), default=list(info.columns))
                d1, d2 = st.columns(2)
                res = d1.multiselect("Merge duplicates when these match (entity resolution)", list(info.columns))
                wm_opts = [""] + [c for c in info.columns if "updated" in c or "modified" in c]
                wm = d2.selectbox("Watermark column (incremental loads)", wm_opts)
                if st.form_submit_button("Add class", type="primary"):
                    attrs = s5.attributes_from_table(cat, t, cols, pii)
                    commit(s5.add_class, name, t, keys, attrs, description=desc, resolution_columns=res,
                           watermark_column=wm or None, category=category or None)
        with tab_a:
            if onto.classes:
                cname = st.selectbox("Class", [c.name for c in onto.classes], key="ea_class")
                cls = onto.class_by_name(cname)
                df = pd.DataFrame([{"name": a.name, "data_type": a.data_type.value, "required": a.required,
                                    "source_column": a.source_column or "", "normalize": a.normalize or "",
                                    "pii": a.pii, "origin": a.origin.value} for a in cls.attributes])
                cols_avail = [""] + (list(cat.tables[cls.mapping.source_table].columns)
                                     if cls.mapping and cls.mapping.source_table in cat.tables else [])
                edited = st.data_editor(df, num_rows="dynamic", width="stretch", hide_index=True,
                                        key=f"ed_{cname}", column_config={
                                            "data_type": st.column_config.SelectboxColumn(options=[d.value for d in DataType]),
                                            "normalize": st.column_config.SelectboxColumn(options=["", "trim", "lower", "upper", "title"]),
                                            "source_column": st.column_config.SelectboxColumn(options=cols_avail),
                                            "origin": st.column_config.TextColumn(disabled=True)})
                if st.button("Apply attribute changes", type="primary"):
                    try:
                        new = onto.model_copy(deep=True)
                        target = new.class_by_name(cname)
                        target.attributes = [AttributeDef(
                            name=r["name"], data_type=r["data_type"] or "string", required=bool(r["required"]),
                            source_column=r["source_column"] or None, normalize=r["normalize"] or None,
                            pii=bool(r["pii"]), origin=r.get("origin") or "manual")
                            for r in edited.to_dict("records") if r.get("name")]
                        st.session_state["onto_edit"] = new
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"{type(e).__name__}: {e}")
        with tab_r:
            if len(onto.classes) >= 1:
                names = [c.name for c in onto.classes]
                r1, r2, r3 = st.columns(3)
                src = r1.selectbox("From class (source)", names, key="nr_src")
                tgt = r2.selectbox("To class (target)", names, key="nr_tgt")
                kind = r3.selectbox("Built from", ["foreign_key", "join_table"], key="nr_kind")
                rt = st.selectbox("Table whose rows become edges", list(cat.tables), key="nr_table")
                tcols = list(cat.tables[rt].columns)
                with st.form("new_rel"):
                    f1, f2 = st.columns(2)
                    rname = f1.text_input("Relationship name (UPPER_SNAKE verb)", "RELATES_TO")
                    card = f2.selectbox("Cardinality", [c.value for c in Cardinality])
                    g1, g2, g3 = st.columns(3)
                    skeys = g1.multiselect(f"Columns identifying the source ({src})", tcols, key="nr_skeys")
                    tkeys = g2.multiselect(f"Columns identifying the target ({tgt})", tcols, key="nr_tkeys")
                    pcols = g3.multiselect("Edge properties", tcols, key="nr_pcols")
                    acyclic = st.checkbox("Forbid cycles (e.g. referral chains)")
                    desc = st.text_input("Description", "")
                    st.caption("Example: Customer PLACED Order is built from `public.orders`, source column "
                               "`customer_id`, target column `order_id` (the row's own key).")
                    if st.form_submit_button("Add relationship", type="primary"):
                        commit(s5.add_relationship, rname, src, tgt, card, kind, rt, skeys, tkeys, pcols,
                               catalog=cat, description=desc, allow_cycles=not acyclic)
        with tab_m:
            m1, m2 = st.columns(2)
            with m1:
                if onto.classes:
                    old = st.selectbox("Class", [c.name for c in onto.classes], key="rn_old")
                    new_name = st.text_input("New name", old, key="rn_new")
                    b1, b2 = st.columns(2)
                    if b1.button("Rename class"):
                        commit(s5.rename_class, old, new_name)
                    if b2.button("Delete class (and its relationships)"):
                        commit(s5.remove_class, old)
            with m2:
                if onto.relationships:
                    rk = st.selectbox("Relationship", [r.key for r in onto.relationships], key="rm_rel")
                    if st.button("Delete relationship"):
                        commit(s5.remove_relationship, rk)

        st.divider()
        if st.button("💾 Save as draft (Stage 5 result)", type="primary"):
            run_stage(s5.run, ctx, onto, success="Draft saved")
        if ctx.manual_ontology is not None:
            with st.expander("Draft ontology JSON"):
                st.json(ctx.manual_ontology.model_dump(mode="json"), expanded=False)
activity(ctx, 5)
next_stage(5)
