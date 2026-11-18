import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./app/layout/AppShell";
import { useSessionStore } from "./app/store";
import { Feedback } from "./shared/ui/WorkspaceUi";
const Overview = lazy(() => import("./features/overview/OverviewPage"));
const Scope = lazy(() => import("./features/projects/ScopePage"));
const Sources = lazy(() => import("./features/sources/SourcesPage"));
const Metadata = lazy(() => import("./features/sources/MetadataPage"));
const Ontology = lazy(() => import("./features/ontology/OntologyPage"));
const Review = lazy(() => import("./features/ontology/ReviewPages"));
const Build = lazy(() => import("./features/build/BuildPage"));
const Storage = lazy(() => import("./features/build/StoragePage"));
const Explorer = lazy(() => import("./features/query/ExplorerPage"));
export function App() {
  const id = useSessionStore((s) => s.id);
  return (
    <AppShell>
      <Suspense fallback={<Feedback pending />}>
        <Routes>
          <Route path="/" element={<Overview />} />
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
                    element={<Review key={`${id}-${mode}`} mode={mode} />}
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
