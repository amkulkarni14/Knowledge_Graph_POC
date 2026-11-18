"""Shared test setup: make pipeline and legacy UI importable and keep every test's output out of the real storage/ folder."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "data_pipeline" / "src", ROOT / "legacy" / "streamlit"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from kg_pipeline.config import SAMPLE_FILES_DIR
from kg_pipeline.config import settings  # noqa: E402
from kg_pipeline.preprocessing.connectors.csv_source import CsvUpload
from kg_pipeline.preprocessing.connectors.csv_source import UploadLimits
from kg_pipeline.preprocessing.connectors.csv_source import read_directory  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Ontology repository, catalog, graph snapshots and the AI log are written under a temp folder."""
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")


@pytest.fixture
def limits() -> UploadLimits:
    return UploadLimits(max_files=10, max_bytes=100_000, max_rows=1_000)


@pytest.fixture
def customer360() -> list[CsvUpload]:
    return read_directory(SAMPLE_FILES_DIR / "customer360")


def csv_file(name: str, text: str, encoding: str = "utf-8") -> CsvUpload:
    """A CsvUpload from literal text (leading blank lines / indentation are not stripped; write flush-left)."""
    return CsvUpload(name, text.encode(encoding))
