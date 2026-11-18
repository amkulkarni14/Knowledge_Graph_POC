import { test, expect } from "@playwright/test";
test("a deleted or expired server session clears client state and allows a fresh workspace", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/sessions") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create workspace" }).click();
  const { data } = await (await response).json();
  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
  await request.delete(`http://127.0.0.1:8000/api/v1/sessions/${data.id}`);
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
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reset workspace", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
});
