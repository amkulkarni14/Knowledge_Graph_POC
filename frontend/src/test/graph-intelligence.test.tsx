import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { send } from "../api/client";
import { IntelligenceTools } from "../features/query/GraphIntelligenceTools";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  send: vi.fn(),
}));

it("previews generated Cypher and waits for an explicit Run", async () => {
  const ui = userEvent.setup();
  const query = "MATCH (n:Person) RETURN n";
  vi.mocked(send)
    .mockResolvedValueOnce({ cypher: query })
    .mockResolvedValueOnce({ rows: [], duration_ms: 5 });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <IntelligenceTools path="/scope/version" published />
    </QueryClientProvider>,
  );
  await ui.click(screen.getByRole("combobox", { name: "Capability" }));
  await ui.click(
    screen.getByRole("option", { name: "Natural language to Cypher" }),
  );
  await ui.type(
    screen.getByRole("textbox", { name: "Question" }),
    "Show all people",
  );
  await ui.click(screen.getByRole("button", { name: "Draft Cypher" }));
  expect(
    await screen.findByRole("textbox", {
      name: "Review or edit generated Cypher",
    }),
  ).toHaveValue(query);
  expect(send).toHaveBeenCalledTimes(1);
  await ui.click(screen.getByRole("button", { name: "Run reviewed query" }));
  expect(send).toHaveBeenLastCalledWith("POST", "/scope/version/query", {
    cypher: query,
  });
});
