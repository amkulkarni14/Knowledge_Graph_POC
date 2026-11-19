import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
const frontendPort = process.env.KG_E2E_FRONTEND_PORT ?? "5173";
const backendPort = process.env.KG_E2E_BACKEND_PORT ?? "8000";
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const backendUrl = `http://127.0.0.1:${backendPort}`;
export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: frontendUrl,
    trace: "retain-on-failure",
    channel: process.env.KG_E2E_CHANNEL ?? "chromium",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `npm run dev -- --port ${frontendPort}`,
      url: frontendUrl,
      env: { VITE_API_BASE_URL: backendUrl + "/api/v1" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `"${process.env.KG_E2E_PYTHON ?? resolve(process.platform === "win32" ? "../.venv/Scripts/python.exe" : "../.venv/bin/python")}" -B -m uvicorn backend.app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "..",
      url: backendUrl + "/api/v1/health",
      reuseExistingServer: !process.env.CI,
      env: {
        KG_API_STORAGE_DIR: resolve(".local/e2e-sessions"),
        KG_API_CORS_ORIGINS: frontendUrl,
      },
    },
  ],
});
