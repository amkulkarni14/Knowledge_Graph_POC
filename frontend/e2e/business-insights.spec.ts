import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { signIn } from "./workflow-fixtures";

test("Business Insights works before construction and exports filtered aggregates", async ({ page }) => {
  test.setTimeout(150000);
  await signIn(page);
  const insights = page.getByRole("link", { name: "Business Insights", exact: true });
  await insights.click();
  await expect(page).toHaveURL(/\/business-insights$/);
  await expect(page.getByText("Select a workspace to explore business insights.")).toBeVisible();

  await page.getByRole("link", { name: "Home", exact: true }).click();
  await page.getByLabel("Workspace name").fill("Business insights verification");
  await page.getByRole("button", { name: "Create workspace" }).click();
  await insights.click();
  await expect(page.getByRole("heading", { name: "Business Insights", exact: true })).toBeVisible();
  await expect(page.getByText("Connect a data source to start generating insights.")).toBeVisible();

  await page.getByRole("alert").getByRole("link", { name: "Data Sources" }).click();
  await page.getByRole("combobox", { name: "Select data source" }).click();
  await page.getByRole("option", { name: "Upload Files", exact: true }).click();
  const csv = ["shipment_id,status,ship_date,units,supplier_name",
    ...Array.from({ length: 12 }, (_, i) =>
      [i + 1, i < 6 ? "Late" : "On time", i % 2 ? "2026-02-01" : "2026-01-01", i + 10, "Private Name"].join(","),
    ),
  ].join("\n");
  await page.getByLabel("Choose source files").setInputFiles({
    name: "shipments.csv", mimeType: "text/csv", buffer: Buffer.from(csv),
  });
  await page.getByRole("button", { name: "Analyze and connect files" }).click();
  await page.getByRole("checkbox", { name: "Select all on this page" }).check();
  await page.getByRole("button", { name: "Confirm selection" }).click();
  await expect(page.getByRole("link", { name: "Continue to Goal & Scope" })).toBeVisible();

  await insights.click();
  await expect(page.getByText(/12 records profiled/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Business trends" })).toBeVisible();
  await expect(page.getByText(/validated graph or available snapshot is required/)).toBeVisible();
  await expect(page.getByText("Private Name", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Late · 6" }).click();
  await expect(page.getByText("category: Late", { exact: true })).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export aggregated CSV" }).click();
  const file = await download;
  const contents = await readFile((await file.path())!, "utf8");
  expect(file.suggestedFilename()).toBe("business-insights.csv");
  expect(contents).toContain('"Matching records","6"');
  expect(contents).toContain('"category","Late","6","75"');
  expect(contents).not.toContain("Private Name");
  const image = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download chart PNG" }).click();
  expect((await image).suggestedFilename()).toBe("business-trends.png");

  await page.getByRole("link", { name: "Home", exact: true }).click();
  await insights.click();
  await expect(page.getByText("category: Late", { exact: true })).toBeVisible();
  await page.route("**/insights?**", (route) => route.fulfill({
    status: 502,
    json: { error: { code: "insights_unavailable", message: "Could not read the selected source or graph." } },
  }), { times: 1 });
  await page.getByRole("button", { name: "Refresh insights" }).click();
  await expect(page.getByText("Could not read the selected source or graph.")).toBeVisible();
  await page.getByRole("button", { name: "Retry insights" }).click();
  await expect(page.getByRole("button", { name: "Export aggregated CSV" })).toBeEnabled();
});
