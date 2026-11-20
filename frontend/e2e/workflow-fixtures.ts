import { expect, type Page } from "@playwright/test";

export const workflowCredentials = {
  username: process.env.KG_TEST_WORKFLOW_USER ?? "admin",
  password: process.env.KG_TEST_WORKFLOW_PASSWORD ?? "admin",
};

export async function signIn(page: Page, path = "/") {
  await page.goto(path);
  await page.getByLabel("Username").fill(workflowCredentials.username);
  await page.getByLabel("Password").fill(workflowCredentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByRole("heading", { name: "Home", exact: true }),
  ).toBeVisible();
}
