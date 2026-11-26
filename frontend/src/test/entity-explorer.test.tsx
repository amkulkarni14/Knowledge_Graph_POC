import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { get } from "../api/client";
import EntityExplorer from "../features/query/EntityExplorer";

vi.mock("../api/client", () => ({ get: vi.fn() }));
vi.mock("../features/query/GraphCanvas", () => ({
  default: () => <div role="img" aria-label="Entity graph" />,
}));

it("disambiguates exact IDs, preserves snapshot scope and resets manual exploration", async () => {
  const supplier = { id: "Supplier:007", label: "Supplier", identifier: "007", display_name: "Supplier:007" };
  const bank = { id: "Bank:007", label: "Bank", identifier: "007", display_name: "Bank:007" };
  vi.mocked(get).mockImplementation(async (path, params) => {
    if (path.endsWith("/entities")) {
      return { types: ["Supplier", "Bank"], matches: params && "q" in params ? [supplier, bank] : [], truncated: false };
    }
    return {
      root: { id: supplier.id, identifier: supplier.identifier, properties: { label: supplier.label }, incoming: 0, outgoing: 0 },
      graph: { nodes: [{ id: supplier.id, properties: { label: supplier.label } }], edges: [], truncated: false },
      ontology: { name: "Supply Chain", version: 3, classes: [{ name: "Supplier" }], relationships: [] },
    };
  });
  const client = new QueryClient();
  const selection = { ontology_id: "supply-chain", build_id: "20261124T000000000000Z" };
  const user = userEvent.setup();
  render(<QueryClientProvider client={client}>
    <EntityExplorer path="/sessions/disposable/graphs" selection={selection}>
      <span>Manual graph controls</span>
    </EntityExplorer>
  </QueryClientProvider>);
  await user.click(screen.getByRole("combobox", { name: "Traversal Depth" }));
  await user.click(screen.getByRole("option", { name: "3 hops" }));
  await user.type(screen.getByRole("textbox", { name: "Entity ID" }), "007");
  await user.click(screen.getByRole("button", { name: "Search by ID" }));
  const results = within(await screen.findByLabelText("Matching entities"));
  expect(results.getByRole("button", { name: "Bank · 007" })).toBeVisible();
  await user.click(results.getByRole("button", { name: "Supplier · 007" }));
  expect(await screen.findByRole("img", { name: "Entity graph" })).toBeVisible();
  expect(screen.getByText("Supply Chain")).toBeVisible();
  expect(screen.getByText(/no relationships in the displayed neighborhood/i)).toBeVisible();
  expect(get).toHaveBeenCalledWith("/sessions/disposable/graphs/entity-neighborhood",
    { ...selection, node_id: "Supplier:007", hops: 3 }, expect.any(AbortSignal));
  expect(screen.queryByText("Manual graph controls")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Reset exploration" }));
  expect(screen.getByText("Manual graph controls")).toBeVisible();
});

it("inspects a directed relationship and collapses a connected-node expansion", async () => {
  const root = { id: "Supplier:007", properties: { label: "Supplier" } };
  const warehouse = { id: "Warehouse:009", properties: { label: "Warehouse" } };
  const shipment = { id: "Shipment:011", properties: { label: "Shipment" } };
  const edge = { key: "STORES", source: warehouse.id, target: root.id, properties: { type: "STORES", capacity: 12 } };
  const extension = { key: "SHIPS", source: warehouse.id, target: shipment.id, properties: { type: "SHIPS" } };
  vi.mocked(get).mockImplementation(async (path, params) => {
    if (path.endsWith("/entities")) return {
      types: ["Supplier", "Warehouse"], truncated: false,
      matches: params && "q" in params ? [{ ...root, label: "Supplier", identifier: "007", display_name: root.id }] : [],
    };
    const query = params as { node_id: string; hops: number };
    const current = query.node_id === warehouse.id ? warehouse : root;
    return {
      root: { ...current, identifier: current.id.split(":")[1], incoming: 1, outgoing: 0 },
      graph: {
        nodes: query.hops === 0 ? [current] : current === root ? [root, warehouse] : [warehouse, shipment],
        edges: query.hops === 0 ? [] : current === root ? [edge] : [extension],
        truncated: false,
      },
      ontology: { name: "Supply Chain", version: 3, classes: [{ name: "Supplier" }],
        relationships: [{ name: "STORES", source_class: "Warehouse", target_class: "Supplier" }] },
    };
  });
  const user = userEvent.setup();
  render(<QueryClientProvider client={new QueryClient()}>
    <EntityExplorer path="/graph-projects/project/versions/version" />
  </QueryClientProvider>);
  await user.type(screen.getByRole("textbox", { name: "Entity ID" }), "007");
  await user.click(screen.getByRole("button", { name: "Search by ID" }));
  await user.click(await screen.findByRole("combobox", { name: "Inspect relationship" }));
  await user.click(screen.getByRole("option", { name: "Warehouse:009 → Supplier:007 · STORES" }));
  expect(screen.getByText("Source → target")).toBeVisible();
  expect(screen.getByText("ontology definition")).toBeVisible();
  await user.click(screen.getByRole("combobox", { name: "Inspect entity" }));
  await user.click(screen.getByRole("option", { name: warehouse.id }));
  await user.click(screen.getByRole("button", { name: "Expand connected node" }));
  await user.click(screen.getByRole("combobox", { name: "Inspect entity" }));
  await screen.findByRole("option", { name: shipment.id });
  await user.keyboard("{Escape}");
  await user.click(screen.getByRole("button", { name: "Collapse expansion" }));
  await user.click(screen.getByRole("combobox", { name: "Inspect entity" }));
  expect(screen.queryByRole("option", { name: shipment.id })).toBeNull();
});
