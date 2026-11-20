"""Stream one authorized version without loading it into application memory."""
import csv
import hashlib
import io
import json
from xml.sax.saxutils import escape
from fastapi.responses import StreamingResponse

from backend.app.services.neo_graph import EDGE_MATCH, NODE_MATCH, NeoGraphStore

NODE_ROWS = NODE_MATCH + " RETURN n.id AS id, properties(n) AS properties"
EDGE_ROWS = EDGE_MATCH + " RETURN a.id AS source, b.id AS target, r.key AS key, properties(r) AS properties"
CONTENT_TYPES = {
    "json": "application/json",
    "graphml": "application/graphml+xml",
    "nodes.csv": "text/csv; charset=utf-8",
    "relationships.csv": "text/csv; charset=utf-8",
}


def json_rows(rows):
    for index, row in enumerate(rows):
        yield ("," if index else "") + json.dumps(row, allow_nan=False)


def xml_id(node):
    return "n" + hashlib.sha256(node.encode()).hexdigest()


def csv_rows(rows, header):
    line = io.StringIO()
    writer = csv.writer(line)
    writer.writerow(header)
    yield line.getvalue()
    for row in rows:
        line.seek(0)
        line.truncate(0)
        values = []
        for key in header:
            value = row[key]
            if isinstance(value, dict):
                value = json.dumps(value)
            elif isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
        yield line.getvalue()


def graphml_rows(nodes, edges):
    yield ('<?xml version="1.0" encoding="UTF-8"?>'
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">'
           '<key id="properties" for="all" attr.name="properties" attr.type="string"/>'
           '<graph edgedefault="directed">')
    for node in nodes:
        data = escape(json.dumps(node))
        yield f'<node id="{xml_id(node["id"])}"><data key="properties">{data}</data></node>'
    for index, edge in enumerate(edges):
        data = escape(json.dumps(edge))
        yield (f'<edge id="e{index}" source="{xml_id(edge["source"])}" target="{xml_id(edge["target"])}">'
               f'<data key="properties">{data}</data></edge>')
    yield "</graph></graphml>"


def stream_graph(project, version, format_name):
    with NeoGraphStore(read=True) as store:
        if format_name == "nodes.csv":
            yield from csv_rows(store.records(NODE_ROWS, project, version, timeout=60), ("id", "properties"))
        elif format_name == "relationships.csv":
            yield from csv_rows(store.records(EDGE_ROWS, project, version, timeout=60),
                                ("source", "target", "key", "properties"))
        elif format_name == "json":
            yield '{"directed":true,"multigraph":true,"graph":{},"nodes":['
            yield from json_rows(store.records(NODE_ROWS, project, version, timeout=60))
            yield '],"edges":['
            yield from json_rows(store.records(EDGE_ROWS, project, version, timeout=60))
            yield "]}"
        else:
            yield from graphml_rows(store.records(NODE_ROWS, project, version, timeout=60),
                                    store.records(EDGE_ROWS, project, version, timeout=60))


def graphml_response(view):
    return StreamingResponse(graphml_rows(view["nodes"], view["edges"]), media_type=CONTENT_TYPES["graphml"],
                             headers={"Content-Disposition": 'attachment; filename="neighborhood.graphml"'})
