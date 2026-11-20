import { test, expect } from "@playwright/test";
import { signIn } from "./workflow-fixtures";
import AxeBuilder from "@axe-core/playwright";
test("CSV workflow through explicit review, approval, build, snapshots, and exploration", async ({
  page,
}) => {
  test.setTimeout(150000);
  const runId = Date.now();
  const domainName = `Customer accounts ${runId}`;
  const workspaceName = `Browser integration workspace ${runId}`;
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await signIn(page, "/ontology");
  await expect(
    page.getByRole("heading", { name: "Workflow stages" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Domains", exact: true }).click();
  await page.getByLabel("Domain name").fill(domainName);
  await page.getByLabel("Project name").fill("Customer 360");
  await page
    .getByLabel("Business questions")
    .fill("How are customers connected to accounts?");
  await page.getByLabel("Scope notes").fill("Account relationships");
  await page
    .getByLabel("Columns in scope", { exact: true })
    .fill("csv.customers.cust_id");
  await page.getByRole("button", { name: "Save domain" }).click();
  await expect(page.getByText(domainName, { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await page.getByLabel("Workspace name").fill(workspaceName);
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Data Sources" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Continue to Goal & Scope" }),
  ).toBeDisabled();
  await expect(page.getByRole("tab")).toHaveText(["CSV upload", "PostgreSQL"]);
  await page
    .getByLabel("Choose source files")
    .setInputFiles(
      [
        "accounts",
        "banks",
        "credit_enquiry",
        "credit_score",
        "customers",
        "loans",
        "payments",
      ].map((file) => `../data/samples/customer360/${file}.csv`),
    );
  await page.getByRole("button", { name: "Analyze and connect files" }).click();
  await expect(
    page.getByRole("link", { name: "Continue to Goal & Scope" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Continue to Goal & Scope" }).click();
  await expect(page.getByRole("heading", { name: "Define your scope" })).toBeVisible();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(
    page.getByRole("progressbar", { name: "Workflow completion" }),
  ).toHaveAttribute("aria-valuenow", "6");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await signIn(page);
  await expect(page.getByText("6% complete", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Open workspace" }).click();
  await page.getByRole("link", { name: "Goal & Scope", exact: true }).click();
  await page.getByRole("combobox", { name: "Saved domain" }).click();
  await page.getByRole("option", { name: domainName }).click();
  await page.getByRole("button", { name: "Use domain" }).click();
  await expect(page.getByLabel("Project name")).toHaveValue("Customer 360");
  await expect(
    page.getByLabel("Columns in scope", { exact: true }),
  ).toHaveValue("csv.customers.cust_id");
  await page.getByRole("button", { name: "Save scope" }).click();
  await expect(page.getByText("Scope saved.")).toBeVisible();
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
  await page.getByRole("link", { name: "AI Suggestions", exact: true }).click();
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
    page.getByRole("link", { name: "Go to Storage & Snapshots" }),
  ).toBeVisible({ timeout: 60000 });
  for (const title of [
    "Data Extraction",
    "Data Quality",
    "Cleaning & Entity Resolution",
    "Graph Construction",
    "Graph Validation",
  ]) {
    await page.getByRole("link", { name: title, exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Stage results", exact: true }),
    ).toBeVisible();
  }
  await page
    .getByRole("link", { name: "Storage & Snapshots", exact: true })
    .click();
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
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(
    page.getByRole("progressbar", { name: "Workflow completion" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(
    page.getByRole("heading", { name: "Created ontologies" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Knowledge Graph", exact: true }),
  ).toBeVisible();
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
  const nodeResponse = page.waitForResponse((r) =>
    r.url().includes("/graphs/node?"),
  );
  await page
    .getByRole("button", { name: /Inspect Account:/ })
    .first()
    .click();
  const nodeDetail = (await (await nodeResponse).json()).data;
  await expect(
    page.getByRole("button", { name: "Explore neighborhood" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Use as path source" }).click();
  await page.getByRole("button", { name: "Use as path target" }).click();
  await page.getByRole("tab", { name: "Path analysis" }).click();
  const relationship = nodeDetail.relationships[0];
  await page
    .getByLabel("Target node ID")
    .fill(
      relationship.source === nodeDetail.id
        ? relationship.target
        : relationship.source,
    );
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
  const ontologyTitle = page.getByText(`Knowledge Graph (${workspaceName})`, {
    exact: true,
  });
  const savedOntology = page.locator("details").filter({ has: ontologyTitle });
  await ontologyTitle.click();
  await expect(
    savedOntology.getByText("Version 1", { exact: true }),
  ).toBeVisible();
  await expect(
    savedOntology.getByText("Working draft", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeVisible();
});
