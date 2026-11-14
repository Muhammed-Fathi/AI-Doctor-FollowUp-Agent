/**
 * Typed API client for the two public system endpoints.
 *
 * Only `/health` and `/version` exist in Phase 1. There is no patient,
 * authentication or clinical endpoint on the client because none exists on the
 * server yet (`MASTER_PLAN.md` §5, P1).
 */

export type DependencyState = "ok" | "unavailable" | "not_configured";

export interface Health {
  status: "ok" | "degraded";
  version: string;
  db: DependencyState;
  ollama: DependencyState;
  tesseract: DependencyState;
  disclaimer?: string | null;
}

export interface VersionInfo {
  app_version: string;
  api_version: string;
  workflow_version: string;
  policy_version: string;
  git_sha: string;
}

export interface SystemStatus {
  health: Health;
  version: VersionInfo;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const REQUEST_TIMEOUT_MS = 8_000;

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const combinedSignal = signal
    ? AbortSignal.any([signal, controller.signal])
    : controller.signal;

  try {
    const response = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: combinedSignal,
    });

    if (!response.ok) {
      throw new ApiError(`${path} returned HTTP ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(`${path} timed out after ${REQUEST_TIMEOUT_MS} ms`, 0);
    }
    throw new ApiError(`${path} request failed`, 0);
  } finally {
    clearTimeout(timeout);
  }
}

/** Fetch liveness and dependency state. */
export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return getJson<Health>("/health", signal);
}

/** Fetch build and contract versions. */
export function fetchVersion(signal?: AbortSignal): Promise<VersionInfo> {
  return getJson<VersionInfo>("/version", signal);
}

/** Fetch both documents; the page shows either a full status or an error card. */
export async function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  const [health, version] = await Promise.all([fetchHealth(signal), fetchVersion(signal)]);
  return { health, version };
}
