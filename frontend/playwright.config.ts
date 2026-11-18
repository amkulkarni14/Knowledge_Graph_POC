import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    channel: "chromium",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `"${resolve(process.platform === "win32" ? "../.venv/Scripts/python.exe" : "../.venv/bin/python")}" -B -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`,
      cwd: "..",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      env: { KG_API_STORAGE_DIR: resolve(".local/e2e-sessions") },
    },
  ],
});
