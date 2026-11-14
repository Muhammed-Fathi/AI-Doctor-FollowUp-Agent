import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { HealthPage } from "../src/pages/HealthPage";
import { DEMO_NOTICE } from "../src/app/constants";

const HEALTH_OK = {
  status: "ok",
  version: "0.1.0",
  db: "ok",
  ollama: "not_configured",
  tesseract: "not_configured",
  disclaimer: DEMO_NOTICE,
};

const VERSION_OK = {
  app_version: "0.1.0",
  api_version: "v1",
  workflow_version: "1.0.0",
  policy_version: "demo-policy-1.1.0",
  git_sha: "a33e693ba16560836312351787769ec5ee18b469",
};

type Json = Record<string, unknown>;

function mockFetch(routes: Record<string, { status: number; body: Json }>) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const key = Object.keys(routes).find((path) => url.endsWith(path));
    const route = key ? routes[key] : undefined;
    if (!route) {
      return Promise.reject(new TypeError(`Unexpected request: ${url}`));
    }
    return Promise.resolve(
      new Response(JSON.stringify(route.body), {
        status: route.status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HealthPage", () => {
  it("shows a loading state before the API responds", () => {
    // A never-settling request models a slow backend, so the loading state is
    // observable without a pending state update escaping the test.
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );

    render(<HealthPage />);

    // Rendered synchronously, before any answer could arrive.
    expect(screen.getByTestId("loading")).toBeInTheDocument();
    expect(screen.getByText(/Checking local services/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("leaves the loading state once the API rejects", async () => {
    // The rejection resolves asynchronously, so the assertion is awaited: React
    // state updates then happen inside act() instead of after the test ends.
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );

    render(<HealthPage />);
    expect(screen.getByTestId("loading")).toBeInTheDocument();

    expect(await screen.findByRole("alert")).toHaveTextContent(/Backend unreachable/i);
    expect(screen.queryByTestId("loading")).not.toBeInTheDocument();
  });

  it("renders dependency states from /health", async () => {
    mockFetch({
      "/health": { status: 200, body: HEALTH_OK },
      "/version": { status: 200, body: VERSION_OK },
    });

    render(<HealthPage />);

    expect(await screen.findByText("Database")).toBeInTheDocument();
    // Two OK badges: the masthead summary plus the database row.
    expect(screen.getAllByTestId("badge-ok")).toHaveLength(2);
    expect(screen.getAllByTestId("badge-not_configured")).toHaveLength(2);
    expect(screen.queryByTestId("loading")).not.toBeInTheDocument();
  });

  it("renders build and contract versions from /version", async () => {
    mockFetch({
      "/health": { status: 200, body: HEALTH_OK },
      "/version": { status: 200, body: VERSION_OK },
    });

    render(<HealthPage />);

    expect(await screen.findByText(VERSION_OK.git_sha)).toBeInTheDocument();
    expect(screen.getByText(VERSION_OK.policy_version)).toBeInTheDocument();
    expect(screen.getByText(VERSION_OK.workflow_version)).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
  });

  it("always shows the educational notice", async () => {
    mockFetch({
      "/health": { status: 200, body: HEALTH_OK },
      "/version": { status: 200, body: VERSION_OK },
    });

    render(<HealthPage />);
    // The notice is rendered synchronously, before any API answer arrives.
    expect(screen.getByRole("note")).toHaveTextContent(DEMO_NOTICE);
    await screen.findByText("Database");
  });

  it("shows a degraded badge when the database is unavailable", async () => {
    mockFetch({
      "/health": { status: 200, body: { ...HEALTH_OK, status: "degraded", db: "unavailable" } },
      "/version": { status: 200, body: VERSION_OK },
    });

    render(<HealthPage />);

    expect(await screen.findByTestId("badge-degraded")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("shows an error card when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );

    render(<HealthPage />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Backend unreachable/i);
    // Guidance, not a stack trace.
    expect(alert).toHaveTextContent(/start\.ps1/);
  });

  it("retries after a failure and recovers", async () => {
    const user = userEvent.setup();
    let attempt = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      attempt += 1;
      if (attempt <= 2) {
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      const body = url.endsWith("/health") ? HEALTH_OK : VERSION_OK;
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthPage />);
    await screen.findByRole("alert");

    await user.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
    expect(await screen.findByText("Database")).toBeInTheDocument();
  });

  it("does not present self-reported or clinical content", async () => {
    mockFetch({
      "/health": { status: 200, body: HEALTH_OK },
      "/version": { status: 200, body: VERSION_OK },
    });

    const { container } = render(<HealthPage />);
    await screen.findByText("Database");

    const text = container.textContent?.toLowerCase() ?? "";
    for (const forbidden of ["diagnos", "prescrib", "treatment", "risk score", "triage"]) {
      expect(text).not.toContain(forbidden);
    }
  });
});

