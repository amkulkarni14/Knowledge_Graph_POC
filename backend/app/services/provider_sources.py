"""Provider factories; SDKs are loaded only when the corresponding source is used."""
from functools import partial
from itertools import islice
from urllib.parse import urlsplit
import os
import re

from backend.app.core.source_network import endpoint_address
from backend.app.exceptions.handlers import ApiError
from kg_pipeline.preprocessing.connectors.bigquery_source import BigQuerySource
from kg_pipeline.preprocessing.connectors.object_source import ObjectSource
from kg_pipeline.preprocessing.connectors.relational_source import RelationalSource

PASSWORD = {"password": ("user", "password")}
AZURE = {"default": (), "key": ("account_key",), "sas": ("sas",),
         "principal": ("tenant", "client", "client_secret")}
AUTH = {"mssql": PASSWORD, "oracle": PASSWORD,
        "s3": {"default": (), "key": ("access_key", "secret_key"),
               "temporary": ("access_key", "secret_key", "session_token")},
        "azure_blob": AZURE, "azure_adls": AZURE, "gcs": {"default": ()}, "bigquery": {"default": ()}}
FIELDS = {"mssql": ("host", "port", "database", "schema"),
          "oracle": ("host", "port", "identifier_type", "identifier", "schema"),
          "s3": ("region", "bucket"), "azure_blob": ("account", "container"), "azure_adls": ("account", "container"),
          "gcs": ("project", "bucket"), "bigquery": ("project", "dataset")}
OPTIONAL = {"s3": ("prefix", "endpoint"), "azure_blob": ("prefix",), "azure_adls": ("prefix",),
            "gcs": ("prefix",), "bigquery": ("location",)}
LOCATIONS = {"s3": "bucket", "azure_blob": "container", "azure_adls": "container", "gcs": "bucket", "bigquery": "dataset"}
PATTERNS = {"host": r"[A-Za-z0-9.:-]{1,253}", "port": r"\d{1,5}", "schema": r"[A-Za-z_][A-Za-z0-9_]{0,62}",
            "identifier_type": r"service|sid", "identifier": r"[A-Za-z0-9._-]{1,200}", "region": r"[a-z0-9-]{2,40}",
            "bucket": r"[a-z0-9][a-z0-9_.-]{1,220}", "account": r"[a-z0-9]{3,24}",
            "container": r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", "project": r"[a-z][a-z0-9-]{4,61}[a-z0-9]",
            "dataset": r"[A-Za-z_][A-Za-z0-9_]{0,62}", "location": r"[A-Za-z0-9-]{0,40}",
            "tenant": r"[A-Za-z0-9.-]{1,100}", "client": r"[A-Za-z0-9-]{1,100}"}


def checked(kind, config, list_only=False):
    method = config.get("authentication")
    fields = AUTH[kind].get(method)
    if fields is None:
        raise ApiError(422, "invalid_source_config", "Select a supported authentication method")
    required = set(FIELDS[kind]) | set(fields)
    permitted = required | set(OPTIONAL.get(kind, ())) | {"authentication"}
    if list_only:
        required.discard(LOCATIONS[kind])
    if set(config) - permitted or any(not config.get(key, "").strip() for key in required):
        raise ApiError(422, "invalid_source_config", "Complete the necessary connection fields")
    for name, value in config.items():
        if name in PATTERNS and not re.fullmatch(PATTERNS[name], value):
            raise ApiError(422, "invalid_source_config", f"Check the format of {name}")
    return config


def mssql(cfg):
    import pyodbc
    if "ODBC Driver 18 for SQL Server" not in pyodbc.drivers():
        raise ApiError(503, "source_driver_unavailable", "Install Microsoft ODBC Driver 18 for SQL Server")
    host, port = cfg["host"], int(cfg["port"])
    address = endpoint_address(host, port)
    options = {"Driver": "ODBC Driver 18 for SQL Server", "Server": f"tcp:{address},{port}",
               "Database": cfg["database"], "UID": cfg["user"], "PWD": cfg["password"],
               "Encrypt": "yes", "TrustServerCertificate": "no", "HostNameInCertificate": host,
               "ApplicationIntent": "ReadOnly"}
    dsn = ";".join(key + "={" + value.replace("}", "}}") + "}" for key, value in options.items())

    def connect():
        conn = pyodbc.connect(dsn, timeout=8, readonly=True)
        conn.timeout = 30
        return conn

    return RelationalSource(cfg["database"], connect, "mssql", cfg["schema"]), f"{host}:{port}"


def oracle(cfg):
    import oracledb
    host, port = cfg["host"], int(cfg["port"])
    endpoint_address(host, port)
    identifier = {"sid" if cfg["identifier_type"] == "sid" else "service_name": cfg["identifier"]}
    params = oracledb.ConnectParams(host=host, port=port, protocol="tcps", ssl_server_dn_match=True,
                                    tcp_connect_timeout=8, retry_count=0, **identifier)
    if wallet := os.getenv("KG_SOURCE_ORACLE_WALLET_DIR"):
        params.set(wallet_location=wallet, wallet_password=os.getenv("KG_SOURCE_ORACLE_WALLET_PASSWORD"))

    def connect():
        conn = oracledb.connect(user=cfg["user"], password=cfg["password"], params=params)
        try:
            conn.call_timeout = 30000
            with conn.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            return conn
        except Exception:
            conn.close()
            raise

    return RelationalSource(cfg["identifier"], connect, "oracle", cfg["schema"].upper()), f"{host}:{port}"


def s3(cfg, *, list_only=False):
    import boto3
    from botocore.config import Config

    endpoint = cfg.get("endpoint")
    options = {}
    if endpoint:
        parsed = urlsplit(endpoint)
        origin = endpoint.rstrip("/")
        allowed = os.getenv("KG_SOURCE_S3_ENDPOINTS", "").split(",")
        if (origin not in {item.strip() for item in allowed} or parsed.scheme not in {"http", "https"}
                or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ApiError(403, "source_endpoint_denied", "Use an explicitly allowed S3 endpoint origin")
        endpoint_address(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
                         verified_tls=parsed.scheme == "https")
        if cfg["authentication"] == "default":
            raise ApiError(422, "invalid_source_config", "Custom endpoints require endpoint-specific credentials")
        options["endpoint_url"] = endpoint
    if cfg["authentication"] != "default":
        options.update(aws_access_key_id=cfg["access_key"], aws_secret_access_key=cfg["secret_key"])
        if cfg["authentication"] == "temporary":
            options["aws_session_token"] = cfg["session_token"]
    client = boto3.client("s3", region_name=cfg["region"], config=Config(
        connect_timeout=5, read_timeout=15, retries={"total_max_attempts": 2},
        s3={"addressing_style": "path"} if endpoint else None), **options)
    if list_only:
        try:
            return [bucket["Name"] for page in client.get_paginator("list_buckets").paginate(
                PaginationConfig={"MaxItems": 100}) for bucket in page.get("Buckets", [])]
        finally:
            client.close()
    bucket, prefix = cfg["bucket"], cfg.get("prefix", "")

    def listing():
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
            yield from ((item["Key"], item["Size"]) for item in page.get("Contents", []))

    def download(path, size):
        with client.get_object(Bucket=bucket, Key=path, Range=f"bytes=0-{size - 1}")["Body"] as body:
            return body.read(size + 1)

    return ObjectSource(bucket, listing, download,
                        lambda: client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1) and None,
                        client.close), endpoint


def azure(cfg, *, datalake=False, list_only=False):
    from azure.identity import ClientSecretCredential, DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    from azure.storage.filedatalake import DataLakeServiceClient
    method = cfg["authentication"]
    if method == "default":
        credential = DefaultAzureCredential()
    elif method == "principal":
        credential = ClientSecretCredential(cfg["tenant"], cfg["client"], cfg["client_secret"])
    else:
        credential = cfg["account_key" if method == "key" else "sas"]
    endpoint = f"https://{cfg['account']}.{'dfs' if datalake else 'blob'}.core.windows.net"
    client = (DataLakeServiceClient if datalake else BlobServiceClient)(
        endpoint, credential=credential, connection_timeout=5, read_timeout=15, retry_total=1)

    def close():
        try:
            client.close()
        finally:
            if hasattr(credential, "close"):
                credential.close()

    try:
        if list_only:
            try:
                values = client.list_file_systems() if datalake else client.list_containers()
                return [item.name for item in islice(values, 100)]
            finally:
                close()
        name, prefix = cfg["container"], cfg.get("prefix", "")
        if datalake:
            handle = client.get_file_system_client(name)

            def listing():
                return ((item.name, item.content_length) for item in handle.get_paths(path=prefix or None)
                        if not item.is_directory)

            def download(path, size):
                return handle.get_file_client(path).download_file(offset=0, length=size).readall()
        else:
            handle = client.get_container_client(name)

            def listing():
                return ((item.name, item.size) for item in handle.list_blobs(name_starts_with=prefix))

            def download(path, size):
                return handle.download_blob(path, offset=0, length=size).readall()
        return ObjectSource(name, listing, download, lambda: next(iter(listing()), None) and None, close), endpoint
    except Exception:
        if not list_only:
            close()
        raise


def gcs(cfg, *, list_only=False):
    from google.cloud import storage
    client = storage.Client(project=cfg["project"])
    if list_only:
        try:
            return [bucket.name for bucket in client.list_buckets(max_results=100, timeout=10)]
        finally:
            client.close()
    bucket = client.bucket(cfg["bucket"])
    prefix = cfg.get("prefix", "")

    def listing():
        return ((item.name, item.size) for item in client.list_blobs(bucket, prefix=prefix, timeout=10))

    def download(path, size):
        return bucket.blob(path).download_as_bytes(start=0, end=size - 1, raw_download=True, timeout=15)

    def ping():
        next(iter(client.list_blobs(bucket, prefix=prefix, max_results=1, timeout=10)), None)

    return ObjectSource(bucket.name, listing, download, ping, client.close), None


def bigquery(cfg, *, list_only=False):
    if list_only:
        from google.cloud.bigquery import Client
        client = Client(project=cfg["project"])
        try:
            return [item.dataset_id for item in client.list_datasets(max_results=100, timeout=10)]
        finally:
            client.close()
    return BigQuerySource(cfg["project"], cfg["dataset"], cfg.get("location")), None


ADAPTERS = {"mssql": mssql, "oracle": oracle, "s3": s3, "azure_blob": azure,
            "azure_adls": partial(azure, datalake=True), "gcs": gcs, "bigquery": bigquery}


def factory(kind, config):
    source, endpoint = ADAPTERS[kind](checked(kind, config))
    return source, {"database": source.name, "endpoint": endpoint, "authentication": config["authentication"]}


FACTORIES = {kind: partial(factory, kind) for kind in ADAPTERS}


def locations(kind, config):
    if kind not in LOCATIONS:
        raise ApiError(422, "unsupported_discovery", "This connector has no cloud locations to list")
    try:
        return ADAPTERS[kind](checked(kind, config, list_only=True), list_only=True)
    except ApiError:
        raise
    except ImportError:
        raise ApiError(503, "source_driver_unavailable", "The connector SDK is unavailable") from None
    except Exception:
        raise ApiError(502, "source_discovery_failed", "Enter a known location or check the permissions to list locations") from None
