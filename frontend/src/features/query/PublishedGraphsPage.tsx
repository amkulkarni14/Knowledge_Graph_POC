import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, MenuItem, TextField } from "@mui/material";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError, get, send, sessionPath } from "../../api/client";
import EntityExplorer from "./EntityExplorer";
import { publishedGraphViews } from "../../constants/publishedGraphViews";
import { useSessionStore } from "../../app/store";
import {
  DataTable,
  Feedback,
  PageHeader,
  Panel,
  Report,
} from "../../shared/ui/WorkspaceUi";
import type { Job, JsonObject, Schema } from "../../types/common.types";
import { saveBlob } from "../build/StoragePage";
import GraphCanvas from "./GraphCanvas";
import { GraphmlImport, IntelligenceTools } from "./GraphIntelligenceTools";

type GraphView = Schema<"GraphView">;
type Project = {
  project_id: string;
  name: string;
  current_build_id: string | null;
};
type Version = JsonObject & { build_id: string; status: string };
type VersionList = {
  current: string | null;
  can_manage: boolean;
  versions: Version[];
};
type QueryResult = {
  template: string;
  rows: JsonObject[];
  duration_ms: number;
};
type WorkspaceSettings = {
  template: string;
  search: string;
  label: string;
  relationship: string;
  focus: string;
  hops: number;
  layout: string;
  cypher?: string;
  property?: string;
  value?: string;
};
type WorkspaceItem = {
  name: string;
  settings: WorkspaceSettings;
  updated_at: string;
};
type Tool =
  "versions" | "explorer" | "query" | "analytics" | "schema" | "operations" | "intelligence" | "graphml";

const titles: Record<Tool, string> = {
  versions: "Graph Versions",
  explorer: "Published Graph Explorer",
  query: "Query Workbench",
  analytics: "Graph Analytics",
  schema: "Graph Schema",
  operations: "Graph Operations",
  intelligence: "Graph Intelligence",
  graphml: "GraphML Import",
};

function downloadJson(value: unknown, name: string) {
  saveBlob(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    name,
  );
}

function resultGraph(result?: QueryResult): GraphView | undefined {
  if (!result) return undefined;
  const nodes = new Map<string, GraphView["nodes"][number]>();
  const edges = new Map<string, GraphView["edges"][number]>();
  const values = result.rows.flatMap((row) =>
    result.template === "cypher"
      ? Object.values(row).filter(
          (value): value is JsonObject =>
            !!value && typeof value === "object" && !Array.isArray(value),
        )
      : [row],
  );
  for (const row of values) {
    if (
      typeof row.id === "string" &&
      row.properties &&
      !Array.isArray(row.properties)
    ) {
      nodes.set(row.id, {
        id: row.id,
        properties: row.properties as JsonObject,
      });
    } else if (typeof row.key === "string" && row.source && row.target) {
      const source = row.source as GraphView["nodes"][number];
      const target = row.target as GraphView["nodes"][number];
      nodes.set(source.id, source);
      nodes.set(target.id, target);
      edges.set(JSON.stringify([source.id, target.id, row.key]), {
        source: source.id,
        target: target.id,
        key: row.key,
        properties: row.properties as JsonObject,
      });
    }
  }
  return {
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    truncated: false,
    total_nodes: nodes.size,
    total_edges: edges.size,
  };
}

export default function PublishedGraphsPage() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("view");
  const tool: Tool =
    requested && Object.hasOwn(titles, requested)
      ? (requested as Tool)
      : "explorer";
  const demoView = publishedGraphViews.some(({ view }) => view === tool);
  const client = useQueryClient();
  const session = useSessionStore((state) => state.id);
  const projects = useQuery({
    queryKey: ["published-projects"],
    queryFn: ({ signal }) =>
      get<Project[]>("/graph-projects", undefined, signal),
    retry: false,
  });
  const project = params.get("project") || projects.data?.[0]?.project_id || "";
  const base = `/graph-projects/${encodeURIComponent(project)}`;
  const versions = useQuery({
    queryKey: ["published-versions", project],
    queryFn: ({ signal }) =>
      get<VersionList>(base + "/versions", undefined, signal),
    enabled: !!project,
  });
  const version = params.get("version") || versions.data?.current || "";
  const versionPath = base + "/versions/" + encodeURIComponent(version);
  const useSessionGraph = !!session && (!version || params.get("source") === "session");
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === "project") {
      next.delete("version");
      next.delete("node");
    }
    if (key === "version") next.delete("node");
    setParams(next);
  };
  const restore = useMutation({
    mutationFn: () => send("PUT", versionPath + "/current"),
    onSuccess: async () => {
      await client.invalidateQueries({
        queryKey: ["published-versions", project],
      });
    },
  });
  return (
    <>
      <PageHeader
        title={titles[tool]}
        description={demoView ? "Explore and query graph versions published to Neo4j." : "Inspect and manage graph versions published to Neo4j."}
      />
      <Panel title="Published graph workspace">
        <div className="toolbar">
          <TextField
            select
            label="Workspace view"
            value={demoView ? tool : ""}
            onChange={(e) => set("view", e.target.value)}
            slotProps={{ select: { displayEmpty: true, renderValue: (value) => value ? titles[value as Tool] : "Choose a published view" }, inputLabel: { shrink: true } }}
          >
            {publishedGraphViews.map(({ view, label }) => (
              <MenuItem key={view} value={view}>
                {label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Project"
            value={
              projects.data?.some((item) => item.project_id === project)
                ? project
                : ""
            }
            onChange={(e) => set("project", e.target.value)}
          >
            <MenuItem value="">Choose project</MenuItem>
            {projects.data?.map((item) => (
              <MenuItem key={item.project_id} value={item.project_id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Graph version"
            value={params.get("version") || ""}
            onChange={(e) => set("version", e.target.value)}
          >
            <MenuItem value="">Current version</MenuItem>
            {versions.data?.versions
              .filter((item) => item.status === "ready")
              .map((item) => (
                <MenuItem key={item.build_id} value={item.build_id}>
                  {item.build_id}
                </MenuItem>
              ))}
          </TextField>
          <Button component={Link} to="/explorer">
            Session Explorer
          </Button>
        </div>
        {projects.error instanceof ApiError && projects.error.code === "registry_unconfigured" && (
          <Alert severity="info">Published graphs are unavailable until an administrator configures the PostgreSQL registry.</Alert>
        )}
        {projects.isSuccess && projects.data.length === 0 && (
          <Alert severity="info">No published graph is available to this account.</Alert>
        )}
        <Feedback
          pending={projects.isFetching || versions.isFetching}
          error={projects.error instanceof ApiError && projects.error.code === "registry_unconfigured"
            ? undefined : projects.error ?? versions.error}
        />
      </Panel>
      {tool === "versions" && (
        <VersionHistory
          key={versionPath}
          data={versions.data}
          path={versionPath}
          version={version}
          restore={() => restore.mutate()}
          restoring={restore.isPending}
          error={restore.error}
        />
      )}
      {tool === "versions" && versions.data?.can_manage && (
        <ProjectMembers key={base} path={base} />
      )}
      {tool === "operations" && (
        <Operations
          session={session}
          project={project}
          versions={versions.data}
        />
      )}
      {tool === "graphml" && <GraphmlImport key={session ?? "no-session"} />}
      {tool === "intelligence" && (
        version || session ? (
          <>
            {version && session && <div className="toolbar section-gap">
              <TextField select label="Intelligence graph source" value={useSessionGraph ? "session" : "published"}
                onChange={(event) => set("source", event.target.value)}>
                <MenuItem value="published">Published version</MenuItem>
                <MenuItem value="session">Current session graph</MenuItem>
              </TextField>
            </div>}
            <IntelligenceTools key={useSessionGraph ? session : versionPath} published={!useSessionGraph}
              path={useSessionGraph ? sessionPath(session!, "/graphs") : versionPath} />
          </>
        ) : <Alert severity="info" className="mt-4">Build a session graph or choose a published version.</Alert>
      )}
      {tool !== "versions" && tool !== "graphml" && tool !== "intelligence" &&
        tool !== "operations" &&
        (version ? (
          <GraphTool
            key={versionPath + tool}
            tool={tool}
            path={versionPath}
            initialNode={params.get("node") ?? ""}
            onOpen={(node) => {
              const next = new URLSearchParams(params);
              next.set("view", "explorer");
              next.set("node", node);
              setParams(next);
            }}
          />
        ) : (
          <Alert severity="info" className="mt-4">
            Publish a validated graph from Storage & snapshots.
          </Alert>
        ))}
    </>
  );
}

function ProjectMembers({ path }: { path: string }) {
  const client = useQueryClient();
  const [username, setUsername] = useState("");
  const key = ["graph-project-members", path];
  const members = useQuery({
    queryKey: key,
    queryFn: ({ signal }) =>
      get<{ username: string; role: string }[]>(
        path + "/members",
        undefined,
        signal,
      ),
  });
  const change = useMutation({
    mutationFn: (remove?: string) =>
      remove
        ? send("DELETE", path + "/members", undefined, { username: remove })
        : send("PUT", path + "/members", { username }),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  return (
    <div className="section-gap">
      <Panel title="Project access">
        <form
          className="toolbar"
          onSubmit={(e) => {
            e.preventDefault();
            change.mutate(undefined);
          }}
        >
          <TextField
            label="Existing username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Button type="submit" disabled={!username.trim() || change.isPending}>
            Grant viewer access
          </Button>
        </form>
        <Feedback
          pending={members.isFetching || change.isPending}
          error={members.error ?? change.error}
        />
        {members.data?.map((member) => (
          <div key={member.username} className="toolbar">
            <span>
              {member.username} · {member.role}
            </span>
            <Button
              disabled={change.isPending}
              onClick={() => {
                if (
                  window.confirm(`Revoke viewer access for ${member.username}?`)
                )
                  change.mutate(member.username);
              }}
            >
              Revoke
            </Button>
          </div>
        ))}
      </Panel>
    </div>
  );
}

function VersionHistory({
  data,
  path,
  version,
  restore,
  restoring,
  error,
}: {
  data?: VersionList;
  path: string;
  version: string;
  restore: () => void;
  restoring: boolean;
  error: Error | null;
}) {
  const [baseline, setBaseline] = useState("");
  const client = useQueryClient();
  const [deleteId, setDeleteId] = useState("");
  const deleteVersion = useMutation({
    mutationFn: () =>
      send(
        "DELETE",
        path.slice(0, path.lastIndexOf("/") + 1) + encodeURIComponent(deleteId),
      ),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: ["published-versions"] }),
  });
  const [format, setFormat] = useState("json");
  const exportVersion = useMutation({
    mutationFn: async () => {
      const response = await api.get<Blob>(path + "/export/" + format, {
        responseType: "blob",
      });
      saveBlob(response.data, `graph-${version}.${format}`);
    },
  });
  const comparison = useQuery({
    queryKey: ["graph-comparison", path, baseline],
    queryFn: ({ signal }) =>
      get<JsonObject>(path + "/compare", { baseline }, signal),
    enabled: !!version && !!baseline,
  });
  return (
    <div className="section-gap">
      <Panel title="Version history">
        <DataTable rows={data?.versions ?? []} />
        <div className="toolbar mt-4">
          <Button
            disabled={
              !data?.can_manage ||
              !version ||
              data?.current === version ||
              restoring
            }
            onClick={() => {
              if (window.confirm("Make this version current?")) restore();
            }}
          >
            Restore selected version
          </Button>
          <TextField
            select
            label="Compare against"
            value={baseline}
            onChange={(e) => setBaseline(e.target.value)}
          >
            <MenuItem value="">Choose a version</MenuItem>
            {data?.versions
              .filter(
                (item) => item.status === "ready" && item.build_id !== version,
              )
              .map((item) => (
                <MenuItem key={item.build_id} value={item.build_id}>
                  {item.build_id}
                </MenuItem>
              ))}
          </TextField>
        </div>
        <Feedback
          pending={comparison.isFetching || restoring}
          error={comparison.error ?? error}
        />
        <Report value={comparison.data} />
      </Panel>
      <Panel title="Export selected version">
        <div className="toolbar">
          <TextField
            select
            label="Export format"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
          >
            <MenuItem value="json">JSON</MenuItem>
            <MenuItem value="graphml">GraphML</MenuItem>
            <MenuItem value="nodes.csv">Node CSV</MenuItem>
            <MenuItem value="relationships.csv">Relationship CSV</MenuItem>
          </TextField>
          <Button
            disabled={!version || exportVersion.isPending}
            onClick={() => exportVersion.mutate()}
          >
            Download version
          </Button>
        </div>
        <Feedback
          pending={exportVersion.isPending}
          error={exportVersion.error}
        />
      </Panel>
      {data?.can_manage && (
        <Panel title="Delete a historical version">
          <div className="toolbar">
            <TextField
              select
              label="Version to delete"
              value={deleteId}
              onChange={(e) => setDeleteId(e.target.value)}
            >
              <MenuItem value="">Choose a version</MenuItem>
              {data.versions
                .filter(
                  (item) =>
                    item.build_id !== data.current &&
                    ["ready", "failed", "deleting", "delete_failed"].includes(
                      item.status,
                    ),
                )
                .map((item) => (
                  <MenuItem key={item.build_id} value={item.build_id}>
                    {item.build_id}
                  </MenuItem>
                ))}
            </TextField>
            <Button
              color="error"
              disabled={!deleteId || deleteVersion.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    "Permanently delete this graph version from Neo4j?",
                  )
                )
                  deleteVersion.mutate();
              }}
            >
              Delete version
            </Button>
          </div>
          <Feedback
            pending={deleteVersion.isPending}
            error={deleteVersion.error}
          />
        </Panel>
      )}
    </div>
  );
}

function Operations({
  session,
  project,
  versions,
}: {
  session: string | null;
  project: string;
  versions?: VersionList;
}) {
  const client = useQueryClient();
  const job = useQuery({
    queryKey: ["published-job", session],
    queryFn: ({ signal }) =>
      get<Job | null>(
        sessionPath(session!, "/builds/status"),
        undefined,
        signal,
      ),
    enabled: !!session,
    refetchInterval: 2000,
  });
  const start = useMutation({
    mutationFn: () =>
      send("POST", sessionPath(session!, "/builds/published"), {}),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: ["published-job", session] }),
  });
  const cancel = useMutation({
    mutationFn: () =>
      send(
        "POST",
        sessionPath(
          session!,
          `/builds/${encodeURIComponent(String(job.data?.id))}/cancel`,
        ),
      ),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: ["published-job", session] }),
  });
  const health = useQuery({
    queryKey: ["published-health", project],
    queryFn: ({ signal }) =>
      get<JsonObject>(
        `/graph-projects/${encodeURIComponent(project)}/health`,
        undefined,
        signal,
      ),
    enabled: !!project,
  });
  const sourceHealth = useQuery({
    queryKey: ["published-source-health", session],
    queryFn: ({ signal }) =>
      get<JsonObject>(
        sessionPath(session!, "/sources/health"),
        undefined,
        signal,
      ),
    enabled: !!session,
  });
  useEffect(() => {
    if (
      job.data?.status === "completed" ||
      job.data?.status === "failed" ||
      job.data?.status === "cancelled"
    ) {
      void client.invalidateQueries({ queryKey: ["published-projects"] });
      void client.invalidateQueries({ queryKey: ["published-versions"] });
      void client.invalidateQueries({ queryKey: ["published-health"] });
    }
  }, [client, job.data?.id, job.data?.status]);
  const cancellable =
    job.data?.status === "running" || job.data?.status === "queued";
  const running =
    cancellable ||
    job.data?.status === "cancelling" ||
    job.data?.status === "publishing";
  return (
    <div className="section-gap">
      <Panel title="Build and publish">
        <p className="muted">
          Reconcile the active workflow's source against its build-ready ontology
          and publish a new validated version.
        </p>
        <div className="toolbar mt-4">
          <Button
            variant="contained"
            disabled={!session || running || start.isPending}
            onClick={() => start.mutate()}
          >
            Rebuild and publish
          </Button>
          {cancellable && (
            <Button disabled={cancel.isPending} onClick={() => cancel.mutate()}>
              Cancel build
            </Button>
          )}
          <Button
            onClick={() => {
              void client.invalidateQueries({
                queryKey: ["published-projects"],
              });
              void client.invalidateQueries({
                queryKey: ["published-versions"],
              });
              void client.invalidateQueries({ queryKey: ["published-health"] });
              void client.invalidateQueries({
                queryKey: ["published-source-health", session],
              });
            }}
          >
            Refresh version history
          </Button>
        </div>
        <Feedback
          pending={start.isPending || cancel.isPending}
          error={
            start.error ??
            cancel.error ??
            job.error ??
            health.error ??
            sourceHealth.error
          }
        />
        {job.data?.status === "failed" && job.data.error && (
          <Alert severity="error" className="mt-4">
            {job.data.error.message} ({job.data.error.code})
          </Alert>
        )}
        <Report value={job.data} />
        <DataTable rows={versions?.versions ?? []} />
      </Panel>
      {(health.data || sourceHealth.data) && (
        <Panel title="Database health and publication history">
          <Report
            value={{
              source: sourceHealth.data?.status,
              source_mode: sourceHealth.data?.mode,
              metadata_postgresql: health.data?.metadata_postgresql,
              neo4j: health.data?.neo4j_read,
              current: health.data?.current,
            }}
          />
          <DataTable
            rows={(health.data?.events as JsonObject[] | undefined) ?? []}
          />
        </Panel>
      )}
    </div>
  );
}

function GraphTool({
  tool,
  path,
  initialNode,
  onOpen,
}: {
  tool: Tool;
  path: string;
  initialNode: string;
  onOpen: (id: string) => void;
}) {
  if (tool === "explorer" || tool === "query") {
    const tools = <QueryTools
        tool={tool}
        path={path}
        initialNode={initialNode}
        onOpen={onOpen}
      />;
    return tool === "explorer" ? <EntityExplorer path={path}>{tools}</EntityExplorer> : tools;
  }
  return <VersionReport tool={tool} path={path} />;
}

function Distribution({ title, values }: { title: string; values: unknown }) {
  if (!values || typeof values !== "object") return null;
  const counts = Object.entries(values)
    .filter((entry): entry is [string, number] => typeof entry[1] === "number")
    .sort((a, b) => b[1] - a[1]);
  const max = counts[0]?.[1];
  if (!max) return null;
  return <Panel title={title}>
    <ul className="form-stack">
      {counts.slice(0, 12).map(([label, count]) => <li key={label}>
        <div className="flex justify-between gap-4"><span>{label}</span><span>{count}</span></div>
        <meter className="w-full" min={0} max={max} value={count} aria-label={label} />
      </li>)}
    </ul>
  </Panel>;
}

function VersionReport({ tool, path }: { tool: Tool; path: string }) {
  const report = useQuery({
    queryKey: ["graph-report", path, tool],
    queryFn: ({ signal }) =>
      get<JsonObject>(path + "/" + tool, undefined, signal),
  });
  const [ranking, setRanking] = useState("degree");
  const [community, setCommunity] = useState("");
  const [selection, setSelection] = useState<string | JsonObject | null>(null);
  const selectNode = useCallback((id: string) => setSelection(id), []);
  const selectEdge = useCallback((edge: JsonObject) => setSelection(edge), []);
  const communityGraph = useQuery({
    queryKey: ["graph-community", path, community],
    queryFn: ({ signal }) =>
      get<GraphView>(path + "/communities/" + community, undefined, signal),
    enabled: tool === "analytics" && community !== "",
  });
  if (tool === "schema")
    return (
      <div className="section-gap">
        <Panel title="Node labels and relationship directions">
          <Feedback pending={report.isFetching} error={report.error} />
          <DataTable
            rows={(report.data?.labels as JsonObject[] | undefined) ?? []}
          />
          <DataTable
            rows={(report.data?.types as JsonObject[] | undefined) ?? []}
          />
        </Panel>
        <Panel title="Indexes and constraints">
          <Report value={report.data?.schema_metadata} />
          <DataTable
            rows={(report.data?.indexes as JsonObject[] | undefined) ?? []}
          />
          <DataTable
            rows={(report.data?.constraints as JsonObject[] | undefined) ?? []}
          />
        </Panel>
      </div>
    );
  const rankings = report.data?.rankings as
    Record<string, JsonObject[]> | undefined;
  const metrics = Object.fromEntries(
    Object.entries(report.data ?? {}).filter(
      ([key]) => key !== "rankings" && key !== "communities",
    ),
  );
  const groups = (report.data?.communities as JsonObject[] | undefined) ?? [];
  return (
    <div className="section-gap grid grid-cols-1 xl:grid-cols-2 gap-5">
      <Panel title="Version metrics">
        <Feedback pending={report.isFetching} error={report.error} />
        <Report value={metrics} />
        <Button
          disabled={!report.data}
          onClick={() => downloadJson(report.data, "graph-analytics.json")}
        >
          Download analytics
        </Button>
      </Panel>
      <Distribution title="Nodes by label" values={report.data?.node_labels} />
      <Distribution title="Relationships by type" values={report.data?.relationship_types} />
      <Panel title="Node rankings">
        <TextField
          select
          label="Algorithm"
          value={ranking}
          onChange={(e) => setRanking(e.target.value)}
        >
          {Object.keys(rankings ?? { degree: [] }).map((key) => (
            <MenuItem key={key} value={key}>
              {key}
            </MenuItem>
          ))}
        </TextField>
        <DataTable rows={rankings?.[ranking] ?? []} />
        <p className="muted">
          Higher scores rank entities by connectivity or influence under the
          selected algorithm.
        </p>
      </Panel>
      <Panel title="Communities">
        {groups.length ? (
          <TextField
            select
            label="Community"
            value={community}
            onChange={(e) => {
              setCommunity(e.target.value);
              setSelection(null);
            }}
          >
            <MenuItem value="">Choose a community</MenuItem>
            {groups.map((group, index) => (
              <MenuItem key={index} value={String(index)}>
                Community {index + 1} · {String(group.size)} members
              </MenuItem>
            ))}
          </TextField>
        ) : (
          <p className="muted">No communities are available for this graph.</p>
        )}
        <Feedback
          pending={communityGraph.isFetching}
          error={communityGraph.error}
        />
        {communityGraph.data && (
          <div className="graph-frame mt-4">
            <GraphCanvas
              graph={communityGraph.data}
              layout="cose"
              onSelect={selectNode}
              onEdge={selectEdge}
              fitKey={0}
            />
          </div>
        )}
        <Report
          value={
            typeof selection === "string"
              ? communityGraph.data?.nodes.find((node) => node.id === selection)
              : selection
          }
        />
      </Panel>
    </div>
  );
}

function QueryTools({
  tool,
  path,
  initialNode,
  onOpen,
}: {
  tool: "query" | "explorer";
  path: string;
  initialNode: string;
  onOpen: (id: string) => void;
}) {
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState("");
  const [property, setProperty] = useState("");
  const [value, setValue] = useState("");
  const [hops, setHops] = useState(1);
  const [focus, setFocus] = useState(initialNode);
  const [selected, setSelected] = useState(initialNode);
  const [edge, setEdge] = useState<JsonObject | null>(null);
  const [template, setTemplate] = useState("entities");
  const [cypher, setCypher] = useState("");
  const [resultMode, setResultMode] = useState("table");
  const [layout, setLayout] = useState("cose");
  const [fit, setFit] = useState(0);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [showPath, setShowPath] = useState(false);
  const [itemName, setItemName] = useState("");
  const itemKind = tool === "query" ? "query" : "scene";
  const itemsKey = ["graph-workspace-items", path, itemKind];
  const historyKey = ["graph-workspace-items", path, "query_run"];
  const items = useQuery({
    queryKey: itemsKey,
    queryFn: ({ signal }) =>
      get<WorkspaceItem[]>(
        path + "/workspace-items",
        { kind: itemKind },
        signal,
      ),
  });
  const history = useQuery({
    queryKey: historyKey,
    queryFn: ({ signal }) =>
      get<{ settings: JsonObject; updated_at: string }[]>(
        path + "/workspace-items",
        { kind: "query_run" },
        signal,
      ),
    enabled: tool === "query",
  });
  const saveItem = useMutation({
    mutationFn: () =>
      send("PUT", path + "/workspace-items", {
        name: itemName,
        kind: itemKind,
        template,
        search,
        label,
        relationship: kind,
        focus,
        hops,
        layout,
        cypher,
        property,
        value,
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: itemsKey }),
  });
  const canvas = useRef<HTMLDivElement>(null);
  const [request, setRequest] = useState({
    template: "entities",
    search: "",
    label: "",
    kind: "",
    property: "",
    value: "",
    offset: 0,
  });
  const query = useQuery({
    queryKey: ["published-query", path, request],
    queryFn: ({ signal }) =>
      get<QueryResult>(path + "/query", { ...request, limit: 25 }, signal),
    enabled: tool === "explorer",
  });
  const workbench = useMutation({
    mutationFn: () =>
      cypher.trim()
        ? send<QueryResult>("POST", path + "/query", { cypher })
        : get<QueryResult>(path + "/query", {
            template,
            search,
            label,
            kind,
            property,
            value,
            limit: 100,
            log_run: true,
          }),
    onSuccess: () => {
      setFocus("");
      setSelected("");
      setEdge(null);
      return client.invalidateQueries({ queryKey: historyKey });
    },
  });
  const graph = useQuery({
    queryKey: ["published-neighborhood", path, focus, hops, kind],
    queryFn: ({ signal }) =>
      get<GraphView>(
        path + "/neighborhood",
        { node_id: focus, hops, kind },
        signal,
      ),
    enabled: !!focus,
  });
  const route = useMutation({
    mutationFn: () =>
      get<GraphView>(path + "/paths", { source, target, limit: 5 }),
    onSuccess: () => setShowPath(true),
  });
  const selectNode = useCallback((id: string) => {
    setSelected(id);
    setEdge(null);
  }, []);
  const selectEdge = useCallback((item: JsonObject) => {
    setEdge(item);
    setSelected("");
  }, []);
  const rows = (tool === "query" ? workbench.data : query.data)?.rows ?? [];
  const queryGraph = useMemo(
    () => resultGraph(workbench.data),
    [workbench.data],
  );
  const displayed = showPath ? route.data : (graph.data ?? queryGraph);
  const chosen =
    displayed?.nodes.find((item) => item.id === selected) ??
    queryGraph?.nodes.find((item) => item.id === selected) ??
    rows.find((item) => item.id === selected);
  const showGraph = tool === "explorer" || resultMode === "graph";
  return (
    <div className="section-gap grid grid-cols-1 xl:grid-cols-[250px_minmax(0,1fr)_270px] gap-4">
      <Panel
        title={tool === "query" ? "Cypher templates" : "Search and filter"}
      >
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            if (tool === "query") workbench.mutate();
            else
              setRequest({
                template: "entities",
                search,
                label,
                kind,
                property,
                value,
                offset: 0,
              });
          }}
        >
          {tool === "query" && (
            <TextField
              select
              label="Query template"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
            >
              {["entities", "relationships", "labels", "types"].map((key) => (
                <MenuItem key={key} value={key}>
                  {key}
                </MenuItem>
              ))}
            </TextField>
          )}
          {tool === "query" && (
            <>
              <TextField
                label="Cypher statement"
                multiline
                minRows={3}
                value={cypher}
                placeholder={"MATCH (c:Customer)\nRETURN c\nLIMIT 50"}
                onChange={(e) => setCypher(e.target.value)}
                slotProps={{
                  htmlInput: {
                    maxLength: 2000,
                    spellCheck: false,
                    style: { fontFamily: "monospace" },
                  },
                }}
                helperText="Enter a labelled MATCH or leave this field blank to run the selected template."
              />
              <div className="toolbar">
                <Button
                  disabled={!cypher.trim()}
                  onClick={() =>
                    setCypher(
                      cypher
                        .trim()
                        .replace(/\s+/g, " ")
                        .replace(
                          /\s+(return|limit)\s+/gi,
                          (_, keyword: string) =>
                            "\n" + keyword.toUpperCase() + " ",
                        ),
                    )
                  }
                >
                  Format
                </Button>
                <Button disabled={!cypher} onClick={() => setCypher("")}>
                  Clear statement
                </Button>
              </div>
            </>
          )}
          <TextField
            label="Name or ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <TextField
            label="Entity label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
          <TextField
            label="Relationship type"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          />
          <details>
            <summary>Entity property filter</summary>
            <div className="form-stack mt-3">
              <TextField
                label="Property name"
                value={property}
                onChange={(e) => setProperty(e.target.value)}
              />
              <TextField
                label="Property value"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
          </details>
          <Button type="submit" variant="contained">
            {tool === "query" ? "Run query" : "Search"}
          </Button>
        </form>
        <div className="form-stack mt-4">
          <TextField
            label={tool === "query" ? "Query name" : "Scene name"}
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
          />
          <Button
            disabled={!itemName.trim() || saveItem.isPending}
            onClick={() => saveItem.mutate()}
          >
            {tool === "query" ? "Save query" : "Save scene"}
          </Button>
          <TextField
            select
            label={tool === "query" ? "Load saved query" : "Restore scene"}
            value=""
            onChange={(e) => {
              const item = items.data?.find(
                (entry) => entry.name === e.target.value,
              );
              if (!item) return;
              const state = item.settings;
              setItemName(item.name);
              setSearch(state.search);
              setLabel(state.label);
              setKind(state.relationship);
              setTemplate(state.template);
              setLayout(state.layout);
              setHops(state.hops);
              setCypher(state.cypher ?? "");
              setProperty(state.property ?? "");
              setValue(state.value ?? "");
              setFocus(state.focus);
              selectNode(state.focus);
              setShowPath(false);
              setRequest({
                template: "entities",
                search: state.search,
                label: state.label,
                kind: state.relationship,
                property: state.property ?? "",
                value: state.value ?? "",
                offset: 0,
              });
            }}
          >
            <MenuItem value="">Choose a saved item</MenuItem>
            {items.data?.map((item) => (
              <MenuItem key={item.name} value={item.name}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <Feedback
            pending={saveItem.isPending}
            error={saveItem.error ?? items.error}
          />
        </div>
        {tool === "explorer" && (
          <div className="toolbar mt-4">
            <Button
              disabled={!request.offset}
              onClick={() =>
                setRequest({ ...request, offset: request.offset - 25 })
              }
            >
              Previous
            </Button>
            <Button
              disabled={rows.length < 25}
              onClick={() =>
                setRequest({ ...request, offset: request.offset + 25 })
              }
            >
              Next
            </Button>
          </div>
        )}
        <Feedback
          pending={query.isFetching || workbench.isPending}
          error={query.error ?? workbench.error}
        />
        {tool === "explorer" &&
          rows.map((row) => (
            <Button
              key={String(row.id)}
              onClick={() => {
                selectNode(String(row.id));
                setFocus(String(row.id));
                setShowPath(false);
              }}
              sx={{
                display: "block",
                overflowWrap: "anywhere",
                textAlign: "left",
              }}
            >
              {String(row.id)}
            </Button>
          ))}
        {tool === "explorer" && (
          <form
            className="form-stack mt-4"
            onSubmit={(e) => {
              e.preventDefault();
              route.mutate();
            }}
          >
            <TextField
              label="Path source ID"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
            <TextField
              label="Path target ID"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
            <Button
              type="submit"
              disabled={!source || !target || route.isPending}
            >
              Find shortest paths
            </Button>
            <Feedback pending={route.isPending} error={route.error} />
          </form>
        )}
      </Panel>
      <Panel title={tool === "query" ? "Query results" : "Graph workspace"}>
        {tool === "query" && (
          <>
            <div className="toolbar mb-4">
              <TextField
                select
                label="Result mode"
                value={resultMode}
                onChange={(e) => setResultMode(e.target.value)}
              >
                {["table", "graph", "json"].map((key) => (
                  <MenuItem key={key} value={key}>
                    {key}
                  </MenuItem>
                ))}
              </TextField>
              <Button
                disabled={!workbench.data}
                onClick={() => downloadJson(rows, "query-results.json")}
              >
                Export results
              </Button>
            </div>
            {workbench.data && (
              <p className="muted">
                {rows.length} rows · {workbench.data.duration_ms} ms
              </p>
            )}
            {resultMode === "json" && <Report value={rows} />}
            {resultMode === "table" && <DataTable rows={rows} />}
            <details className="mt-4">
              <summary>Recent query executions</summary>
              <Feedback pending={history.isFetching} error={history.error} />
              <DataTable
                rows={(history.data ?? []).map((item) => ({
                  ...item.settings,
                  executed_at: item.updated_at,
                }))}
              />
            </details>
            {(queryGraph?.nodes ?? [])
              .map((node) => node.id)
              .map((id) => (
                <Button
                  key={id}
                  onClick={() => {
                    selectNode(id);
                    setFocus(id);
                  }}
                >
                  {id}
                </Button>
              ))}
          </>
        )}
        {showGraph && (
          <>
            <div className="toolbar mb-4">
              <TextField
                select
                label="Layout"
                value={layout}
                onChange={(e) => setLayout(e.target.value)}
              >
                {["cose", "breadthfirst", "circle", "grid", "concentric"].map(
                  (key) => (
                    <MenuItem key={key} value={key}>
                      {key}
                    </MenuItem>
                  ),
                )}
              </TextField>
              <Button onClick={() => setFit((value) => value + 1)}>
                Fit graph
              </Button>
              <Button
                disabled={!displayed?.nodes.length}
                onClick={() => {
                  void canvas.current
                    ?.requestFullscreen()
                    .catch(() => undefined);
                }}
              >
                Full screen
              </Button>
              <Button
                disabled={!focus && !showPath}
                onClick={() => {
                  setFocus("");
                  setSelected("");
                  setEdge(null);
                  setShowPath(false);
                }}
              >
                Clear canvas
              </Button>
            </div>
            <Feedback pending={graph.isFetching} error={graph.error} />
            {displayed?.nodes.length ? (
              <div className="graph-frame" ref={canvas}>
                <GraphCanvas
                  graph={displayed}
                  layout={layout}
                  onSelect={selectNode}
                  onEdge={selectEdge}
                  fitKey={fit}
                />
              </div>
            ) : (
              <p className="muted">
                {showPath
                  ? "No connection found within 12 hops."
                  : "Select an entity to display its neighborhood."}
              </p>
            )}
          </>
        )}
      </Panel>
      <Panel title="Properties">
        <Report value={edge ?? chosen} />
        {selected && (
          <>
            <div className="toolbar">
              <Button
                onClick={() => {
                  setFocus(selected);
                  setHops(1);
                  setShowPath(false);
                }}
              >
                Expand one hop
              </Button>
              <Button
                onClick={() => {
                  setFocus(selected);
                  setHops(2);
                  setShowPath(false);
                }}
              >
                Expand two hops
              </Button>
              {tool === "explorer" && (
                <Button onClick={() => setSource(selected)}>
                  Use as path source
                </Button>
              )}
              {tool === "explorer" && (
                <Button onClick={() => setTarget(selected)}>
                  Use as path target
                </Button>
              )}
              {tool === "query" && (
                <Button onClick={() => onOpen(selected)}>
                  Open in Graph Explorer
                </Button>
              )}
            </div>
          </>
        )}
      </Panel>
    </div>
  );
}
