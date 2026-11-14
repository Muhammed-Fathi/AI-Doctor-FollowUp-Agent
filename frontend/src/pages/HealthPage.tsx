import { useCallback, useEffect, useState } from "react";

import { DEPENDENCY_NOTES, DEMO_NOTICE } from "../app/constants";
import { ErrorNotice } from "../components/ErrorNotice";
import { StatusBadge } from "../components/StatusBadge";
import {
  fetchSystemStatus,
  type DependencyState,
  type SystemStatus,
} from "../services/systemApi";

type LoadState =
  | { readonly kind: "loading" }
  | { readonly kind: "ready"; readonly data: SystemStatus }
  | { readonly kind: "error"; readonly message: string };

const DEPENDENCIES = ["db", "ollama", "tesseract"] as const;

/**
 * Phase 1 application/health page.
 *
 * Reports process and build facts only. It contains no patient data, no
 * clinical values and no action beyond a read-only status refresh.
 */
export function HealthPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    // The loading state is set by the initial useState and by `retry()`, never
    // synchronously inside the effect (react-hooks/set-state-in-effect).
    fetchSystemStatus(controller.signal)
      .then((data) => {
        if (active) {
          setState({ kind: "ready", data });
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Unknown error while contacting the API";
        setState({ kind: "error", message });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [refreshToken]);

  const retry = useCallback(() => {
    setState({ kind: "loading" });
    setRefreshToken((token) => token + 1);
  }, []);

  return (
    <main className="page" id="main-content">
      <header className="masthead">
        <div>
          <p className="eyebrow">AI Doctor Follow-Up Agent</p>
          <h1>Foundation status</h1>
          <p className="subtitle">
            Phase 1 — local environment, API liveness and build metadata. No patient data
            and no clinical functionality is present in this phase.
          </p>
        </div>
        {state.kind === "ready" ? (
          <StatusBadge state={state.data.health.status} />
        ) : null}
      </header>

      <p className="notice" role="note">
        {DEMO_NOTICE}
      </p>

      {state.kind === "loading" ? (
        <div className="card" aria-live="polite" data-testid="loading">
          <h2>Checking local services…</h2>
          <p className="muted">Reading /health and /version from the local API.</p>
        </div>
      ) : null}

      {state.kind === "error" ? (
        <ErrorNotice message={state.message} onRetry={retry} />
      ) : null}

      {state.kind === "ready" ? (
        <StatusPanels data={state.data} onRefresh={retry} />
      ) : null}

      <footer className="footer">
        <p>
          Academic prototype. Local-only, synthetic-data demonstration. Not a medical device
          and not validated for clinical use.
        </p>
      </footer>
    </main>
  );
}

interface StatusPanelsProps {
  readonly data: SystemStatus;
  readonly onRefresh: () => void;
}

function StatusPanels({ data, onRefresh }: StatusPanelsProps) {
  const { health, version } = data;

  return (
    <>
      <section className="card" aria-labelledby="dependencies-heading">
        <div className="card__header">
          <h2 id="dependencies-heading">Dependencies</h2>
          <button type="button" className="button button--ghost" onClick={onRefresh}>
            Refresh
          </button>
        </div>
        <table className="table">
          <caption className="sr-only">
            Dependency state as reported by the local API health endpoint
          </caption>
          <thead>
            <tr>
              <th scope="col">Component</th>
              <th scope="col">State</th>
              <th scope="col">Notes</th>
            </tr>
          </thead>
          <tbody>
            {DEPENDENCIES.map((name) => {
              const value: DependencyState = health[name];
              return (
                <tr key={name}>
                  <th scope="row">{name === "db" ? "Database" : name}</th>
                  <td>
                    <StatusBadge state={value} />
                  </td>
                  <td className="muted">{DEPENDENCY_NOTES[name]}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="card" aria-labelledby="versions-heading">
        <h2 id="versions-heading">Build and contract versions</h2>
        <dl className="definition-list">
          <div>
            <dt>Application</dt>
            <dd>{version.app_version}</dd>
          </div>
          <div>
            <dt>API</dt>
            <dd>{version.api_version}</dd>
          </div>
          <div>
            <dt>Workflow contract</dt>
            <dd>{version.workflow_version}</dd>
          </div>
          <div>
            <dt>Demo policy</dt>
            <dd>{version.policy_version}</dd>
          </div>
          <div>
            <dt>Build SHA</dt>
            <dd>
              <code>{version.git_sha}</code>
            </dd>
          </div>
          <div>
            <dt>Health version</dt>
            <dd>{health.version}</dd>
          </div>
        </dl>
      </section>
    </>
  );
}
