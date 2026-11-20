import { expect, test } from "@playwright/test";

test("opens a live Neo4j graph, expands an entity, and visualizes a scoped query", async ({
  page,
}) => {
  const username = process.env.KG_TEST_BROWSER_USER;
  const password = process.env.KG_TEST_BROWSER_PASSWORD;
  test.skip(
    !username || !password,
    "Requires a published version in disposable graph databases",
  );

  await page.goto("/");
  await page.getByLabel("Username").fill(username!);
  await page.getByLabel("Password").fill(password!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Published Graphs" }).click();
  await expect(
    page.getByRole("heading", { name: "Graph Versions", exact: true }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Workspace view" }).click();
  await page.getByRole("option", { name: "Published Graph Explorer" }).click();
  await page.getByRole("textbox", { name: "Entity label" }).fill("Order");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page.getByRole("button", { name: "Order:1001", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Knowledge graph with/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Expand two hops" }).click();
  await expect(
    page.getByRole("img", { name: /visible relationships/ }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Workspace view" }).click();
  await page.getByRole("option", { name: "Query Workbench" }).click();
  await page
    .getByRole("textbox", { name: "Cypher statement" })
    .fill("MATCH (o:Order) RETURN o LIMIT 1");
  await page.getByRole("button", { name: "Run query" }).click();
  await expect(page.getByText(/1 rows .* ms/)).toBeVisible();
  await page.getByRole("combobox", { name: "Result mode" }).click();
  await page.getByRole("option", { name: "graph" }).click();
  await expect(
    page.getByRole("img", { name: /Knowledge graph with 1 visible nodes/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Graph Intelligence", exact: true }).click();
  await page.getByRole("textbox", { name: "Anchor node ID" }).fill("Order:1001");
  await page.getByRole("button", { name: "Analyze neighborhood" }).click();
  await expect(page.getByRole("heading", { name: "Candidate links" })).toBeVisible();
  const file = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export neighborhood GraphML" }).click();
  expect((await file).suggestedFilename()).toBe("neighborhood.graphml");
});
