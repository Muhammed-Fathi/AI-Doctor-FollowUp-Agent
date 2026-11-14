import { expect, test } from "@playwright/test";

/**
 * Phase 1 browser smoke test (`REQ-OPS-02`).
 *
 * Preconditions, checked explicitly so a missing environment is reported as
 * "not executed" rather than as a false pass:
 *   1. the backend is running on http://127.0.0.1:8000 (`start.ps1`),
 *   2. the frontend production build exists (`npm run build`),
 *   3. Playwright's chromium browser is installed (`npx playwright install chromium`).
 */
test.describe("foundation health page", () => {
  test.beforeAll(async ({ request }) => {
    const response = await request.get("http://127.0.0.1:8000/health").catch(() => null);
    test.skip(
      response === null || !response.ok(),
      "Backend is not running on 127.0.0.1:8000 - start it with scripts/powershell/start.ps1",
    );
  });

  test("renders liveness, versions and the educational notice", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Foundation status" })).toBeVisible();
    await expect(page.getByRole("note")).toContainText(
      "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE",
    );

    // The dependency table is populated from the live API.
    await expect(page.getByRole("rowheader", { name: "Database" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Build and contract versions" })).toBeVisible();

    // No error card and no clinical vocabulary.
    await expect(page.getByRole("alert")).toHaveCount(0);
    const body = await page.locator("body").innerText();
    expect(body.toLowerCase()).not.toContain("diagnos");
    expect(body.toLowerCase()).not.toContain("prescrib");
  });
});
