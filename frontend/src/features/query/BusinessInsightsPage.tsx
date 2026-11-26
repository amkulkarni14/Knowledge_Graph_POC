import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, MenuItem, Skeleton, TextField } from "@mui/material";
import { Link } from "react-router-dom";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { get, sessionPath } from "../../api/client";
import { sessionsApi } from "../../api/sessionsApi";
import { snapshotsApi } from "../../api/workflowApi";
import { useAuthStore } from "../../app/authStore";
import { useGraphStore, useSessionStore } from "../../app/store";
import { Feedback, PageHeader, Panel } from "../../shared/ui/WorkspaceUi";
import { useSession } from "../../shared/hooks/useWorkspace";
import type { JsonObject, Schema } from "../../types/common.types";
import { AggregateTable, Bars, CategoryDonut, exportInsights, MetricCards, PerformanceBars, TrendChart } from "./InsightsCharts";

const GraphCanvas = lazy(() => import("./GraphCanvas"));
const EMPTY = "Not enough data is available to generate this insight.";
type Dashboard = Schema<"InsightsResponse">;
type Filters = {
  table?: string;
  dimension?: string;
  category?: string;
  measure?: string;
  date_field?: string;
  start?: string;
  end?: string;
  minimum?: string;
  maximum?: string;
  interval?: string;
  entity_type?: string;
  build_id?: string;
};
const DEFAULT_FILTERS: Filters = {};
const useInsightsFilters = create<{
  workspaces: Record<string, Filters>;
  write: (key: string, filters: Filters) => void;
}>()(persist((set) => ({
  workspaces: {},
  write: (key, filters) => set((state) => ({
    workspaces: Object.fromEntries(
      [...Object.entries(state.workspaces).filter(([stored]) => key !== stored), [key, filters]].slice(-40),
    ),
  })),
}), { name: "kg.business-insights.filters" }));

type Option = { value: string; label: string };
function Select({ label, value, options, onChange }: {
  label: string;
  value?: string | null;
  options: Option[];
  onChange: (value: string) => void;
}) {
  return (
    <TextField select size="small" fullWidth label={label}
      value={options.some((option) => option.value === value) ? value : ""}
      onChange={(event) => onChange(event.target.value)}>
      {options.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
    </TextField>
  );
}
const options = (values: string[]) => values.map((value) => ({ value, label: value }));
const anyOption = (label: string) => ({ value: "", label });

export default function BusinessInsightsPage() {
  const id = useSessionStore((state) => state.id);
  const username = useAuthStore((state) => state.user?.username);
  const session = useSession();
  const workspaces = useQuery({
    queryKey: ["sessions", "insights"],
    queryFn: ({ signal }) => sessionsApi.list(signal),
    staleTime: 10000,
  });
  const version = session.data?.source_version ?? 0;
  const storageKey = JSON.stringify([username, id, version]);
  const filters = useInsightsFilters((state) => state.workspaces[storageKey] ?? DEFAULT_FILTERS);
  const write = useInsightsFilters((state) => state.write);
  const [delayed, setDelayed] = useState({ key: storageKey, filters });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDelayed({ key: storageKey, filters }), 300);
    return () => window.clearTimeout(timeout);
  }, [storageKey, filters]);
  const ontologyId = session.data?.summary?.ontology?.id;
  const snapshots = useQuery({
    queryKey: ["workspace", id, "snapshots", ontologyId],
    queryFn: ({ signal }) => snapshotsApi.list(id!, ontologyId!, signal),
    enabled: !!id && !!ontologyId,
  });
  const selectedFilters = delayed.key === storageKey ? delayed.filters : filters;
  const params = {
    ...Object.fromEntries(Object.entries(selectedFilters).filter(([, value]) => value !== "" && value != null)),
    ...(selectedFilters.build_id ? { ontology_id: ontologyId } : {}),
  };
  const [node, setNode] = useState("");
  const [edge, setEdge] = useState("");
  const selectNode = useCallback((next: string) => {
    setNode(next);
    setEdge("");
  }, []);
  const selectEdge = useCallback((next: JsonObject) => {
    setNode("");
    setEdge(String(next.source) + " → " + String(next.target) + " · " + String(next.title));
  }, []);
  const report = useQuery({
    queryKey: ["workspace", id, "business-insights", version, session.data?.completed_stages, params, revision],
    queryFn: ({ signal }) => get<Dashboard>(
      sessionPath(id!, "/insights"), { ...params, refresh: revision > 0 }, signal,
    ),
    enabled: !!id && !!session.data && (!selectedFilters.build_id || !!ontologyId),
    staleTime: 60000,
    retry: false,
    placeholderData: (previous, query) =>
      query?.queryKey[1] === id && query.queryKey[3] === version ? previous : undefined,
  });
  const data = report.isPlaceholderData ? undefined : report.data;
  const ranked = data?.distribution.filter((item) => item.total != null)
    .sort((a, b) => (b.total ?? 0) - (a.total ?? 0)) ?? [];
  const update = (change: Filters) => write(storageKey, { ...filters, ...change });
  const isSelected = delayed.key === storageKey && selectedFilters === filters;
  const controls = report.data;
  const currentNodes = data?.graph?.topology.nodes ?? [];
  const currentEdges = data?.graph?.topology.edges ?? [];
  const downstream = [...new Set(currentEdges.filter((item) => item.source === node).map((item) => item.target))];
  const snapshotsOptions = (snapshots.data ?? []).map((snapshot) => String(snapshot.build_id));
  const activeFilters = Object.entries(filters)
    .filter(([, value]) => value != null && value !== "")
    .map(([key, value]) => key.replaceAll("_", " ") + ": " + value);
  const switchWorkspace = (next: string) => {
    useGraphStore.getState().reset();
    useSessionStore.getState().setSession(next || null);
    setNode("");
    setEdge("");
  };
  const changeTable = (table: string) => write(storageKey, { table, build_id: filters.build_id, entity_type: filters.entity_type });
  const fieldList = (role: string) =>
    options(controls?.fields.filter((field) => field.role === role).map((field) => field.name) ?? []);

  return (
    <div className="business-insights grid gap-5">
      <PageHeader title="Business Insights" eyebrow="Graph Intelligence"
        description="Explore key business metrics, trends, relationships, and actionable insights generated from your connected enterprise data and knowledge graph." />
      <div className="insights-toolbar panel grid gap-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Select label="Workspace" value={id}
            options={[anyOption("Select a workspace"), ...(workspaces.data ?? []).map((item) => ({ value: item.id, label: item.name }))]}
            onChange={switchWorkspace} />
          {controls?.source && <Select label="Data source" value={controls.source}
            options={options([controls.source])} onChange={() => undefined} />}
          {snapshotsOptions.length > 0 && <Select label="Graph or snapshot" value={filters.build_id}
            options={[anyOption("Current workspace graph"), ...options(snapshotsOptions)]}
            onChange={(build_id) => { update({ build_id, entity_type: undefined }); setNode(""); setEdge(""); }} />}
        </div>
        <Feedback error={workspaces.error || session.error || snapshots.error} />
        {id && <div className="flex flex-wrap items-center gap-3">
          <Button variant="outlined" disabled={report.isFetching}
            onClick={() => setRevision((value) => value + 1)}>Refresh insights</Button>
          <Button disabled={!data || !isSelected} onClick={() => {
            if (data) exportInsights(data, session.data?.name ?? "", filters);
          }}>Export aggregated CSV</Button>
          <Button disabled={!data || !isSelected} onClick={() => window.print()}>Print / Save PDF</Button>
        </div>}
      </div>
      {controls && (controls.tables.length > 0 || controls.graph) && (
        <Panel title="Filters" action={<Button onClick={() => write(storageKey, {})}>Reset filters</Button>}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 insights-filter-fields">
            {controls.tables.length > 0 && <Select label="Dataset" value={filters.table ?? controls.table}
              options={options(controls.tables)} onChange={changeTable} />}
            {fieldList("category").length > 0 && <Select label="Category field" value={filters.dimension ?? controls.dimension}
              options={fieldList("category")} onChange={(dimension) => update({ dimension, category: undefined })} />}
            {controls.dimension && <Select label="Category" value={filters.category}
              options={[anyOption("All categories"), ...options([...new Set([...controls.distribution.map((row) => row.label), ...(filters.category ? [filters.category] : [])])])]}
              onChange={(category) => update({ category })} />}
            {fieldList("measure").length > 0 && <Select label="Measure" value={filters.measure ?? controls.measure}
              options={fieldList("measure")} onChange={(measure) => update({ measure, minimum: undefined, maximum: undefined })} />}
            {fieldList("date").length > 0 && <Select label="Date field" value={filters.date_field ?? controls.date_field}
              options={fieldList("date")} onChange={(date_field) => update({ date_field, start: undefined, end: undefined })} />}
            {controls.date_field && <>
              <Select label="Time interval" value={filters.interval ?? "month"} options={[
                { value: "day", label: "Daily" }, { value: "week", label: "Weekly" }, { value: "month", label: "Monthly" },
                { value: "quarter", label: "Quarterly" }, { value: "year", label: "Yearly" },
              ]} onChange={(interval) => update({ interval })} />
              {(["start", "end"] as const).map((key) => <TextField key={key}
                label={key === "start" ? "From date" : "To date"} type="date" size="small"
                slotProps={{ inputLabel: { shrink: true } }} value={filters[key] ?? ""}
                onChange={(event) => update({ [key]: event.target.value })} />)}
            </>}
            {controls.measure && (["minimum", "maximum"] as const).map((key) => <TextField key={key}
              label={key === "minimum" ? "Minimum value" : "Maximum value"} type="number" size="small"
              value={filters[key] ?? ""} onChange={(event) => update({ [key]: event.target.value })} />)}
            {controls.graph && <Select label="Entity type" value={filters.entity_type}
              options={[anyOption("All entity types"), ...options(controls.graph.entity_types)]}
              onChange={(entity_type) => { update({ entity_type }); setNode(""); setEdge(""); }} />}
          </div>
          <p className="mt-3 muted break-words">{activeFilters.length ? activeFilters.join(" · ") : "No filters applied."}</p>
        </Panel>
      )}
      {!id ? <Alert severity="info">Select a workspace to explore business insights.</Alert> : null}
      {report.isFetching && <Skeleton aria-label="Loading insights" variant="rounded" height={125} />}
      {report.error && <div>
        <Feedback error={report.error} />
        <Button onClick={() => void report.refetch()}>Retry insights</Button>
        <Button onClick={() => write(storageKey, {})}>Reset filters</Button>
      </div>}
      {data && isSelected && <>
        <p className="muted">
          Last refreshed {new Date(data.refreshed_at).toLocaleString()}
          {data.table && (" · " + data.table + " · " + data.scanned.toLocaleString() + " records profiled")}
        </p>
        <p className="hidden print:block">{[session.data?.name, data.source, filters.build_id].filter(Boolean).join(" · ")}</p>
        {data.truncated && <Alert severity="info">
          These aggregates use a bounded profile of the selected dataset. Filters apply within the profiled rows.
        </Alert>}
        {!data.source && <Alert severity="info" action={<Button component={Link} to="/sources">Data Sources</Button>}>
          Connect a data source to start generating insights.
        </Alert>}
        <MetricCards metrics={[...data.metrics, ...(data.graph?.metrics ?? [])]} />
        {data.source && <div className="grid gap-5 xl:grid-cols-2">
          <div id="distribution">
            <Panel title="Category distribution">
              {data.distribution.length ? <>
                {data.distribution.length >= 2 && data.distribution.length <= 6 &&
                  <CategoryDonut rows={data.distribution} />}
                <Bars rows={data.distribution} active={filters.category}
                  onSelect={(category) => update({ category: filters.category === category ? "" : category })} />
                <AggregateTable rows={data.distribution} />
              </> : <p className="muted">{EMPTY}</p>}
            </Panel>
          </div>
          <div id="trends">
            <Panel title="Business trends">
              {data.trends.length ? <TrendChart rows={data.trends} measure={data.measure}
                context={[data.table, filters.interval ?? "month", data.refreshed_at].join(" · ")} />
                : <p className="muted">{EMPTY}</p>}
            </Panel>
          </div>
          {ranked.length > 0 && <Panel title="Performance comparison">
            <p className="muted mb-3">Visible categories ranked by total {data.measure}.</p>
            <PerformanceBars rows={ranked.slice(0, 10)} />
            <AggregateTable rows={ranked} />
          </Panel>}
          <div id="quality">
            <Panel title="Data quality insights">
              {data.quality.length ? <>
                <p className="muted mb-3">Latest pipeline quality report for the selected dataset, independent of row filters.</p>
                <AggregateTable rows={data.quality} />
              </> : <p className="muted">Run Data Quality to see pipeline findings for this dataset.</p>}
            </Panel>
          </div>
        </div>}
        <div id="network" className="grid gap-5">
          <Panel title="Knowledge graph intelligence">
            {data.graph ? <div className="grid gap-5 md:grid-cols-2">
              <div><h3>Entity types</h3><Bars rows={data.graph.entities} active={filters.entity_type}
                onSelect={(entity_type) => { update({ entity_type: filters.entity_type === entity_type ? "" : entity_type }); setNode(""); setEdge(""); }} /></div>
              <div><h3>Relationship types</h3><Bars rows={data.graph.relationships} /></div>
            </div> : <p className="muted">A validated graph or available snapshot is required. Graph insights are limited to graphs within the configured size bounds.</p>}
          </Panel>
          {data.graph && <>
            <Panel title="Relationship and dependency insights">
              <p className="muted mb-3">Distinct outgoing links by entity type in the selected graph view.</p>
              <AggregateTable rows={data.graph.dependencies} />
              <h3 className="mt-4">Highly connected entities</h3>
              <p className="muted mb-3">Incoming and outgoing links per masked entity.</p>
              <Bars rows={data.graph.most_connected}
                onSelect={(next) => { setNode(next); setEdge(""); document.getElementById("network-preview")?.scrollIntoView(); }} />
            </Panel>
            <Panel title="Connected groups">
              <p className="muted mb-3">Weakly connected components grouped by size. Relationship directions are ignored for this calculation.</p>
              <Bars rows={data.graph.communities} />
            </Panel>
            <div id="network-preview"><Panel title="Network preview" action={<Button component={Link} to="/explorer?view=path">Path Analysis</Button>}>
              <p className="muted mb-3">Entity IDs are masked. Node and relationship inspection is limited to the preview.</p>
              <div className="graph-frame insights-network">
                <Suspense fallback={<Skeleton variant="rounded" height={300} />}>
                  <GraphCanvas graph={data.graph.topology} layout="cose" fitKey={0}
                    onSelect={selectNode} onEdge={selectEdge} />
                </Suspense>
              </div>
              <div className="mt-3 max-w-sm">
                <Select label="Inspect preview entity" value={node}
                  options={[anyOption("Select an entity"), ...options(currentNodes.map((item) => item.id))]}
                  onChange={selectNode} />
              </div>
              {currentNodes.some((item) => item.id === node) && <div className="mt-3">
                <p>{node} · {String(currentNodes.find((item) => item.id === node)?.properties.label)}</p>
                <p className="muted">Downstream in this preview {downstream.length ? downstream.join(", ") : "None"}</p>
              </div>}
              {edge && <p className="mt-3">{edge}</p>}
            </Panel></div>
          </>}
        </div>
        <Panel title="Key Business Insights">
          {data.findings.length ? <div className="grid gap-3 md:grid-cols-2">
            {data.findings.map((finding) => <article key={finding.target} className="rounded border border-slate-200 p-4">
              <h3>{finding.title}</h3><p className="muted">{finding.explanation}</p>
              <strong>{finding.metric}</strong>
              <div><Button size="small" href={"#" + finding.target}>View details</Button></div>
            </article>)}
          </div> : <p className="muted">{EMPTY}</p>}
        </Panel>
      </>}
    </div>
  );
}
