/**
 * Configuration gate.
 *
 * The Playwright smoke test loads the *production* build through `vite preview`,
 * and the page fetches `/health` and `/version` with relative URLs. Both the dev
 * and the preview server therefore need the same two-endpoint proxy; without the
 * preview proxy the deployed page would show the "backend unreachable" card.
 *
 * This file is read as text (not imported) so Vitest never has to transform
 * `vite.config.ts` through esbuild inside the jsdom environment.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const configSource = readFileSync(resolve(import.meta.dirname, "..", "vite.config.ts"), "utf8");

describe("vite configuration", () => {
  it("proxies /health and /version in the dev server", () => {
    const serverBlock = configSource.slice(
      configSource.indexOf("server: {"),
      configSource.indexOf("preview: {"),
    );
    expect(serverBlock).toContain('"/health"');
    expect(serverBlock).toContain('"/version"');
  });

  it("proxies /health and /version in the preview server", () => {
    const previewBlock = configSource.slice(configSource.indexOf("preview: {"));
    expect(previewBlock).toContain('"/health"');
    expect(previewBlock).toContain('"/version"');
  });

  it("binds loopback only and uses the documented ports", () => {
    expect(configSource).toContain('host: "127.0.0.1"');
    expect(configSource).toContain("port: 5173");
    expect(configSource).toContain("port: 4173");
    expect(configSource).toContain("strictPort: true");
  });

  it("targets the local backend by default", () => {
    expect(configSource).toContain("http://127.0.0.1:8000");
  });
});
