"""Backend settings and access to the existing pipeline package."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
PIPELINE_SRC = ROOT / "data_pipeline" / "src"
if str(PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINE_SRC))


@dataclass(frozen=True)
class ApiSettings:
    storage_root: Path = field(default_factory=lambda: Path(
        os.environ.get("KG_API_STORAGE_DIR", str(ROOT / "storage" / "api_sessions"))).resolve())
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        value.strip() for value in os.environ.get(
            "KG_API_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if value.strip()))
    session_ttl_seconds: int = 3600
    max_sessions: int = 100
    max_request_bytes: int = 64 * 1024 * 1024
    max_jobs: int = 2

    def __post_init__(self):
        if min(self.session_ttl_seconds, self.max_sessions, self.max_request_bytes, self.max_jobs) < 1:
            raise ValueError("API resource limits must be positive")
        if "*" in self.cors_origins:
            raise ValueError("Configure explicit CORS origins")
