"""Drives the real Streamlit app (legacy/streamlit/app.py) page by page, the way a person would, using uploaded CSV files."""
from __future__ import annotations

import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

from kg_pipeline.config import SAMPLE_FILES_DIR
from kg_pipeline.core.context import PipelineContext
from kg_pipeline.preprocessing.connectors.csv_source import read_directory
from kg_pipeline.core import s01_scope

APP = str(ROOT / "legacy" / "streamlit" / "app.py")


def new_app(ctx: PipelineContext | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    if ctx is not None:
        at.session_state["ctx"] = ctx
    return at.run()


def ctx_with_scope() -> PipelineContext:
    ctx = PipelineContext()
    s01_scope.run(ctx, s01_scope.default_scope())
    return ctx


def page(at: AppTest, name: str) -> AppTest:
    at.switch_page(f"pages/{name}.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def click(at: AppTest, label: str) -> AppTest:
    matches = [b for b in at.button if label in b.label]
    assert matches, f"no button '{label}' on the page; buttons: {[b.label for b in at.button]}"
    matches[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def text_of(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [e.value for e in at.error] + [w.value for w in at.warning]
    parts += [i.value for i in at.info] + [c.value for c in at.caption]
    return "\n".join(parts)


class TestStage2Upload:
    def test_uploading_several_files_at_once(self):
        ctx = ctx_with_scope()
        at = page(new_app(ctx), "s02_connect")
        at.radio[0].set_value("Upload CSV files").run()
        assert [u.label for u in at.file_uploader] == ["CSV files"] and at.file_uploader[0].accept_multiple_files
        uploader = at.file_uploader[0]
        for f in read_directory(SAMPLE_FILES_DIR / "customer360"):
            uploader.upload(f.filename, f.content)
        at.run()
        assert ctx.source is None                      # choosing files does nothing until the button is pressed
        click(at, "Analyse & connect")
        assert ctx.source_info["mode"] == "csv" and len(ctx.source_info["files"]) == 7 and ctx.is_done(2)
        assert {s.value for s in at.subheader} >= {"Connection", "What was understood from the files"}
        assert len(at.dataframe) >= 2                  # file table and link table
        assert "Links between the files" in text_of(at)

    def test_a_bad_file_rejects_the_whole_upload_with_every_reason_and_changes_nothing(self):
        ctx = ctx_with_scope()
        at = page(new_app(ctx), "s02_connect")
        at.radio[0].set_value("Upload CSV files").run()
        at.file_uploader[0].upload("good.csv", b"id,x\n1,a\n").upload("empty.csv", b"").upload("data.txt", b"\x00\x01\x02")
        at.run()
        click(at, "Analyse & connect")
        message = "\n".join(e.value for e in at.error)
        assert "rejected and nothing was loaded" in message and "empty.csv: the file is empty" in message
        assert "data.txt: this looks like a binary file" in message
        assert ctx.source is None and not ctx.is_done(2)

    def test_the_bundled_example_button_and_the_other_sources_are_still_offered(self):
        ctx = ctx_with_scope()
        at = page(new_app(ctx), "s02_connect")
        assert at.radio[0].options == ["Sample retail database (in memory, no setup)", "Upload CSV files", "PostgreSQL"]
        at.radio[0].set_value("Upload CSV files").run()
        click(at, "bundled Customer 360")
        assert ctx.source_info["mode"] == "csv" and len(ctx.source_info["files"]) == 7
        # switching to the sample database still works and replaces the files
        at.radio[0].set_value("Sample retail database (in memory, no setup)").run()
        click(at, "Connect to sample database")
        assert ctx.source_info["mode"] == "sample"

    def test_analyse_button_is_disabled_until_files_are_chosen(self):
        at = page(new_app(ctx_with_scope()), "s02_connect")
        at.radio[0].set_value("Upload CSV files").run()
        analyse = next(b for b in at.button if "Analyse & connect" in b.label)
        assert analyse.disabled

    def test_stage_2_needs_stage_1(self):
        at = page(new_app(), "s02_connect")
        assert not at.radio and "Stage 1" in text_of(at)


class TestWholeFlowThroughTheScreens:
    def test_every_stage_screen_from_upload_to_stored_graph(self):
        ctx = ctx_with_scope()
        at = new_app(ctx)

        page(at, "s02_connect")
        at.radio[0].set_value("Upload CSV files").run()
        uploader = at.file_uploader[0]
        for f in read_directory(SAMPLE_FILES_DIR / "customer360"):
            uploader.upload(f.filename, f.content)
        at.run()
        click(at, "Analyse & connect")
        assert ctx.is_done(2)

        page(at, "s03_schema")
        click(at, "Read database structure")
        assert ctx.is_done(3) and len(ctx.catalog.tables) == 7

        page(at, "s04_analysis")
        click(at, "Analyse tables")
        assert ctx.is_done(4)

        # Stage 5: the example draft is not offered for files, the rule-based draft is
        page(at, "s05_manual")
        example = next(b for b in at.button if "Load example draft" in b.label)
        assert example.disabled
        click(at, "Create the draft")
        notes = text_of(at)
        assert "note(s) from the draft" in " ".join(e.label for e in at.expander)
        assert "small code table" in notes
        assert {c.name for c in at.session_state["onto_edit"].classes} >= {"Customer", "Loan", "Payment"}
        click(at, "Save as draft")
        assert ctx.is_done(5) and len(ctx.manual_ontology.classes) == 7 and len(ctx.manual_ontology.relationships) == 7

        # Stage 6: the offline answer is not offered for files; skipping is
        page(at, "s06_ai")
        ask = next(b for b in at.button if "Ask AI" in b.label)
        assert ask.disabled and "only fits the built-in sample database" in text_of(at)
        click(at, "Skip AI")
        assert ctx.is_done(6)

        page(at, "s07_review")
        click(at, "Build hybrid draft")
        assert ctx.is_done(7)

        page(at, "s08_validate")
        click(at, "Run validation")
        assert ctx.is_done(8) and ctx.ontology_report.ok and not ctx.ontology_report.issues

        page(at, "s09_repo")
        click(at, "Save new version & approve")
        assert ctx.approved_ontology is not None and ctx.approved_ontology.version == 1

        for name, label, stage in [("s10_plan", "Generate build plan", 10), ("s11_extract", "Extract data", 11),
                                   ("s12_quality", "Run data quality checks", 12),
                                   ("s13_clean", "Clean, normalise", 13), ("s14_build", "Build the NetworkX graph", 14),
                                   ("s15_gvalidate", "Validate the graph", 15)]:
            page(at, name)
            click(at, label)
            assert ctx.is_done(stage), f"stage {stage} did not complete: {[e['message'] for e in ctx.events[-3:]]}"

        assert (ctx.graph.number_of_nodes(), ctx.graph.number_of_edges()) == (54, 64)

        page(at, "s16_store")
        click(at, "Save graph version")
        assert ctx.is_done(16) and ctx.snapshot["published"]
        assert len(ctx.completed) == 16

        page(at, "explorer")                            # the stored graph can be explored
        assert not at.exception

    def test_changing_the_source_resets_the_ontology_editor(self):
        ctx = ctx_with_scope()
        at = new_app(ctx)
        page(at, "s02_connect")
        at.radio[0].set_value("Upload CSV files").run()
        click(at, "bundled Customer 360")
        page(at, "s03_schema")
        click(at, "Read database structure")
        page(at, "s04_analysis")
        click(at, "Analyse tables")
        page(at, "s05_manual")
        click(at, "Create the draft")
        assert len(at.session_state["onto_edit"].classes) == 7
        # connect to the sample database instead: the CSV draft must not be shown for it
        page(at, "s02_connect")
        click(at, "Connect to sample database")
        page(at, "s03_schema")
        click(at, "Read database structure")
        page(at, "s04_analysis")
        click(at, "Analyse tables")
        page(at, "s05_manual")
        assert at.session_state["onto_edit"] is None
        assert not next(b for b in at.button if "Load example draft" in b.label).disabled


class TestHomeQuickRuns:
    def test_quick_run_on_the_customer_360_files(self):
        at = new_app()
        click(at, "Customer 360 CSV files")
        ctx = at.session_state["ctx"]
        assert len(ctx.completed) == 16 and ctx.graph.number_of_nodes() == 54 and ctx.graph.number_of_edges() == 64

    def test_quick_run_on_the_sample_database_is_unchanged(self):
        at = new_app()
        click(at, "on sample data")
        ctx = at.session_state["ctx"]
        assert len(ctx.completed) == 16 and ctx.graph.number_of_nodes() == 33 and ctx.graph.number_of_edges() == 52


class TestPagesRenderAfterAFileBuild:
    @pytest.mark.parametrize("name", ["s03_schema", "s04_analysis", "s05_manual", "s06_ai", "s07_review", "s08_validate",
                                      "s09_repo", "s10_plan", "s11_extract", "s12_quality", "s13_clean", "s14_build",
                                      "s15_gvalidate", "s16_store", "explorer", "home"])
    def test_every_page_renders_with_results_from_uploaded_files(self, name):
        at = new_app()
        click(at, "Customer 360 CSV files")
        page(at, name)
