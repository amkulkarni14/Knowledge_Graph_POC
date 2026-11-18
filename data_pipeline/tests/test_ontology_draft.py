"""Rule-based ontology drafting from a catalog (Stage 5) - and that the draft passes the Stage 8 validator."""
from __future__ import annotations

import pytest
from conftest import csv_file
from pydantic import ValidationError

from kg_pipeline.ontology_compiler.ontology_draft import draft_from_catalog
from kg_pipeline.core.ontology_models import Cardinality
from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.core.ontology_models import OntologyStatus
from kg_pipeline.core.schema_models import ColumnInfo
from kg_pipeline.core.schema_models import ForeignKey
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.core.schema_models import TableInfo
from kg_pipeline.preprocessing.connectors import sample_data
from kg_pipeline.preprocessing.connectors.csv_source import UploadLimits
from kg_pipeline.preprocessing.connectors.csv_source import build_csv_source
from kg_pipeline.metadata_extractor.s04_schema_analysis import classify_table
from kg_pipeline.ontology_compiler.s08_ontology_validation import validate_ontology


def draft(catalog, **kw):
    kinds = {t.name: classify_table(t, catalog) for t in catalog.tables.values()}
    return draft_from_catalog(catalog, kinds, ontology_id="t", namespace="com.example.t", name="T", **kw)


def assert_valid(d, catalog):
    report = validate_ontology(d.ontology, catalog)
    assert report.ok and not report.issues, [(i.code, i.path, i.message) for i in report.issues]


class TestFromCsvFiles:
    @pytest.fixture
    def result(self, customer360):
        src = build_csv_source(customer360, UploadLimits())
        return src.catalog, draft(src.catalog)

    def test_a_class_per_table_with_keys_from_the_files(self, result):
        _, d = result
        assert {c.name: c.mapping.key_columns for c in d.ontology.classes} == {
            "Account": ["acct_id"], "Bank": ["bank_code"], "CreditEnquiry": ["enquiry_id"],
            "CreditScore": ["cust_id", "score_date"], "Customer": ["cust_id"], "Loan": ["loan_no"],
            "Payment": ["payment_id"]}

    def test_a_relationship_per_link_owner_to_holder(self, result):
        _, d = result
        got = {r.key: (r.cardinality, r.mapping.table, r.mapping.source_key_columns, r.mapping.target_key_columns)
               for r in d.ontology.relationships}
        assert got == {
            "Customer-[HAS_ACCOUNT]->Account": (Cardinality.ONE_TO_MANY, "csv.accounts", ["cust_id"], ["acct_id"]),
            "Bank-[HAS_ACCOUNT]->Account": (Cardinality.ONE_TO_MANY, "csv.accounts", ["bank_code"], ["acct_id"]),
            "Customer-[HAS_CREDIT_ENQUIRY]->CreditEnquiry": (Cardinality.ONE_TO_MANY, "csv.credit_enquiry",
                                                             ["cust_id"], ["enquiry_id"]),
            "Customer-[HAS_CREDIT_SCORE]->CreditScore": (Cardinality.ONE_TO_MANY, "csv.credit_score", ["cust_id"],
                                                         ["cust_id", "score_date"]),
            "Customer-[HAS_LOAN]->Loan": (Cardinality.ONE_TO_MANY, "csv.loans", ["cust_id"], ["loan_no"]),
            "Loan-[HAS_PAYMENT]->Payment": (Cardinality.ONE_TO_MANY, "csv.payments", ["loan_no"], ["payment_id"]),
            "Account-[HAS_PAYMENT]->Payment": (Cardinality.ONE_TO_MANY, "csv.payments", ["acct_id"], ["payment_id"]),
        }

    def test_the_draft_passes_validation_with_no_errors_and_no_warnings(self, result):
        catalog, d = result
        assert_valid(d, catalog)

    def test_draft_is_a_draft_with_every_column_as_an_attribute(self, result):
        catalog, d = result
        assert d.ontology.status is OntologyStatus.DRAFT and d.ontology.change_note.startswith("Drafted")
        customer = d.ontology.class_by_name("Customer")
        assert [a.source_column for a in customer.attributes] == list(catalog.tables["csv.customers"].columns)
        assert {a.name: a.data_type.value for a in customer.attributes}["dob"] == "date"

    def test_keys_are_required_and_personal_columns_are_flagged_pii(self, result):
        _, d = result
        by_name = {a.name: a for a in d.ontology.class_by_name("Customer").attributes}
        assert by_name["cust_id"].required and not by_name["segment"].required
        assert {n for n, a in by_name.items() if a.pii} == {"dob", "email", "mobile", "pan"}
        assert by_name["email"].normalize == "lower"

    def test_the_small_code_table_is_kept_but_the_user_is_told(self, result):
        _, d = result
        assert d.ontology.class_by_name("Bank") and any("small code table" in n for n in d.notes)

    def test_sensitive_columns_from_the_scope_sheet_are_flagged(self, customer360):
        src = build_csv_source(customer360, UploadLimits())
        d = draft(src.catalog, sensitive_columns=["csv.customers.city"])
        assert {a.name: a.pii for a in d.ontology.class_by_name("Customer").attributes}["city"] is True


def tbl(name, spec, pk=(), fks=(), unique=()):
    """A TableInfo where primary-key columns are NOT NULL, as in a real database."""
    return TableInfo(name=name, primary_key=list(pk), foreign_keys=list(fks), unique_constraints=list(unique),
                     columns={n: ColumnInfo(name=n, pg_type=t, nullable=n not in pk) for n, t in spec.items()})


def fk(columns, ref_table, ref_columns):
    return ForeignKey(columns=columns, ref_table=ref_table, ref_columns=ref_columns)


class TestShapes:
    def test_table_without_a_primary_key_is_left_out_with_a_note_and_relationships_to_it_are_skipped(self):
        cat = SchemaCatalog(tables={
            "s.people": tbl("s.people", dict(id="integer", name="text"), pk=["id"]),
            "s.events": tbl("s.events", dict(person_id="integer", what="text"),
                            fks=[fk(["person_id"], "s.people", ["id"])])})
        d = draft(cat)
        assert [c.name for c in d.ontology.classes] == ["Person"] and d.ontology.relationships == []
        assert any("s.events: no primary key" in n for n in d.notes)

    def test_nothing_to_draft_says_so(self):
        d = draft(SchemaCatalog(tables={"s.t": tbl("s.t", dict(a="text"))}))
        assert d.ontology.classes == [] and any("No class could be drafted" in n for n in d.notes)

    def test_bridge_table_becomes_a_many_to_many_relationship_with_properties(self):
        d = draft(sample_data.build_catalog())
        rel = d.ontology.relationship_by_name("ORDER_ITEM")
        assert rel.cardinality is Cardinality.MANY_TO_MANY and rel.mapping.kind == "join_table"
        assert (rel.source_class, rel.target_class) == ("Order", "Product")
        assert rel.mapping.property_columns == ["quantity", "unit_price"]
        assert d.ontology.class_by_name("OrderItem") is None            # a bridge is edges, not a node type

    def test_draft_from_the_built_in_sample_catalog_is_valid(self):
        catalog = sample_data.build_catalog()
        d = draft(catalog)
        assert {c.name for c in d.ontology.classes} == {"Location", "Organization", "Customer", "Product", "Order"}
        assert_valid(d, catalog)

    def test_self_reference_goes_from_the_row_to_the_row_it_points_at(self):
        d = draft(sample_data.build_catalog())
        rel = d.ontology.relationship_by_name("REFERRED_BY")
        assert (rel.source_class, rel.target_class) == ("Customer", "Customer")
        assert rel.cardinality is Cardinality.MANY_TO_ONE
        assert rel.mapping.source_key_columns == ["customer_id"] and rel.mapping.target_key_columns == ["referred_by"]
        assert any("self reference" in n for n in d.notes)

    def test_two_foreign_keys_to_the_same_table_get_distinct_names(self):
        cat = SchemaCatalog(tables={
            "s.accounts": tbl("s.accounts", dict(id="integer"), pk=["id"]),
            "s.transfers": tbl("s.transfers", dict(id="integer", from_id="integer", to_id="integer", at="date"),
                               pk=["id"], fks=[fk(["from_id"], "s.accounts", ["id"]),
                                               fk(["to_id"], "s.accounts", ["id"])])})
        d = draft(cat)
        assert {r.name for r in d.ontology.relationships} == {"HAS_TRANSFER_FROM", "HAS_TRANSFER_TO"}
        assert_valid(d, cat)

    def test_unique_foreign_key_is_one_to_one(self):
        cat = SchemaCatalog(tables={
            "s.people": tbl("s.people", dict(id="integer"), pk=["id"]),
            "s.passports": tbl("s.passports", dict(id="integer", person_id="integer"), pk=["id"],
                               unique=[["person_id"]], fks=[fk(["person_id"], "s.people", ["id"])])})
        assert draft(cat).ontology.relationships[0].cardinality is Cardinality.ONE_TO_ONE

    def test_foreign_key_to_a_non_key_column_is_skipped_with_a_note(self):
        cat = SchemaCatalog(tables={
            "s.a": tbl("s.a", dict(id="integer", code="text"), pk=["id"]),
            "s.b": tbl("s.b", dict(id="integer", a_code="text"), pk=["id"], fks=[fk(["a_code"], "s.a", ["code"])])})
        d = draft(cat)
        assert d.ontology.relationships == [] and any("does not point at the primary key" in n for n in d.notes)

    def test_composite_foreign_key_is_ordered_like_the_owner_key(self):
        cat = SchemaCatalog(tables={
            "s.a": tbl("s.a", dict(x="integer", y="integer"), pk=["x", "y"]),
            "s.b": tbl("s.b", dict(id="integer", fy="integer", fx="integer"), pk=["id"],
                       fks=[fk(["fy", "fx"], "s.a", ["y", "x"])])})
        d = draft(cat)
        assert d.ontology.relationships[0].mapping.source_key_columns == ["fx", "fy"]
        assert_valid(d, cat)

    def test_names_that_clash_with_what_the_graph_builder_writes_are_renamed(self):
        cat = SchemaCatalog(tables={
            "s.a": tbl("s.a", dict(id="integer", label="text", source_key="text"), pk=["id"]),
            "s.b": tbl("s.b", dict(id="integer", a_id="integer"), pk=["id"], fks=[fk(["a_id"], "s.a", ["id"])]),
            "s.link": tbl("s.link", dict(a_id="integer", b_id="integer", type="text", weight="integer"),
                          pk=["a_id", "b_id"], fks=[fk(["a_id"], "s.a", ["id"]), fk(["b_id"], "s.b", ["id"])])})
        d = draft(cat)
        assert [a.name for a in d.ontology.class_by_name("A").attributes] == ["id", "label_value", "source_key_value"]
        link = d.ontology.relationship_by_name("LINK")
        assert [p.name for p in link.properties] == ["type_value", "weight_value"]
        assert [p.source_column for p in link.properties] == ["type", "weight"]
        assert_valid(d, cat)

    def test_watermark_column_is_used_when_the_table_has_one(self):
        d = draft(sample_data.build_catalog())
        assert d.ontology.class_by_name("Customer").mapping.watermark_column == "updated_at"

    def test_attribute_names_are_valid_and_unique_whatever_the_columns_are_called(self):
        cat = SchemaCatalog(tables={"s.t": tbl(
            "s.t", {n: "text" for n in ("Order ID", "order_id", "1st Name", "Total $", "Total %")}, pk=["Order ID"])})
        d = draft(cat)
        names = [a.name for a in d.ontology.class_by_name("T").attributes]
        assert len(set(names)) == 5 and all(n[0].isalpha() for n in names)
        Ontology.model_validate(d.ontology.model_dump())

class TestHardening:
    @pytest.mark.parametrize("bad", ["../x", "a/b", "a\\b", "", " ", "a" * 64, "..", ".hidden", "x y"])
    def test_ontology_id_cannot_escape_the_repository_folder(self, bad):
        with pytest.raises(ValidationError, match="ontology id"):
            Ontology(ontology_id=bad, namespace="n", name="n")

    def test_good_ontology_ids(self):
        for ok in ("retail", "customer360", "my-graph_2"):
            assert Ontology(ontology_id=ok, namespace="n", name="n").ontology_id == ok

    def test_validator_rejects_attribute_names_the_builder_writes_itself(self):
        cat = SchemaCatalog(tables={"s.t": tbl("s.t", dict(id="integer", label="text"), pk=["id"])})
        onto = draft(cat).ontology
        onto.classes[0].attributes[1].name = "label"
        report = validate_ontology(onto, cat)
        assert not report.ok and "RESERVED_NAME" in {i.code for i in report.issues}

    def test_validator_rejects_reserved_edge_property_names(self):
        d = draft(sample_data.build_catalog())
        d.ontology.relationship_by_name("ORDER_ITEM").properties[0].name = "weight"
        report = validate_ontology(d.ontology, sample_data.build_catalog())
        assert "RESERVED_NAME" in {i.code for i in report.issues}


def test_drafting_from_a_single_file_with_no_links_still_works():
    src = build_csv_source([csv_file("people.csv", "Person ID,Name\nP1,A\nP2,B\n")], UploadLimits())
    d = draft(src.catalog)
    assert [c.name for c in d.ontology.classes] == ["Person"] and d.ontology.relationships == []
    assert_valid(d, src.catalog)

