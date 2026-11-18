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
import { stageRoutes } from "../../constants/stages.constants";
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
        <div className="intro-icon">
          <Network size={31} />
        </div>
        <PageHeader
          eyebrow="ENTERPRISE KNOWLEDGE GRAPH"
          title="Connect data. Build understanding."
          description="Bring your sources, ontology, and graph together in one guided workspace. Start with the built-in retail sample or connect your own data."
        />
        <Panel title="Create your workspace">
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
              Sessions expire after inactivity. Keep this tab open while
              working. A server restart ends active sessions.
            </p>
          </form>
        </Panel>
        <div className="section-gap">
          <Feedback error={health.error} />
          {health.data && <StatusChip done>API connected</StatusChip>}
        </div>
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[
          {
            title: "Workflow progress",
            value: `${done.length} / 16`,
            detail: "Stages completed",
            icon: GitBranch,
          },
          {
            title: "Data sources",
            value: done.includes(2) ? "Connected" : "Not connected",
            detail: "Session-specific connection",
            icon: Database,
          },
          {
            title: "Ontology",
            value: done.includes(9)
              ? "Approved"
              : done.includes(5)
                ? "Draft"
                : "Not started",
            detail: "Review and approval required",
            icon: Shapes,
          },
        ].map((m) => (
          <Panel
            title={m.title}
            key={m.title}
            action={<m.icon size={17} className="text-slate-400" />}
          >
            <div className="metric">{m.value}</div>
            <p className="muted">{m.detail}</p>
          </Panel>
        ))}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-5">
        <Panel
          title="Your workflow"
          action={<StatusChip>{session.data?.name}</StatusChip>}
        >
          {stages.data?.map((s) => (
            <Link className="stage-item" to={stageRoutes[s.no]} key={s.no}>
              <span
                className={`stage-icon ${done.includes(s.no) ? "done" : ""}`}
              >
                {done.includes(s.no) ? (
                  <Check size={14} />
                ) : (
                  String(s.no).padStart(2, "0")
                )}
              </span>
              <span className="stage-label">{s.title}</span>
              <span className="muted">
                {done.includes(s.no) ? "Complete" : "Open"}
              </span>
              <ArrowRight size={13} />
            </Link>
          ))}
        </Panel>
        <div className="flex flex-col gap-5">
          <Panel title="Start with sample data">
            <p className="muted mb-4">
              Define your scope, select the built-in retail source, and follow
              each stage. AI suggestions can use the offline fixture or be
              skipped. Review and approval remain explicit.
            </p>
            <Button component={Link} to="/scope" variant="outlined">
              Open scope definition
            </Button>
          </Panel>
          <Panel title="Workspace details">
            <div className="report-row">
              <span>Session</span>
              <code className="text-[10px] break-all">{id}</code>
            </div>
            <div className="report-row">
              <span>Idle expiration</span>
              <strong>
                {session.data?.expires_in_seconds ?? 3600} seconds
              </strong>
            </div>
            <p className="muted mt-3">
              This is a temporary workflow session. Saved artifacts are managed
              by the backend.
            </p>
          </Panel>
        </div>
      </div>
    </>
  );
}
