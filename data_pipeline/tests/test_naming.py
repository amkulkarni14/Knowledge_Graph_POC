import re

import pytest

from kg_pipeline.core.naming import split_words
from kg_pipeline.core.naming import to_class_name
from kg_pipeline.core.naming import to_snake
from kg_pipeline.core.naming import to_upper_snake
from kg_pipeline.core.naming import unique_name
from kg_pipeline.core.ontology_models import ATTR_NAME_RE
from kg_pipeline.core.ontology_models import CLASS_NAME_RE
from kg_pipeline.core.ontology_models import REL_NAME_RE


@pytest.mark.parametrize("text,words", [
    ("Cust ID", ["cust", "id"]), ("cust_id", ["cust", "id"]), ("CustID", ["cust", "id"]),
    ("CreditScore", ["credit", "score"]), ("HTTPServer", ["http", "server"]), ("Prénom", ["prenom"]),
    ("  loan--no ", ["loan", "no"]), ("日本", []), ("a1b2", ["a1b2"])])
def test_split_words(text, words):
    assert split_words(text) == words


@pytest.mark.parametrize("header", ["Cust ID", "1st Name", "日本", "", "a" * 200, "select * from x; --", "Type"])
def test_to_snake_always_gives_a_valid_attribute_name(header):
    assert ATTR_NAME_RE.match(to_snake(header))


@pytest.mark.parametrize("table,cls", [
    ("csv.customers", "Customer"), ("csv.credit_score", "CreditScore"), ("csv.credit_enquiry", "CreditEnquiry"),
    ("public.order_items", "OrderItem"), ("csv.status", "Status"), ("csv.address", "Address"),
    ("csv.categories", "Category"), ("csv.boxes", "Box"), ("csv.2024_sales", "N2024Sale"), ("csv.日本", "Record")])
def test_class_names(table, cls):
    assert to_class_name(table) == cls
    assert CLASS_NAME_RE.match(cls)


def test_upper_snake_is_a_valid_relationship_name():
    for text in ("CreditScore", "referred_by", "9lives", "!!!"):
        assert REL_NAME_RE.match(to_upper_snake(text))


def test_unique_name_numbers_duplicates_and_respects_the_length_limit():
    taken: set[str] = set()
    assert [unique_name("a", taken) for _ in range(3)] == ["a", "a_2", "a_3"]
    long = "x" * 63
    first, second = unique_name(long, taken), unique_name(long, taken)
    assert first == long and second != first and len(second) <= 63 and re.match(r"^x+_2$", second)
