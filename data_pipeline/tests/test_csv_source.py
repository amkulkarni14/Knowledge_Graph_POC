"""The CSV upload source: safe parsing, typing, key inference, link inference, and the DataSource interface."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from conftest import csv_file

from kg_pipeline.preprocessing.connectors.csv_source import BIGINT
from kg_pipeline.preprocessing.connectors.csv_source import BOOL
from kg_pipeline.preprocessing.connectors.csv_source import DATE
from kg_pipeline.preprocessing.connectors.csv_source import DOUBLE
from kg_pipeline.preprocessing.connectors.csv_source import TEXT
from kg_pipeline.preprocessing.connectors.csv_source import TS
from kg_pipeline.preprocessing.connectors.csv_source import TSTZ
from kg_pipeline.preprocessing.connectors.csv_source import CsvImportError
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload
from kg_pipeline.preprocessing.connectors.csv_source import UploadLimits
from kg_pipeline.preprocessing.connectors.csv_source import build_csv_source


def build(*files, limits=None):
    return build_csv_source(list(files), limits or UploadLimits(10, 100_000, 1_000))


def types(src, table):
    return {c.name: c.pg_type for c in src.catalog.tables[table].columns.values()}


# --------------------------------------------------------------------------- limits and safety
class TestSafety:
    def test_nothing_uploaded(self):
        with pytest.raises(CsvImportError, match="at least one"):
            build_csv_source([], UploadLimits())

    def test_too_many_files(self):
        files = [csv_file(f"f{i}.csv", "id,x\n1,a\n") for i in range(4)]
        with pytest.raises(CsvImportError, match="at most 3 files"):
            build_csv_source(files, UploadLimits(max_files=3))

    def test_file_too_large(self):
        with pytest.raises(CsvImportError, match="larger than"):
            build_csv_source([csv_file("a.csv", "id,x\n" + "1,aaaa\n" * 10)], UploadLimits(max_bytes=20))

    def test_too_many_rows(self):
        with pytest.raises(CsvImportError, match="more than 5 rows"):
            build_csv_source([csv_file("a.csv", "id\n" + "\n".join(str(i) for i in range(20)))],
                             UploadLimits(max_rows=5))

    @pytest.mark.parametrize("name", ["a.xlsx", "a.exe", "a", "a.csv.php"])
    def test_other_extensions_are_refused(self, name):
        with pytest.raises(CsvImportError, match="only"):
            build(csv_file(name, "id\n1\n"))

    def test_binary_file_is_refused(self):
        with pytest.raises(CsvImportError, match="binary"):
            build(CsvUpload("a.csv", b"PK\x03\x04\x00\x00\x00binary"))

    def test_empty_and_header_only(self):
        with pytest.raises(CsvImportError, match="empty"):
            build(csv_file("a.csv", "  \n\n"))
        with pytest.raises(CsvImportError, match="no data rows"):
            build(csv_file("a.csv", "id,name\n\n,\n"))

    def test_one_bad_file_rejects_everything_and_lists_every_problem(self):
        with pytest.raises(CsvImportError) as e:
            build(csv_file("good.csv", "id\n1\n"), csv_file("empty.csv", ""), csv_file("b.xlsx", "x"))
        lines = str(e.value).splitlines()
        assert len(lines) == 2 and lines[0].startswith("empty.csv") and lines[1].startswith("b.xlsx")

    def test_path_in_file_name_is_removed_and_table_name_is_a_safe_identifier(self):
        src = build(csv_file("..\\..\\etc/passwd; DROP TABLE x--.csv", "id\n1\n"))
        (table,) = src.catalog.tables
        assert table.startswith("csv.") and table.removeprefix("csv.").replace("_", "").isalnum()
        assert src.reports[0].filename == "passwd; DROP TABLE x--.csv"

    def test_same_file_name_twice_gets_two_tables(self):
        src = build(csv_file("a.csv", "id\n1\n"), csv_file("a.csv", "id\n2\n"))
        assert sorted(src.catalog.tables) == ["csv.a", "csv.a_2"]

    def test_source_is_read_only_and_in_memory(self):
        src = build(csv_file("a.csv", "id\n1\n"))
        assert src.ping()["read_only"] is True and "never written to disk" in src.ping()["server_version"]


# --------------------------------------------------------------------------- parsing
class TestParsing:
    @pytest.mark.parametrize("sep", [",", ";", "\t", "|"])
    def test_delimiters(self, sep):
        src = build(csv_file("a.csv", sep.join(["id", "name"]) + "\n" + sep.join(["1", "x"]) + "\n"))
        assert list(src.catalog.tables["csv.a"].columns) == ["id", "name"]

    def test_other_delimiter_inside_a_cell_does_not_confuse_detection(self):
        src = build(csv_file("a.csv", 'id,skills\n1,"Neo4j;Python"\n2,"Go;Rust"\n'))
        assert list(src.catalog.tables["csv.a"].columns) == ["id", "skills"]
        assert src.rows["csv.a"][0]["skills"] == "Neo4j;Python"

    def test_bom_and_windows_line_endings(self):
        src = build(CsvUpload("a.csv", "﻿id,name\r\n1,x\r\n2,y\r\n".encode("utf-8")))
        assert list(src.catalog.tables["csv.a"].columns) == ["id", "name"] and len(src.rows["csv.a"]) == 2

    def test_non_utf8_is_read_as_windows_1252(self):
        src = build(csv_file("a.csv", "id,city\n1,Zürich\n", encoding="cp1252"))
        assert src.rows["csv.a"][0]["city"] == "Zürich"

    def test_blank_lines_before_the_header_are_skipped(self):
        src = build(csv_file("a.csv", "\n  \r\n\nid,name\n1,x\n"))
        assert list(src.catalog.tables["csv.a"].columns) == ["id", "name"] and len(src.rows["csv.a"]) == 1

    def test_quoted_newline_and_blank_lines(self):
        src = build(csv_file("a.csv", 'id,note\n1,"line1\nline2"\n\n2,b\n'))
        assert [r["id"] for r in src.rows["csv.a"]] == [1, 2] and "\n" in src.rows["csv.a"][0]["note"]

    def test_short_rows_are_padded_and_long_rows_trimmed_with_a_warning(self):
        src = build(csv_file("a.csv", "id,a,b\n1,x\n2,y,z,EXTRA\n"))
        assert src.rows["csv.a"][0]["b"] is None and src.rows["csv.a"][1]["b"] == "z"
        assert any("more cells than the header" in w for w in src.warnings)

    def test_headers_become_unique_snake_case_names_and_keep_the_original(self):
        src = build(csv_file("a.csv", "Cust ID,Cust ID,,Total $,1st\n1,2,3,4,5\n"))
        cols = src.catalog.tables["csv.a"].columns
        assert list(cols) == ["cust_id", "cust_id_2", "column_3", "total", "c_1st"]
        assert cols["cust_id"].source_header == "Cust ID" and cols["total"].source_header == "Total $"


# --------------------------------------------------------------------------- types
class TestTyping:
    def test_basic_types(self):
        src = build(csv_file("t.csv", "\n".join([
            "id,n,price,flag,day,moment,name",
            "1,10,1.5,true,2026-01-31,2026-01-31T10:00:00,Asha",
            "2,-3,2,FALSE,2026-02-01,2026-02-01 11:30,Rohan",
            "3,,,,,,"])))
        assert types(src, "csv.t") == {"id": BIGINT, "n": BIGINT, "price": DOUBLE, "flag": BOOL, "day": DATE,
                                       "moment": TS, "name": TEXT}
        first, third = src.rows["csv.t"][0], src.rows["csv.t"][2]
        assert first["id"] == 1 and first["price"] == 1.5 and first["flag"] is True
        assert first["day"] == date(2026, 1, 31) and first["moment"] == datetime(2026, 1, 31, 10, 0)
        assert third["n"] is None and third["flag"] is None and third["name"] is None   # empty cells are NULL

    def test_timezone_aware_timestamps_and_mixing_aware_with_naive(self):
        aware = build(csv_file("a.csv", "id,t\n1,2026-01-01T10:00:00Z\n2,2026-01-01T10:00:00+05:30\n"))
        assert types(aware, "csv.a")["t"] == TSTZ
        mixed = build(csv_file("a.csv", "id,t\n1,2026-01-01T10:00:00Z\n2,2026-01-01T10:00:00\n"))
        assert types(mixed, "csv.a")["t"] == TEXT          # cannot be compared safely, so kept as text

    def test_thousands_separators(self):
        src = build(csv_file("a.csv", 'id,amount,rate\n1,"4,500,000",8.5\n2,500000,"1,234.50"\n'))
        assert types(src, "csv.a")["amount"] == BIGINT and [r["amount"] for r in src.rows["csv.a"]] == [4500000, 500000]
        assert types(src, "csv.a")["rate"] == DOUBLE and src.rows["csv.a"][1]["rate"] == 1234.5

    def test_numbers_that_are_labels_stay_text_and_keep_leading_zeros(self):
        src = build(csv_file("a.csv", "id,mobile,account_no,pin,zip_code,code\n"
                                      "1,9810000001,50100011111,411001,00123,007\n"))
        t = types(src, "csv.a")
        assert t["id"] == BIGINT and all(t[c] == TEXT for c in ("mobile", "account_no", "pin", "zip_code", "code"))
        assert src.rows["csv.a"][0]["zip_code"] == "00123"

    def test_leading_zero_ids_and_huge_numbers_are_not_turned_into_numbers(self):
        src = build(csv_file("a.csv", "id,big\n007,12345678901234567890123\n008,99999999999999999999999\n"))
        assert types(src, "csv.a") == {"id": TEXT, "big": TEXT}

    def test_text_keeps_original_cell_untrimmed_for_stage_13(self):
        src = build(csv_file("a.csv", "id,name\n1,  Asha   Verma \n"))
        assert src.rows["csv.a"][0]["name"] == "  Asha   Verma "   # Stage 13 trims and reports the change

    @pytest.mark.parametrize("token", ["", "null", "NULL", "None", "NaN", "N/A"])
    def test_null_tokens(self, token):
        src = build(csv_file("a.csv", f"id,x\n1,{token}\n2,5\n"))
        assert src.rows["csv.a"][0]["x"] is None and types(src, "csv.a")["x"] == BIGINT

    def test_na_is_not_null_because_it_can_be_a_country_code(self):
        assert build(csv_file("a.csv", "id,country\n1,NA\n")).rows["csv.a"][0]["country"] == "NA"

    def test_all_empty_column_is_text(self):
        assert types(build(csv_file("a.csv", "id,x\n1,\n2,\n")), "csv.a")["x"] == TEXT


class TestWarnings:
    def test_mostly_numbers_with_a_few_bad_values(self):
        src = build(csv_file("a.csv", "id,amt\n1,10\n2,20\n3,abc\n4,40\n5,50\n"))
        assert types(src, "csv.a")["amt"] == TEXT
        assert any("mostly numbers" in w and "'abc'" in w for w in src.warnings)

    def test_dates_in_a_non_iso_form(self):
        src = build(csv_file("a.csv", "id,dob\n1,12/03/1985\n2,25/07/1990\n3,02/11/1978\n"))
        assert types(src, "csv.a")["dob"] == TEXT and any("YYYY-MM-DD" in w for w in src.warnings)

    def test_invalid_calendar_date_is_not_a_date(self):
        src = build(csv_file("a.csv", "id,d\n1,2026-13-45\n"))
        assert types(src, "csv.a")["d"] == TEXT

    def test_spreadsheet_formula_cells_are_reported_and_kept_as_text(self):
        src = build(csv_file("a.csv", "id,note\n1,=SUM(A1)\n2,@cmd\n3,-5\n4,ok\n"))
        assert [r["note"] for r in src.rows["csv.a"]][:2] == ["=SUM(A1)", "@cmd"]
        assert any("2 cell(s) start with" in w for w in src.warnings)

    def test_warnings_per_file_are_capped(self):
        header = "id," + ",".join(f"c{i}" for i in range(30))
        row = lambda n: f"{n}," + ",".join(["1", "2", "x"] * 10)       # noqa: E731
        src = build(csv_file("a.csv", header + "\n" + "\n".join(row(i) for i in range(3)) + "\n"))
        assert len(src.reports[0].warnings) <= 13


# --------------------------------------------------------------------------- keys
class TestKeys:
    def pk(self, src, table):
        return src.catalog.tables[table].primary_key

    def test_identifier_column_is_the_key(self):
        src = build(csv_file("people.csv", "Name,Person ID\nAsha,P1\nRohan,P2\n"))
        assert self.pk(src, "csv.people") == ["person_id"] and src.reports[0].key_how == "id"

    def test_first_identifier_wins_but_an_identifier_owned_by_another_file_is_demoted(self):
        loans = "Loan No,Cust ID,Amount\nL1,C1,10\nL2,C2,20\n"                 # cust_id is also unique here: by chance
        customers = "Cust ID,Name\nC1,A\nC2,B\n"
        src = build(csv_file("loans.csv", loans), csv_file("customers.csv", customers))
        assert self.pk(src, "csv.loans") == ["loan_no"] and self.pk(src, "csv.customers") == ["cust_id"]
        # even when the foreign key is listed first
        src = build(csv_file("loans.csv", "Cust ID,Loan No,Amount\nC1,L1,10\nC2,L2,20\n"),
                    csv_file("customers.csv", customers))
        assert self.pk(src, "csv.loans") == ["loan_no"]

    def test_composite_key_for_a_record_repeated_over_time(self):
        src = build(csv_file("scores.csv", "Cust ID,Score Date,Score\nC1,2026-01-01,700\nC1,2026-02-01,710\n"
                                           "C2,2026-01-01,650\n"))
        assert self.pk(src, "csv.scores") == ["cust_id", "score_date"] and src.reports[0].key_how == "composite"

    def test_unique_column_without_identifier_name_is_used_with_a_warning(self):
        src = build(csv_file("people.csv", "Email,City\na@x.com,Pune\nb@x.com,Pune\n"))
        assert self.pk(src, "csv.people") == ["email"] and src.reports[0].key_how == "unique"
        assert any("check that it identifies a record" in w for w in src.warnings)

    def test_duplicate_identifiers_mean_no_key_and_the_warning_names_the_repeat(self):
        src = build(csv_file("loans.csv", "Loan No,Amt\nL1,10\nL1,10\nL2,5\n"))
        assert self.pk(src, "csv.loans") == [] and src.reports[0].key_how == "none"
        assert any("'Loan No'" in w and "'L1'" in w and "will not become a class" in w for w in src.warnings)

    def test_a_failing_identifier_is_reported_not_replaced_by_another_unique_column(self):
        # "Amount" is unique too, but promoting it would hide that Loan No repeats
        src = build(csv_file("loans.csv", "Loan No,Amount Text\nL1,ten\nL1,twenty\nL2,thirty\n"))
        assert self.pk(src, "csv.loans") == [] and any("'Loan No'" in w for w in src.warnings)

    def test_empty_identifier_means_no_key(self):
        src = build(csv_file("loans.csv", "Loan No,Amt\nL1,10\n,20\n"))
        assert self.pk(src, "csv.loans") == [] and any("row(s) are empty" in w for w in src.warnings)

    def test_key_columns_are_not_nullable_and_other_columns_are(self):
        cols = build(csv_file("a.csv", "id,x\n1,a\n2,b\n")).catalog.tables["csv.a"].columns
        assert cols["id"].nullable is False and cols["x"].nullable is True

    def test_other_unique_identifier_columns_become_unique_constraints(self):
        src = build(csv_file("a.csv", "Acct ID,Account No,City\nA1,111,P\nA2,222,P\n"))
        assert src.catalog.tables["csv.a"].unique_constraints == [["account_no"]]


# --------------------------------------------------------------------------- links
class TestLinks:
    CUSTOMERS = "Cust ID,Name\nC1,A\nC2,B\nC3,C\n"

    def links(self, src, table):
        return [(f.columns, f.ref_table, f.ref_columns) for f in src.catalog.tables[table].foreign_keys]

    def test_same_name_and_matching_values_make_a_foreign_key(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS),
                    csv_file("orders.csv", "Order No,Cust ID\nO1,C1\nO2,C1\nO3,C2\n"))
        assert self.links(src, "csv.orders") == [(["cust_id"], "csv.customers", ["cust_id"])]
        assert self.links(src, "csv.customers") == []

    def test_class_name_plus_generic_key_name_links(self):
        src = build(csv_file("customers.csv", "id,name\n1,A\n2,B\n"),
                    csv_file("orders.csv", "order_id,customer_id\n10,1\n11,2\n"))
        assert self.links(src, "csv.orders") == [(["customer_id"], "csv.customers", ["id"])]

    def test_two_files_that_both_have_a_generic_id_are_not_linked(self):
        src = build(csv_file("a.csv", "id,x\n1,a\n2,b\n"), csv_file("b.csv", "id,y\n1,a\n2,b\n"))
        assert self.links(src, "csv.a") == [] and self.links(src, "csv.b") == []

    def test_same_name_with_unrelated_values_is_not_linked_and_says_so(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS),
                    csv_file("tickets.csv", "Ticket,Cust ID\nT1,X9\nT2,X8\nT3,X7\nT4,X6\nT5,X5\n"))
        assert self.links(src, "csv.tickets") == []
        assert any("same name as the key" in w and "0%" in w for w in src.warnings)

    def test_orphan_values_are_reported_not_hidden(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS),
                    csv_file("orders.csv", "Order No,Cust ID\nO1,C1\nO2,C99\nO3,C2\n"))
        assert self.links(src, "csv.orders")            # still a link: Stage 12 quarantines the orphan edge
        assert any("no match in customers.csv" in w and "'C99'" in w for w in src.warnings)

    def test_empty_foreign_values_are_fine(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS), csv_file("orders.csv", "Order No,Cust ID\nO1,C1\nO2,\n"))
        assert self.links(src, "csv.orders") and not any("no match" in w for w in src.warnings)

    def test_different_name_is_linked_by_values_only_when_it_mentions_the_owner_and_overlaps_strongly(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS),
                    csv_file("referrals.csv", "Ref No,Referred Customer\nR1,C1\nR2,C2\nR3,C3\n"))
        assert self.links(src, "csv.referrals") == [(["referred_customer"], "csv.customers", ["cust_id"])]
        assert any("only because its values match" in w for w in src.warnings)
        assert src.reports[1].link_specs[0]["basis"] == "values only"

    def test_values_only_link_needs_strong_overlap(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS),
                    csv_file("referrals.csv", "Ref No,Referred Customer\nR1,C1\nR2,Z2\nR3,Z3\n"))
        assert self.links(src, "csv.referrals") == []

    def test_self_reference(self):
        src = build(csv_file("employees.csv", "Emp ID,Name,Manager\nE1,A,\nE2,B,E1\nE3,C,E1\n"))
        assert self.links(src, "csv.employees") == [(["manager"], "csv.employees", ["emp_id"])]

    def test_two_files_keyed_on_the_same_thing_are_linked_once_the_smaller_points_at_the_larger(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS),
                    csv_file("profiles.csv", "Cust ID,Tier\nC1,Gold\nC2,Silver\n"))
        assert self.links(src, "csv.profiles") == [(["cust_id"], "csv.customers", ["cust_id"])]
        assert self.links(src, "csv.customers") == []

    def test_equal_sized_files_keyed_alike_are_linked_once_the_later_points_at_the_earlier(self):
        a, b = "Cust ID,X\nC1,a\nC2,b\n", "Cust ID,Y\nC1,a\nC2,b\n"
        src = build(csv_file("first.csv", a), csv_file("second.csv", b))
        assert self.links(src, "csv.second") and not self.links(src, "csv.first")

    def test_a_column_links_to_one_table_only(self):
        src = build(csv_file("customers.csv", self.CUSTOMERS), csv_file("banks.csv", "Bank Code,Name\nB1,X\n"),
                    csv_file("accounts.csv", "Acct ID,Cust ID,Bank Code\nA1,C1,B1\nA2,C2,B1\n"))
        assert sorted(c[0][0] for c in self.links(src, "csv.accounts")) == ["bank_code", "cust_id"]

    def test_floats_and_booleans_are_never_foreign_keys(self):
        src = build(csv_file("a.csv", "Score ID,x\n1,1.5\n2,2.5\n"), csv_file("b.csv", "Row ID,Score ID\n7,1.5\n8,2.5\n"))
        assert self.links(src, "csv.b") == []

    def test_composite_key_owners_are_not_linked_automatically(self):
        src = build(csv_file("scores.csv", "Cust ID,Score Date,Score\nC1,2026-01-01,7\nC1,2026-02-01,8\n"),
                    csv_file("notes.csv", "Note ID,Cust ID\nN1,C1\n"))
        assert self.links(src, "csv.notes") == []

    def test_customer360_end_to_end_links(self, customer360):
        src = build_csv_source(customer360, UploadLimits())
        keys = {t.name: t.primary_key for t in src.catalog.tables.values()}
        assert keys == {"csv.accounts": ["acct_id"], "csv.banks": ["bank_code"], "csv.credit_enquiry": ["enquiry_id"],
                        "csv.credit_score": ["cust_id", "score_date"], "csv.customers": ["cust_id"],
                        "csv.loans": ["loan_no"], "csv.payments": ["payment_id"]}
        fks = {(t.name, tuple(fk.columns), fk.ref_table) for t in src.catalog.tables.values() for fk in t.foreign_keys}
        assert fks == {("csv.accounts", ("cust_id",), "csv.customers"), ("csv.accounts", ("bank_code",), "csv.banks"),
                       ("csv.credit_enquiry", ("cust_id",), "csv.customers"),
                       ("csv.credit_score", ("cust_id",), "csv.customers"), ("csv.loans", ("cust_id",), "csv.customers"),
                       ("csv.payments", ("loan_no",), "csv.loans"), ("csv.payments", ("acct_id",), "csv.accounts")}

    def test_the_order_of_the_files_does_not_matter(self, customer360):
        forward = build_csv_source(customer360, UploadLimits())
        backward = build_csv_source(list(reversed(customer360)), UploadLimits())
        dump = lambda s: {n: (t.primary_key, sorted((tuple(f.columns), f.ref_table) for f in t.foreign_keys))   # noqa: E731
                          for n, t in s.catalog.tables.items()}
        assert dump(forward) == dump(backward)


# --------------------------------------------------------------------------- DataSource interface
class TestInterface:
    @pytest.fixture
    def src(self):
        return build(csv_file("t.csv", "id,v\n3,c\n1,a\n2,b\n,orphan\n"))

    def test_catalog_row_estimates_and_introspection_copy(self, src):
        assert src.catalog.tables["csv.t"].row_estimate == 4
        copy = src.introspect_schema()
        copy.tables["csv.t"].columns.clear()
        assert src.catalog.tables["csv.t"].columns            # callers cannot damage the source's catalog

    def test_keyset_batches_resume_after_a_checkpoint_and_tolerate_null_keys(self):
        src = build(csv_file("t.csv", "id,v\n3,c\n1,a\n2,b\n"))
        batches = list(src.iter_batches("csv.t", ["v"], ["id"], batch_size=2))
        assert [[r["id"] for r in b] for b in batches] == [[1, 2], [3]]
        resumed = list(src.iter_batches("csv.t", ["v"], ["id"], batch_size=2, start_after=(1,)))
        assert [[r["id"] for r in b] for b in resumed] == [[2, 3]]
        # rows whose key is NULL (a table without a primary key is read by its first column) sort last, no crash
        nullable = build(csv_file("t.csv", "name,v\nb,1\n,2\na,3\n"))
        rows = [r for b in nullable.iter_batches("csv.t", ["v"], ["name"]) for r in b]
        assert [r["name"] for r in rows] == ["a", "b", None]

    def test_unknown_table_or_column_is_refused(self, src):
        with pytest.raises(ValueError, match="unknown table"):
            list(src.iter_batches("csv.nope", ["v"], ["id"]))
        with pytest.raises(ValueError, match="unknown columns"):
            list(src.iter_batches("csv.t", ["v; DROP TABLE t"], ["id"]))

    def test_sample_rows_and_count_return_copies(self, src):
        assert src.count("csv.t") == 4
        sample = src.sample_rows("csv.t", 2)
        sample[0]["v"] = "changed"
        assert src.rows["csv.t"][0]["v"] != "changed"
