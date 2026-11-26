"""Connection candidates and selection-scoped pipeline sources."""
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4
import os

from backend.app.core.source_network import endpoint_address
from backend.app.dto.models import PostgresRequest
from backend.app.dto.sources import ConnectionView
from backend.app.exceptions.handlers import ApiError
from backend.app.services import provider_sources
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.preprocessing.connectors.base import DataSource
from kg_pipeline.preprocessing.connectors.csv_source import build_csv_source
from kg_pipeline.preprocessing.connectors.postgres_source import PostgresSource
from kg_pipeline.preprocessing.connectors.sample_source import SampleSource


@dataclass
class Candidate:
    source: DataSource
    catalog: SchemaCatalog
    info: ConnectionView

    def close(self):
        close(self.source)


def close(source):
    if source is not None:
        try:
            source.close()
        except Exception:
            pass


def postgres_options(configuration):
    values = configuration.model_dump(exclude={"password"})
    values["hostaddr"] = endpoint_address(configuration.host, configuration.port,
                                           verified_tls=configuration.sslmode == "verify-full")
    values["password"] = configuration.password.get_secret_value()
    return values


def _postgres(config):
    config = dict(config)
    config["port"] = int(config.get("port") or 5432)
    config["schemas"] = [value.strip() for value in config.get("schemas", "public").split(",") if value.strip()]
    config.setdefault("sslmode", "verify-full")
    request = PostgresRequest.model_validate(config)
    return PostgresSource(**postgres_options(request)), {
        "database": request.dbname, "endpoint": f"{request.host}:{request.port}", "authentication": "password",
    }


def _sample(_config):
    return SampleSource(), {"read_only": True}


FACTORIES = {"postgres": _postgres, "sample": _sample, **provider_sources.FACTORIES}


def _prepare(kind, name, open_source, *, discover):
    source = None
    started = monotonic()
    try:
        source, details = open_source()
        ping = getattr(source, "ping", None)
        if ping is not None:
            check = ping() or {}
            if "read_only" in check:
                details["read_only"] = check["read_only"]
        catalog = source.introspect_schema() if discover else SchemaCatalog(tables={})
        if discover and not catalog.tables:
            raise ApiError(422, "source_has_no_assets", "No accessible supported assets were found")
        info = ConnectionView(id=uuid4(), source=kind, name=name,
                              connected_at=datetime.now(timezone.utc).isoformat(),
                              duration_ms=int((monotonic() - started) * 1000), asset_count=len(catalog.tables),
                              **details)
        return Candidate(source, catalog, info)
    except ApiError:
        close(source)
        raise
    except ImportError:
        close(source)
        raise ApiError(503, "source_driver_unavailable", "The connector driver is unavailable") from None
    except ValueError:
        close(source)
        raise ApiError(422, "invalid_source_config", "Check the connection fields and source format") from None
    except Exception:
        close(source)
        raise ApiError(502, "source_connection_failed", "Check source credentials, connectivity, permissions and TLS") from None


def prepare(request, *, discover=True):
    if request.source not in FACTORIES:
        raise ApiError(422, "invalid_connector", "Use the file upload endpoint for local files")
    config = {name: value.get_secret_value() for name, value in request.configuration.items()}
    if any(len(value) > 4096 for value in config.values()):
        raise ApiError(422, "invalid_source_config", "A connection field exceeds its supported length")
    return _prepare(request.source, request.name, lambda: FACTORIES[request.source](config), discover=discover)


def prepare_upload(uploads, limits):
    return _prepare("csv", "Uploaded CSV files", lambda: (build_csv_source(uploads, limits), {"read_only": True}),
                    discover=True)


class SelectedSource:
    def __init__(self, candidate, assets):
        if len(assets) != len(set(assets)) or not set(assets) <= candidate.catalog.tables.keys():
            raise ApiError(422, "invalid_assets", "Select distinct assets from the current connection")
        self.source = candidate.source
        self.name = candidate.info.name
        self.max_extraction_rows = int(os.getenv("KG_SOURCE_MAX_ROWS", "100000"))
        self.max_extraction_bytes = int(os.getenv("KG_SOURCE_MAX_BYTES", "134217728"))
        self.catalog = candidate.catalog.model_copy(deep=True)
        self.catalog.source_type = candidate.info.source
        self.catalog.connection_id = str(candidate.info.id)
        describe = getattr(self.source, "describe", None)
        self.catalog.tables = {asset: describe(asset) if describe else self.catalog.tables[asset] for asset in assets}
        for table in self.catalog.tables.values():
            table.foreign_keys = [key for key in table.foreign_keys if key.ref_table in self.catalog.tables]

    def introspect_schema(self):
        return self.catalog.model_copy(deep=True, update={"extracted_at": datetime.now(timezone.utc).isoformat()})

    def _require(self, table):
        if table not in self.catalog.tables:
            raise ValueError("Asset was not selected")

    def iter_batches(self, table, *args, **kwargs):
        self._require(table)
        return self.source.iter_batches(table, *args, **kwargs)

    def sample_rows(self, table, limit=5):
        self._require(table)
        return self.source.sample_rows(table, limit)

    def count(self, table):
        self._require(table)
        return self.source.count(table)

    def ping(self):
        return self.source.ping()

    def close(self):
        close(self.source)
