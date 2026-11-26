import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { sourcesApi } from "../api/workflowApi";
import { useSessionStore } from "../app/store";
import SourcesPage from "../features/sources/SourcesPage";
import { guidedSources, labels, type ConnectorId, type ConnectorSpec } from "../features/sources/guidedSources";

vi.mock("../shared/hooks/useWorkspace", async (original) => ({
  ...await original<typeof import("../shared/hooks/useWorkspace")>(),
  useWorkspace: () => ({ id: "test-workspace", can: () => true, done: [], session: {} }),
}));

const manifest = Object.fromEntries(Object.keys(labels).map((id) => [
  id, { required: [`${id}_field`], authentication: {} },
])) as Record<ConnectorId, ConnectorSpec>;

beforeEach(() => {
  vi.restoreAllMocks();
  useSessionStore.getState().setSession("test-workspace");
  vi.spyOn(guidedSources, "types").mockResolvedValue(manifest);
  vi.spyOn(guidedSources, "candidate").mockResolvedValue(null);
});

function mount() {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>
    <MemoryRouter><SourcesPage /></MemoryRouter>
  </QueryClientProvider>);
}

const input = () => screen.getByRole("combobox", { name: "Select data source" });
const field = (id: ConnectorId) => new RegExp(`${id}_field`);

it("starts empty and displays each selected connector with its configuration", async () => {
  vi.spyOn(sourcesApi, "read").mockResolvedValue({});
  const user = userEvent.setup();
  mount();
  await waitFor(() => expect(input()).toBeEnabled());
  expect(input()).toHaveValue("");
  expect(screen.queryByLabelText("Connection name")).toBeNull();
  async function choose(option: string) {
    await user.click(input());
    await user.click(screen.getByRole("option", { name: option }));
  }
  for (const kind of ["sample", "csv", "postgres", "mssql", "oracle"] as const) {
    await choose(labels[kind]);
    expect(input()).toHaveValue(labels[kind]);
    if (kind === "sample") expect(screen.getByRole("button", { name: "Connect retail sample" })).toBeVisible();
    else if (kind === "csv") expect(screen.getByRole("button", { name: "Analyze and connect files" })).toBeVisible();
    else expect(screen.getByLabelText(field(kind))).toBeVisible();
  }
  for (const [family, first, next] of [
    ["Amazon Web Services", "s3", "postgres"],
    ["Microsoft Azure", "azure_blob", "azure_adls"],
    ["Google Cloud Platform", "gcs", "bigquery"],
  ] as const) {
    await choose(family);
    expect(input()).toHaveValue(labels[first]);
    expect(screen.getByLabelText(field(first))).toBeVisible();
    await user.click(screen.getByRole("combobox", { name: "Cloud service" }));
    await user.click(screen.getByRole("option", {
      name: next === "postgres" ? "Amazon RDS PostgreSQL" : labels[next],
    }));
    await waitFor(() => expect(input()).toHaveValue(labels[next]));
    expect(screen.getByLabelText(field(next))).toBeVisible();
    expect(screen.queryByLabelText(field(first))).toBeNull();
  }
}, 20000);

it("restores a saved connector on fresh mounts and ignores invalid saved values", async () => {
  const read = vi.spyOn(sourcesApi, "read").mockResolvedValue({ mode: "bigquery" });
  for (let attempt = 0; attempt < 2; attempt++) {
    const view = mount();
    await waitFor(() => expect(input()).toHaveValue(labels.bigquery));
    expect(await screen.findByLabelText(field("bigquery"))).toBeVisible();
    view.unmount();
  }
  for (const mode of [null, undefined, { label: "PostgreSQL" }, "toString", "unrecognized"]) {
    read.mockResolvedValue({ mode });
    const view = mount();
    await waitFor(() => expect(input()).toBeEnabled());
    expect(input()).toHaveValue("");
    expect(screen.queryByLabelText(/Connection name/)).toBeNull();
    view.unmount();
  }
}, 20000);
