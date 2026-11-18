import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Alert } from "@mui/material";
import {
  Network,
  LayoutDashboard,
  Compass,
  PanelLeftClose,
  PanelLeftOpen,
  Activity,
  Check,
  RotateCcw,
} from "lucide-react";
import { useSessionStore, useUiStore, useGraphStore } from "../store";
import {
  useSession,
  useData,
  useAction,
} from "../../shared/hooks/useWorkspace";
import { sessionsApi } from "../../api/sessionsApi";
import { stageRoutes } from "../../constants/stages.constants";
import { Confirm, DataTable, Feedback } from "../../shared/ui/WorkspaceUi";
import { ApiError } from "../../api/client";
import { StageStepper } from "./StageStepper";
export function AppShell({ children }: { children: ReactNode }) {
  const { collapsed, activity, toggleSidebar, toggleActivity } = useUiStore();
  const id = useSessionStore((s) => s.id);
  const session = useSession();
  const client = useQueryClient();
  const location = useLocation();
  const [reset, setReset] = useState(false);
  useEffect(() => {
    if (
      session.error instanceof ApiError &&
      session.error.code === "session_not_found" &&
      id
    ) {
      void client.cancelQueries({ queryKey: ["workspace", id] });
      client.removeQueries({ queryKey: ["workspace", id] });
      useSessionStore
        .getState()
        .setSession(
          null,
          "Your session has expired. Create a new workspace to continue.",
        );
      useGraphStore.getState().reset();
    }
  }, [session.error, id, client]);
  const stages = useQuery({
    queryKey: ["stages"],
    queryFn: ({ signal }) => sessionsApi.stages(signal),
    staleTime: Infinity,
  });
  const events = useData(
    ["events"],
    (signal) => sessionsApi.events(id!, 0, signal),
    activity,
  );
  const remove = useAction((sid) => sessionsApi.remove(sid), {
    invalidate: false,
  });
  async function close() {
    await remove.mutateAsync();
    await client.cancelQueries({ queryKey: ["workspace", id] });
    client.removeQueries({ queryKey: ["workspace", id] });
    useSessionStore.getState().setSession(null);
    useGraphStore.getState().reset();
    setReset(false);
  }
  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside
        className={`sidebar ${collapsed ? "collapsed" : ""}`}
        aria-label="Main navigation"
      >
        <div className="brand">
          <Network size={27} />
          {!collapsed && (
            <span className="brand-name">
              Knowledge Graph
              <span className="block text-[10px] font-normal tracking-widest text-slate-400 mt-1">
                ENTERPRISE STUDIO
              </span>
            </span>
          )}
        </div>
        <NavLink to="/" className="nav-link" title="Overview">
          <LayoutDashboard size={17} />
          {!collapsed && <span className="nav-text">Overview</span>}
        </NavLink>
        {["A", "B", "C"].map((part, index) => (
          <div key={part}>
            {!collapsed && (
              <div className="nav-group">
                {
                  [
                    "Data & metadata",
                    "Ontology engineering",
                    "Graph construction",
                  ][index]
                }
              </div>
            )}
            {stages.data
              ?.filter((s) => (s.no === 10 ? "C" : s.part) === part)
              .map((s) => (
                <NavLink
                  to={stageRoutes[s.no]}
                  key={s.no}
                  className="nav-link"
                  title={s.title}
                  aria-label={`${String(s.no).padStart(2, "0")} ${s.title}`}
                >
                  <span className="nav-number">
                    {String(s.no).padStart(2, "0")}
                  </span>
                  {!collapsed && (
                    <>
                      <span className="nav-text">{s.title}</span>
                      {session.data?.completed_stages.includes(s.no) && (
                        <Check className="nav-check" size={13} />
                      )}
                    </>
                  )}
                </NavLink>
              ))}
          </div>
        ))}
        {!collapsed && <div className="nav-group">Explore</div>}
        <NavLink to="/explorer" className="nav-link" title="Graph explorer">
          <Compass size={17} />
          {!collapsed && <span className="nav-text">Graph Explorer</span>}
        </NavLink>
        <Feedback error={stages.error} />
      </aside>
      <div className={`shell-main ${collapsed ? "wide" : ""}`}>
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button"
              aria-label="Toggle navigation"
              onClick={toggleSidebar}
            >
              {collapsed ? (
                <PanelLeftOpen size={18} />
              ) : (
                <PanelLeftClose size={18} />
              )}
            </button>
            <span className="breadcrumb">
              Workspace /{" "}
              {location.pathname === "/"
                ? "Overview"
                : location.pathname.slice(1).replaceAll("/", " / ")}
            </span>
          </div>
          <div className="topbar-right">
            <span className="workspace-badge">
              {session.data?.name ?? "No active workspace"}
            </span>
            <button
              className="icon-button"
              aria-label="Toggle activity log"
              onClick={toggleActivity}
            >
              <Activity size={18} />
            </button>
            {id && (
              <button
                className="icon-button"
                aria-label="Reset workspace"
                onClick={() => setReset(true)}
              >
                <RotateCcw size={16} />
              </button>
            )}
          </div>
        </header>
        {id && stages.data && (
          <StageStepper
            stages={stages.data}
            completed={session.data?.completed_stages ?? []}
          />
        )}
        <main id="main" className="main-content">
          {session.error && (
            <Alert
              severity="error"
              action={
                <Button
                  onClick={() => {
                    useSessionStore.getState().setSession(null);
                    client.removeQueries({ queryKey: ["workspace", id] });
                  }}
                >
                  Close workspace
                </Button>
              }
            >
              {session.error.message}
            </Alert>
          )}
          {children}
        </main>
        {activity && (
          <section className="activity-panel" aria-label="Activity log">
            <div className="panel-heading">
              <h2>Activity log</h2>
              <Button size="small" onClick={() => events.refetch()}>
                Refresh
              </Button>
            </div>
            <Feedback pending={events.isFetching} error={events.error} />
            <DataTable rows={events.data?.items ?? []} />
          </section>
        )}
      </div>
      <Confirm
        open={reset}
        title="Reset this workspace?"
        onClose={() => setReset(false)}
        onConfirm={() => void close()}
        pending={remove.isPending}
      >
        <p>
          This closes the current session and clears the workspace. Deleted
          sessions cannot be restored.
        </p>
        <Feedback error={remove.error} />
      </Confirm>
    </div>
  );
}
