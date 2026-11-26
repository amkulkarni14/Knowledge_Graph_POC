import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { BuildMonitor } from "../features/build/BuildMonitor";
import type { BuildPipeline, Job } from "../types/common.types";

const pipeline: BuildPipeline = {
  steps: [
    { stage: 10, title: "Build Plan" },
    { stage: 11, title: "Data Extraction" },
    { stage: 12, title: "Data Quality" },
  ],
  persistence: { stage: 16, title: "Store Graph" },
};
const running = {
  id: "active", status: "running", stage: 11, progress: { rows: 300 }, error: null,
  started_at: "2026-11-25T08:00:00Z",
  steps: [
    { stage: 10, status: "completed", duration_ms: 38, result: { entity_types: 3 } },
    { stage: 11, status: "running" },
    { stage: 12, status: "pending" },
  ],
  events: [
    { time: "2026-11-25T08:00:01Z", stage: 10, severity: "success", message: "Stage completed." },
    { time: "2026-11-25T08:00:02Z", stage: 11, severity: "info", message: "Stage started." },
  ],
} satisfies Job;

it("shows backend progress, retains open stages, and expands the failed stage", async () => {
  const user = userEvent.setup();
  const client = new QueryClient();
  const monitor = (job: Job) => <QueryClientProvider client={client}>
    <MemoryRouter>
      <BuildMonitor id="workspace" pipeline={pipeline} job={job} busy={job.status === "running"} configuration={null}>
        {() => null}
      </BuildMonitor>
    </MemoryRouter>
  </QueryClientProvider>;
  const view = render(monitor(running));
  expect(screen.getByRole("progressbar", { name: "Build progress" })).toHaveAttribute("aria-valuenow", "33");
  expect(screen.getByRole("button", { name: /Execution events/ })).toHaveAttribute("aria-expanded", "false");
  await user.click(screen.getByRole("button", { name: /Build Plan/ }));
  expect(screen.getByText("entity types")).toBeVisible();
  view.rerender(monitor({
    ...running,
    status: "failed", error: { code: "source_failed", message: "Source unavailable." },
    finished_at: "2026-11-25T08:00:03Z",
    steps: [running.steps[0], { stage: 11, status: "failed", duration_ms: 51 }, { stage: 12, status: "skipped" }],
    events: [...running.events, {
      time: "2026-11-25T08:00:03Z", stage: 11, severity: "error", message: "Stage stopped before completion.",
    }],
  }));
  expect(screen.getByRole("button", { name: /Build Plan/ })).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("button", { name: /Data Extraction/ })).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText("Source unavailable.")).toBeVisible();
  expect(screen.getByRole("button", { name: /Data Quality.*Skipped/ })).toBeVisible();
  await user.click(screen.getByRole("button", { name: /Execution events/ }));
  await user.click(screen.getByRole("combobox", { name: "Event severity" }));
  await user.click(screen.getByRole("option", { name: "ERROR" }));
  expect(screen.getByText("Stage stopped before completion.")).toBeVisible();
  expect(screen.queryByText("Stage started.")).toBeNull();
}, 20000);
