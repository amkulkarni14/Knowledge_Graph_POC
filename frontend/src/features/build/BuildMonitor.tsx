import { useEffect, useState, type ReactNode } from "react";
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Button,
  CircularProgress, LinearProgress, MenuItem, TextField,
} from "@mui/material";
import { AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, Circle, MinusCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { buildsApi, snapshotsApi } from "../../api/workflowApi";
import { stageNavigation } from "../../constants/stageNavigation";
import { useData } from "../../shared/hooks/useWorkspace";
import { Feedback, Panel, Report } from "../../shared/ui/WorkspaceUi";
import type { BuildPipeline, BuildStage, BuildStep, Job, Schema } from "../../types/common.types";

const statusLabels = {
  queued: "Queued", running: "In progress", cancelling: "Cancelling", publishing: "Publishing",
  completed: "Completed", blocked: "Blocked", failed: "Failed", cancelled: "Cancelled", interrupted: "Interrupted",
  pending: "Pending", skipped: "Skipped",
} as const;
const accordion = { "&:before": { display: "none" }, borderRadius: 1 };

export function buildStageTitle(stage: BuildStage, first: number) {
  return stage.stage === first ? stage.title : stageNavigation[stage.stage]?.title ?? stage.title;
}

function duration(ms: number | undefined) {
  if (ms === undefined) return "—";
  if (ms < 1000) return `${ms} ms`;
  const seconds = Math.floor(ms / 1000);
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function timestamp(value?: string) {
  return value ? new Date(value).toLocaleString() : "—";
}

function StepIcon({ status }: { status: BuildStep["status"] }) {
  const props = { size: 17, "aria-hidden": true } as const;
  switch (status) {
    case "running": return <CircularProgress size={16} aria-hidden />;
    case "completed": return <CheckCircle2 {...props} className="text-green-700" />;
    case "failed": return <AlertCircle {...props} className="text-red-700" />;
    case "interrupted": return <AlertTriangle {...props} className="text-amber-700" />;
    case "skipped": return <MinusCircle {...props} className="muted" />;
    default: return <Circle {...props} className="muted" />;
  }
}

function BuildOverview({ job, busy, stages, current }: {
  job?: Job | null; busy: boolean; stages: BuildStep[]; current?: string;
}) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [busy]);
  const completed = stages.filter((stage) => stage.status === "completed").length;
  const hasProgress = !job || !!job.steps;
  const percent = stages.length ? Math.floor(completed * 100 / stages.length) : 0;
  const elapsed = job?.started_at && job.status !== "interrupted" && (job.finished_at || busy)
    ? Math.max(0, (job.finished_at ? Date.parse(job.finished_at) : now) - Date.parse(job.started_at))
    : undefined;
  return <Panel title="Build overview">
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6" aria-live="polite">
      {Object.entries({
        Status: job ? statusLabels[job.status] : "Not started",
        Progress: hasProgress ? `${percent}%` : "Unavailable",
        "Completed stages": hasProgress ? `${completed} of ${stages.length}` : "Unavailable",
        "Current stage": busy ? current ?? "Waiting to start" : "—",
        Elapsed: duration(elapsed),
        Started: timestamp(job?.started_at),
        Finished: timestamp(job?.finished_at),
      }).map(([key, value]) => <div key={key}><div className="muted">{key}</div><strong>{value}</strong></div>)}
    </div>
    {hasProgress && <LinearProgress className="mt-4" variant="determinate" value={percent} aria-label="Build progress" />}
  </Panel>;
}

function StageDetails({ id, step, busy, persistence, workspace, children }: {
  id: string; step: BuildStep; busy: boolean; persistence: boolean;
  workspace?: Schema<"SessionView">; children?: ReactNode;
}) {
  const fetchDetails = !persistence && !busy &&
    (workspace?.completed_stages.includes(step.stage) || step.status === "failed" && !!step.result);
  const result = useData(["build", "result", step.stage, step.duration_ms],
    (signal) => buildsApi.result(id, step.stage, signal), !!fetchDetails);
  const snapshot = workspace?.snapshot;
  const snapshots = useData(["build", "saved-snapshot", snapshot?.ontology_id, snapshot?.build_id],
    (signal) => snapshotsApi.list(id, snapshot!.ontology_id, signal),
    persistence && !busy && !!snapshot?.ontology_id && !workspace?.published_build);
  const stored = persistence && (workspace?.published_build
    ? { destination: "Neo4j", ...workspace.published_build }
    : snapshot ? { destination: "Workspace snapshot", ...snapshot,
      ...snapshots.data?.find((item) => item.build_id === snapshot.build_id) } : undefined);
  const detail = result.data ?? step.result ?? (stored || undefined);
  return <>
    <h3 className="mb-2">Stage results</h3>
    <Feedback pending={(!detail && result.isFetching) || snapshots.isFetching} error={result.error ?? snapshots.error} />
    {detail ? <Report value={detail} /> : <p className="muted">Results appear when this stage produces an output.</p>}
    {children}
  </>;
}

function ExecutionEvents({ job, title }: { job?: Job | null; title: (stage: number) => string }) {
  const events = job?.events ?? [];
  const [severity, setSeverity] = useState("");
  const [stage, setStage] = useState("");
  const [search, setSearch] = useState("");
  const stages = [...new Set(events.flatMap((event) => event.stage === null ? [] : [event.stage]))];
  const filtered = events.filter((event) => (!severity || event.severity === severity) &&
    (!stage || String(event.stage) === stage) && event.message.toLowerCase().includes(search.trim().toLowerCase()));
  return <Accordion variant="outlined" disableGutters sx={accordion}>
    <AccordionSummary expandIcon={<ChevronDown size={17} />} aria-controls="build-events-content" id="build-events-heading">
      <strong>Execution events</strong><span className="muted ml-2">({events.length})</span>
    </AccordionSummary>
    <AccordionDetails>
      <div className="toolbar mb-3">
        <TextField size="small" select label="Event severity" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <MenuItem value="">All severities</MenuItem>
          {["info", "success", "warning", "error"].map((value) => <MenuItem key={value} value={value}>{value.toUpperCase()}</MenuItem>)}
        </TextField>
        <TextField size="small" select label="Event stage" value={stages.some((number) => String(number) === stage) ? stage : ""}
          onChange={(e) => setStage(e.target.value)}>
          <MenuItem value="">All stages</MenuItem>
          {stages.map((number) => <MenuItem key={number} value={String(number)}>{title(number)}</MenuItem>)}
        </TextField>
        <TextField size="small" label="Search execution messages" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      <div className="max-h-64 overflow-auto" aria-label="Timestamped execution events">
        {filtered.length ? <ol className="divide-y">
          {filtered.map(({ time, stage, severity, message }, index) => <li key={`${time}-${index}`} className="flex flex-wrap gap-2 py-2">
            <time dateTime={time} className="muted">{timestamp(time)}</time>
            <strong>{severity.toUpperCase()}</strong>
            <span>{stage === null ? "Build" : title(stage)}</span>
            <span>{message}</span>
          </li>)}
        </ol> : <p className="muted">{events.length ? "No matching events." : "No execution events recorded."}</p>}
      </div>
    </AccordionDetails>
  </Accordion>;
}

export function BuildMonitor({ id, pipeline, job, busy, workspace, selected, error, configuration, children }: {
  id: string;
  pipeline: BuildPipeline;
  job?: Job | null;
  busy: boolean;
  workspace?: Schema<"SessionView">;
  selected?: number;
  error?: unknown;
  configuration: ReactNode;
  children: (stage: number) => ReactNode;
}) {
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const first = pipeline.steps[0].stage;
  const definitions = [...pipeline.steps, pipeline.persistence];
  const title = (stage: number) => {
    const definition = definitions.find((item) => item.stage === stage);
    return definition ? buildStageTitle(definition, first) : "Pipeline stage";
  };
  const fallbackStep = (stage: number): BuildStep => {
    if (job?.stage === stage) {
      if (busy) return { stage, status: "running" };
      if (job.status === "interrupted") return { stage, status: "interrupted" };
      if (job.status === "blocked" || job.status === "failed") return { stage, status: "failed" };
    }
    return { stage, status: workspace?.completed_stages.includes(stage) ||
      (stage === pipeline.persistence.stage && !!(workspace?.snapshot || workspace?.published_build)) ? "completed" : "pending" };
  };
  const defaultSteps = pipeline.steps.map(({ stage }) => fallbackStep(stage));
  const summarySteps = job?.steps ?? defaultSteps;
  const steps = definitions.map(({ stage }) => summarySteps.find((item) => item.stage === stage) ?? fallbackStep(stage));
  const saved = workspace?.snapshot || workspace?.published_build;
  const validated = steps.find((step) => step.stage === pipeline.steps.at(-1)?.stage);
  const graph = validated?.result;
  const graphReady = !!workspace?.snapshot || workspace?.completed_stages.includes(14);
  const published = workspace?.published_build;
  const quality = pipeline.steps.find((step) => stageNavigation[step.stage]?.title === "Data Quality");
  const showCompletion = job?.status === "completed" && !!(graph || workspace?.completed_stages.includes(15) || saved);

  return <div className="flex flex-col gap-5">
    <BuildOverview job={job} busy={busy} stages={summarySteps} current={job?.stage ? title(job.stage) : undefined} />
    {configuration}
    <Feedback error={error} />
    {job?.status === "interrupted" && <Alert severity="warning">{job.error?.message ?? "The build was interrupted."}</Alert>}
    {job?.status === "failed" && !job.stage && <Alert severity="error">{job.error?.message ?? "The build could not start."}</Alert>}
    <Panel title="Pipeline stages">
      <div className="flex flex-col gap-2">
        {steps.map((step) => {
          const persistence = step.stage === pipeline.persistence.stage;
          const key = step.status === "failed" || step.status === "interrupted"
            ? `${job?.id}:${step.stage}:${step.status}` : String(step.stage);
          const expanded = overrides[key] ?? (step.stage === selected || step.status === "failed" || step.status === "interrupted");
          const name = title(step.stage);
          return <Accordion key={step.stage} expanded={expanded} disableGutters variant="outlined" sx={accordion}
            onChange={(_, open) => setOverrides((previous) => ({ ...previous, [key]: open }))}>
            <AccordionSummary expandIcon={<ChevronDown size={17} />} id={`pipeline-${step.stage}`} aria-controls={`pipeline-${step.stage}-details`}>
              <div className="flex w-full flex-wrap items-center gap-2 pr-2">
                <StepIcon status={step.status} />
                <strong>{name}</strong>
                {persistence && !summarySteps.some((item) => item.stage === step.stage) &&
                  <span className="muted">Separate action</span>}
                <span className="muted ml-auto">{statusLabels[step.status]} · {duration(step.duration_ms)}</span>
              </div>
            </AccordionSummary>
            <AccordionDetails>
              {(step.status === "failed" || step.status === "interrupted") && <Alert
                severity={step.status === "failed" ? "error" : "warning"} className="mb-3">
                {job?.error?.message ?? "This stage did not pass validation. Review its results before building again."}
              </Alert>}
              {step.status === "running" && job?.stage === step.stage && job.progress && <Report value={job.progress} />}
              {expanded && <StageDetails id={id} step={step} busy={busy} persistence={persistence} workspace={workspace}>
                {!persistence && step.stage !== selected && <Button component={Link} to={`/build/${step.stage}`}>Open {name}</Button>}
                {children(step.stage)}
              </StageDetails>}
            </AccordionDetails>
          </Accordion>;
        })}
      </div>
    </Panel>
    <ExecutionEvents key={job?.id ?? "none"} job={job} title={title} />
    {showCompletion && <Panel title="Build completion">
      <Report value={{
        nodes: graph?.nodes ?? workspace?.summary?.nodes,
        relationships: graph?.edges ?? workspace?.summary?.edges,
        ...(graph ? { entity_types: graph.nodes_by_class, relationship_types: graph.edges_by_type } : {}),
        ...(quality && steps.some((step) => step.stage === quality.stage && step.status === "completed")
          ? { data_quality: "Passed" } : {}),
        duration: duration(job.started_at && job.finished_at ? Date.parse(job.finished_at) - Date.parse(job.started_at) : undefined),
        storage: published ? "Published to Neo4j" : workspace?.snapshot ? "Snapshot saved"
          : graphReady ? "In workspace memory" : "Graph unavailable",
      }} />
      <div className="toolbar mt-3">
        {graphReady && <Button component={Link} to="/explorer">Explore Knowledge Graph</Button>}
        {!graphReady && published?.project_id && published.version_id && <Button component={Link}
          to={`/published-graphs?view=explorer&${new URLSearchParams({ project: published.project_id, version: published.version_id })}`}>
          Explore Knowledge Graph
        </Button>}
        {workspace?.completed_stages.includes(14) && <Button component={Link} to="/business-insights">View Business Insights</Button>}
        {quality && workspace?.completed_stages.includes(quality.stage) && <Button component={Link}
          to={`/build/${quality.stage}`}>View Quality Report</Button>}
        {workspace?.completed_stages.includes(15) && <Button component={Link} to="/storage">Go to Storage &amp; Snapshots</Button>}
      </div>
    </Panel>}
  </div>;
}
