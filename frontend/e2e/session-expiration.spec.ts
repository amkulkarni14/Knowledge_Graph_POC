import { test, expect } from "@playwright/test";
import { signIn } from "./workflow-fixtures";
test("a deleted or expired server session clears client state and allows a fresh workspace", async ({
  page,
  request,
}) => {
  await signIn(page);
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/sessions") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create workspace" }).click();
  const { data } = await (await response).json();
  await expect(
    page.getByRole("heading", { name: "Data Sources" }),
  ).toBeVisible();
  const authorization = await (
    await response
  )
    .request()
    .headerValue("authorization");
  const backendPort = process.env.KG_E2E_BACKEND_PORT ?? "8000";
  expect(
    (
      await request.delete(
        `http://127.0.0.1:${backendPort}/api/v1/sessions/${data.id}`,
        {
          headers: { Authorization: authorization ?? "" },
        },
      )
    ).ok(),
  ).toBeTruthy();
  await expect(
    page.getByText(
      "Your session has expired. Create a new workspace to continue.",
    ),
  ).toBeVisible({ timeout: 20000 });
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Data Sources" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reset workspace", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
});
