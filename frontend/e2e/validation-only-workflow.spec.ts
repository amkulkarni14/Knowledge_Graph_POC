import { expect, test } from "@playwright/test";
import { signIn } from "./workflow-fixtures";

test("validation-only policy hides governance stages and continues to build", async ({
  page,
}) => {
  test.skip(process.env.KG_WORKFLOW_POLICY !== "poc_validation_only");
  await signIn(page);
  await page
    .getByLabel("Workspace name")
    .fill("Validation-only browser workspace");
  await page.getByRole("button", { name: "Create workspace" }).click();
  const sidebar = page.getByRole("complementary", { name: "Main navigation" });
  const navigation = page.getByRole("navigation", {
    name: "Workflow navigation",
  });
  await expect(
    sidebar.getByRole("link", { name: "Ontology Studio", exact: true }),
  ).toBeVisible();
  for (const title of [
    "AI Suggestions",
    "Review & Approval",
    "Ontology Versioning",
  ])
    await expect(
      sidebar.getByRole("link", { name: title, exact: true }),
    ).toHaveCount(0);
  await expect(
    page.getByLabel("Workflow progress", { exact: true }),
  ).toContainText("0 of 13");
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(
    page.getByText("0 of 13 stages completed", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("7. Graph Build Manager")).toBeVisible();
  await expect(
    sidebar.getByRole("link", { name: "Graph Build Manager", exact: true }),
  ).toHaveAttribute("title", "Graph Build Manager");

  await sidebar
    .getByRole("link", { name: "Data Sources", exact: true })
    .click();
  await page.getByRole("combobox", { name: "Select data source" }).click();
  await page.getByRole("option", { name: "Upload Files", exact: true }).click();
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
  await page.getByRole("checkbox", { name: "Select all on this page" }).check();
  await page.getByRole("button", { name: "Confirm selection" }).click();
  await navigation
    .getByRole("link", { name: "Continue to Goal & Scope" })
    .click();
  await page.getByLabel("Project name").fill("Customer 360");
  const input = page.getByLabel("Add custom business question");
  await input.fill("How are customers connected to accounts?");
  await input.press("Enter");
  await page.getByRole("button", { name: "Save scope" }).click();
  await navigation
    .getByRole("link", { name: "Continue to Schema Extraction" })
    .click();
  await page.getByRole("button", { name: "Extract metadata" }).click();
  await navigation
    .getByRole("link", { name: "Continue to Schema Analysis" })
    .click();
  await page.getByRole("button", { name: "Analyze metadata" }).click();
  await navigation
    .getByRole("link", { name: "Continue to Ontology Studio" })
    .click();
  const ontologyName = page.getByRole("textbox", { name: "Ontology Name" });
  await ontologyName.fill("Customer 360 Ontology");
  await page.getByRole("button", { name: "Create draft" }).click();
  await expect(ontologyName).toHaveValue("Customer 360 Ontology");
  await ontologyName.fill("   ");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByText("Enter an ontology name.")).toBeVisible();
  await ontologyName.fill("x".repeat(201));
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByText("Use 200 characters or fewer.")).toBeVisible();
  await ontologyName.fill("Customer 360 Ontology");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByText("Ontology draft saved.")).toBeVisible();

  await expect(
    navigation.getByRole("link", { name: "Continue to Ontology Validation" }),
  ).toBeVisible();
  // Simulate a location change without reloading the workspace session.
  for (const [route, target] of [
    ["/suggestions", "/ontology"],
    ["/review", "/ontology"],
    ["/repository", "/validation"],
  ]) {
    await sidebar
      .getByRole("link", { name: "Schema Analysis", exact: true })
      .click();
    await expect(
      navigation.getByRole("link", { name: "Continue to Ontology Studio" }),
    ).toBeVisible();
    await page.evaluate(
      `history.pushState({ ...history.state, key: ${JSON.stringify(route)}, idx: (history.state.idx ?? 0) + 1 }, "", ${JSON.stringify(route)}); dispatchEvent(new PopStateEvent("popstate"));`,
    );
    await expect(page).toHaveURL(new RegExp(target + "$"));
    await expect(
      navigation.getByRole(target === "/validation" ? "button" : "link", {
        name:
          target === "/validation"
            ? "Continue to Graph Build Manager"
            : "Continue to Ontology Validation",
      }),
    ).toBeVisible();
  }
  await expect(
    page.getByRole("button", { name: "Approve ontology" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Independent reviewer")).toHaveCount(0);
  await expect(
    navigation.getByRole("button", { name: "Continue to Graph Build Manager" }),
  ).toBeDisabled();
  await navigation.getByRole("link", { name: "Back", exact: true }).click();
  await expect(page).toHaveURL(/\/ontology$/);
  await navigation
    .getByRole("link", { name: "Continue to Ontology Validation" })
    .click();
  await page.getByRole("button", { name: "Validate ontology" }).click();
  await expect(page.getByText("Validation passed.")).toBeVisible();
  await navigation
    .getByRole("link", { name: "Continue to Graph Build Manager" })
    .click();
  await expect(page).toHaveURL(/\/build\/10$/);
  await expect(
    page.getByRole("heading", { name: "Graph Build Manager", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Breadcrumb")).toHaveText(
    "Workspace/Graph Build Manager",
  );
  await expect(page.getByLabel("Workflow progress")).toContainText(
    "Stage 7 · Graph Build Manager",
  );
  await expect(
    page.getByText(
      "Configure, execute, and monitor the knowledge graph construction pipeline.",
      { exact: true },
    ),
  ).toBeVisible();
  const backToValidation = navigation.getByRole("link", {
    name: "Back",
    exact: true,
  });
  await expect(backToValidation).toHaveAttribute("href", "/validation");
  await backToValidation.click();
  await expect(page).toHaveURL(/\/validation$/);
  await expect(
    page.getByText("Customer 360 Ontology", { exact: true }),
  ).toBeVisible();
  await navigation.getByRole("link", { name: "Back", exact: true }).click();
  await ontologyName.fill("  Retail Customer Ontology  ");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Retail Customer Ontology" }),
  ).toBeVisible();
  await page.reload();
  await page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "Workspaces", exact: true }),
    })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await sidebar
    .getByRole("link", { name: "Ontology Studio", exact: true })
    .click();
  await expect(ontologyName).toHaveValue("Retail Customer Ontology");
  await navigation
    .getByRole("link", { name: "Continue to Ontology Validation" })
    .click();
  await expect(
    page.getByText("Retail Customer Ontology", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Validation passed.")).toBeVisible();
  await expect(
    navigation.getByRole("link", { name: "Continue to Graph Build Manager" }),
  ).toBeVisible();
});
