import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Alert, Button, MenuItem, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { get } from "../../api/client";
import { Feedback, Panel, Report } from "../../shared/ui/WorkspaceUi";
import type { GraphSelection, JsonObject, Schema } from "../../types/common.types";
import GraphCanvas from "./GraphCanvas";

type Match = { id: string; label: string; identifier: string; display_name: string };
type SearchResult = { types: string[]; matches: Match[]; truncated: boolean };
type Definition = JsonObject & { name: string };
type Relationship = Definition & { source_class: string; target_class: string };
type Neighborhood = {
  root: { id: string; identifier: string; properties: JsonObject; incoming: number; outgoing: number };
  graph: Schema<"GraphView">;
  ontology?: { name: string; version: number; classes: Definition[]; relationships: Relationship[] } | null;
};
type Graph = Neighborhood["graph"];
type Expansion = { anchor: string; previous: Graph };
const edgeKey = (edge: JsonObject) => JSON.stringify([edge.source, edge.target, edge.key]);
const edgeKind = (edge: Graph["edges"][number]) => String(edge.properties.type ?? edge.properties.label ?? edge.key);

function mergeNeighborhoods(previous: Graph | undefined, current: Graph): Graph {
  if (!previous) return current;
  const nodes = new Map(previous.nodes.map((node) => [node.id, node]));
  const edges = new Map(previous.edges.map((edge) => [edgeKey(edge), edge]));
  let truncated = previous.truncated || current.truncated;
  for (const node of current.nodes) {
    if (nodes.size < 100 || nodes.has(node.id)) nodes.set(node.id, node);
    else truncated = true;
  }
  for (const edge of current.edges) {
    const key = edgeKey(edge);
    if (nodes.has(edge.source) && nodes.has(edge.target) && (edges.size < 300 || edges.has(key))) edges.set(key, edge);
    else truncated = true;
  }
  return { ...current, nodes: [...nodes.values()], edges: [...edges.values()], truncated };
}

type ExplorerProps = {
  path: string;
  selection?: GraphSelection;
  children?: ReactNode;
  fitKey?: number;
};

export default function EntityExplorer({ enabled = true, ...props }: ExplorerProps & { enabled?: boolean }) {
  return enabled ? <EntitySearchPanel {...props} /> : props.children;
}

function EntitySearchPanel({ path, selection, children, fitKey = 0 }: ExplorerProps) {
  const [label, setLabel] = useState("");
  const [value, setValue] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [lookup, setLookup] = useState<{ q: string; label: string }>();
  const [root, setRoot] = useState("");
  const [expanded, setExpanded] = useState<Expansion[]>([]);
  const [depth, setDepth] = useState(1);
  const [inspected, setInspected] = useState("");
  const [edge, setEdge] = useState<JsonObject | null>(null);
  const [fit, setFit] = useState(0);
  const [layout, setLayout] = useState("concentric");
  useEffect(() => {
    const timer = setTimeout(() => setSuggestion(value.trim()), 300);
    return () => clearTimeout(timer);
  }, [value]);

  const types = useQuery({
    queryKey: ["entity-types", path, selection],
    queryFn: ({ signal }) => get<SearchResult>(path + "/entities", selection, signal),
    retry: false,
  });
  const suggestions = useQuery({
    queryKey: ["entity-suggestions", path, selection, label, suggestion],
    queryFn: ({ signal }) => get<SearchResult>(path + "/entities", { ...selection, label, q: suggestion, prefix: true }, signal),
    enabled: suggestion.length >= 2 && suggestion === value.trim() && !lookup && !root,
    retry: false,
  });
  const matches = useQuery({
    queryKey: ["entity-lookup", path, selection, lookup],
    queryFn: ({ signal }) => get<SearchResult>(path + "/entities", { ...selection, ...lookup }, signal),
    enabled: !!lookup,
    retry: false,
  });
  const match = matches.data?.matches;
  const origin = root || (match?.length === 1 && !matches.data?.truncated ? match[0].id : "");
  const expansion = expanded.at(-1);
  const focus = expansion?.anchor || origin;
  const neighborhood = useQuery({
    queryKey: ["entity-neighborhood", path, selection, focus, depth],
    queryFn: ({ signal }) => get<Neighborhood>(path + "/entity-neighborhood", { ...selection, node_id: focus, hops: depth }, signal),
    enabled: !!focus,
    retry: false,
  });
  const result = neighborhood.data;
  const visible = useMemo(() => result ? mergeNeighborhoods(expansion?.previous, result.graph) : expansion?.previous,
    [expansion, result]);
  const selectNode = useCallback((node: string) => { setInspected(node); setEdge(null); }, []);
  const selectEdge = useCallback((item: JsonObject) => { setEdge(item); setInspected(""); }, []);
  const selectedNode = inspected || focus;
  const detail = useQuery({
    queryKey: ["entity-inspection", path, selection, selectedNode],
    queryFn: ({ signal }) => get<Neighborhood>(path + "/entity-neighborhood", { ...selection, node_id: selectedNode, hops: 0 }, signal),
    enabled: !!inspected && inspected !== focus && !edge,
    retry: false,
  });
  const inspectedNode = inspected && inspected !== focus ? detail.data?.root : result?.root;
  const entityClass = String(inspectedNode?.properties.label ?? "");
  const ontology = result?.ontology;
  const definition = ontology?.classes.find((item) => item.name === entityClass);
  const relationships = ontology?.relationships.filter((item) => item.source_class === entityClass || item.target_class === entityClass);
  const nodes = visible?.nodes ?? [];
  const edges = visible?.edges ?? [];
  const breakdown: Record<string, number> = Object.create(null);
  for (const item of edges) {
    const type = edgeKind(item);
    breakdown[type] = (breakdown[type] ?? 0) + 1;
  }
  const edgeDefinition = ontology?.relationships.find((item) =>
    item.name === edge?.title &&
    item.source_class === nodes.find((node) => node.id === edge.source)?.properties.label &&
    item.target_class === nodes.find((node) => node.id === edge.target)?.properties.label);
  const shownResults = (lookup ? matches.data : suggestions.data);
  function clearFocus() {
    setRoot(""); setExpanded([]); selectNode("");
  }
  return <>
    <Panel title="Entity search">
      <form className="toolbar" onSubmit={(event) => {
        event.preventDefault();
        if (!value.trim()) return;
        clearFocus(); setLookup({ q: value.trim(), label });
      }}>
        <TextField select label="Entity Type" value={label}
          onChange={(event) => { setLabel(event.target.value); setLookup(undefined); clearFocus(); }}>
          <MenuItem value="">All Entity Types</MenuItem>
          {types.data?.types.map((type) => <MenuItem value={type} key={type}>{type}</MenuItem>)}
        </TextField>
        <TextField label="Entity ID" value={value}
          slotProps={{ htmlInput: { maxLength: 300 } }}
          onChange={(event) => { setValue(event.target.value); setLookup(undefined); clearFocus(); }} />
        <TextField select label="Traversal Depth" value={depth} onChange={(event) => {
          setDepth(Number(event.target.value)); setExpanded([]); selectNode("");
        }}>
          {[1, 2, 3].map((hops) => <MenuItem value={hops} key={hops}>{hops} {hops === 1 ? "hop" : "hops"}</MenuItem>)}
        </TextField>
        <Button type="submit" variant="contained" disabled={!value.trim() || matches.isFetching}>Search by ID</Button>
        <Button onClick={() => { setValue(""); setSuggestion(""); setLabel(""); setDepth(1); setLookup(undefined); clearFocus(); }}>Reset exploration</Button>
      </form>
      <p className="muted mt-2">Identifiers are case-sensitive. Separate composite key parts with | in their mapped order.</p>
      <Feedback pending={types.isFetching || matches.isFetching} error={types.error ?? matches.error ?? suggestions.error} />
      {types.data?.truncated && <Alert severity="info">The entity type list reached its display limit. Search across all types to include unlisted types.</Alert>}
      {lookup && matches.isSuccess && match?.length === 0 && <Alert severity="info">No entity matches that identifier.</Alert>}
      {!focus && !!shownResults?.matches.length && <div className="toolbar" aria-label="Matching entities">
        {shownResults.matches.map((item) => <Button key={item.id} onClick={() => {
          setRoot(item.id); setExpanded([]); selectNode("");
        }}>{item.label} · {item.identifier}{item.display_name === item.id ? "" : ` · ${item.display_name}`}</Button>)}
      </div>}
      {shownResults?.truncated && !focus && <Alert severity="info">More matches exist. Choose an entity type or enter the full ID.</Alert>}
    </Panel>
    {focus ? <div className="section-gap">
      <Feedback pending={neighborhood.isFetching} error={neighborhood.error} />
      {visible && <>
        <Panel title="Entity neighborhood" action={<Button onClick={() => setFit((key) => key + 1)}>Fit neighborhood</Button>}>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-3">
            {Object.entries({ "Selected entity": origin, "Connected nodes": nodes.length - 1,
              Relationships: edges.length, "Connected entity types": new Set(nodes.filter((node) => node.id !== origin)
                .map((node) => node.properties.label)).size, "Traversal depth": depth }).map(([title, count]) =>
              <div key={title}><span className="muted">{title}</span><p><strong>{count}</strong></p></div>)}
          </div>
          <p className="muted">Counts describe the displayed neighborhood. Depth applies to each expansion.</p>
          {visible.truncated && <Alert severity="warning">Traversal reached its display limit. Try a smaller depth or collapse an expansion.</Alert>}
          {!edges.length && <Alert severity="info">This entity has no relationships in the displayed neighborhood.</Alert>}
          <div className="toolbar mb-3">
            <TextField select label="Neighborhood layout" value={layout} onChange={(event) => setLayout(event.target.value)}>
              {["cose", "breadthfirst", "circle", "grid", "concentric"].map((name) => <MenuItem key={name} value={name}>{name}</MenuItem>)}
            </TextField>
            <Button disabled={!inspected || inspected === focus || neighborhood.isFetching || expanded.length >= 10}
              onClick={() => {
              setExpanded((stack) => [...stack, { anchor: inspected, previous: visible }]); selectNode("");
            }}>Expand connected node</Button>
            <Button disabled={!expanded.length} onClick={() => {
              setExpanded((stack) => stack.slice(0, -1)); selectNode("");
            }}>Collapse expansion</Button>
          </div>
          <div className="graph-frame">
            <GraphCanvas graph={visible} layout={layout} onSelect={selectNode} onEdge={selectEdge} fitKey={fit + fitKey} focus={origin} />
          </div>
          <div className="toolbar mt-3">
            <TextField select label="Inspect entity" value={edge ? "" : selectedNode}
              onChange={(event) => selectNode(event.target.value)}>
              <MenuItem value="">Choose an entity</MenuItem>
              {nodes.map((node) => <MenuItem key={node.id} value={node.id}>{node.id}</MenuItem>)}
            </TextField>
            {!!edges.length && <TextField select label="Inspect relationship" value={edge ? edgeKey(edge) : ""}
              onChange={(event) => {
                const item = edges.find((candidate) => edgeKey(candidate) === event.target.value);
                if (item) selectEdge({ ...item, title: edgeKind(item) });
                else selectNode("");
              }}>
              <MenuItem value="">Choose a relationship</MenuItem>
              {edges.map((item) => <MenuItem key={edgeKey(item)} value={edgeKey(item)}>
                {item.source} → {item.target} · {edgeKind(item)}
              </MenuItem>)}
            </TextField>}
          </div>
          <Report value={breakdown} />
        </Panel>
        <Panel title={edge ? "Relationship details" : "Entity details"}>
          {edge ? <Report value={{ type: edge.title, source: edge.source, target: edge.target, direction: "Source → target",
            properties: edge.properties, ontology_definition: edgeDefinition }} /> : <>
            <Feedback pending={detail.isFetching} error={detail.error} />
            {inspectedNode && <Report value={{ entity_id: inspectedNode.identifier,
              entity_type: entityClass, display_name: inspectedNode.properties.display_name ?? inspectedNode.properties.name ??
                inspectedNode.properties.title ?? inspectedNode.id,
              incoming_relationships: inspectedNode.incoming, outgoing_relationships: inspectedNode.outgoing,
              properties: inspectedNode.properties }} />}
            <h3 className="mt-4">Ontology context</h3>
            {definition ? <Report value={{ ontology: ontology?.name, version: ontology?.version, ...definition,
              defined_relationships: relationships }} /> : <p className="muted">The selected graph has no saved ontology definition for this entity type.</p>}
            {definition && !definition.mapping && <p className="muted">No source identity mapping is recorded for this class.</p>}
          </>}
        </Panel>
      </>}
    </div> : children}
  </>;
}
