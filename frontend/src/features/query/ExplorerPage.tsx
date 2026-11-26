import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Button, TextField, MenuItem, Tabs, Tab, Alert } from "@mui/material";
import { Maximize2 } from "lucide-react";
import { graphsApi, ontologyApi, snapshotsApi } from "../../api/workflowApi";
import { sessionPath } from "../../api/client";
import { useData, useWorkspace } from "../../shared/hooks/useWorkspace";
import { useGraphStore } from "../../app/store";
import {
  DataTable,
  Feedback,
  PageHeader,
  Panel,
  Report,
} from "../../shared/ui/WorkspaceUi";
import type { JsonObject, GraphSelection, Schema } from "../../types/common.types";
import { colorForLabel } from "../../constants/stages.constants";
import GraphCanvas from "./GraphCanvas";
import GraphQuestions from "./GraphQuestions";
import EntityExplorer from "./EntityExplorer";
const relationshipType = (edge: Schema<"GraphView">["edges"][number]) =>
  String(edge.properties.type ?? edge.properties.label ?? edge.key);

export default function ExplorerPage() {
  const { id, done, session } = useWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();
  const { selected, layout, select, setLayout } = useGraphStore();
  const [snapshotPreference, setSnapshot] = useState<boolean>();
  const snapshot = snapshotPreference ?? (searchParams.get("recovered") === "1" ||
    (!done.includes(14) && Boolean(session.data?.snapshot)));
  const [ontology, setOntology] = useState("");
  const [build, setBuild] = useState("");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [label, setLabel] = useState("");
  const [focus, setFocus] = useState("");
  const [hops, setHops] = useState(1);
  const [limit, setLimit] = useState(150);
  const [offset, setOffset] = useState(0);
  const [fit, setFit] = useState(0);
  const [entitySearchRevision, setEntitySearchRevision] = useState(0);
  const [relationship, setRelationship] = useState("");
  const [evidence, setEvidence] = useState<{ scope: string; graph: Schema<"GraphView"> }>();
  const view = searchParams.get("view");
  const tab = view === "path" ? 1 : view === "metrics" ? 2 : 0;
  const [edge, setEdge] = useState<JsonObject | null>(null);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [maxHops, setMaxHops] = useState(20);
  const [pathInput, setPathInput] = useState<{
    source: string;
    target: string;
    max_hops: number;
  } | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);
  const draft = useData(
    ["ontology", "draft"],
    (signal) => ontologyApi.draft(id, signal),
    done.includes(5),
  );
  const recovery = session.data?.snapshot;
  const oid = ontology || (snapshot && recovery?.ontology_id) || draft.data?.ontology_id || "";
  const selection: GraphSelection = snapshot
    ? { ontology_id: oid, build_id: build || (oid === recovery?.ontology_id ? recovery?.build_id : undefined) }
    : {};
  const enabled = snapshot ? !!oid : done.includes(14);
  const questionScope = JSON.stringify([id, session.data?.source_version, selection]);
  const snapshots = useData(
    ["snapshots", oid],
    (signal) => snapshotsApi.list(id, oid, signal),
    snapshot && !!oid,
  );
  const graph = useData(
    ["graph", "data", selection, label, focus, hops, limit],
    (signal) =>
      graphsApi.data(
        id,
        {
          ...selection,
          labels: label ? [label] : undefined,
          focus: focus || undefined,
          hops,
          limit,
          edge_limit: 1000,
        },
        signal,
      ),
    enabled,
  );
  const nodes = useData(
    ["graph", "nodes", selection, debounced, label, offset],
    (signal) =>
      graphsApi.nodes(
        id,
        {
          ...selection,
          search: debounced,
          label: label || undefined,
          offset,
          limit: 25,
        },
        signal,
      ),
    enabled,
  );
  const detail = useData(
    ["graph", "node", selection, selected],
    (signal) =>
      graphsApi.node(id, { ...selection, node_id: selected! }, signal),
    enabled && !!selected,
  );
  const metrics = useData(
    ["graph", "metrics", selection],
    (signal) => graphsApi.metrics(id, selection, signal),
    enabled,
  );
  const path = useData(
    ["graph", "path", selection, pathInput],
    (signal) => graphsApi.path(id, { ...selection, ...pathInput! }, signal),
    enabled && !!pathInput,
  );
  const evidenceGraph = evidence?.scope === questionScope ? evidence.graph : undefined;
  const displayed = evidenceGraph ?? graph.data;
  const types = useMemo(() => [...new Set((displayed?.edges ?? []).map(relationshipType))].sort(), [displayed]);
  const visibleGraph = useMemo(() => displayed && relationship && types.includes(relationship)
    ? { ...displayed, edges: displayed.edges.filter((edge) => relationshipType(edge) === relationship) }
    : displayed, [displayed, relationship, types]);
  const highlightedPath = useMemo(() =>
    tab === 1 && Array.isArray(path.data?.nodes) ? path.data.nodes.map(String) : undefined, [tab, path.data]);
  const labels = Array.from(
    new Set([
      ...(draft.data?.classes?.map((c) => c.name) ?? []),
      ...(graph.data?.nodes.map((n) =>
        String(n.properties.label ?? "Entity"),
      ) ?? []),
    ]),
  );
  const onNode = useCallback(
    (node: string) => {
      select(node);
      setEdge(null);
    },
    [select],
  );
  const onEdge = useCallback(
    (e: JsonObject) => {
      setEdge(e);
      select(null);
    },
    [select],
  );
  function resetSelection() {
    select(null);
    setEdge(null);
    setFocus("");
    setOffset(0);
    setPathInput(null);
  }
  return (
    <>
      <PageHeader
        eyebrow="GRAPH EXPLORATION"
        title="Explore your knowledge graph"
        description="Search entities, inspect relationships, and trace connections in a bounded view of the current graph or a saved snapshot."
        action={
          <Button
            variant="outlined"
            onClick={() => setFit(fit + 1)}
            startIcon={<Maximize2 size={15} />}
          >
            Fit graph
          </Button>
        }
      />
      <Panel title="Graph source and filters">
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <TextField
            select
            label="Graph source"
            value={snapshot ? "snapshot" : "memory"}
            onChange={(e) => {
              setSnapshot(e.target.value === "snapshot");
              resetSelection();
            }}
          >
            <MenuItem value="memory">Current session graph</MenuItem>
            <MenuItem value="snapshot">Saved snapshot</MenuItem>
          </TextField>
          {snapshot && (
            <>
              <TextField
                label="Ontology ID"
                value={oid}
                onChange={(e) => {
                  setOntology(e.target.value);
                  setBuild("");
                  resetSelection();
                }}
              />
              <TextField
                select
                label="Snapshot"
                value={snapshots.data?.some(s=>String(s.build_id)===build)?build:""}
                onChange={(e) => {
                  setBuild(e.target.value);
                  resetSelection();
                }}
              >
                <MenuItem value="">CURRENT</MenuItem>
                {snapshots.data?.map((s) => (
                  <MenuItem key={String(s.build_id)} value={String(s.build_id)}>
                    {String(s.build_id)}
                  </MenuItem>
                ))}
              </TextField>
            </>
          )}
          <TextField
            select
            label="Entity label"
            value={label}
            onChange={(e) => {
              setLabel(e.target.value);
              setOffset(0);
            }}
          >
            <MenuItem value="">All labels</MenuItem>
            {labels.map((l) => (
              <MenuItem value={l} key={l}>
                {l}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Layout"
            value={layout}
            onChange={(e) => setLayout(e.target.value)}
          >
            {[
              ["cose", "Force-directed"],
              ["circle", "Circle"],
              ["grid", "Grid"],
              ["label-grid", "Grid grouped by label"],
              ["breadthfirst", "Hierarchy"],
            ].map(([v, l]) => (
              <MenuItem key={v} value={v}>
                {l}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Node limit"
            type="number"
            value={limit}
            onChange={(e) =>
              setLimit(Math.max(1, Math.min(500, Number(e.target.value) || 1)))
            }
            slotProps={{ htmlInput: { min: 1, max: 500 } }}
          />
        </div>
        <Feedback error={snapshots.error} />
      </Panel>
      <GraphQuestions key={questionScope} id={id} selection={selection} scope={questionScope}
        enabled={enabled} showGraph={(result) => {
          setEvidence({ scope: questionScope, graph: result });
          setRelationship("");
          setEntitySearchRevision((revision) => revision + 1);
        }} />
      {!enabled && (
        <Alert severity="info" className="mt-5">
          Complete graph construction or choose a saved snapshot.
        </Alert>
      )}
      <EntityExplorer key={questionScope + "/" + entitySearchRevision}
        enabled={enabled && tab === 0 && !!id} path={id ? sessionPath(id, "/graphs") : ""} selection={selection} fitKey={fit}>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_330px] gap-5 mt-5">
        <Panel
          title="Graph workspace"
          action={
            <span className="muted">
              {visibleGraph?.nodes.length ?? 0} visible /{" "}
              {visibleGraph?.total_nodes ?? 0} total nodes
            </span>
          }
        >
          <Feedback
            pending={graph.isFetching}
            error={graph.error}
            onRetry={() => void graph.refetch()}
          />
          <div className="graph-frame">
            {visibleGraph && (
              <GraphCanvas
                graph={visibleGraph}
                layout={layout}
                onSelect={onNode}
                onEdge={onEdge}
                fitKey={fit}
                path={highlightedPath}
              />
            )}
          </div>
          <div className="toolbar mt-4">
            {types.length > 0 && <TextField select size="small" label="Relationship type"
              value={types.includes(relationship) ? relationship : ""}
              onChange={(event) => setRelationship(event.target.value)}>
              <MenuItem value="">All visible types</MenuItem>
              {types.map((type) => <MenuItem key={type} value={type}>{type}</MenuItem>)}
            </TextField>}
            {evidenceGraph && <Button onClick={() => { setEvidence(undefined); setRelationship(""); }}>Clear query evidence</Button>}
            <Button onClick={() => {
              resetSelection();
              setEvidence(undefined);
              setLabel("");
              setRelationship("");
              setSearch("");
              setHops(1);
              setLimit(150);
              setLayout("cose");
              setFit((value) => value + 1);
            }}>Reset graph filters</Button>
            {labels.map((l) => (
              <span className="text-[11px] flex items-center gap-1.5" key={l}>
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ background: colorForLabel(l) }}
                />
                {l}
              </span>
            ))}
          </div>
          {visibleGraph?.truncated && (
            <p className="muted mt-3">
              This is a bounded graph view. Use filters or neighborhood
              exploration to inspect other entities.
            </p>
          )}
        </Panel>
        <Panel title="Property inspector">
          <Feedback pending={detail.isFetching} error={detail.error} />
          {edge ? (
            <Report value={edge} />
          ) : selected ? (
            <>
              <Report value={detail.data} />
              <Button
                className="mt-4"
                variant="outlined"
                onClick={() => {
                  if (focus === selected) setHops(Math.min(3, hops + 1));
                  else setFocus(selected);
                }}
                disabled={focus === selected && hops === 3}
              >
                Explore neighborhood
              </Button>
              <Button onClick={() => setSource(selected)}>
                Use as path source
              </Button>
              <Button onClick={() => setTarget(selected)}>
                Use as path target
              </Button>
            </>
          ) : (
            <p className="muted">
              Select a node or relationship, or inspect an entity from the table
              below.
            </p>
          )}
          <div className="form-stack mt-6">
            <TextField
              label="Neighborhood focus node"
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
            />
            <TextField
              select
              label="Neighborhood hops"
              value={hops}
              onChange={(e) => setHops(Number(e.target.value))}
            >
              {[1, 2, 3].map((n) => (
                <MenuItem value={n} key={n}>
                  {n}
                </MenuItem>
              ))}
            </TextField>
            {focus && (
              <div className="toolbar">
                <Button disabled={hops === 1} onClick={() => setHops(hops - 1)}>Collapse one hop</Button>
                <Button onClick={() => setFocus("")}>Clear neighborhood</Button>
              </div>
            )}
          </div>
        </Panel>
      </div>
      <div className="section-gap">
        <Panel title="Graph analysis">
          <Tabs
            value={tab}
            onChange={(_, v: number) => {
              const next = new URLSearchParams(searchParams);
              if (v === 1) next.set("view", "path");
              else if (v === 2) next.set("view", "metrics");
              else next.delete("view");
              setSearchParams(next, { replace: true });
            }}
            className="mb-5"
          >
            <Tab label="Entities" />
            <Tab label="Path analysis" />
            <Tab label="Metrics" />
          </Tabs>
          {tab === 0 && (
            <>
              <TextField
                label="Search node IDs or names"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setOffset(0);
                }}
              />
              <Feedback error={nodes.error} />
              <div className="mt-4">
                <DataTable rows={nodes.data?.items ?? []} />
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                {nodes.data?.items.map((n) => (
                  <Button
                    key={String(n.id)}
                    size="small"
                    onClick={() => onNode(String(n.id))}
                  >
                    Inspect {String(n.id)}
                  </Button>
                ))}
              </div>
              <div className="toolbar mt-3">
                <Button
                  disabled={!offset}
                  onClick={() => setOffset(Math.max(0, offset - 25))}
                >
                  Previous
                </Button>
                <span className="muted">
                  {offset}–{offset + (nodes.data?.items.length ?? 0)} of{" "}
                  {nodes.data?.total ?? 0}
                </span>
                <Button
                  disabled={offset + 25 >= (nodes.data?.total ?? 0)}
                  onClick={() => setOffset(offset + 25)}
                >
                  Next
                </Button>
              </div>
            </>
          )}
          {tab === 1 && (
            <div className="form-stack">
              <p className="muted">
                Pathfinding ignores relationship direction. A path may include
                entities outside the visible canvas.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <TextField
                  label="Source node ID"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                />
                <TextField
                  label="Target node ID"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                />
                <TextField
                  label="Maximum hops"
                  type="number"
                  value={maxHops}
                  onChange={(e) => setMaxHops(Number(e.target.value))}
                  slotProps={{ htmlInput: { min: 1, max: 100 } }}
                />
              </div>
              <Button
                variant="outlined"
                disabled={
                  !source ||
                  !target ||
                  !Number.isInteger(maxHops) ||
                  maxHops < 1 ||
                  maxHops > 100
                }
                onClick={() =>
                  setPathInput({ source, target, max_hops: maxHops })
                }
              >
                Find connection
              </Button>
              <Feedback pending={path.isFetching} error={path.error} />
              <Report value={path.data} />
            </div>
          )}
          {tab === 2 && (
            <>
              <Feedback pending={metrics.isFetching} error={metrics.error} />
              <Report value={metrics.data} />
            </>
          )}
        </Panel>
      </div>
      </EntityExplorer>
    </>
  );
}
