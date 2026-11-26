import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { sessionsApi } from "../api/sessionsApi";
import OverviewPage from "../features/overview/OverviewPage";
import type { Schema } from "../types/common.types";

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(),
  get: vi.fn().mockResolvedValue([]),
}));

afterEach(() => vi.restoreAllMocks());

it("requires the exact name, supports cancel, and refreshes Home after deletion", async () => {
  const workspace: Schema<"SessionView"> = {
    id: "disposable", name: "Sales Workspace", completed_stages: [], active: false,
    reconnect_required: false, source_version: 0, expires_in_seconds: 0, job: null,
  };
  let inventory = [workspace];
  let rejectDeletion!: (error: Error) => void;
  const list = vi.spyOn(sessionsApi, "workspaces").mockImplementation(async () => inventory);
  const remove = vi.spyOn(sessionsApi, "deleteWorkspace")
    .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectDeletion = reject; }))
    .mockImplementation(async () => { inventory = []; });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const user = userEvent.setup();
  render(<QueryClientProvider client={client}>
    <MemoryRouter><OverviewPage /></MemoryRouter>
  </QueryClientProvider>);

  const action = await screen.findByRole("button", { name: "Delete workspace Sales Workspace" });
  await user.click(action);
  const dialog = within(screen.getByRole("dialog", { name: "Delete Workspace" }));
  const confirm = dialog.getByRole("button", { name: "Delete Workspace" });
  expect(confirm).toBeDisabled();
  await user.type(dialog.getByRole("textbox"), "sales workspace");
  expect(confirm).toBeDisabled();
  await user.click(dialog.getByRole("button", { name: "Cancel" }));
  expect(remove).not.toHaveBeenCalled();

  await user.click(action);
  expect(dialog.getByRole("textbox")).toHaveValue("");
  await user.type(dialog.getByRole("textbox"), workspace.name);
  await user.click(confirm);
  await waitFor(() => expect(confirm).toBeDisabled());
  expect(dialog.getByRole("button", { name: "Cancel" })).toBeDisabled();
  await act(async () => rejectDeletion(new Error("Workspace is busy")));
  expect(await dialog.findByText("Workspace is busy")).toBeVisible();
  await user.click(confirm);
  expect(await screen.findByText("Workspace “Sales Workspace” deleted.")).toBeVisible();
  expect(remove).toHaveBeenCalledWith(workspace.id);
  await waitFor(() => expect(list.mock.calls.length).toBeGreaterThan(1));
  expect(screen.queryByRole("button", { name: "Delete workspace Sales Workspace" })).toBeNull();
});
