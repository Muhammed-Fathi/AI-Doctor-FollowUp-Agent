import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

/**
 * Vite configuration for the Phase 1 frontend foundation.
 *
 * The dev server proxies `/health` and `/version` to the local FastAPI backend
 * so the browser only ever talks to one origin (no CORS configuration and no
 * hardcoded backend host in browser code).
 */
const BACKEND_ORIGIN = process.env["VITE_BACKEND_ORIGIN"] ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/health": { target: BACKEND_ORIGIN, changeOrigin: true },
      "/version": { target: BACKEND_ORIGIN, changeOrigin: true },
      "/openapi.json": { target: BACKEND_ORIGIN, changeOrigin: true },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    // The Playwright smoke test loads the *production* build, so the preview
    // server needs the same two-endpoint proxy as the dev server.
    proxy: {
      "/health": { target: BACKEND_ORIGIN, changeOrigin: true },
      "/version": { target: BACKEND_ORIGIN, changeOrigin: true },
      "/openapi.json": { target: BACKEND_ORIGIN, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: false,
    include: ["tests/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**"],
    restoreMocks: true,
  },
});
