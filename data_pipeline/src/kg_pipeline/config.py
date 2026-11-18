"""Central settings. Values come from environment variables (or a local .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
ONTOLOGY_DIR = DATA_DIR / "ontologies"
SAMPLE_FILES_DIR = DATA_DIR / "samples"
FIXTURE_DIR = DATA_DIR / "fixtures"


def _storage_dir() -> Path:
    p = Path(os.environ.get("KG_STORAGE_DIR", "storage"))
    return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass
class Settings:
    storage_dir: Path = field(default_factory=_storage_dir)
    batch_size: int = int(os.environ.get("KG_BATCH_SIZE", "5000"))
    groq_model: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    pg_schemas: list[str] = field(
        default_factory=lambda: [s.strip() for s in os.environ.get("PG_SCHEMAS", "public").split(",") if s.strip()])
    # Uploaded CSV files (Stage 2) are held in memory, so they are bounded.
    max_upload_files: int = int(os.environ.get("KG_MAX_UPLOAD_FILES", "25"))
    max_upload_mb: int = int(os.environ.get("KG_MAX_UPLOAD_MB", "25"))
    max_upload_rows: int = int(os.environ.get("KG_MAX_UPLOAD_ROWS", "200000"))

    @property
    def ontology_repo_dir(self) -> Path:
        return self.storage_dir / "ontology_repo"

    @property
    def graph_store_dir(self) -> Path:
        return self.storage_dir / "graphs"

    @property
    def catalog_dir(self) -> Path:
        return self.storage_dir / "catalog"

    @property
    def ai_log_path(self) -> Path:
        return self.storage_dir / "logs" / "ai_requests.jsonl"

    @property
    def groq_available(self) -> bool:
        return bool(os.environ.get("GROQ_API_KEY"))


settings = Settings()
