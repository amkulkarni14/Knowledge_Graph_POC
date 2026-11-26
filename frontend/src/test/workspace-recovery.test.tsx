import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { expect, it, vi } from "vitest";
import OverviewPage from "../features/overview/OverviewPage";
import { sessionsApi } from "../api/sessionsApi";

vi.mock("../api/client", () => ({ get: vi.fn(async () => []), ApiError: class extends Error {} }));
vi.mock("../api/libraryApi", () => ({ useSavedOntologies: () => ({ data: [] }) }));
vi.mock("../api/sessionsApi", () => ({ sessionsApi: {
  workspaces: vi.fn(), reopen: vi.fn(), health: vi.fn(async () => ({ status: "ok" })),
} }));
vi.mock("../shared/hooks/useWorkspace", () => ({ useWorkspace: () => ({
  id: null, session: {}, done: [], can: () => false, workflow: { order: [2, 1, 8], groups: [] },
}) }));

it("reopens an inactive workspace before navigating to reconnect its source", async () => {
  const row = {
    id: "recovery-test", name: "Durable workspace", active: false, reconnect_required: true,
    completed_stages: [], source_version: 1, job: null, expires_in_seconds: 0,
    historical_stages: [1, 2, 8], updated_at: "2026-11-24T00:00:00Z",
  };
  vi.mocked(sessionsApi.workspaces).mockResolvedValue([row]);
  vi.mocked(sessionsApi.reopen).mockResolvedValue({ ...row, active: true, completed_stages: [1, 8] });
  render(<QueryClientProvider client={new QueryClient()}>
    <MemoryRouter><Routes>
      <Route path="/" element={<OverviewPage />} />
      <Route path="/sources" element={<h1>Source reconnection page</h1>} />
    </Routes></MemoryRouter>
  </QueryClientProvider>);
  expect(await screen.findByText("Durable workspace")).toBeVisible();
  expect(screen.getByText(/last completed stage ontology validation/i)).toBeVisible();
  expect(screen.getByText(/available to reopen/i)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Reconnect source" }));
  expect(await screen.findByRole("heading", { name: "Source reconnection page" })).toBeVisible();
  expect(sessionsApi.reopen).toHaveBeenCalledWith(row.id);
});
