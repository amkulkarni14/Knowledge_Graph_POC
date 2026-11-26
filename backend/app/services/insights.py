"""Aggregate bounded, read-only profiles without returning source rows."""
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from heapq import nlargest
from itertools import islice
from math import isfinite
from time import monotonic

import networkx as nx

from backend.app.exceptions.handlers import ApiError
from backend.app.services import graphs
from kg_pipeline.core.ontology_models import DataType

CATEGORY_WORDS = {"category", "type", "status", "region", "country", "segment",
                  "department", "tier", "currency", "classification", "channel"}
PRIVATE_WORDS = {"name", "address", "email", "phone", "identifier", "id", "key",
                 "password", "secret", "token", "birth", "dob", "ssn", "accountnumber",
                 "zip", "postal", "latitude", "longitude", "customer", "patient", "employee"}
SAFE_CATEGORY = re.compile(r"[\w][\w .&()/+-]{0,39}\Z")
MIN_GROUP = 3


def limit(name, default, maximum):
    try:
        return min(maximum, max(1, int(os.getenv(name, default))))
    except ValueError:
        return default


def discover(ctx, table):
    keys = set(table.primary_key)
    keys.update(column for group in table.unique_constraints for column in group)
    keys.update(column for fk in table.foreign_keys for column in fk.columns)
    sensitive = set(ctx.scope.sensitive_columns if ctx.scope else [])
    onto = ctx.build_ontology or ctx.manual_ontology
    if onto:
        for cls in onto.classes:
            if cls.mapping and cls.mapping.source_table == table.name:
                sensitive.update(f"{table.name}.{a.source_column}" for a in cls.attributes if a.pii)
        for relationship in onto.relationships:
            if relationship.mapping and relationship.mapping.table == table.name:
                sensitive.update(f"{table.name}.{a.source_column}" for a in relationship.properties if a.pii)
    fields = []
    for name, column in table.columns.items():
        words = set(re.findall(r"[a-z]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower()))
        if name in keys or f"{table.name}.{name}" in sensitive or words & PRIVATE_WORDS:
            continue
        dtype = column.data_type
        if dtype in {DataType.DATE, DataType.DATETIME}:
            role, semantic = "date", "time"
        elif words & CATEGORY_WORDS and dtype == DataType.STRING:
            role = "category"
            semantic = next(word for word in ("status", "region", "country", "segment", "category", "type", "department",
                                               "tier", "currency", "classification", "channel") if word in words)
        elif dtype in {DataType.INTEGER, DataType.DECIMAL, DataType.FLOAT}:
            role, semantic = "measure", "numeric"
        else:
            continue
        fields.append({"name": name, "role": role, "semantic": semantic})
        if len(fields) == 100:
            break
    return fields


def selected_field(fields, role, value):
    options = [field["name"] for field in fields if field["role"] == role]
    if value is not None and value not in options:
        raise ApiError(422, "invalid_insight_field", "Select a field available for this dataset")
    return value or next(iter(options), None)


def day_of(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return None


def period(day, interval):
    if interval == "week":
        return (day - timedelta(days=day.weekday())).isoformat()
    if interval == "month":
        return day.strftime("%Y-%m")
    if interval == "quarter":
        return f"{day.year:04d}-Q{(day.month - 1) // 3 + 1}"
    if interval == "year":
        return f"{day.year:04d}"
    return day.isoformat()


def numeric(value):
    if not isinstance(value, (int, float, Decimal, str)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if isfinite(number) and abs(number) <= 1e100 else None
    except (OverflowError, ValueError):
        return None


def category_of(value):
    value = str(value).strip() if value is not None else ""
    return value if SAFE_CATEGORY.fullmatch(value) and not value.isdecimal() else None


def metric(label, value, definition, unit=None):
    return dict(label=label, value=value, definition=definition, unit=unit)


def bucket(label, records, total=None):
    return dict(label=label, records=records, total=total)


def profile(source, table, filters, fields, row_limit):
    dimension = selected_field(fields, "category", filters.dimension)
    measure = selected_field(fields, "measure", filters.measure)
    date_field = selected_field(fields, "date", filters.date_field)
    currency_field = next((field["name"] for field in fields if field["semantic"] == "currency"), None) if measure else None
    if (filters.category is not None and not dimension
            or (filters.start or filters.end) and not date_field
            or (filters.minimum is not None or filters.maximum is not None) and not measure):
        raise ApiError(422, "invalid_insight_filter", "Select a field before applying its filter")

    profile_columns = list(dict.fromkeys(name for name in (dimension, measure, date_field) if name))
    columns = list(dict.fromkeys([*profile_columns, *([currency_field] if currency_field else [])]))
    groups, periods = defaultdict(lambda: [0, 0, 0.0]), defaultdict(lambda: [0, 0, 0.0])
    scanned = matched = missing = measured = 0
    total = 0.0
    currencies = set()
    truncated = False
    deadline = monotonic() + 8
    if not columns:
        columns = (table.primary_key or list(table.columns))[:1]
    iterator = source.iter_batches(table.name, columns, table.primary_key or columns, min(500, row_limit + 1))
    try:
        for batch in iterator:
            for row in batch:
                if scanned >= row_limit:
                    truncated = True
                    break
                scanned += 1
                cat = category_of(row.get(dimension))
                day = day_of(row.get(date_field))
                value = numeric(row.get(measure))
                if filters.category is not None and cat != filters.category:
                    continue
                if filters.start and (day is None or day < filters.start):
                    continue
                if filters.end and (day is None or day > filters.end):
                    continue
                if filters.minimum is not None and (value is None or value < filters.minimum):
                    continue
                if filters.maximum is not None and (value is None or value > filters.maximum):
                    continue
                matched += 1
                missing += sum(row.get(column) is None or row.get(column) == "" for column in profile_columns)
                if value is not None:
                    measured += 1
                    total += value
                    if currency_field:
                        currency = row.get(currency_field)
                        currencies.add(currency if isinstance(currency, str) and re.fullmatch("[A-Z]{3}", currency) else None)
                for label, target in ((cat, groups), (period(day, filters.interval) if day else None, periods)):
                    if label is not None:
                        cell = target[label]
                        cell[0] += 1
                        if value is not None:
                            cell[1] += 1
                            cell[2] += value
            if truncated or monotonic() >= deadline:
                truncated = True
                break
    finally:
        close = getattr(iterator, "close", None)
        if close:
            close()

    # A sparse filtered cohort must not reveal individual measures.
    cells = matched * len(profile_columns)
    filtered = any(value is not None for value in (
        filters.category, filters.start, filters.end, filters.minimum, filters.maximum,
    ))
    metrics = [
        metric("Matching records", matched if not filtered or matched == 0 or matched >= MIN_GROUP else None,
               "Records matching the active filters within the profiled rows. Small filtered groups are withheld."),
        metric("Missing values", 100 * missing / cells if cells and matched >= MIN_GROUP else None,
               "Empty or null cells across the profiled fields for the matching records", "%"),
        metric("Data completeness", 100 * (cells - missing) / cells if cells and matched >= MIN_GROUP else None,
               "Populated cells across the profiled fields for the matching records", "%"),
    ]
    comparable = not currency_field or len(currencies) == 1 and None not in currencies
    currency_unit = next(iter(currencies)) if comparable and currency_field else None
    if measure:
        unit_definition = f" Uses {currency_unit}." if currency_unit else (
            " Uses the source unit." if not currency_field else " Totals require a single known currency."
        )
        metrics.extend([
            metric(f"Total {measure}", total if comparable and measured >= MIN_GROUP else None,
                   f"Sum of finite {measure} values in the matching records." + unit_definition, currency_unit),
            metric(f"Average {measure}", total / measured if comparable and measured >= MIN_GROUP else None,
                   f"Mean of finite {measure} values in the matching records." + unit_definition, currency_unit),
        ])

    def rows(items):
        return [bucket(label, records, amount if comparable and count >= MIN_GROUP else None)
                for label, (records, count, amount) in items if records >= MIN_GROUP]
    distribution = sorted(rows(groups.items()), key=lambda item: (-item["records"], item["label"]))[:20]
    trends = rows(sorted(periods.items()))[-180:]
    if len(trends) > 1:
        previous, latest = trends[-2:]
        change = (latest["records"] - previous["records"]) / previous["records"] * 100
        metrics.append(metric("Observed activity change", change,
                              f'Record count in {latest["label"]} versus {previous["label"]}. Periods may be partial.', "%"))
    return dict(scanned=scanned, truncated=truncated, metrics=metrics, dimension=dimension,
                measure=measure, date_field=date_field, distribution=distribution, trends=trends)


def quality_rows(report, table):
    if report is None:
        return []
    rows = []
    for name, stats in report["tables"].items():
        if table and name != table:
            continue
        for label, count, severity in [
            ("Duplicate primary keys", stats["duplicate_primary_keys"], "Block"),
            ("Duplicate entity groups", len(stats["duplicate_entities"]), "Warning"),
            ("Type errors", stats["type_errors"], "Quarantine"),
            ("Business rule failures", stats["rule_failures"], "Quarantine"),
            ("Missing values", sum(stats["null_counts"].values()), "Review"),
        ]:
            rows.append(dict(dataset=name, issue=label, count=count, severity=severity if count else "None"))
    for entry in report["referential_integrity"]:
        if not table or entry["table"] == table:
            rows.append(dict(dataset=entry["table"], issue="Orphan references",
                             count=entry["orphan_references"], severity="Quarantine" if entry["orphan_references"] else "None"))
    return rows[:300]


def graph_summary(session, filters):
    ctx = session.ctx
    if filters.ontology_id:
        graph = graphs.select_graph(session, filters.ontology_id, filters.build_id)
    elif ctx.is_done(15) and ctx.graph is not None:
        graph = graphs.select_graph(session)
    else:
        return None
    if graph.number_of_nodes() > limit("KG_INSIGHTS_GRAPH_NODES", 100000, 300000) or graph.number_of_edges() > limit(
            "KG_INSIGHTS_GRAPH_EDGES", 300000, 1000000):
        return None
    labels = Counter(str(props.get("label", "Entity")) for _, props in graph.nodes(data=True))
    if filters.entity_type and filters.entity_type not in labels:
        raise ApiError(422, "invalid_insight_entity", "Select an entity type available in this graph")
    selected = graph if not filters.entity_type else graph.subgraph(
        node for node, props in graph.nodes(data=True) if props.get("label", "Entity") == filters.entity_type)
    nodes, edges = selected.number_of_nodes(), selected.number_of_edges()
    relationships = Counter(str(props.get("type") or props.get("label") or key)
                            for _, _, key, props in selected.edges(keys=True, data=True))
    isolated = nx.number_of_isolates(selected)
    simple = nx.DiGraph()
    simple.add_nodes_from(selected)
    simple.add_edges_from((left, right) for left, right in selected.edges() if left != right)
    component_sizes = Counter(len(component) for component in nx.weakly_connected_components(simple))
    visible = nlargest(60, simple.nodes, key=simple.degree)
    aliases = {node: f"Entity {index}" for index, node in enumerate(visible, 1)}
    visible_graph = selected.subgraph(visible)
    visible_edges = list(islice(visible_graph.edges(keys=True, data=True), 160))
    topology = dict(nodes=[dict(id=alias, properties={"label": str(selected.nodes[node].get("label", "Entity"))})
                           for node, alias in aliases.items()],
                    edges=[dict(source=aliases[left], target=aliases[right], key=str(index),
                                properties={"type": str(props.get("type") or props.get("label") or key)})
                           for index, (left, right, key, props) in enumerate(visible_edges)],
                    total_nodes=nodes, total_edges=edges,
                    truncated=len(visible) < nodes or len(visible_edges) < edges)
    dependencies = Counter()
    for node, props in selected.nodes(data=True):
        dependencies[str(props.get("label", "Entity"))] += simple.out_degree(node)
    ontology = ctx.build_ontology
    mapped = {cls.name for cls in ontology.classes if cls.mapping} if ontology and not filters.ontology_id else set()
    coverage = 100 * len(mapped & labels.keys()) / len(mapped) if mapped and not filters.entity_type else None
    return dict(entity_types=sorted(labels)[:100],
                entities=[bucket(label, count) for label, count in labels.most_common(20)
                          if not filters.entity_type or label == filters.entity_type],
                relationships=[bucket(label, count) for label, count in relationships.most_common(20)],
                communities=[bucket(f"{size} {'entity' if size == 1 else 'entities'}", count)
                             for size, count in sorted(component_sizes.items(), reverse=True)[:20]],
                dependencies=[bucket(label, count) for label, count in dependencies.most_common(20)],
                most_connected=[bucket(aliases[node], simple.degree(node)) for node in visible[:10]],
                topology=topology,
                metrics=[
                    metric("Total entities", nodes, "Nodes in the selected graph view"),
                    metric("Total relationships", edges, "Edges in the selected graph view, including parallel edges"),
                    metric("Connected entities", nodes - isolated, "Entities with at least one incident relationship"),
                    metric("Isolated entities", isolated, "Entities with no incident relationships"),
                    metric("Connected components", component_sizes.total(),
                           "Groups connected by a path when directions are ignored"),
                    metric("Relationship density", nx.density(simple) * 100,
                           "Distinct directed links, excluding self-loops, as a share of possible links", "%"),
                    metric("Graph coverage", coverage, "Mapped ontology classes represented in the current graph", "%"),
                ])


def findings(result, graph, quality):
    output = []
    if result["distribution"]:
        group = result["distribution"][0]
        output.append(dict(title="Largest visible segment", explanation=f'{group["label"]} leads the displayed categories.',
                           metric=f'{group["records"]:,} matching records', target="distribution"))
    if len(result["trends"]) >= 2:
        previous, latest = result["trends"][-2:]
        output.append(dict(title="Recent observed activity",
                           explanation=f'{latest["label"]} compared with {previous["label"]}. Periods may be partial.',
                           metric=f'{latest["records"] - previous["records"]:+,} records', target="trends"))
    issues = [row for row in quality if row["count"]]
    if issues:
        row = max(issues, key=lambda issue: issue["count"])
        output.append(dict(title=row["issue"], explanation=f'The latest quality report flags {row["dataset"]}.',
                           metric=f'{row["count"]:,} occurrences', target="quality"))
    if graph and graph["relationships"]:
        leading = graph["relationships"][0]
        output.append(dict(title="Most common relationship type", explanation=leading["label"],
                           metric=f'{leading["records"]:,} relationships', target="network"))
    return output


def dashboard(session, filters):
    ctx = session.ctx
    row_limit = limit("KG_INSIGHTS_ROWS", 5000, 25000)
    try:
        catalog = ctx.catalog or (ctx.source.introspect_schema() if ctx.source is not None else None)
        tables = sorted(catalog.tables) if catalog else []
        if filters.table is not None and filters.table not in tables:
            raise ApiError(422, "invalid_insight_table", "Select a dataset available in this workspace")
        table = filters.table or next(iter(tables), None)
        fields = discover(ctx, catalog.tables[table]) if table else []
        result = dict(scanned=0, truncated=False, dimension=None, measure=None, date_field=None,
                      metrics=[], distribution=[], trends=[])
        if table and ctx.source is not None:
            result = profile(ctx.source, catalog.tables[table], filters, fields, row_limit)
        graph = graph_summary(session, filters)
    except ApiError:
        raise
    except Exception:
        raise ApiError(502, "insights_unavailable", "Could not read the selected source or graph. Check its connection and retry.") from None

    quality = quality_rows(ctx.dq_report, table)
    result["metrics"] = [
        metric("Total data sources", int(ctx.source is not None), "Active source connections in this workspace"),
        metric("Tables / collections", len(tables) if catalog else None, "Assets in the active source catalog"),
        metric("Total records", result["scanned"] if table and ctx.source is not None and not result["truncated"] else None,
               "Total records in the selected dataset when its complete profile fits the read limit"),
        *result["metrics"],
    ]
    source_name = ctx.source_info.get("name") or (ctx.source.name if ctx.source is not None else None)
    return dict(**result, refreshed_at=datetime.now(timezone.utc), source=source_name,
                table=table, tables=tables, fields=fields, row_limit=row_limit,
                quality=quality, graph=graph, findings=findings(result, graph, quality))
