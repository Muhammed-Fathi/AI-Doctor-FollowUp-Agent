import { defineConfig, devices } from "@playwright/test";

/**
 * Minimal browser smoke configuration (Phase 1).
 *
 * Playwright browser binaries are **not** committed and are not downloaded by
 * `setup.ps1`. Install them explicitly with `npx playwright install chromium`
 * before running `npm run test:e2e`; the run is otherwise reported as
 * "not executed — prerequisite missing" rather than silently skipped.
 *
 * The smoke test starts the built preview server, which proxies the two system
 * endpoints to the already-running backend, so a single browser context proves
 * "frontend page loads and the API answers".
 */
const PREVIEW_PORT = 4173;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env["CI"],
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${PREVIEW_PORT}`,
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run preview -- --port 4173 --strictPort",
    url: `http://127.0.0.1:${PREVIEW_PORT}`,
    reuseExistingServer: !process.env["CI"],
    timeout: 60_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
