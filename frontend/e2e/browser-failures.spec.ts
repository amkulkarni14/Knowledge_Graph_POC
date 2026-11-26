import { test, expect } from "@playwright/test";
import { signIn } from "./workflow-fixtures";
test("scope form validation, route guard, and multiple CSV upload use the live backend", async ({
  page,
}) => {
  await signIn(page, "/ontology");
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  const workspaceName = `CSV browser workflow ${Date.now()}`;
  await page.getByLabel("Workspace name").fill(workspaceName);
  await page.getByRole("button", { name: "Create workspace" }).click();
  await page.getByRole("link", { name: "Goal & Scope", exact: true }).click();
  await page.getByLabel("Project name").fill("CSV files");
  const saveScope = page.getByRole("button", { name: "Save scope" });
  const next = page.getByRole("button", {
    name: "Continue to Schema Extraction",
  });
  await saveScope.click();
  await expect(
    page.getByText(/Add at least one business question/),
  ).toBeVisible();
  await expect(next).toBeDisabled();

  const picker = page.getByRole("combobox", {
    name: "Search and select business questions",
  });
  const first = "How are different entities connected?";
  const second = "Which entities have the highest number of connections?";
  await picker.fill("relationships");
  await expect(
    page.getByRole("option", { name: "How many unique entities exist?" }),
  ).toHaveCount(0);
  await page.getByRole("option", { name: first }).click();
  await expect(page.getByRole("listbox")).toBeVisible();
  await picker.fill("highest number of connections");
  await expect(page.getByRole("option", { name: second })).toBeVisible();
  await picker.press("End");
  await picker.press("Enter");
  await picker.press("Escape");
  await expect(page.getByRole("listbox")).toBeHidden();
  await picker.fill("relationships");
  await expect(page.getByRole("option", { name: first })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("option", { name: second })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await picker.press("Escape");

  const custom = page.getByLabel("Add custom business question");
  await custom.fill("  HOW ARE DIFFERENT entities   connected?  ");
  await page.getByRole("button", { name: "Add question" }).click();
  await expect(
    page.getByText("This business question is already selected."),
  ).toBeVisible();
  await custom.fill("  How are customer accounts connected?  ");
  await custom.press("Enter");
  await expect(page.getByText("Selected questions: 3")).toBeVisible();
  await page.getByRole("button", { name: "Edit question 3" }).click();
  await page
    .getByLabel("Edit custom business question")
    .fill("Which customer accounts share a bank?");
  await page.getByRole("button", { name: "Update question" }).click();
  await page.getByRole("button", { name: "Remove question 2" }).click();
  await expect(page.getByText("Selected questions: 2")).toBeVisible();

  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith("/scope") &&
      response.request().method() === "PUT",
  );
  await saveScope.click();
  const response = await saved;
  expect(response.ok()).toBeTruthy();
  expect(response.request().postDataJSON().business_questions).toEqual([
    first,
    "Which customer accounts share a bank?",
  ]);
  await expect(page.getByText("Scope saved.")).toBeVisible();
  await page.getByRole("link", { name: "Data Sources", exact: true }).click();
  await page.getByRole("link", { name: "Goal & Scope", exact: true }).click();
  const selected = page.getByRole("region", {
    name: "Selected Business Questions",
  });
  await expect(selected.getByRole("listitem")).toHaveCount(2);
  await expect(selected.getByRole("listitem").nth(0)).toContainText(first);
  await expect(selected.getByRole("listitem").nth(1)).toContainText(
    "Which customer accounts share a bank?",
  );
  await page.reload();
  await page
    .locator(".report-row")
    .filter({ hasText: workspaceName })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page.getByRole("link", { name: "Goal & Scope", exact: true }).click();
  await expect(selected.getByRole("listitem").nth(0)).toContainText(first);
  await expect(selected.getByRole("listitem").nth(1)).toContainText(
    "Which customer accounts share a bank?",
  );
  await page.getByRole("link", { name: "Data Sources", exact: true }).click();
  await page.getByRole("combobox", { name: "Select data source" }).click();
  await page
    .getByRole("option", { name: "Amazon Web Services", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Cloud service" }),
  ).toContainText("Amazon S3");
  await page.getByRole("combobox", { name: "Authentication" }).click();
  await page.getByRole("option", { name: "Temporary credentials" }).click();
  await expect(page.getByLabel("Session token")).toBeVisible();
  await page.getByRole("combobox", { name: "Select data source" }).click();
  await page
    .getByRole("option", { name: "Microsoft Azure", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Cloud service" }),
  ).toContainText("Azure Blob Storage");
  await expect(page.getByLabel("Session token")).toHaveCount(0);
  await page.getByRole("combobox", { name: "Select data source" }).click();
  await page.getByRole("option", { name: "Upload Files", exact: true }).click();
  await page
    .getByLabel("Choose source files")
    .setInputFiles([
      "../data/samples/customer360/customers.csv",
      "../data/samples/customer360/accounts.csv",
      "../data/samples/customer360/banks.csv",
    ]);
  await page.getByRole("button", { name: "Analyze and connect files" }).click();
  await page.getByRole("checkbox", { name: "Select all on this page" }).check();
  await page.getByRole("button", { name: "Confirm selection" }).click();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Goal & Scope", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Continue to Schema Extraction" }),
  ).toBeVisible();
  await page
    .getByLabel("Add custom business question")
    .fill("Which accounts are active?");
  await expect(next).toBeDisabled();
  await page.getByRole("button", { name: "Add question" }).click();
  await expect(next).toBeDisabled();
  await saveScope.click();
  await expect(
    page.getByRole("link", { name: "Continue to Schema Extraction" }),
  ).toBeVisible();

  await picker.hover();
  await page
    .getByRole("button", { name: "Clear predefined questions" })
    .click();
  await expect(page.getByText("Selected questions: 2")).toBeVisible();
  await expect(selected).toContainText("Which accounts are active?");
  await expect(selected).toContainText("Which customer accounts share a bank?");
  await page
    .getByRole("button", { name: "Reset workspace", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeVisible();
});
test("shows backend conflicts and connection failures without reporting success", async ({
  page,
}) => {
  await signIn(page);
  await page.route("**/api/v1/sessions", (route) =>
    route.request().method() !== "POST"
      ? route.continue()
      : route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "session_capacity",
              message: "Session capacity reached",
            },
          }),
        }),
  );
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Session capacity reached",
  );
  await expect(
    page.getByRole("heading", { name: "Data Sources" }),
  ).toBeHidden();
});
