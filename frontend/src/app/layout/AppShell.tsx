import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Alert } from "@mui/material";
import {
  Network,
  LayoutDashboard,
  Compass,
  PanelLeftClose,
  PanelLeftOpen,
  Activity,
  RotateCcw,
  ChartNoAxesCombined,
  Shapes,
  BadgeCheck,
  Workflow,
  HardDrive,
  BookOpen,
  ChevronDown,
  ChevronRight,
  LogOut,
} from "lucide-react";
import { useSessionStore, useUiStore, useGraphStore } from "../store";
import { useAuthStore } from "../authStore";
import {
  useSession,
  useData,
  useAction,
} from "../../shared/hooks/useWorkspace";
import { sessionsApi } from "../../api/sessionsApi";
import { authApi } from "../../api/authApi";
import { stageForPath, stageGroups, stageRoutes } from "../../constants/stages.constants";
import { Confirm, DataTable, Feedback } from "../../shared/ui/WorkspaceUi";
import { ApiError } from "../../api/client";
import { stageNavigation } from "../../constants/stageNavigation";
import { publishedTools } from "../../constants/publishedTools";
import { PageNavigation } from "./PageNavigation";
import { StageHelp } from "./StageHelp";
import { StageStepper } from "./StageStepper";

function titleForRoute(pathname: string) {
  if (pathname === "/") return "Home";
  if (pathname === "/domains") return "Domains";
  if (pathname === "/published-graphs") return "Published Graphs";
  if (pathname === "/explorer") return "Graph Explorer";
  if (pathname.startsWith("/build")) {
    const stage = Number(pathname.split("/")[2]) || 10;
    return stageNavigation[stage]?.title ?? "Graph Construction";
  }
  const stage = Number(
    Object.keys(stageRoutes).find((number) => stageRoutes[Number(number)] === pathname),
  );
  return stageNavigation[stage]?.title ?? pathname.slice(1).replaceAll("/", " / ");
}

function documentationUrl() {
  try {
    const base = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
    return new URL("/docs", new URL(base, window.location.origin)).toString();
  } catch {
    return undefined;
  }
}

export function AppShell({ children }: { children: ReactNode }) {
  const { collapsed, activity, collapsedGroups, toggleSidebar, toggleActivity, toggleGroup } = useUiStore();
  const id = useSessionStore((s) => s.id);
  const session = useSession();
  const client = useQueryClient();
  const location = useLocation();
  const graphView = new URLSearchParams(location.search).get("view");
  const adviceStage = stageForPath(location.pathname) ??
    (location.pathname === "/explorer" ? graphView === "path" ? 18 : graphView === "metrics" ? 19 : 17 : undefined);
  const [reset, setReset] = useState(false);
  const authUser = useAuthStore((s) => s.user?.username);
  async function signOut() {
    try {
      // Revoke the token server-side first; it is still attached to this request.
      await authApi.logout();
    } catch {
      /* already expired or backend unreachable: sign out locally regardless */
    } finally {
      // App clears the workspace and query cache when the token disappears.
      useAuthStore.getState().logout();
    }
  }
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
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => sessionsApi.health(signal),
    staleTime: 15000,
    retry: false,
  });
  const remove = useAction((sid) => sessionsApi.remove(sid), {
    invalidate: false,
  });
  async function close() {
    await remove.mutateAsync();
    void client.invalidateQueries({ queryKey: ["workspaces"] });
    await client.cancelQueries({ queryKey: ["workspace", id] });
    client.removeQueries({ queryKey: ["workspace", id] });
    useSessionStore.getState().setSession(null);
    useGraphStore.getState().reset();
    setReset(false);
  }
  const docs = documentationUrl();
  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside
        className={`sidebar ${collapsed ? "collapsed" : ""}`}
        aria-label="Main navigation"
      >
        <div className="brand" title="Knowledge Graph Studio">
          <Network size={27} />
          {!collapsed && <span className="brand-name">Knowledge Graph Studio</span>}
        </div>
        <nav className="sidebar-nav">
          {!collapsed && <div className="nav-group">Workspace</div>}
          <NavLink to="/" end className="nav-link" title="Home" aria-label="Home">
            <LayoutDashboard size={16} />
            {!collapsed && <span className="nav-text">Home</span>}
          </NavLink>
          <NavLink to="/domains" className="nav-link" title="Domains" aria-label="Domains">
            <Shapes size={16} />
            {!collapsed && <span className="nav-text">Domains</span>}
          </NavLink>
          <NavLink to="/published-graphs" className="nav-link" title="Published Graphs" aria-label="Published Graphs">
            <HardDrive size={16} />
            {!collapsed && <span className="nav-text">Published Graphs</span>}
          </NavLink>
          {publishedTools.map(({ view, label, icon: Icon }) => {
            const inPublishedWorkspace = location.pathname === "/published-graphs";
            const active = inPublishedWorkspace && graphView === view;
            const params = new URLSearchParams(inPublishedWorkspace ? location.search : "");
            params.set("view", view);
            if (view !== "explorer") params.delete("node");
            return (
              <Link key={view} to={{ pathname: "/published-graphs", search: params.toString() }}
                className={`nav-link nav-sub-link${active ? " active" : ""}`}
                title={label} aria-label={label} aria-current={active ? "page" : undefined}>
                <Icon size={15} />
                {!collapsed && <span className="nav-text">{label}</span>}
              </Link>
            );
          })}
          {id && stageGroups.map((group) => (
            <div key={group.title}>
              {!collapsed && (
                <button
                  className="nav-group nav-group-toggle"
                  aria-expanded={!collapsedGroups.includes(group.title)}
                  onClick={() => toggleGroup(group.title)}
                >
                  {collapsedGroups.includes(group.title) ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                  {group.title}
                </button>
              )}
              {(!collapsed && collapsedGroups.includes(group.title) ? [] : group.numbers)
                .map((stage) => {
                  const item = stageNavigation[stage];
                  if (!item) return null;
                  const Icon = item.icon;
                  const complete = session.data?.completed_stages.includes(stage) ?? false;
                  return (
                    <NavLink
                      to={stageRoutes[stage]}
                      key={stage}
                      className="nav-link"
                      title={item.title}
                      aria-label={item.title}
                    >
                      <Icon className="nav-icon" size={15} />
                      {!collapsed && (
                        <>
                          <span className="nav-text">{item.title}</span>
                          {complete && <BadgeCheck className="nav-status" size={14} aria-label="Completed" />}
                        </>
                      )}
                    </NavLink>
                  );
                })}
            </div>
          ))}
          {id && !collapsed && (
            <button
              className="nav-group nav-group-toggle"
              aria-expanded={!collapsedGroups.includes("Graph Intelligence")}
              onClick={() => toggleGroup("Graph Intelligence")}
            >
              {collapsedGroups.includes("Graph Intelligence") ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
              Graph Intelligence
            </button>
          )}
          {id && (collapsed || !collapsedGroups.includes("Graph Intelligence")) && (
            <>
              <NavLink to="/explorer" end className={({ isActive }) => `nav-link ${isActive && graphView !== "path" && graphView !== "metrics" ? "active" : ""}`} title="Graph Explorer" aria-label="Graph Explorer">
                <Compass size={16} />
                {!collapsed && <span className="nav-text">Graph Explorer</span>}
              </NavLink>
              <NavLink to="/explorer?view=path" className={({ isActive }) => `nav-link nav-sub-link ${isActive && graphView === "path" ? "active" : ""}`} title="Path Analysis" aria-label="Path Analysis">
                <Workflow size={15} />
                {!collapsed && <span className="nav-text">Path Analysis</span>}
              </NavLink>
              <NavLink to="/explorer?view=metrics" className={({ isActive }) => `nav-link nav-sub-link ${isActive && graphView === "metrics" ? "active" : ""}`} title="Graph Metrics" aria-label="Graph Metrics">
                <ChartNoAxesCombined size={15} />
                {!collapsed && <span className="nav-text">Graph Metrics</span>}
              </NavLink>
            </>
          )}
        </nav>
        {stages.error && <Feedback error={stages.error} />}
        <div className="sidebar-footer">
          <div className="connection-row" title={health.isError ? "API disconnected" : health.data ? "API connected" : "Checking API connection"}>
            <span className={`connection-dot ${health.isError ? "disconnected" : health.data ? "connected" : ""}`} />
            {!collapsed && <span className="footer-label">{health.isError ? "API disconnected" : health.data ? "API connected" : "Connecting to API…"}</span>}
          </div>
          {docs && (
            <a className="nav-link" href={docs} target="_blank" rel="noreferrer" title="API documentation" aria-label="API documentation">
              <BookOpen size={15} />
              {!collapsed && <span className="nav-text">API documentation</span>}
            </a>
          )}
          <button className="nav-link sidebar-collapse" onClick={toggleSidebar} title={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
            {!collapsed && <span className="nav-text">Collapse sidebar</span>}
          </button>
        </div>
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
            <div className="topbar-context" aria-label="Breadcrumb">
              <span className="breadcrumb-muted">Workspace</span>
              <span aria-hidden="true">/</span>
              <strong>{titleForRoute(location.pathname)}</strong>
            </div>
          </div>
          <div className="topbar-right">
            {id && adviceStage && <StageHelp key={`${id}/${adviceStage}`} id={id} stage={adviceStage} />}
            {id && <span className="workspace-badge" title={session.data?.name}>{session.data?.name ?? "Loading workspace…"}</span>}
            <span className="topbar-divider" />
            {docs && <a className="icon-button" href={docs} target="_blank" rel="noreferrer" aria-label="API documentation" title="API documentation"><BookOpen size={16} /></a>}
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
            <button
              className="icon-button"
              aria-label="Sign out"
              title="Sign out"
              onClick={() => void signOut()}
            >
              <LogOut size={16} />
            </button>
            <span className="workspace-badge">{authUser}</span>
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
        <PageNavigation workspace={session.data} />
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
