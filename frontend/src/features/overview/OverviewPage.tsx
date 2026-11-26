import { labels, type ConnectorId } from "../sources/guidedSources";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, LinearProgress, TextField } from "@mui/material";
import { ArrowRight, ChartNoAxesCombined, Check, Trash2, Workflow } from "lucide-react";
import { ApiError, get } from "../../api/client";
import { useSavedOntologies } from "../../api/libraryApi";
import { sessionsApi } from "../../api/sessionsApi";
import { useGraphStore, useSessionStore } from "../../app/store";
import { useWorkspace } from "../../shared/hooks/useWorkspace";
import {
  PageHeader,
  Panel,
  Feedback,
  StatusChip,
} from "../../shared/ui/WorkspaceUi";
import {
  stageRoutes,
} from "../../constants/stages.constants";
import { stageNavigation } from "../../constants/stageNavigation";
import type { Schema } from "../../types/common.types";

type PublishedProject = {
  project_id: string;
  name: string;
  current_build_id: string | null;
  ontology_id?: string | null;
  ontology_version?: number | null;
};

const descriptions: Record<number, string> = {
  2: "Connect and select data assets for this workspace.",
  1: "Define business questions and the data in scope.",
  3: "Extract tables, columns, keys, and relationships.",
  4: "Classify tables and identify candidate relationships.",
  5: "Map source tables to entities and relationships.",
  6: "Generate AI suggestions or skip this step.",
  7: "Review mappings and apply decisions.",
  8: "Check ontology structure and source mappings.",
  9: "Approve and manage ontology versions.",
  10: "Plan how source records become graph entities.",
  11: "Read the source records selected for graph construction.",
  12: "Check records against quality rules.",
  13: "Standardize records and resolve duplicates.",
  14: "Build graph nodes and edges.",
  15: "Check graph integrity before saving.",
  16: "Save or publish a validated graph.",
};

export default function OverviewPage() {
  const [name, setName] = useState("Knowledge workspace");
  const [deleteTarget, setDeleteTarget] = useState<Schema<"SessionView"> | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [deletedName, setDeletedName] = useState("");
  const navigate = useNavigate();
  const client = useQueryClient();
  const savedOntologies = useSavedOntologies();
  const { id, session, done, can, workflow } = useWorkspace();
  const notice = useSessionStore((s) => s.notice);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => sessionsApi.health(signal),
    staleTime: 15000,
    retry: false,
  });
  const projects = useQuery({
    queryKey: ["published-projects"],
    queryFn: ({ signal }) =>
      get<PublishedProject[]>("/graph-projects", undefined, signal),
    retry: false,
  });
  const workspaces = useQuery({
    queryKey: ["workspaces"],
    queryFn: ({ signal }) => sessionsApi.workspaces(signal),
    refetchInterval: 10000,
    retry: false,
  });
  const create = useMutation({
    mutationFn: () => sessionsApi.create({ name: name.trim() }),
    onSuccess: (workspace) => {
      void client.invalidateQueries({ queryKey: ["workspaces"] });
      client.setQueryData(["workspace", workspace.id, "session"], workspace);
      useSessionStore.getState().setSession(workspace.id);
      navigate("/sources");
    },
    gcTime: 0,
  });

  const published =
    projects.data?.filter((project) => project.current_build_id) ?? [];
  const registryDisabled =
    projects.error instanceof ApiError &&
    projects.error.code === "registry_unconfigured";
  const summary = session.data?.summary;
  const ontology = summary?.ontology;
  const job = session.data?.job;
  const running = ["queued", "running", "cancelling", "publishing"].includes(
    String(job?.status),
  );
  const runningStage =
    running && typeof job?.stage === "number" ? job.stage : undefined;
  const { order: stageOrder, groups: stageGroups } = workflow;
  const next = stageOrder.find((stage) => !done.includes(stage) && can(stage));
  const completed = stageOrder.filter((stage) => done.includes(stage)).length;
  const percent = stageOrder.length ? Math.round((completed / stageOrder.length) * 100) : 0;
  const hasGraph = done.includes(14);
  const otherWorkspaces =
    workspaces.data?.filter((workspace) => workspace.id !== id) ?? [];
  const builtCount =
    Number(hasGraph) +
    otherWorkspaces.filter((workspace) =>
      workspace.completed_stages.includes(14),
    ).length;
  const reopen = useMutation({
    mutationFn: ({ workspaceId }: { workspaceId: string; resume?: boolean }) => sessionsApi.reopen(workspaceId),
    onSuccess: (workspace, { resume }) => {
      useGraphStore.getState().reset();
      client.setQueryData(["workspace", workspace.id, "session"], workspace);
      useSessionStore.getState().setSession(workspace.id);
      void client.invalidateQueries({ queryKey: ["workspaces"] });
      if (resume) {
        const nextStage = stageOrder.find((stage) => !workspace.completed_stages.includes(stage));
        navigate(workspace.reconnect_required ? "/sources"
          : workspace.snapshot && !workspace.completed_stages.includes(14) ? "/explorer?recovered=1"
          : nextStage ? stageRoutes[nextStage] : "/explorer");
      }
    },
  });
  const deletion = useMutation({
    mutationFn: (workspace: Schema<"SessionView">) => sessionsApi.deleteWorkspace(workspace.id),
    onSuccess: (_, workspace) => {
      if (useSessionStore.getState().id === workspace.id) {
        useSessionStore.getState().setSession(null);
        useGraphStore.getState().reset();
      }
      client.removeQueries({ queryKey: ["workspace", workspace.id] });
      client.setQueryData<Schema<"SessionView">[]>(["workspaces"], (current) =>
        current?.filter((item) => item.id !== workspace.id));
      setDeleteTarget(null);
      setDeletedName(workspace.name);
      void client.invalidateQueries({ queryKey: ["workspaces"] });
      void client.invalidateQueries({ queryKey: ["saved-ontologies"] });
    },
  });
  function openWorkspace(workspaceId: string) {
    if (!reopen.isPending) reopen.mutate({ workspaceId });
  }
  function lastStage(workspace: Schema<"SessionView">) {
    const evidence = [...workspace.completed_stages, ...(workspace.historical_stages ?? [])];
    const stage = stageOrder.filter((number) => evidence.includes(number)).at(-1);
    return stage ? stageNavigation[stage].title : "None";
  }
  const sourceType =
    summary?.source_type === "csv"
      ? "CSV"
      : summary?.source_type && Object.hasOwn(labels, summary.source_type)
        ? labels[summary.source_type as ConnectorId]
        : undefined;
  const publishedOntologies = published.filter(
    (project) => project.ontology_id,
  );
  const useWorkspaceGraph = Boolean(id) && (hasGraph || !published.length);
  const intelligencePath = useWorkspaceGraph
    ? "/explorer"
    : "/published-graphs";

  return (
    <>
      <PageHeader
        title="Home"
        action={
          id &&
          session.data && (
            <Button
              component={Link}
              to={
                runningStage
                  ? stageRoutes[runningStage]
                  : next
                    ? stageRoutes[next]
                    : "/explorer"
              }
              variant="contained"
              endIcon={<ArrowRight size={16} />}
            >
              {runningStage
                ? "View running stage"
                : next
                  ? "Continue workflow"
                  : "Explore graph"}
            </Button>
          )
        }
      />
      {notice && (
        <Alert severity="info" className="mb-5">
          {notice}
        </Alert>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        <Panel title="Created knowledge graphs">
          <div className="metric">
            {projects.data ? published.length : registryDisabled ? "0" : "—"}
          </div>
          <p className="muted">
            Published graphs
            {registryDisabled ? " · Publishing is not configured" : ""}
          </p>
          <div className="report-row">
            <span>Built in active workspaces</span>
            <strong>{workspaces.data ? builtCount : "Pending"}</strong>
          </div>
          <Feedback
            pending={projects.isLoading}
            error={registryDisabled ? undefined : projects.error}
          />
          <Button component={Link} to="/published-graphs">
            View published graphs
          </Button>
        </Panel>
        <Panel title="Workflow progress">
          <div className="metric">{percent}%</div>
          <LinearProgress
            variant="determinate"
            value={percent}
            aria-label="Workflow completion"
          />
          <p className="muted mt-2">
            {completed} of {stageOrder.length} stages completed
          </p>
          <p className="muted">
            {session.isLoading
              ? "Loading workspace"
              : runningStage
                ? `Running · ${stageNavigation[runningStage]?.title ?? "Build"}`
                : running
                  ? `Build ${String(job?.status)}`
                  : job?.status === "failed" ||
                      job?.status === "blocked" ||
                      job?.status === "cancelled"
                    ? `Build ${job.status}`
                    : percent === 100
                      ? "Workflow complete"
                      : completed
                        ? "In progress"
                        : id
                          ? "Ready to start"
                          : otherWorkspaces.length
                            ? "Open a workspace to see its stages"
                            : "No active workspace"}
          </p>
        </Panel>
        <Panel title="Connections">
          <div className="report-row">
            <span>API</span>
            <strong>
              {health.isError
                ? "Offline"
                : health.data
                  ? "Connected"
                  : "Checking"}
            </strong>
          </div>
          <div className="report-row">
            <span>Data source</span>
            <strong>{sourceType ?? "Unconfigured"}</strong>
          </div>
          {sourceType && (
            <p className="muted mt-2">
              {summary?.source_name}
              {sourceType === "CSV" && ` · ${summary?.source_files ?? 0} files`}
            </p>
          )}
          {id && (
            <Button component={Link} to="/sources">
              Manage source
            </Button>
          )}
        </Panel>
      </div>

      {deletedName && <Alert severity="success" onClose={() => setDeletedName("")}>
        Workspace “{deletedName}” deleted.
      </Alert>}
      {!!workspaces.data?.length && (
        <div className="mb-5">
          <Panel title="Workspaces">
            {workspaces.data.map((workspace) => {
              const progress = workspace.active
                ? workspace.completed_stages
                : (workspace.historical_stages ?? []);
              const count = stageOrder.filter((stage) =>
                progress.includes(stage),
              ).length;
              const status =
                typeof workspace.job?.status === "string"
                  ? workspace.job.status
                  : undefined;
              return (
                <div className="report-row items-center" key={workspace.id}>
                  <div>
                    <strong>{workspace.name}</strong>
                    <p className="muted">
                      {stageOrder.length ? Math.round((count / stageOrder.length) * 100) : 0}% complete
                      {status && ` · Build ${status}`}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button disabled={reopen.isPending} onClick={() => openWorkspace(workspace.id)}>
                      Open workspace
                    </Button>
                    <Button disabled={reopen.isPending} onClick={() =>
                      reopen.mutate({ workspaceId: workspace.id, resume: true })}>
                      {workspace.reconnect_required ? "Reconnect source" : "Resume workflow"}
                    </Button>
                    <Button color="error" startIcon={<Trash2 size={16} />}
                      aria-label={`Delete workspace ${workspace.name}`}
                      disabled={deletion.isPending}
                      onClick={() => {
                        deletion.reset();
                        setConfirmation("");
                        setDeleteTarget(workspace);
                      }}>
                      Delete
                    </Button>
                  </div>
                  <div className="muted text-sm">
                    <p>Last updated {workspace.updated_at ? new Date(workspace.updated_at).toLocaleString() : "Unavailable"}</p>
                    <p>Last completed stage {lastStage(workspace)}</p>
                    <p>{workspace.active ? "Active" : "Available to reopen"}{workspace.reconnect_required ? " · Source reconnection required" : ""}</p>
                  </div>
                </div>
              );
            })}
          </Panel>
        </div>
      )}
      <Feedback error={workspaces.error} />
      <Feedback error={reopen.error} />
      <Dialog open={!!deleteTarget} aria-labelledby="delete-workspace-title"
        onClose={() => { if (!deletion.isPending) setDeleteTarget(null); }}>
        <DialogTitle id="delete-workspace-title">Delete Workspace</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Deleting “{deleteTarget?.name}” removes it from the workspace list and clears its recovery checkpoint.
            Local drafts, snapshots, and artifacts are retained. Published Neo4j graphs and versions remain available.
          </DialogContentText>
          <TextField autoFocus fullWidth margin="normal" label="Type the exact workspace name"
            value={confirmation} disabled={deletion.isPending}
            onChange={(event) => setConfirmation(event.target.value)} />
          <Feedback error={deletion.error} />
        </DialogContent>
        <DialogActions>
          <Button disabled={deletion.isPending} onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button color="error" variant="contained"
            disabled={!deleteTarget || confirmation !== deleteTarget.name || deletion.isPending}
            onClick={() => { if (deleteTarget && confirmation === deleteTarget.name) deletion.mutate(deleteTarget); }}>
            Delete Workspace
          </Button>
        </DialogActions>
      </Dialog>
      {session.data?.recovery_issues?.map((issue) => <Alert key={issue} severity="warning">{issue}</Alert>)}
      {session.data?.job?.status === "interrupted" && <Alert severity="warning">
        The previous job was interrupted. Review the saved state before retrying.
      </Alert>}
      {session.data?.reconnect_required && <Alert severity="info"
        action={<Button component={Link} to="/sources">Reconnect source</Button>}>
        Reconnect the source to rebuild. Saved snapshots remain available for inspection.
      </Alert>}
      {session.data?.snapshot && !done.includes(14) && (
        <Button component={Link} to="/explorer?recovered=1">Open saved graph</Button>
      )}

      {!id && (
        <div className="mb-5">
          <Panel title="Create a workspace">
            <form
              className="form-stack"
              onSubmit={(event) => {
                event.preventDefault();
                create.mutate();
              }}
            >
              <TextField
                label="Workspace name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                slotProps={{ htmlInput: { maxLength: 200 } }}
              />
              <div>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={create.isPending || !name.trim()}
                >
                  Create workspace
                </Button>
              </div>
              <Feedback pending={create.isPending} error={create.error} />
            </form>
          </Panel>
        </div>
      )}
      <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-5">
        <Panel
          title="Workflow stages"
          action={session.data && <StatusChip>{session.data.name}</StatusChip>}
        >
          {stageGroups.map(({ title, numbers }) => (
            <section key={title} className="mb-5">
              <h3 className="mb-2">{title}</h3>
              <div className="workflow-list">
                {numbers.map((stage) => {
                  const { icon: Icon, title } = stageNavigation[stage];
                  const complete = done.includes(stage);
                  const active = runningStage === stage;
                  const blocked = Boolean(session.data) && !can(stage);
                  const status = active
                    ? "Running"
                    : complete
                      ? "Completed"
                      : blocked
                        ? "Waiting"
                        : "Pending";
                  const content = (
                    <>
                      <span
                        className={`stage-icon ${complete ? "done" : ""}`}
                        aria-hidden="true"
                      >
                        {complete ? <Check size={14} /> : <Icon size={14} />}
                      </span>
                      <span className="stage-label">
                        {stageOrder.indexOf(stage) + 1}. {title}
                        <small className="muted block mt-1">
                          {descriptions[stage]}
                        </small>
                      </span>
                      {session.data && (
                        <span
                          className={`status-pill ${complete && !active ? "success" : blocked ? "blocked" : "pending"}`}
                        >
                          {status}
                        </span>
                      )}
                      {id && <ArrowRight size={13} aria-hidden="true" />}
                    </>
                  );
                  return id ? (
                    <Link
                      className="stage-item"
                      to={stageRoutes[stage]}
                      key={stage}
                    >
                      {content}
                    </Link>
                  ) : (
                    <div className="stage-item" key={stage}>
                      {content}
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
          <section>
            <h3 className="mb-2">Graph Intelligence</h3>
            <div className="toolbar">
              <Button
                component={Link}
                to={`${intelligencePath}?view=${useWorkspaceGraph ? "path" : "explorer"}`}
                startIcon={<Workflow size={15} />}
              >
                Path Analysis
              </Button>
              <Button
                component={Link}
                to={`${intelligencePath}?view=${useWorkspaceGraph ? "metrics" : "analytics"}`}
                startIcon={<ChartNoAxesCombined size={15} />}
              >
                Graph Metrics
              </Button>
            </div>
          </section>
        </Panel>
        <div className="flex flex-col gap-5">
          <Panel title="Data analysis">
            {summary?.tables == null ? (
              <p className="muted">
                Extract and analyze a schema to see table statistics.
              </p>
            ) : (
              <>
                <div className="report-row">
                  <span>Catalog tables</span>
                  <strong>{summary.tables}</strong>
                </div>
                {Object.entries(summary.table_types ?? {}).map(
                  ([type, count]) => (
                    <div className="report-row capitalize" key={type}>
                      <span>{type} tables</span>
                      <strong>{count}</strong>
                    </div>
                  ),
                )}
              </>
            )}
            {summary?.nodes != null && (
              <div className="report-row">
                <span>Graph nodes</span>
                <strong>{summary.nodes}</strong>
              </div>
            )}
            {summary?.edges != null && (
              <div className="report-row">
                <span>Graph edges</span>
                <strong>{summary.edges}</strong>
              </div>
            )}
            {id && (
              <Button component={Link} to="/analysis">
                View schema analysis
              </Button>
            )}
          </Panel>
          <Panel title="Created ontologies">
            <Feedback
              pending={savedOntologies.isLoading}
              error={savedOntologies.error}
            />
            {savedOntologies.data?.map((saved) => (
              <details
                key={`${saved.workspace_id}/${saved.ontology_id}`}
                className="mb-3"
              >
                <summary className="cursor-pointer font-semibold">
                  {saved.name} ({saved.workspace_name})
                </summary>
                {saved.versions.map((version) => (
                  <div
                    className="report-row"
                    key={version.version ?? "working"}
                  >
                    <span>
                      {version.version === null
                        ? "Working draft"
                        : `Version ${version.version}`}
                    </span>
                    <strong>
                      {version.status.replaceAll("_", " ")} / {version.classes}{" "}
                      classes / {version.relationships} relationships
                    </strong>
                  </div>
                ))}
              </details>
            ))}
            {!ontology &&
              !otherWorkspaces.some(
                (workspace) => workspace.summary?.ontology,
              ) &&
              !publishedOntologies.length &&
              !savedOntologies.data?.length &&
              !savedOntologies.isLoading && (
                <p className="muted">
                  No workspace or published graph ontologies yet.
                </p>
              )}
            {ontology && (
              <div className="mb-3">
                <Link
                  className="font-semibold"
                  to={
                    workflow.enabled(9) && done.includes(9)
                      ? `/repository?ontology=${encodeURIComponent(ontology.id)}`
                      : "/ontology"
                  }
                >
                  {ontology.name}
                </Link>
                <p className="muted">
                  Workspace · Version {ontology.version} ·{" "}
                  {ontology.status.replaceAll("_", " ")}
                </p>
                <p className="muted">
                  {ontology.classes} classes · {ontology.relationships}{" "}
                  relationships
                </p>
              </div>
            )}
            {otherWorkspaces.map((workspace) => {
              const saved = workspace.summary?.ontology;
              return (
                saved && (
                  <div className="report-row items-center" key={workspace.id}>
                    <div>
                      <strong>{saved.name}</strong>
                      <p className="muted">
                        {workspace.name} · Version {saved.version} ·{" "}
                        {saved.status.replaceAll("_", " ")}
                      </p>
                    </div>
                    <Button onClick={() => openWorkspace(workspace.id)}>
                      Open workspace
                    </Button>
                  </div>
                )
              );
            })}
            {publishedOntologies.map((project) => (
              <div key={project.project_id} className="report-row">
                <Link
                  to={`/published-graphs?project=${encodeURIComponent(project.project_id)}`}
                >
                  {project.name}
                </Link>
                <span className="muted">
                  {project.ontology_id} · v{project.ontology_version}
                </span>
              </div>
            ))}
          </Panel>
        </div>
      </div>
    </>
  );
}
