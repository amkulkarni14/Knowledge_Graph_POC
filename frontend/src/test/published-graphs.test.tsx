import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { get, send } from "../api/client";
import PublishedGraphsPage from "../features/query/PublishedGraphsPage";

vi.mock("../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/client")>()),
  get: vi.fn(),
  send: vi.fn(),
}));
vi.mock("../features/query/GraphCanvas", () => ({
  default: () => <div aria-label="Test graph canvas" />,
}));

const project = "10f96b60-33a7-4720-8bfd-c2b03ae2d98e";
const version = "6df4e49b-fec1-4c94-9c60-eec45a7ae82f";
const path = `/graph-projects/${project}/versions/${version}`;

function open(view: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/published-graphs?view=${view}`]}>
        <PublishedGraphsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("published graph workspace", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(get).mockImplementation(async (url) => {
      if (url === "/graph-projects")
        return [
          { project_id: project, name: "Retail", current_build_id: version },
        ];
      if (url.endsWith("/versions"))
        return {
          current: version,
          can_manage: false,
          versions: [{ build_id: version, status: "ready" }],
        };
      if (url.endsWith("/workspace-items")) return [];
      if (url.endsWith("/entities")) return { types: ["Order"], matches: [], truncated: false };
      if (url.endsWith("/query"))
        return {
          template: "entities",
          duration_ms: 8,
          rows: [{ id: "Order:1001", properties: { label: "Order" } }],
        };
      if (url.endsWith("/neighborhood"))
        return {
          nodes: [{ id: "Order:1001", properties: { label: "Order" } }],
          edges: [],
          total_nodes: 1,
          total_edges: 0,
          truncated: false,
        };
      throw new Error("Unexpected API call");
    });
  });

  it("loads an entity and requests its bounded two-hop neighborhood", async () => {
    const user = userEvent.setup();
    open("explorer");
    await user.click(await screen.findByRole("button", { name: /^Search$/ }));
    await user.click(await screen.findByRole("button", { name: "Order:1001" }));
    await screen.findByLabelText("Test graph canvas");
    await user.click(screen.getByRole("button", { name: "Expand two hops" }));
    await waitFor(() =>
      expect(get).toHaveBeenCalledWith(
        path + "/neighborhood",
        { node_id: "Order:1001", hops: 2, kind: "" },
        expect.any(AbortSignal),
      ),
    );
  });

  it("submits an editable Cypher statement scoped to the selected version", async () => {
    const user = userEvent.setup();
    const cypher = "MATCH (o:Order) RETURN o LIMIT 1";
    vi.mocked(send).mockResolvedValue({
      template: "cypher",
      rows: [{ o: { id: "Order:1001", properties: {} } }],
      duration_ms: 12,
    });
    open("query");
    await user.click(
      await screen.findByRole("textbox", { name: "Cypher statement" }),
    );
    await user.paste(cypher);
    await user.click(screen.getByRole("button", { name: "Run query" }));
    await waitFor(() =>
      expect(send).toHaveBeenCalledWith("POST", path + "/query", { cypher }),
    );
    expect(await screen.findByText("1 rows · 12 ms")).toBeInTheDocument();
  });

  it("keeps restoration and project administration unavailable to viewers", async () => {
    open("versions");
    expect(
      await screen.findByRole("button", { name: "Restore selected version" }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Grant viewer access" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Delete version" }),
    ).not.toBeInTheDocument();
  });

  it("defaults to the explorer and offers only the four demo views", async () => {
    const user = userEvent.setup();
    open("");
    expect(screen.getByRole("heading", { name: "Published Graph Explorer" })).toBeVisible();
    await user.click(screen.getByRole("combobox", { name: "Workspace view" }));
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Published Graph Explorer", "Query Workbench", "Graph Analytics", "Graph Schema",
    ]);
    expect(send).not.toHaveBeenCalled();
  });

  it.each([
    ["operations", "Graph Operations"], ["intelligence", "Graph Intelligence"], ["graphml", "GraphML Import"],
  ])("retains the direct %s view", (view, title) => {
    open(view);
    expect(screen.getByRole("heading", { name: title })).toBeVisible();
  });
});
