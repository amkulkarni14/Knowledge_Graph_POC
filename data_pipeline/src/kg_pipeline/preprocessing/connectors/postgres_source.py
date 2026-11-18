"""Read-only PostgreSQL source (psycopg 3 + connection pool).

* Schema is read from pg_catalog (composite keys keep their column order).
* Data is read with KEYSET pagination: WHERE (pk) > (last_pk) ORDER BY pk LIMIT n.
  Every batch costs the same and a failed run can resume from the last key.
* Table/column names are checked against the introspected catalog (whitelist)
  and quoted with psycopg.sql.Identifier, so names from the UI/AI cannot inject SQL.
* The session is read-only and has a statement timeout.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from kg_pipeline.core.schema_models import ColumnInfo
from kg_pipeline.core.schema_models import ForeignKey
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.core.schema_models import TableInfo

log = logging.getLogger(__name__)

COLUMNS_SQL = """
SELECT n.nspname || '.' || c.relname AS table_name, a.attname AS column_name,
       format_type(a.atttypid, NULL) AS pg_type, NOT a.attnotnull AS nullable
FROM pg_attribute a
JOIN pg_class c     ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'v', 'm') AND a.attnum > 0 AND NOT a.attisdropped
  AND n.nspname = ANY(%(schemas)s)
ORDER BY 1, a.attnum
"""

CONSTRAINTS_SQL = """
SELECT n.nspname || '.' || c.relname AS table_name, con.contype AS kind,
       ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY k(attnum, ord)
             JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
             ORDER BY k.ord) AS columns,
       rn.nspname || '.' || rc.relname AS ref_table,
       ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY k(attnum, ord)
             JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.attnum
             ORDER BY k.ord) AS ref_columns
FROM pg_constraint con
JOIN pg_class c       ON c.oid = con.conrelid
JOIN pg_namespace n   ON n.oid = c.relnamespace
LEFT JOIN pg_class rc     ON rc.oid = con.confrelid
LEFT JOIN pg_namespace rn ON rn.oid = rc.relnamespace
WHERE con.contype IN ('p', 'f', 'u') AND n.nspname = ANY(%(schemas)s)
"""

ROW_ESTIMATE_SQL = """
SELECT n.nspname || '.' || c.relname, c.reltuples::bigint
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p') AND n.nspname = ANY(%(schemas)s)
"""


class PostgresSource:
    def __init__(self, host: str, dbname: str, user: str, password: str, port: int | str = 5432,
                 sslmode: str = "prefer", schemas: Optional[list[str]] = None,
                 statement_timeout_ms: int = 300_000, max_size: int = 4):
        import psycopg
        from psycopg_pool import ConnectionPool

        self._psycopg = psycopg
        self.schemas = schemas or ["public"]
        self.name = f"postgresql://{user}@{host}:{port}/{dbname}"
        conninfo = psycopg.conninfo.make_conninfo(
            host=host, port=str(port), dbname=dbname, user=user, password=password, sslmode=sslmode,
            application_name="kg-networkx-builder", connect_timeout="10",
            options=f"-c statement_timeout={int(statement_timeout_ms)} -c default_transaction_read_only=on",
        )
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=max_size, open=True, timeout=15)
        self._catalog: Optional[SchemaCatalog] = None

    # ------------------------------------------------------------ health
    def ping(self) -> dict:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT version(), current_user, current_setting('default_transaction_read_only')")
            version, user, ro = cur.fetchone()
        return {"server_version": version.split(",")[0], "user": user, "read_only": ro == "on"}

    # ------------------------------------------------------------ schema
    def introspect_schema(self) -> SchemaCatalog:
        params = {"schemas": self.schemas}
        tables: dict[str, TableInfo] = {}
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(COLUMNS_SQL, params)
            for table, col, pg_type, nullable in cur.fetchall():
                t = tables.setdefault(table, TableInfo(name=table, columns={}))
                t.columns[col] = ColumnInfo(name=col, pg_type=pg_type, nullable=nullable)
            cur.execute(CONSTRAINTS_SQL, params)
            for table, kind, cols, ref_table, ref_cols in cur.fetchall():
                t = tables.get(table)
                if t is None:
                    continue
                if kind == "p":
                    t.primary_key = list(cols)
                elif kind == "u":
                    t.unique_constraints.append(list(cols))
                elif kind == "f":
                    t.foreign_keys.append(ForeignKey(columns=list(cols), ref_table=ref_table,
                                                     ref_columns=list(ref_cols)))
            cur.execute(ROW_ESTIMATE_SQL, params)
            for table, est in cur.fetchall():
                if table in tables:
                    tables[table].row_estimate = max(int(est), 0)
        self._catalog = SchemaCatalog(tables=tables, source_name=self.name,
                                      extracted_at=datetime.now(timezone.utc).isoformat())
        return self._catalog

    def _check_identifiers(self, table: str, columns: list[str]) -> None:
        cat = self._catalog or self.introspect_schema()
        if table not in cat.tables:
            raise ValueError(f"unknown table {table}")
        unknown = [c for c in columns if c not in cat.tables[table].columns]
        if unknown:
            raise ValueError(f"unknown columns {unknown} in {table}")

    # ------------------------------------------------------------ data
    def iter_batches(self, table: str, columns: list[str], key_columns: list[str],
                     batch_size: int = 5000, since: Any = None,
                     watermark_column: Optional[str] = None,
                     start_after: Optional[tuple] = None) -> Iterator[list[dict]]:
        sql = self._psycopg.sql
        self._check_identifiers(table, list(columns) + list(key_columns) +
                                ([watermark_column] if watermark_column else []))
        schema, name = table.split(".")
        select_cols = list(dict.fromkeys(list(key_columns) + list(columns)))
        cols_sql = sql.SQL(", ").join(sql.Identifier(c) for c in select_cols)
        keys_sql = sql.SQL(", ").join(sql.Identifier(c) for c in key_columns)
        last_key = start_after
        while True:
            conds, params = [], []
            if since is not None and watermark_column:
                # >= so rows sharing the watermark timestamp are not lost (upserts are idempotent)
                conds.append(sql.SQL("{} >= %s").format(sql.Identifier(watermark_column)))
                params.append(since)
            if last_key is not None:
                ph = sql.SQL(", ").join(sql.Placeholder() for _ in key_columns)
                conds.append(sql.SQL("({}) > ({})").format(keys_sql, ph))
                params.extend(last_key)
            where = (sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conds)) if conds else sql.SQL("")
            query = sql.SQL("SELECT {} FROM {}.{}{} ORDER BY {} LIMIT %s").format(
                cols_sql, sql.Identifier(schema), sql.Identifier(name), where, keys_sql)
            params.append(batch_size)
            with self.pool.connection() as conn, \
                    conn.cursor(row_factory=self._psycopg.rows.dict_row) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
            if not rows:
                return
            yield rows
            last_key = tuple(rows[-1][k] for k in key_columns)
            if len(rows) < batch_size:
                return

    def count(self, table: str) -> int:
        sql = self._psycopg.sql
        self._check_identifiers(table, [])
        schema, name = table.split(".")
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(name)))
            return cur.fetchone()[0]

    def sample_rows(self, table: str, limit: int = 5) -> list[dict]:
        sql = self._psycopg.sql
        self._check_identifiers(table, [])
        schema, name = table.split(".")
        with self.pool.connection() as conn, conn.cursor(row_factory=self._psycopg.rows.dict_row) as cur:
            cur.execute(sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
                sql.Identifier(schema), sql.Identifier(name)), [int(limit)])
            return cur.fetchall()

    def close(self) -> None:
        self.pool.close()
