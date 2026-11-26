import {
  stageForPath,
  stageOrder,
  stageRoutes,
} from "./constants/stages.constants";
import { useWorkflowStages } from "./shared/hooks/useWorkflowStages";
import { lazy, Suspense, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "./app/layout/AppShell";
import { useGraphStore, useSessionStore } from "./app/store";
import { useAuthStore } from "./app/authStore";
import { authApi } from "./api/authApi";
import { LoginPage } from "./features/auth/LoginPage";
import { Feedback } from "./shared/ui/WorkspaceUi";
const Overview = lazy(() => import("./features/overview/OverviewPage"));
const Domains = lazy(() => import("./features/projects/DomainsPage"));
const Scope = lazy(() => import("./features/projects/ScopePage"));
const Sources = lazy(() => import("./features/sources/SourcesPage"));
const Metadata = lazy(() => import("./features/sources/MetadataPage"));
const Ontology = lazy(() => import("./features/ontology/OntologyPage"));
const Review = lazy(() => import("./features/ontology/ReviewPages"));
const Build = lazy(() => import("./features/build/BuildPage"));
const Storage = lazy(() => import("./features/build/StoragePage"));
const Explorer = lazy(() => import("./features/query/ExplorerPage"));
const BusinessInsights = lazy(() => import("./features/query/BusinessInsightsPage"));
const PublishedGraphs = lazy(
  () => import("./features/query/PublishedGraphsPage"),
);
export function App() {
  const token = useAuthStore((s) => s.token);
  const client = useQueryClient();
  // Whenever the session ends (sign-out, expired token, 401) drop all per-user state.
  useEffect(() => {
    if (token) return;
    useSessionStore.getState().setSession(null);
    useGraphStore.getState().reset();
    client.clear();
  }, [token, client]);
  if (!token) return <LoginPage />;
  return <AuthGate token={token} />;
}

// Validates a stored token with the backend before showing the workspace, so a
// refresh with an expired or revoked token lands on the login page, not a broken app.
function AuthGate({ token }: { token: string }) {
  const me = useQuery({
    queryKey: ["auth", "me", token],
    queryFn: ({ signal }) => authApi.me(signal),
    staleTime: Infinity,
    retry: false,
  });
  if (me.isPending) return <Feedback pending />;
  // A 401 has already cleared the token (client.ts). Other failures such as an
  // unreachable backend fall through to the workspace, which reports them itself.
  return <Workspace />;
}

function Workspace() {
  const id = useSessionStore((s) => s.id);
  const workflow = useWorkflowStages();
  function ontologyStage(mode: string) {
    if (workflow.query.isPending) return <Feedback pending />;
    if (workflow.query.isError) return <Navigate to="/" replace />;
    const stage = stageForPath(`/${mode}`)!;
    if (workflow.enabled(stage))
      return <Review key={`${id}-${mode}`} mode={mode} />;
    const previous = stageOrder
      .slice(0, stageOrder.indexOf(stage))
      .filter(workflow.enabled)
      .at(-1);
    return (
      <Navigate
        key={mode}
        to={previous ? stageRoutes[previous] : "/"}
        replace
      />
    );
  }
  return (
    <AppShell>
      <Suspense fallback={<Feedback pending />}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/domains" element={<Domains />} />
          <Route path="/published-graphs" element={<PublishedGraphs />} />
          <Route path="/business-insights" element={<BusinessInsights />} />
          {id && (
            <>
              <Route path="/scope" element={<Scope />} />
              <Route path="/sources" element={<Sources />} />
              <Route path="/metadata" element={<Metadata />} />
              <Route path="/analysis" element={<Metadata analysis />} />
              <Route path="/ontology" element={<Ontology key={id} />} />
              {["suggestions", "review", "validation", "repository"].map(
                (mode) => (
                  <Route
                    key={mode}
                    path={`/${mode}`}
                    element={ontologyStage(mode)}
                  />
                ),
              )}
              <Route path="/build" element={<Build />} />
              <Route path="/build/:stage" element={<Build />} />
              <Route path="/storage" element={<Storage />} />
              <Route path="/explorer" element={<Explorer key={id} />} />
            </>
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AppShell>
  );
}
