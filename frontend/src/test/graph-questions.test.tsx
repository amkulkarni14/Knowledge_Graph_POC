import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { api, get } from "../api/client";
import GraphQuestions from "../features/query/GraphQuestions";

vi.mock("../api/client", () => ({
  api: { post: vi.fn() },
  get: vi.fn(),
  sessionPath: (id: string, path: string) => id + path,
}));

it.each([
  ["groq", true, "groq", null],
  ["ollama", true, "ollama", null],
  ["rules", true, "rules", null],
  ["ollama", false, "rules", "Cannot reach Ollama. Using predefined graph questions."],
] as const)("shows the configured %s provider and the actual %s result", async (provider, ready, actual, notice) => {
  const suggestion = "How many Account entities are there?";
  vi.mocked(get).mockImplementation(async (path) => path.endsWith("/provider")
    ? { provider, ready, fallback: provider === "ollama", message: ready ? null : "Cannot reach Ollama." }
    : [suggestion]);
  vi.mocked(api.post).mockResolvedValue({
    data: { data: { provider: actual, notice, count: 1, plan: { operation: "count_entities" },
      explanation: "1 matching entity.", explanation_source: "calculated", rows: [{ entity: "Account:1" }],
      graph: { nodes: [{ id: "Account:1", properties: { label: "Account" } }], edges: [] }, followups: [] } },
  });
  render(<QueryClientProvider client={new QueryClient()}>
    <GraphQuestions id="test" selection={{}} scope={provider + ready} enabled showGraph={vi.fn()} />
  </QueryClientProvider>);
  const summary = screen.getByText("Ask Your Knowledge Graph");
  const details = summary.parentElement!;
  details.setAttribute("open", "");
  fireEvent(details, new Event("toggle"));
  expect(await screen.findByText(new RegExp("Provider: " + provider))).toBeVisible();
  fireEvent.click(await screen.findByRole("button", { name: suggestion }));
  fireEvent.click(screen.getByRole("button", { name: "Ask graph" }));
  expect(await screen.findByText("Answered by " + actual + ".")).toBeVisible();
  if (notice) expect(screen.getByText(notice)).toBeVisible();
});
