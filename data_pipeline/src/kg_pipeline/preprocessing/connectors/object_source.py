"""Bounded delimited object access, using the same parser as file uploads."""
from hashlib import sha256
from itertools import islice
from pathlib import PurePosixPath
import re

from kg_pipeline.core.schema_models import SchemaCatalog, TableInfo
from kg_pipeline.preprocessing.connectors.csv_source import ALLOWED_EXTENSIONS, CsvUpload, UploadLimits, build_csv_source


class ObjectSource:
    def __init__(self, name, listing, download, ping, close):
        self.name, self.listing, self.download = name, listing, download
        self.ping, self.close = ping, close
        self.limits = UploadLimits.from_settings()
        self.objects = {}
        self.catalog = None

    def introspect_schema(self):
        if self.catalog is None:
            tables = {}
            for path, size in islice(self.listing(), 1000):
                if not path.lower().endswith(ALLOWED_EXTENSIONS) or not size or size > self.limits.max_bytes:
                    continue
                stem = re.sub(r"[^a-z0-9_]", "_", PurePosixPath(path).stem.lower())[:40].strip("_")
                key = f"objects.file_{stem}_{sha256(path.encode()).hexdigest()[:12]}"
                self.objects[key] = (path, size)
                tables[key] = TableInfo(name=key, columns={}, source_path=path, size_bytes=size,
                                        asset_kind="file", relationship_origin="inferred")
            self.catalog = SchemaCatalog(tables=tables, source_name=self.name)
        return self.catalog

    def _read(self, table, preview=False):
        path, size = self.objects[table]
        count = min(size, 128 * 1024) if preview else size
        content = self.download(path, count)
        if len(content) != count:
            raise ValueError("Object size changed")
        if count < size:
            last = content.rfind(b"\n")
            if last < 0:
                raise ValueError("No complete rows in the preview range")
            content = content[:last + 1]
        filename = table.split(".", 1)[1] + ".csv"
        parsed = build_csv_source([CsvUpload(filename, content)], self.limits)
        return parsed, next(iter(parsed.introspect_schema().tables))

    def describe(self, table):
        parsed, key = self._read(table, preview=True)
        facts = parsed.introspect_schema().tables[key]
        path, size = self.objects[table]
        return facts.model_copy(update={"name": table, "source_path": path, "size_bytes": size,
                                        "foreign_keys": [], "asset_kind": "file", "relationship_origin": "inferred",
                                        "primary_key": facts.primary_key if size <= 128 * 1024 else [],
                                        "unique_constraints": facts.unique_constraints if size <= 128 * 1024 else []})

    def sample_rows(self, table, limit=5):
        parsed, key = self._read(table, preview=True)
        return parsed.sample_rows(key, limit)

    def count(self, table):
        parsed, key = self._read(table)
        return parsed.count(key)

    def iter_batches(self, table, *args, **kwargs):
        parsed, key = self._read(table)
        return parsed.iter_batches(key, *args, **kwargs)
