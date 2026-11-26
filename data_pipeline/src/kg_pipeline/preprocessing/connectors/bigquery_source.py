"""BigQuery table reads using generated queries and bounded scan costs."""
from contextlib import closing
import re

from kg_pipeline.core.schema_models import ColumnInfo, SchemaCatalog, TableInfo

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}")
TYPES = {"INTEGER": "bigint", "INT64": "bigint", "BOOLEAN": "boolean", "BOOL": "boolean",
         "FLOAT": "double precision", "FLOAT64": "double precision", "NUMERIC": "numeric",
         "BIGNUMERIC": "numeric", "DATE": "date", "TIMESTAMP": "timestamp with time zone",
         "DATETIME": "timestamp without time zone", "JSON": "json"}


class BigQuerySource:
    def __init__(self, project, dataset, location=None):
        from google.cloud import bigquery
        self.sdk = bigquery
        self.client = bigquery.Client(project=project, location=location)
        self.project, self.dataset = project, dataset
        self.name = f"{project}.{dataset}"
        self.catalog = None

    def ping(self):
        self.client.get_dataset(self.name, timeout=10)

    def introspect_schema(self):
        if self.catalog is not None:
            return self.catalog
        tables = {}
        for item in self.client.list_tables(self.name, max_results=200, timeout=10):
            if item.table_type not in {"TABLE", "VIEW", "MATERIALIZED_VIEW"} or not IDENTIFIER.fullmatch(item.table_id):
                continue
            remote = self.client.get_table(item.reference, timeout=10)
            known = {f.name: ColumnInfo(name=f.name, pg_type=TYPES.get(f.field_type, "text"),
                                        nullable=f.mode != "REQUIRED", original_type=f.field_type)
                     for f in remote.schema if f.mode != "REPEATED" and f.field_type not in {"RECORD", "STRUCT", "BYTES"}
                     and IDENTIFIER.fullmatch(f.name)}
            if known:
                name = f"{self.dataset}.{item.table_id}"
                tables[name] = TableInfo(name=name, columns=known, asset_kind=item.table_type.lower(),
                                         source_path=f"{self.project}.{name}", row_estimate=remote.num_rows)
        self.catalog = SchemaCatalog(tables=tables, source_name=self.name)
        return self.catalog

    def iter_batches(self, table, columns, key_columns, batch_size=5000, since=None,
                     watermark_column=None, start_after=None, *, limit=None):
        info = self.introspect_schema().tables[table]
        fields = list(dict.fromkeys([*columns, *key_columns]))
        if not fields or not set(fields) <= info.columns.keys() or since is not None or start_after is not None:
            raise ValueError("Unsupported read")
        projection = ", ".join(f"`{name}`" for name in fields)
        query = f"SELECT {projection} FROM `{info.source_path}`"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        maximum = 64 * 1024 * 1024
        estimate = self.client.query(query, job_config=self.sdk.QueryJobConfig(dry_run=True, use_query_cache=False), timeout=10)
        if estimate.total_bytes_processed is None or estimate.total_bytes_processed > maximum:
            raise ValueError("Query exceeds the connector scan cap")
        job = self.client.query(query, job_config=self.sdk.QueryJobConfig(maximum_bytes_billed=maximum), timeout=10)
        try:
            for page in job.result(timeout=30, page_size=batch_size).pages:
                yield [dict(row) for row in page]
        finally:
            if not job.done():
                job.cancel()

    def sample_rows(self, table, limit=5):
        fields = list(self.introspect_schema().tables[table].columns)
        with closing(self.iter_batches(table, fields, [], limit, limit=limit)) as batches:
            return next(batches, [])

    def count(self, table):
        return self.introspect_schema().tables[table].row_estimate or 0

    def close(self):
        self.client.close()
