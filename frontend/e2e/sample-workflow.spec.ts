import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("sample workflow through explicit review, approval, build, snapshots, and exploration", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("Workspace name").fill("Browser integration workspace");
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Goal & Scope", exact: true })
    .click();
  await page.getByLabel("Project name").fill("Retail");
  await page
    .getByLabel("Business questions")
    .fill("How are customers connected to orders?");
  await page.getByRole("button", { name: "Save scope" }).click();
  await expect(page.getByText("Scope saved.")).toBeVisible();
  await page
    .getByRole("link", { name: "Data Sources", exact: true })
    .click();
  await page.getByRole("button", { name: "Connect retail sample" }).click();
  await expect(page.getByText("sample", { exact: true }).first()).toBeVisible();
  await page
    .getByRole("link", { name: "Schema Extraction", exact: true })
    .click();
  await page.getByRole("button", { name: "Extract metadata" }).click();
  await expect(page.getByLabel("Qualified table")).toBeEnabled();
  await page
    .getByRole("link", { name: "Schema Analysis", exact: true })
    .click();
  await page.getByRole("button", { name: "Analyze metadata" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Latest analysis and relationship candidates",
    }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Ontology Studio", exact: true })
    .click();
  await page.getByRole("button", { name: "Create draft" }).click();
  await expect(
    page.getByRole("button", { name: "Save draft", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await page
    .getByRole("link", { name: "AI Suggestions", exact: true })
    .click();
  await page.getByRole("button", { name: "Skip AI suggestions" }).click();
  await page
    .getByRole("link", { name: "Review & Approval", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Apply review" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Preview review" }).click();
  await page.getByRole("button", { name: "Apply review" }).click();
  await expect(page.getByText("Review applied.")).toBeVisible();
  await page
    .getByRole("link", { name: "Ontology Validation", exact: true })
    .click();
  await page.getByRole("button", { name: "Validate ontology" }).click();
  await expect(page.getByText("Validation passed.")).toBeVisible();
  await page
    .getByRole("link", { name: "Ontology Versioning", exact: true })
    .click();
  await page.getByLabel("Independent reviewer").fill("reviewer.lead");
  await page
    .getByRole("button", { name: "Approve ontology", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await page.getByRole("link", { name: "Build Plan", exact: true }).click();
  await page.getByRole("button", { name: "Run full build" }).click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Continue to snapshot storage" }),
  ).toBeVisible({ timeout: 60000 });
  for (const title of [
    "Data Extraction",
    "Data Quality",
    "Cleaning & Entity Resolution",
    "Graph Construction",
    "Graph Validation",
  ]) {
    await page
      .getByRole("link", { name: title, exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Stage results", exact: true }),
    ).toBeVisible();
  }
  await page.getByRole("link", { name: "Storage & Snapshots", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Save validated graph" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Save validated graph" }).click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByText("reload check", { exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Snapshot build ID" }).click();
  await page
    .getByRole("option")
    .filter({ hasText: /^\d{8}T/ })
    .first()
    .click();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download", exact: true }).click();
  expect((await downloadEvent).suggestedFilename()).toBe("graph.json.gz");
  await page.getByRole("button", { name: "Make CURRENT" }).click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await page.getByRole("link", { name: "Graph Explorer", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Knowledge graph with/ }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Graph source", exact: true })
    .click();
  await page
    .getByRole("option", { name: "Saved snapshot", exact: true })
    .click();
  await expect(
    page.getByRole("img", { name: /Knowledge graph with/ }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Entities", exact: true }).click();
  const nodeResponse=page.waitForResponse(r=>r.url().includes('/graphs/node?'));
  await page
    .getByRole("button", { name: /Inspect Customer/ })
    .first()
    .click();
  const nodeDetail=(await (await nodeResponse).json()).data;
  await expect(
    page.getByRole("button", { name: "Explore neighborhood" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Use as path source" }).click();
  await page.getByRole("button", { name: "Use as path target" }).click();
  await page.getByRole("tab", { name: "Path analysis" }).click();
  const relationship=nodeDetail.relationships[0];
  await page.getByLabel('Target node ID').fill(relationship.source===nodeDetail.id?relationship.target:relationship.source);
  await page.getByRole("button", { name: "Find connection" }).click();
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Metrics", exact: true }).click();
  await expect(page.getByText("most connected", { exact: true })).toBeVisible();
  await page.evaluate("window.scrollTo(0, 0)");
  await page.screenshot({
    animations: "disabled",
    path: ".local/graph-workspace.png",
    fullPage: true,
  });
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(errors).toEqual([]);
  await page
    .getByRole("button", { name: "Reset workspace", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeVisible();
});
