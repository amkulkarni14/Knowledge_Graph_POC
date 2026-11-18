"""Normalization, type coercion and identifier helpers (used by Stages 12-14)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from kg_pipeline.core.ontology_models import DataType

_WS = re.compile(r"\s+")


class CoercionError(ValueError):
    pass


def normalize(value: Any, mode: Optional[str]) -> Any:
    """Always trims and collapses whitespace; optionally changes case."""
    if not isinstance(value, str):
        return value
    v = _WS.sub(" ", value).strip()
    if mode == "lower":
        return v.lower()
    if mode == "upper":
        return v.upper()
    if mode == "title":
        return v.title()
    return v


def coerce(value: Any, dt: DataType) -> Any:
    """Converts a source value into a graph-safe (JSON/GraphML friendly) value."""
    if value is None:
        return None
    try:
        if dt == DataType.STRING:
            return str(value)
        if dt == DataType.INTEGER:
            if isinstance(value, float) and not value.is_integer():
                raise CoercionError(f"{value} is not an integer")
            return int(value)
        if dt == DataType.FLOAT:
            return float(value)
        if dt == DataType.DECIMAL:
            return round(float(Decimal(str(value))), 2)
        if dt == DataType.BOOLEAN:
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in {"true", "t", "1", "yes", "y"}:
                return True
            if s in {"false", "f", "0", "no", "n"}:
                return False
            raise CoercionError(f"{value!r} is not a boolean")
        if dt == DataType.DATE:
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            return date.fromisoformat(str(value)).isoformat()
        if dt == DataType.DATETIME:
            if isinstance(value, datetime):
                return value.isoformat()
            return datetime.fromisoformat(str(value)).isoformat()
        if dt == DataType.JSON:
            return value if isinstance(value, str) else json.dumps(value, default=str)
    except (ValueError, TypeError, InvalidOperation) as e:
        raise CoercionError(str(e)) from e
    raise CoercionError(f"unsupported type {dt}")


def canon_key(values) -> Optional[tuple]:
    """Canonical key for ids and lookups: 42 and '42' match. None if any part is NULL."""
    values = tuple(values)
    if any(v is None for v in values):
        return None
    return tuple(str(v).strip() for v in values)


def node_id(class_name: str, key_values: tuple) -> str:
    """Deterministic, globally unique node id: '<Class>:<pk>' (composite keys joined by '|')."""
    return f"{class_name}:{'|'.join(str(v) for v in key_values)}"
