"""Data sources. Both implement the same read-only interface (see base.py)."""
from kg_pipeline.preprocessing.connectors.base import DataSource
from kg_pipeline.preprocessing.connectors.sample_source import SampleSource

__all__ = ["DataSource", "SampleSource"]
