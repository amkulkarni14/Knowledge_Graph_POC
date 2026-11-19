"""Compile a small read-only Cypher grammar to server-owned scoped statements.

Accepted statements match one labelled node or one directed typed relationship.
Projections select declared variables or count(variable). A row limit is optional.
"""
from dataclasses import dataclass
import re

from backend.app.exceptions.handlers import ApiError
from backend.app.services.neo_graph import EDGE_MATCH, NODE_MATCH

NAME = r"[A-Za-z][A-Za-z0-9_]{0,62}"
PATTERN = re.compile(
    rf"MATCH\s*\(\s*(?P<left>{NAME})\s*:\s*(?P<label>{NAME})\s*\)"
    rf"(?:\s*-\[\s*(?P<edge>{NAME})?\s*:\s*(?P<kind>{NAME})\s*\]->\s*"
    rf"\(\s*(?P<right>{NAME})\s*:\s*(?P<target>{NAME})\s*\))?"
    rf"\s*RETURN\s+(?P<projection>.+?)(?:\s+LIMIT\s+(?P<limit>[0-9]{{1,6}}))?\s*;?",
    re.IGNORECASE,
)
PROJECTION = re.compile(rf"(?:(?P<variable>{NAME})|count\(\s*(?P<counted>{NAME})\s*\))", re.IGNORECASE)

NODE_MAP = "{id: %(alias)s.id, properties: properties(%(alias)s)}"
EDGE_MAP = "{source: {id: a.id, properties: properties(a)}, target: {id: b.id, properties: properties(b)}, " \
           "key: r.key, properties: properties(r)}"


@dataclass(frozen=True)
class ScopedQuery:
    statement: str
    parameters: dict
    columns: list[str]


def compile_query(text):
    parsed = PATTERN.fullmatch(" ".join(text.split()))
    if not parsed:
        raise ApiError(422, "unsupported_cypher", "Use MATCH with one labelled node or typed directed relationship, RETURN variables or counts, and an optional LIMIT.")
    data = parsed.groupdict()
    aliases = {data["left"]: "a" if data["right"] else "n"}
    match = NODE_MATCH + " WHERE n.label = $label"
    parameters = {"label": data["label"], "limit": min(int(data["limit"] or 50), 200)}
    if data["right"]:
        if data["right"] in aliases or data["edge"] in (data["left"], data["right"]):
            raise ApiError(422, "duplicate_cypher_variable", "Use distinct graph variables")
        aliases[data["right"]] = "b"
        if data["edge"]:
            aliases[data["edge"]] = "r"
        match = EDGE_MATCH + " WHERE a.label = $label AND b.label = $target AND type(r) = $kind"
        parameters.update(target=data["target"], kind=data["kind"])
    expressions = []
    columns = []
    for projection in data["projection"].split(","):
        item = PROJECTION.fullmatch(projection.strip())
        if not item or (item["variable"] or item["counted"]) not in aliases:
            raise ApiError(422, "unsupported_cypher_projection", "Return only declared variables or count(variable)")
        alias = aliases[item["variable"] or item["counted"]]
        if item["counted"]:
            expression, column = f"count({alias})", f"count({item['counted']})"
        else:
            expression = EDGE_MAP if alias == "r" else NODE_MAP % {"alias": alias}
            column = item["variable"]
        if column in columns:
            raise ApiError(422, "duplicate_cypher_column", "Return each column once")
        expressions.append(f"{expression} AS value{len(columns)}")
        columns.append(column)
    return ScopedQuery(match + " RETURN " + ", ".join(expressions) + " LIMIT $limit", parameters, columns)
