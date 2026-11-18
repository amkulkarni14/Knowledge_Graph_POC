"""The whole 16-stage pipeline on uploaded CSV files, plus the stage-level behaviour around Stage 2."""
from __future__ import annotations

import csv
import io
import subprocess
import sys
import time

import pytest
from conftest import ROOT, csv_file

from kg_pipeline.config import SAMPLE_FILES_DIR
from kg_pipeline.config import settings
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.pipeline import run_all
from kg_pipeline.preprocessing.connectors.csv_source import CsvImportError
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload
from kg_pipeline.preprocessing.connectors.csv_source import read_directory
from kg_pipeline.core import s01_scope
from kg_pipeline.preprocessing import s02_connect
from kg_pipeline.metadata_extractor import s03_schema_extraction
from kg_pipeline.metadata_extractor import s04_schema_analysis
from kg_pipeline.ontology_compiler import s05_manual_ontology
from kg_pipeline.ontology_compiler import s06_ai_suggestions


def run_csv(files, project="Test Project") -> PipelineContext:
    return run_all(PipelineContext(), csv_files=files, project=project)


def signature(ctx) -> tuple:
    """Everything that defines the graph, independent of insertion order."""
    g = ctx.graph
    return (sorted((n, d["label"], d["source_key"]) for n, d in g.nodes(data=True)),
            sorted((u, v, k) for u, v, k in g.edges(keys=True)))


# --------------------------------------------------------------------------- customer 360 (the reference data set)
class TestCustomer360:
    @pytest.fixture
    def ctx(self):
        return run_csv(read_directory(SAMPLE_FILES_DIR / "customer360"), "Customer 360")

    def test_all_sixteen_stages_complete(self, ctx):
        assert ctx.completed == set(range(1, 17)), sorted(set(range(1, 17)) - ctx.completed)

    def test_54_nodes_and_64_relationships_as_documented_for_these_files(self, ctx):
        assert (ctx.graph.number_of_nodes(), ctx.graph.number_of_edges()) == (54, 64)
        assert ctx.graph_report["ok"] and ctx.graph_report["errors"] == []

    def test_nodes_and_edges_by_type(self, ctx):
        assert ctx.graph_report["nodes_by_class"] == {"Account": 9, "Bank": 4, "CreditEnquiry": 8, "CreditScore": 10,
                                                      "Customer": 6, "Loan": 5, "Payment": 12}
        assert ctx.graph_report["edges_by_type"] == {"HAS_PAYMENT": 23, "HAS_ACCOUNT": 18, "HAS_CREDIT_ENQUIRY": 8,
                                                     "HAS_CREDIT_SCORE": 10, "HAS_LOAN": 5}

    def test_values_are_typed_and_named_after_the_file_headers(self, ctx):
        asha = ctx.graph.nodes["Customer:C001"]
        assert asha["customer_name"] == "Asha Verma" and asha["dob"] == "1985-03-12"
        assert asha["mobile"] == "9810000001" and asha["label"] == "Customer"      # label numbers stay text
        loan = ctx.graph.nodes["Loan:L500"]
        assert loan["loan_amount"] == 4500000 and loan["outstanding"] == 3900000.0 and loan["rate"] == 8.5
        assert ctx.graph.nodes["CreditScore:C001|2025-10-01"]["credit_score"] == 782   # composite key node id

    def test_edges_follow_the_links(self, ctx):
        assert ctx.graph.has_edge("Customer:C001", "Loan:L500", key="HAS_LOAN")
        assert ctx.graph.has_edge("Loan:L500", "Payment:P9001", key="HAS_PAYMENT")
        assert ctx.graph.has_edge("Bank:HDFC", "Account:A100", key="HAS_ACCOUNT")
        assert not any(ctx.graph.has_edge("Account:A100", "Payment:P9011", key="HAS_PAYMENT") for _ in [0])

    def test_payment_without_an_account_gets_no_account_edge_and_no_quarantine(self, ctx):
        into_p9011 = [(u, k) for u, _, k in ctx.graph.in_edges("Payment:P9011", keys=True)]
        assert into_p9011 == [("Loan:" + ctx.graph.nodes["Payment:P9011"]["loan_no"], "HAS_PAYMENT")]
        assert ctx.build_stats["quarantine"] == []

    def test_the_ontology_is_approved_versioned_and_the_graph_is_current(self, ctx):
        assert ctx.approved_ontology.version == 1 and ctx.approved_ontology.ontology_id == "customer_360"
        assert ctx.snapshot["published"] is True
        assert (settings.graph_store_dir / "customer_360").is_dir()

    def test_every_class_and_edge_is_traceable_to_a_file_table(self, ctx):
        assert {d["source_table"] for _, d in ctx.graph.nodes(data=True)} == {
            f"csv.{t}" for t in ("accounts", "banks", "credit_enquiry", "credit_score", "customers", "loans", "payments")}
        assert ctx.graph.graph["source"].startswith("csv-upload://")

    def test_pii_columns_are_flagged_so_they_never_reach_the_ai(self, ctx):
        customer = ctx.approved_ontology.class_by_name("Customer")
        assert {a.name for a in customer.attributes if a.pii} == {"dob", "email", "mobile", "pan"}
        sent = s06_ai_suggestions.build_schema_context(ctx.catalog, ctx.approved_ontology,
                                                       {"csv.customers": ctx.source.sample_rows("csv.customers", 3)})
        shown = next(t for t in sent["tables"] if t["table"] == "csv.customers")["masked_samples"][0]
        # the guard is stricter than the flags: names are hidden too, only structure-like columns remain
        assert set(shown) == {"cust_id", "segment", "city", "status"}
        assert not {"Mumbai", "Premium", "Active", "Asha"} & set(str(shown).replace("'", " ").split())  # no real values


class TestSameDataDifferentShape:
    def reference(self):
        return signature(run_csv(read_directory(SAMPLE_FILES_DIR / "customer360")))

    def test_file_order_does_not_matter(self):
        files = read_directory(SAMPLE_FILES_DIR / "customer360")
        assert signature(run_csv(list(reversed(files)))) == self.reference()

    def test_semicolon_delimited_windows_1252_files_give_the_same_graph(self):
        def convert(upload: CsvUpload) -> CsvUpload:
            rows = list(csv.reader(io.StringIO(upload.content.decode("utf-8-sig"))))
            out = io.StringIO()
            csv.writer(out, delimiter=";", lineterminator="\r\n").writerows(rows)
            return CsvUpload(upload.filename, out.getvalue().encode("cp1252"))
        files = [convert(f) for f in read_directory(SAMPLE_FILES_DIR / "customer360")]
        assert signature(run_csv(files)) == self.reference()

    def test_upper_case_headers_and_messy_file_names_give_the_same_graph(self):
        def rename(upload: CsvUpload) -> CsvUpload:
            text = upload.content.decode("utf-8-sig")
            header, _, rest = text.partition("\n")
            return CsvUpload(f"C:\\exports\\CUSTOMER360 {upload.filename.upper()}", (header.upper() + "\n" + rest).encode())
        files = [rename(f) for f in read_directory(SAMPLE_FILES_DIR / "customer360")]
        ctx = run_csv(files)
        assert (ctx.graph.number_of_nodes(), ctx.graph.number_of_edges()) == (54, 64)


# --------------------------------------------------------------------------- real-world problems
CUSTOMERS = "Cust ID,Customer Name,Email,Status\nC1,  Asha   Verma ,ASHA@X.COM,Active\nC2,Rohan Iyer,rohan@x.com,Active\nC3,Meera Nair,meera@x.com,Dormant\n"


class TestProblemsInTheData:
    def test_order_for_a_customer_that_does_not_exist_is_set_aside_with_a_reason_not_dropped_or_crashed(self):
        orders = "Order No,Cust ID,Total\nO1,C1,100\nO2,C99,50\nO3,C2,70\n"
        ctx = run_csv([csv_file("customers.csv", CUSTOMERS), csv_file("orders.csv", orders)])
        assert ctx.is_done(16) and ctx.snapshot["published"]
        assert ctx.graph.number_of_nodes() == 6 and ctx.graph.number_of_edges() == 2
        dangling = [q for q in ctx.build_stats["quarantine"] if q["stage"] == "edge"]
        assert len(dangling) == 1 and dangling[0]["reason"] == "source node missing" and "C99" in dangling[0]["key"]
        assert any(f["check"] == "orphan_reference" for f in ctx.dq_report["findings"])
        assert any("no match in customers.csv" in e["message"] for e in ctx.events if e["stage"] == 2)

    def test_whitespace_is_cleaned_in_stage_13_and_reported(self):
        ctx = run_csv([csv_file("customers.csv", CUSTOMERS)])
        assert ctx.graph.nodes["Customer:C1"]["customer_name"] == "Asha Verma"
        assert ctx.clean.stats["Customer"]["values_changed"] >= 1
        assert any(c["before"] == "'  Asha   Verma '" for c in ctx.clean.changes)

    def test_files_without_any_identifier_stop_with_an_explanation(self):
        messy = read_directory(SAMPLE_FILES_DIR / "customer360_messy")
        with pytest.raises(ValueError) as e:
            run_csv(messy)
        msg = str(e.value)
        assert "Nothing can be built" in msg and "'Cust ID'" in msg and "'C002'" in msg and "Fix the file" in msg

    def test_flawed_file_with_formula_cell_missing_key_and_text_in_a_number_column(self):
        flawed = ("Loan No,Cust ID,Loan Type,Loan Amount\nL600,C001,Home,1000000\n,C002,Personal,200000\n"
                  "L602,C003,Auto,abc\nL604,C005,Personal,300000\nL604,C005,Personal,310000\n=SUM(A1),C006,Home,ten\n")
        ctx = PipelineContext()
        s01_scope.run(ctx, s01_scope.default_scope())
        s02_connect.connect_csv(ctx, [csv_file("loans.csv", flawed)])
        warnings = " ".join(ctx.source_info["warnings"])
        assert "'Loan Amount' is mostly numbers" in warnings and "start with = + - or @" in warnings
        assert "'Loan No' looks like the identifier" in warnings and "'L604'" in warnings
        assert ctx.catalog is None                          # nothing downstream of the connection exists yet
        s03_schema_extraction.run(ctx)
        s04_schema_analysis.run(ctx)
        assert ctx.table_analysis[0]["type"] == "log"       # no key -> Stage 4 says it cannot become a class

    def test_a_table_that_is_only_a_lookup_or_has_no_links_still_builds(self):
        ctx = run_csv([csv_file("people.csv", "Person ID,Name\nP1,A\nP2,B\n")])
        assert ctx.is_done(16) and ctx.graph.number_of_nodes() == 2 and ctx.graph.number_of_edges() == 0

    def test_single_row_file(self):
        ctx = run_csv([csv_file("people.csv", "Person ID,Name\nP1,A\n")])
        assert ctx.graph.number_of_nodes() == 1

    def test_unicode_values_survive_the_whole_pipeline_and_the_snapshot(self):
        ctx = run_csv([csv_file("people.csv", "Person ID,Name\nP1,Zoë Müller\nP2,日本語\n")])
        assert ctx.graph.nodes["Person:P2"]["name"] == "日本語" and ctx.snapshot["published"]

    def test_a_reference_column_that_mixes_numbers_and_text_still_links(self):
        ctx = run_csv([csv_file("customers.csv", "id,name\n1,A\n2,B\n"),
                       csv_file("orders.csv", "order_id,customer_id\n10,1\n11,2\n12,2\n")])
        assert ctx.graph_report["edges_by_type"] == {"HAS_ORDER": 3}

    def test_self_reference_chain(self):
        ctx = run_csv([csv_file("employees.csv", "Emp ID,Name,Manager\nE1,A,\nE2,B,E1\nE3,C,E2\n")])
        assert ctx.graph_report["edges_by_type"] == {"MANAGER": 2}
        assert ctx.graph.has_edge("Employee:E3", "Employee:E2", key="MANAGER")

    def test_a_bridge_table_becomes_edges_with_properties(self):
        ctx = run_csv([
            csv_file("students.csv", "Student ID,Name\nS1,A\nS2,B\n"), csv_file("courses.csv", "Course ID,Title\nK1,X\nK2,Y\n"),
            csv_file("enrolments.csv", "Student ID,Course ID,Grade\nS1,K1,A\nS1,K2,B\nS2,K1,C\n")])
        edges = {(u, v): d for u, v, d in ctx.graph.edges(data=True)}
        assert len(edges) == 3 and edges[("Student:S1", "Course:K2")]["grade"] == "B"
        assert ctx.approved_ontology.relationship_by_name("ENROLMENT").mapping.kind == "join_table"


# --------------------------------------------------------------------------- size
class TestScale:
    def test_keyset_batches_and_speed_with_thousands_of_rows(self):
        n = 6000
        customers = "Cust ID,Name\n" + "".join(f"C{i:05d},Name {i}\n" for i in range(n))
        orders = "Order No,Cust ID,Total\n" + "".join(f"O{i:05d},C{i % n:05d},{i}\n" for i in range(2 * n))
        started = time.perf_counter()
        ctx = run_csv([csv_file("customers.csv", customers), csv_file("orders.csv", orders)])
        elapsed = time.perf_counter() - started
        assert ctx.graph.number_of_nodes() == 3 * n and ctx.graph.number_of_edges() == 2 * n
        assert ctx.extraction.tables["csv.customers"]["batches"] == 2 and ctx.extraction.tables["csv.orders"]["batches"] == 3
        assert elapsed < 60, f"{elapsed:.1f}s"


# --------------------------------------------------------------------------- stage 2 behaviour
class TestConnectStage:
    def test_a_rejected_upload_leaves_the_previous_connection_and_results_untouched(self):
        ctx = PipelineContext()
        s01_scope.run(ctx, s01_scope.default_scope())
        s02_connect.connect_sample(ctx)
        sample = ctx.source
        with pytest.raises(CsvImportError, match="empty.csv"):
            s02_connect.connect_csv(ctx, [csv_file("good.csv", "id\n1\n"), csv_file("empty.csv", "")])
        assert ctx.source is sample and ctx.source_info["mode"] == "sample" and ctx.is_done(2)

    def test_connecting_a_new_source_drops_everything_built_from_the_old_one(self):
        ctx = run_all(PipelineContext())                      # built-in sample, all 16 stages
        version = ctx.source_version
        assert ctx.graph is not None and ctx.approved_ontology is not None
        s02_connect.connect_csv(ctx, read_directory(SAMPLE_FILES_DIR / "customer360"))
        assert ctx.completed == {1, 2} and ctx.source_version == version + 1
        for attr in ("catalog", "manual_ontology", "hybrid_draft", "approved_ontology", "build_plan", "extraction",
                     "dq_report", "clean", "graph", "graph_report", "snapshot", "ontology_report"):
            assert getattr(ctx, attr) is None, attr
        assert ctx.table_analysis == [] and ctx.ai_items == []

    def test_reconnecting_replaces_the_source_and_logs_each_file(self):
        ctx = PipelineContext()
        s02_connect.connect_csv(ctx, [csv_file("a.csv", "id\n1\n")])
        s02_connect.connect_csv(ctx, [csv_file("b.csv", "id\n1\n"), csv_file("c.csv", "id\n1\n")])
        assert [f["file"] for f in ctx.source_info["files"]] == ["b.csv", "c.csv"]
        assert len([e for e in ctx.events if "→ csv." in e["message"]]) == 3

    def test_scope_with_table_names_that_do_not_exist_in_the_files_is_an_error_not_an_empty_graph(self):
        ctx = PipelineContext()
        s01_scope.run(ctx, s01_scope.ScopeSheet(business_questions=["q"], tables_in_scope=["public.customers"]))
        s02_connect.connect_csv(ctx, [csv_file("people.csv", "Person ID\nP1\n")])
        with pytest.raises(ValueError, match="None of the tables in the Stage 1 scope"):
            s03_schema_extraction.run(ctx)

    def test_scope_can_select_some_of_the_uploaded_tables(self):
        ctx = PipelineContext()
        s01_scope.run(ctx, s01_scope.ScopeSheet(business_questions=["q"], tables_in_scope=["csv.customers", "csv.loans"]))
        s02_connect.connect_csv(ctx, read_directory(SAMPLE_FILES_DIR / "customer360"))
        s03_schema_extraction.run(ctx)
        assert sorted(ctx.catalog.tables) == ["csv.customers", "csv.loans"]

    def test_catalog_column_table_shows_the_original_file_header_only_for_files(self):
        ctx = PipelineContext()
        s02_connect.connect_csv(ctx, [csv_file("a.csv", "Cust ID\nC1\n")])
        s03_schema_extraction.run(ctx)
        assert s03_schema_extraction.column_rows(ctx.catalog, "csv.a")[0]["file header"] == "Cust ID"
        sample = PipelineContext()
        s02_connect.connect_sample(sample)
        s03_schema_extraction.run(sample)
        assert "file header" not in s03_schema_extraction.column_rows(sample.catalog, "public.customers")[0]


class TestAiStageWithFiles:
    def test_the_recorded_offline_answer_is_refused_for_uploaded_files(self):
        ctx = PipelineContext()
        s02_connect.connect_csv(ctx, read_directory(SAMPLE_FILES_DIR / "customer360"))
        s03_schema_extraction.run(ctx)
        s04_schema_analysis.run(ctx)
        draft = s05_manual_ontology.draft_from_schema(ctx, "x", "n", "N")
        s05_manual_ontology.run(ctx, draft.ontology)
        with pytest.raises(ValueError, match="only fits the built-in sample"):
            s06_ai_suggestions.run(ctx, actor="me")
        s06_ai_suggestions.skip(ctx)
        assert ctx.is_done(6)


class TestStage5Draft:
    def test_drafting_does_not_save_anything(self):
        ctx = PipelineContext()
        s02_connect.connect_csv(ctx, read_directory(SAMPLE_FILES_DIR / "customer360"))
        s03_schema_extraction.run(ctx)
        s04_schema_analysis.run(ctx)
        draft = s05_manual_ontology.draft_from_schema(ctx, "c360", "com.example.c360", "C360", "me")
        assert ctx.manual_ontology is None and not ctx.is_done(5) and len(draft.ontology.classes) == 7

    def test_stage_3_is_required(self):
        with pytest.raises(RuntimeError, match="Stage 3"):
            s05_manual_ontology.draft_from_schema(PipelineContext(), "x", "n", "N")

    @pytest.mark.parametrize("project,expected", [("Customer 360", "customer_360"), ("  ", "ontology"),
                                                  ("360 Degrees!", "o_360_degrees"), ("Wow--Café", "wow_caf")])
    def test_default_ids_are_always_valid(self, project, expected):
        oid, namespace, name = s05_manual_ontology.default_ids(project)
        assert oid == expected and namespace == f"com.example.{expected}" and name
        from kg_pipeline.core.ontology_models import Ontology
        Ontology(ontology_id=oid, namespace=namespace, name=name)


# --------------------------------------------------------------------------- unchanged behaviour
class TestBuiltInSampleStillWorks:
    def test_sample_pipeline_numbers_are_unchanged(self):
        ctx = run_all(PipelineContext())
        assert (ctx.graph.number_of_nodes(), ctx.graph.number_of_edges()) == (33, 52)
        assert ctx.graph_report["ok"] and ctx.snapshot["published"]
        reasons = [q["reason"] for q in ctx.build_stats["quarantine"]]
        assert any("business rule" in r for r in reasons) and any("target node missing" in r or "source node missing" in r
                                                                  for r in reasons)

    def test_sample_ai_step_still_uses_the_offline_fixture(self):
        ctx = run_all(PipelineContext())
        assert ctx.ai_meta["model"] == "offline-fixture"


# --------------------------------------------------------------------------- command line
class TestCommandLine:
    def run(self, *args, tmp_path):
        env = {**__import__("os").environ, "KG_STORAGE_DIR": str(tmp_path / "cli_storage"), "PYTHONUTF8": "1"}
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "run_pipeline.py"), *args], cwd=ROOT, env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=120)

    def test_csv_dir_runs_everything(self, tmp_path):
        r = self.run("--csv-dir", str(SAMPLE_FILES_DIR / "customer360"), tmp_path=tmp_path)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "NetworkX MultiDiGraph built: 54 nodes, 64 edges" in r.stdout and "published: True" in r.stdout

    def test_messy_files_exit_with_a_message_not_a_traceback(self, tmp_path):
        r = self.run("--csv-dir", str(SAMPLE_FILES_DIR / "customer360_messy"), tmp_path=tmp_path)
        assert r.returncode == 2 and "Cannot build a graph" in r.stdout and "Traceback" not in r.stderr

    def test_missing_folder(self, tmp_path):
        r = self.run("--csv-dir", str(tmp_path / "nope"), tmp_path=tmp_path)
        assert r.returncode == 2 and "folder not found" in r.stdout

    def test_empty_folder(self, tmp_path):
        (tmp_path / "empty").mkdir()
        r = self.run("--csv-dir", str(tmp_path / "empty"), tmp_path=tmp_path)
        assert r.returncode == 2 and "no .csv files" in r.stdout

