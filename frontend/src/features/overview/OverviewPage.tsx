import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, TextField } from "@mui/material";
import {
  Network,
  ArrowRight,
  Check,
  Database,
  Shapes,
  GitBranch,
  Compass,
  ScanSearch,
  ChartNoAxesCombined,
  Sparkles,
  ClipboardCheck,
  BadgeCheck,
  History,
  ListChecks,
  Rows3,
  ShieldCheck,
  Workflow,
  HardDrive,
  type LucideIcon,
} from "lucide-react";
import { sessionsApi } from "../../api/sessionsApi";
import { useSessionStore } from "../../app/store";
import { useWorkspace } from "../../shared/hooks/useWorkspace";
import {
  PageHeader,
  Panel,
  Feedback,
  StatusChip,
} from "../../shared/ui/WorkspaceUi";
import { prerequisites, stageRoutes } from "../../constants/stages.constants";

const stageIcons: Record<number, LucideIcon> = {
  1: Compass,
  2: Database,
  3: ScanSearch,
  4: ChartNoAxesCombined,
  5: Shapes,
  6: Sparkles,
  7: ClipboardCheck,
  8: BadgeCheck,
  9: History,
  10: ListChecks,
  11: Rows3,
  12: ShieldCheck,
  13: Workflow,
  14: Network,
  15: BadgeCheck,
  16: HardDrive,
};

const stageTitles: Record<number, string> = {
  1: "Goal & Scope",
  2: "Data Sources",
  3: "Schema Extraction",
  4: "Schema Analysis",
  5: "Ontology Studio",
  6: "AI Suggestions",
  7: "Review & Approval",
  8: "Ontology Validation",
  9: "Ontology Versioning",
  10: "Build Plan",
  11: "Data Extraction",
  12: "Data Quality",
  13: "Cleaning & Entity Resolution",
  14: "Graph Construction",
  15: "Graph Validation",
  16: "Storage & Snapshots",
};

const lifecycle = [
  { title: "Data Sources", icon: Database },
  { title: "Metadata", icon: ScanSearch },
  { title: "Ontology", icon: Shapes },
  { title: "Graph Construction", icon: Network },
  { title: "Exploration", icon: Compass },
];

export default function OverviewPage() {
  const [name, setName] = useState("Knowledge workspace");
  const { id, session, done } = useWorkspace();
  const notice = useSessionStore((s) => s.notice);
  const stages = useQuery({
    queryKey: ["stages"],
    queryFn: ({ signal }) => sessionsApi.stages(signal),
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => sessionsApi.health(signal),
  });
  const create = useMutation({
    mutationFn: () => sessionsApi.create({ name: name.trim() }),
    onSuccess: (s) => useSessionStore.getState().setSession(s.id),
    gcTime: 0,
  });
  if (!id)
    return (
      <div className="empty-workspace">
        {notice && (
          <Alert severity="info" className="mb-5">
            {notice}
          </Alert>
        )}
        <div className="creation-lifecycle" aria-label="Knowledge graph workflow">
          {lifecycle.map(({ title, icon: Icon }, index) => (
            <span className="lifecycle-step" key={title}>
              <Icon size={15} />
              <span>{title}</span>
              {index < lifecycle.length - 1 && <span className="lifecycle-connector" aria-hidden="true" />}
            </span>
          ))}
        </div>
        <div className="creation-heading">
          <div className="intro-icon">
            <Network size={23} />
          </div>
          <PageHeader
            eyebrow="KNOWLEDGE GRAPH WORKSPACE"
            title="Create your knowledge workspace"
            description="Connect data sources, define an ontology, and build a knowledge graph through a guided workflow."
          />
        </div>
        <Panel title="Workspace details">
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <TextField
              label="Workspace name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              slotProps={{ htmlInput: { maxLength: 200 } }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={create.isPending || !name.trim()}
              endIcon={<ArrowRight size={16} />}
            >
              Create workspace
            </Button>
            <Feedback pending={create.isPending} error={create.error} />
            <p className="muted">
              Sessions expire after inactivity. Keep this browser session open;
              restarting the backend ends active sessions.
            </p>
          </form>
        </Panel>
        <Feedback error={health.error} />
      </div>
    );
  const next = stages.data?.find((s) => !done.includes(s.no));
  return (
    <>
      <PageHeader
        title="Workspace overview"
        description="Turn source data into a reviewed, validated knowledge graph. Every stage uses your live workspace state."
        action={
          <Button
            component={Link}
            to={next ? stageRoutes[next.no] : "/explorer"}
            variant="contained"
            endIcon={<ArrowRight size={16} />}
          >
            {next ? "Continue workflow" : "Explore graph"}
          </Button>
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        {[
          {
            title: "Workflow progress",
            value: `${done.length} / ${stages.data?.length ?? 16}`,
            detail: "Workflow stages completed",
            icon: GitBranch,
          },
          {
            title: "Data sources",
            value: done.includes(2) ? "Connected" : "Not connected",
            detail: done.includes(2) ? "Source stage completed" : "Connect a source to continue",
            icon: Database,
          },
          {
            title: "Ontology",
            value: done.includes(9)
              ? "Approved"
              : done.includes(5)
                ? "Draft"
                : "Not started",
            detail: done.includes(9) ? "Approved ontology available" : "Review and approval required",
            icon: Shapes,
          },
        ].map((m) => (
          <Panel
            title={m.title}
            key={m.title}
            action={<m.icon size={17} className="text-slate-400" />}
          >
            <div className={`metric ${m.title === "Workflow progress" ? "metric-compact" : ""}`}>{m.value}</div>
            <p className="muted">{m.detail}</p>
          </Panel>
        ))}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-5">
        <Panel
          title="Your workflow"
          action={<StatusChip>{session.data?.name ?? "Active workspace"}</StatusChip>}
        >
          <div className="workflow-list">
            {stages.data?.map((s) => {
              const Icon = stageIcons[s.no] ?? Workflow;
              const complete = done.includes(s.no);
              const blocked = !complete && !(prerequisites[s.no] ?? []).every((n) => done.includes(n));
              const status = complete ? "Completed" : blocked ? "Blocked" : "Pending";
              return (
                <Link className="stage-item" to={stageRoutes[s.no]} key={s.no}>
                  <span className={`stage-icon ${complete ? "done" : ""}`} aria-hidden="true">
                    {complete ? <Check size={14} /> : <Icon size={14} />}
                  </span>
                  <span className="stage-label">{stageTitles[s.no] ?? s.title}</span>
                  <span className={`status-pill ${complete ? "success" : blocked ? "blocked" : "pending"}`}>
                    {status}
                  </span>
                  <ArrowRight size={13} aria-hidden="true" />
                </Link>
              );
            })}
          </div>
        </Panel>
        <div className="flex flex-col gap-5">
          <Panel title="Start with sample data" action={<Database size={16} className="text-slate-400" />}>
            <p className="muted mb-4">
              Start by defining your scope, then choose the built-in retail
              sample or connect your own source. AI suggestions can be skipped;
              ontology review and approval remain explicit.
            </p>
            <Button component={Link} to={next ? stageRoutes[next.no] : "/explorer"} variant="outlined" endIcon={<ArrowRight size={15} />}>
              {next ? "Continue workflow" : "Explore graph"}
            </Button>
          </Panel>
          <Panel title="Workspace details">
            <div className="report-row">
              <span>Session</span>
              <code className="text-[10px] break-all">{id}</code>
            </div>
            <div className="report-row">
              <span>Session expires in</span>
              <strong>{session.data?.expires_in_seconds != null ? `${session.data.expires_in_seconds} seconds` : "Unavailable"}</strong>
            </div>
            <p className="muted mt-3">
              This is a temporary workflow session. Saved graph artifacts are
              managed by the backend.
            </p>
          </Panel>
        </div>
      </div>
    </>
  );
}
