"""In-memory copy of database/postgres/init/01_source_schema.sql so the prototype runs without a database.

Values use the same Python types psycopg returns (date, datetime, Decimal).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal as D

from kg_pipeline.core.schema_models import ColumnInfo
from kg_pipeline.core.schema_models import ForeignKey
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.core.schema_models import TableInfo

T0 = datetime(2026, 11, 1, 9, 0)
T1 = datetime(2026, 11, 9, 18, 30)


def _cols(*spec):
    return {n: ColumnInfo(name=n, pg_type=t, nullable=nl) for n, t, nl in spec}


INT, VC, NUM, DATE, TS = "integer", "character varying", "numeric", "date", "timestamp with time zone"


def build_catalog() -> SchemaCatalog:
    tables = {
        "public.locations": TableInfo(
            name="public.locations",
            columns=_cols(("location_id", INT, False), ("city", VC, False), ("state", VC, True),
                          ("country", VC, False), ("updated_at", TS, False)),
            primary_key=["location_id"]),
        "public.organizations": TableInfo(
            name="public.organizations",
            columns=_cols(("org_id", INT, False), ("org_name", VC, False), ("industry", VC, True),
                          ("hq_location_id", INT, True), ("updated_at", TS, False)),
            primary_key=["org_id"],
            foreign_keys=[ForeignKey(columns=["hq_location_id"], ref_table="public.locations",
                                     ref_columns=["location_id"])]),
        "public.customers": TableInfo(
            name="public.customers",
            columns=_cols(("customer_id", INT, False), ("full_name", VC, False), ("email", VC, False),
                          ("phone", VC, True), ("location_id", INT, True), ("org_id", INT, True),
                          ("referred_by", INT, True), ("segment", VC, True), ("updated_at", TS, False)),
            primary_key=["customer_id"],
            foreign_keys=[
                ForeignKey(columns=["location_id"], ref_table="public.locations", ref_columns=["location_id"]),
                ForeignKey(columns=["org_id"], ref_table="public.organizations", ref_columns=["org_id"]),
                ForeignKey(columns=["referred_by"], ref_table="public.customers", ref_columns=["customer_id"])]),
        "public.products": TableInfo(
            name="public.products",
            columns=_cols(("product_id", INT, False), ("product_name", VC, False), ("category", VC, True),
                          ("unit_price", NUM, False), ("manufacturer_id", INT, True), ("updated_at", TS, False)),
            primary_key=["product_id"],
            foreign_keys=[ForeignKey(columns=["manufacturer_id"], ref_table="public.organizations",
                                     ref_columns=["org_id"])]),
        "public.orders": TableInfo(
            name="public.orders",
            columns=_cols(("order_id", INT, False), ("customer_id", INT, False), ("order_date", DATE, False),
                          ("status", VC, False), ("total_amount", NUM, True), ("updated_at", TS, False)),
            primary_key=["order_id"]),          # customer_id: no declared FK on purpose
        "public.order_items": TableInfo(
            name="public.order_items",
            columns=_cols(("order_id", INT, False), ("product_id", INT, False), ("quantity", INT, False),
                          ("unit_price", NUM, False)),
            primary_key=["order_id", "product_id"],
            foreign_keys=[
                ForeignKey(columns=["order_id"], ref_table="public.orders", ref_columns=["order_id"]),
                ForeignKey(columns=["product_id"], ref_table="public.products", ref_columns=["product_id"])]),
    }
    return SchemaCatalog(tables=tables, source_name="sample://retail")


def build_rows() -> dict[str, list[dict]]:
    loc = [(1, "Pune", "Maharashtra"), (2, "Mumbai", "Maharashtra"), (3, "Bengaluru", "Karnataka"),
           (4, "Hyderabad", "Telangana"), (5, "Delhi", "Delhi")]
    org = [(10, "Acme Retail Pvt Ltd", "Retail", 2), (11, "Zenith Electronics", "Manufacturing", 3),
           (12, "Nimbus Software", "IT Services", 1)]
    cust = [
        (1, "Rahul Verma", "rahul.verma@example.com", "9876500001", 1, 12, None, "Gold", T0),
        (2, "Priya Sharma", "priya.sharma@example.com", "9876500002", 2, 10, 1, "Silver", T0),
        (3, "Amit Patel", "amit.patel@example.com", None, 3, 11, 1, "Gold", T0),
        (4, "Sneha Iyer", "sneha.iyer@example.com", "9876500004", 3, 12, 3, "Bronze", T0),
        (5, "Vikram Singh", "vikram.singh@example.com", "9876500005", 5, None, None, "Silver", T0),
        (6, "Anjali Rao", "anjali.rao@example.com", "9876500006", 4, 11, 2, "Gold", T0),
        (7, "Karan Mehta", "karan.mehta@example.com", None, None, None, None, None, T0),
        (8, "Neha Gupta", "neha.gupta@example.com", "9876500008", 1, 10, 4, "Silver", T1),
        (11, "  priya SHARMA ", "Priya.Sharma@Example.com ", "9876500002", 2, 10, None, "silver", T0),
    ]
    prod = [(201, "Laptop Pro 14", "Electronics", "89999", 11), (202, "Wireless Mouse", "Accessories", "1299", 11),
            (203, "Office Chair", "Furniture", "15499", 10),
            (204, "Noise Cancelling Headphones", "Electronics", "24999", 11),
            (205, "Project Tracker SaaS", "Software", "4999", 12), (206, "USB-C Hub", "Accessories", "-50", 11)]
    orders = [
        (1001, 1, date(2026, 9, 2), "DELIVERED", "91298", T0), (1002, 2, date(2026, 9, 5), "DELIVERED", "15499", T0),
        (1003, 3, date(2026, 9, 9), "SHIPPED", "114998", T0), (1004, 1, date(2026, 9, 20), "DELIVERED", "4999", T0),
        (1005, 4, date(2026, 10, 1), "CANCELLED", "24999", T0), (1006, 5, date(2026, 10, 3), "DELIVERED", "1299", T0),
        (1007, 6, date(2026, 10, 7), "DELIVERED", "90000", T0), (1008, 11, date(2026, 10, 12), "DELIVERED", "2598", T0),
        (1009, 8, date(2026, 10, 15), "PLACED", "26298", T1), (1010, 3, date(2026, 10, 18), "DELIVERED", "4999", T0),
        (1011, 6, date(2026, 10, 22), "SHIPPED", "15499", T1), (1012, 99, date(2026, 10, 25), "PLACED", "1299", T0),
    ]
    items = [(1001, 201, 1, "89999"), (1001, 202, 1, "1299"), (1002, 203, 1, "15499"), (1003, 201, 1, "89999"),
             (1003, 204, 1, "24999"), (1004, 205, 1, "4999"), (1005, 204, 1, "24999"), (1006, 202, 1, "1299"),
             (1007, 201, 1, "89999"), (1008, 202, 2, "1299"), (1009, 204, 1, "24999"), (1009, 202, 1, "1299"),
             (1010, 205, 1, "4999"), (1011, 203, 1, "15499"), (1012, 202, 1, "1299")]
    return {
        "public.locations": [dict(location_id=i, city=c, state=s, country="India", updated_at=T0) for i, c, s in loc],
        "public.organizations": [dict(org_id=i, org_name=n, industry=ind, hq_location_id=h, updated_at=T0)
                                 for i, n, ind, h in org],
        "public.customers": [dict(customer_id=i, full_name=n, email=e, phone=p, location_id=l, org_id=o,
                                  referred_by=r, segment=s, updated_at=u) for i, n, e, p, l, o, r, s, u in cust],
        "public.products": [dict(product_id=i, product_name=n, category=c, unit_price=D(p), manufacturer_id=m,
                                 updated_at=T0) for i, n, c, p, m in prod],
        "public.orders": [dict(order_id=i, customer_id=c, order_date=d, status=s, total_amount=D(t), updated_at=u)
                          for i, c, d, s, t, u in orders],
        "public.order_items": [dict(order_id=o, product_id=p, quantity=q, unit_price=D(u)) for o, p, q, u in items],
    }
