"""Catalog-constrained, read-only relations for Oracle and SQL Server."""
from collections import defaultdict
from contextlib import closing
import re

from kg_pipeline.core.schema_models import ColumnInfo, ForeignKey, SchemaCatalog, TableInfo

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}")
TYPES = {"number": "numeric", "int": "integer", "bigint": "bigint", "smallint": "smallint",
         "tinyint": "smallint", "decimal": "numeric", "numeric": "numeric", "bit": "boolean",
         "float": "double precision", "binary_double": "double precision", "real": "real",
         "binary_float": "real", "date": "date", "datetime": "timestamp without time zone",
         "datetime2": "timestamp without time zone", "timestamp": "timestamp without time zone",
         "datetimeoffset": "timestamp with time zone"}
UNSUPPORTED = {"blob", "clob", "nclob", "bfile", "raw", "long raw", "varbinary", "binary", "image"}

ORACLE_COLUMNS = """
SELECT owner, table_name, column_name, data_type, nullable FROM all_tab_columns
WHERE owner = :owner ORDER BY table_name, column_id
"""
ORACLE_KEYS = """
SELECT c.table_name, c.constraint_type, a.column_name, r.owner, r.table_name, b.column_name, c.constraint_name
FROM all_constraints c JOIN all_cons_columns a
 ON c.owner = a.owner AND c.constraint_name = a.constraint_name
LEFT JOIN all_constraints r ON c.r_owner = r.owner AND c.r_constraint_name = r.constraint_name
LEFT JOIN all_cons_columns b ON r.owner = b.owner AND r.constraint_name = b.constraint_name AND b.position = a.position
WHERE c.owner = :owner AND c.constraint_type IN ('P','U','R')
ORDER BY c.table_name, c.constraint_name, a.position
"""


class RelationalSource:
    def __init__(self, name, connect, kind, schema):
        self.name, self.connect, self.kind, self.schema = name, connect, kind, schema
        self.catalog = None

    def ping(self):
        with closing(self.connect()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM DUAL" if self.kind == "oracle" else "SELECT 1")
            cursor.fetchone()
        return {"read_only": True} if self.kind == "oracle" else {}

    def introspect_schema(self):
        if self.catalog is not None:
            return self.catalog
        tables = {}
        with closing(self.connect()) as conn, closing(conn.cursor()) as cursor:
            if self.kind == "oracle":
                cursor.execute(ORACLE_COLUMNS, owner=self.schema)
                for schema, table, column, kind, nullable in cursor:
                    self._add(tables, schema, table, column, kind, nullable == "Y")
                cursor.execute(ORACLE_KEYS, owner=self.schema)
                groups = defaultdict(list)
                for table, kind, column, ref_owner, ref_table, ref_column, constraint in cursor:
                    groups[(table, kind, ref_owner, ref_table, constraint)].append((column, ref_column))
                for (table, kind, ref_owner, ref_table, _), pairs in groups.items():
                    info = tables.get(f"{self.schema}.{table}")
                    names = [column for column, _ in pairs]
                    if not info or not set(names) <= info.columns.keys():
                        continue
                    if kind == "P":
                        info.primary_key = names
                    elif kind == "U":
                        info.unique_constraints.append(names)
                    elif ref_table and all(ref_column for _, ref_column in pairs):
                        info.foreign_keys.append(ForeignKey(columns=names, ref_table=f"{ref_owner}.{ref_table}",
                                                            ref_columns=[column for _, column in pairs]))
            else:
                for row in cursor.columns(schema=self.schema):
                    self._add(tables, row.table_schem, row.table_name, row.column_name, row.type_name, bool(row.nullable))
                for name, info in tables.items():
                    schema, table = name.split(".", 1)
                    primary = sorted(cursor.primaryKeys(table=table, schema=schema), key=lambda row: row.key_seq)
                    keys = [row.column_name for row in primary]
                    if set(keys) <= info.columns.keys():
                        info.primary_key = keys
                    groups = defaultdict(list)
                    for row in cursor.foreignKeys(foreignTable=table, foreignSchema=schema):
                        groups[(row.fk_name, row.pktable_schem, row.pktable_name)].append(row)
                    for (_, ref_schema, ref_table), rows in groups.items():
                        ordered = sorted(rows, key=lambda row: row.key_seq)
                        columns = [row.fkcolumn_name for row in ordered]
                        if set(columns) <= info.columns.keys():
                            info.foreign_keys.append(ForeignKey(columns=columns, ref_table=f"{ref_schema}.{ref_table}",
                                                                ref_columns=[row.pkcolumn_name for row in ordered]))
        self.catalog = SchemaCatalog(tables=tables, source_name=self.name)
        return self.catalog

    @staticmethod
    def _add(tables, schema, table, column, kind, nullable):
        if not all(value and IDENTIFIER.fullmatch(value) for value in (schema, table, column)) or kind.lower() in UNSUPPORTED:
            return
        name = f"{schema}.{table}"
        tables.setdefault(name, TableInfo(name=name, columns={})).columns[column] = ColumnInfo(
            name=column, pg_type=TYPES.get(kind.lower(), "text"), nullable=nullable, original_type=kind)

    def _quote(self, name):
        return f"[{name}]" if self.kind == "mssql" else f'"{name}"'

    def _table(self, table):
        if table not in self.introspect_schema().tables:
            raise ValueError("Unknown resource")
        return ".".join(self._quote(name) for name in table.split("."))

    def iter_batches(self, table, columns, key_columns, batch_size=5000, since=None,
                     watermark_column=None, start_after=None, *, limit=None):
        name = self._table(table)
        fields = list(dict.fromkeys([*columns, *key_columns]))
        if not fields or not set(fields) <= self.catalog.tables[table].columns.keys() or since is not None or start_after is not None:
            raise ValueError("Unsupported read")
        projection = ", ".join(map(self._quote, fields))
        top = f"TOP ({limit}) " if limit is not None and self.kind == "mssql" else ""
        tail = f" FETCH FIRST {limit} ROWS ONLY" if limit is not None and self.kind == "oracle" else ""
        with closing(self.connect()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(f"SELECT {top}{projection} FROM {name}{tail}")
            while rows := cursor.fetchmany(batch_size):
                yield [dict(zip(fields, row)) for row in rows]

    def sample_rows(self, table, limit=5):
        fields = list(self.introspect_schema().tables[table].columns)
        with closing(self.iter_batches(table, fields, [], limit, limit=int(limit))) as batches:
            return next(batches, [])

    def count(self, table):
        name = self._table(table)
        with closing(self.connect()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {name}")
            return cursor.fetchone()[0]

    def close(self):
        pass
