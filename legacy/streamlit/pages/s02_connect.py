import pandas as pd
import streamlit as st

from components.layout import activity, guard, next_stage, run_stage, stage_header, table
from kg_pipeline.config import SAMPLE_FILES_DIR
from kg_pipeline.preprocessing.connectors.csv_source import CsvImportError
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload
from kg_pipeline.preprocessing.connectors.csv_source import UploadLimits
from kg_pipeline.preprocessing.connectors.csv_source import read_directory
from kg_pipeline.preprocessing import s02_connect

SAMPLE, CSV, POSTGRES = "Sample retail database (in memory, no setup)", "Upload CSV files", "PostgreSQL"


def connect_csv(ctx, uploads: list[CsvUpload]) -> None:
    """Connects, or shows every problem with the files and leaves the previous connection untouched."""
    try:
        with st.spinner("Reading and analysing the files..."):
            s02_connect.connect_csv(ctx, uploads)
    except CsvImportError as e:
        st.error("The upload was rejected and nothing was loaded:\n\n" +
                 "\n".join(f"- {line}" for line in str(e).splitlines()))
        return
    except Exception as e:  # noqa: BLE001 - shown to the user
        st.error(f"{type(e).__name__}: {e}")
        return
    st.toast(f"Connected to {len(uploads)} file(s)", icon="✅")


def link_graph(info: dict) -> str:
    edges = "".join(f'  "{l["from"]}" -> "{l["to_table"]}" [label="{l["column"]}"'
                    f'{", style=dashed" if l["basis"] == "values only" else ""}];\n' for l in info["links"])
    nodes = "".join(f'  "{f["table"]}" [label="{f["table"].split(".")[-1]}\\n{f["rows"]} rows"];\n'
                    for f in info["files"])
    return ('digraph G { rankdir=LR; bgcolor="transparent"; node [shape=box style="rounded,filled" '
            'fillcolor="#E6EEF8" color="#9AA8B8" fontname="Segoe UI" fontsize=11]; edge [color="#5B6B7F" '
            'fontname="Segoe UI" fontsize=9];\n' + nodes + edges + "}")


ctx = stage_header(2)
if guard(ctx, 1):
    mode = st.radio("Data source", [SAMPLE, CSV, POSTGRES], horizontal=True)
    if mode == SAMPLE:
        st.info("Same tables and rows as `database/postgres/init/01_source_schema.sql`, including deliberate data problems "
                "(duplicate customer, orphan order, negative price, undeclared FK) so every stage has "
                "something to show.")
        if st.button("Connect to sample database", type="primary"):
            run_stage(s02_connect.connect_sample, ctx, success="Connected")
    elif mode == CSV:
        limits = UploadLimits.from_settings()
        st.info("Select **several CSV files at once**. Each file becomes a table (its name is the table name). "
                "The pipeline works out each table's key and which columns link the files together, then "
                "Stage 5 can draft the ontology from that. Files are read in memory and never written to disk.")
        files = st.file_uploader("CSV files", type=["csv", "tsv", "txt"], accept_multiple_files=True,
                                 key="csv_files", help="Comma, semicolon, tab or pipe separated; first row = headers.")
        st.caption(f"Limits: {limits.max_files} files, {limits.max_bytes // (1024 * 1024)} MB and "
                   f"{limits.max_rows:,} rows per file (KG_MAX_UPLOAD_FILES / _MB / _ROWS). Dates should be "
                   "YYYY-MM-DD. Excel files must be saved as CSV first.")
        c1, c2 = st.columns(2)
        if c1.button("Analyse & connect the files", type="primary", disabled=not files, width="stretch"):
            connect_csv(ctx, [CsvUpload(f.name, f.getvalue()) for f in files])
        if c2.button("Use the bundled Customer 360 example files (7 CSVs)", width="stretch"):
            try:
                bundled = read_directory(SAMPLE_FILES_DIR / "customer360")
            except CsvImportError as e:
                st.error(f"The bundled example files are not available: {e}")
            else:
                connect_csv(ctx, bundled)
    else:
        d = s02_connect.env_defaults()
        with st.form("pg"):
            c1, c2, c3 = st.columns([2, 1, 2])
            host = c1.text_input("Host (prefer a read replica)", d["host"])
            port = c2.number_input("Port", value=int(d["port"]), step=1)
            dbname = c3.text_input("Database", d["dbname"])
            c4, c5, c6 = st.columns(3)
            user = c4.text_input("Read-only user", d["user"])
            password = c5.text_input("Password", d["password"], type="password",
                                     help="Used only for this session; never written to disk or logs.")
            sslmode = c6.selectbox("SSL mode", ["prefer", "require", "verify-full", "disable"],
                                   index=["prefer", "require", "verify-full", "disable"].index(d["sslmode"])
                                   if d["sslmode"] in ("prefer", "require", "verify-full", "disable") else 0)
            schemas = st.text_input("Schemas (comma separated)", ", ".join(d["schemas"]))
            ok = st.form_submit_button("Test & connect", type="primary")
        if ok:
            run_stage(s02_connect.connect_postgres, ctx, host=host, port=int(port), dbname=dbname, user=user,
                      password=password, sslmode=sslmode,
                      schemas=[s.strip() for s in schemas.split(",") if s.strip()], success="Connected")

    if ctx.source_info:
        st.subheader("Connection")
        i = ctx.source_info
        c = st.columns(4)
        c[0].metric("Mode", i["mode"])
        c[1].metric("User", i["user"])
        c[2].metric("Read-only session", "yes" if i["read_only"] else "enforced per session")
        c[3].metric("Server", i["server_version"][:28])
        if i["mode"] == "csv":
            st.caption("Safety controls: files are read in memory only (never written to disk), limited in number, "
                       "size and rows, file names are reduced to a safe table name, and no formula is ever run.")
            st.subheader("What was understood from the files")
            table(i["files"])
            if i["links"]:
                st.markdown("**Links between the files** (a column that holds the values of another file's key; "
                            "dashed = matched by values only, check it)")
                st.graphviz_chart(link_graph(i), width="stretch")
                table(i["links"])
            else:
                st.warning("No links between the files were found, so Stage 5 can only draft separate classes. "
                           "A link needs a column named like another file's key (for example `cust_id`) whose "
                           "values appear in that key.")
            if i["warnings"]:
                with st.expander(f"⚠ {len(i['warnings'])} thing(s) to check in the files", expanded=True):
                    for w in i["warnings"]:
                        st.markdown(f"- {w}")
            if ctx.source is not None and hasattr(ctx.source, "reports"):
                with st.expander("Preview the first rows of a file"):
                    pick = st.selectbox("File", [r.table for r in ctx.source.reports],
                                        format_func=lambda t: next(r.filename for r in ctx.source.reports
                                                                   if r.table == t))
                    st.dataframe(pd.DataFrame(ctx.source.sample_rows(pick, 8)), hide_index=True, width="stretch")
        else:
            st.caption("Safety controls: `default_transaction_read_only=on`, `statement_timeout=5 min`, "
                       "connection pool of max 4, `application_name=kg-networkx-builder` for tracing in pg_stat_activity.")
activity(ctx, 2)
next_stage(2)
