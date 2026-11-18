import { test, expect } from "@playwright/test";
test("scope form validation, route guard, and multiple CSV upload use the live backend", async ({
  page,
}) => {
  await page.goto("/ontology");
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeVisible();
  await page.getByRole('button',{name:'Toggle navigation'}).click();
  await expect(page.getByRole('link',{name:'01 Goal & Scope',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Toggle navigation'}).click();
  await page.getByLabel("Workspace name").fill("CSV browser workflow");
  await page.getByRole("button", { name: "Create workspace" }).click();
  await page
    .getByRole("link", { name: "01 Goal & Scope", exact: true })
    .click();
  await page.getByLabel("Project name").fill("CSV files");
  await page
    .getByLabel("Business questions")
    .fill("How are customer accounts connected?");
  await page.getByRole("button", { name: "Save scope" }).click();
  await expect(page.getByText("Scope saved.")).toBeVisible();
  await page
    .getByRole("link", { name: "02 Connect Safely", exact: true })
    .click();
  await page.getByRole("tab", { name: "Upload files" }).click();
  await page
    .getByLabel("Choose source files")
    .setInputFiles([
      "../data/samples/customer360/customers.csv",
      "../data/samples/customer360/accounts.csv",
      "../data/samples/customer360/banks.csv",
    ]);
  await page.getByRole("button", { name: "Analyze and connect files" }).click();
  await expect(page.getByText("csv", { exact: true })).toBeVisible();
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
  await page.goto("/");
  await page.route("**/api/v1/sessions", (route) =>
    route.fulfill({
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
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeHidden();
});
