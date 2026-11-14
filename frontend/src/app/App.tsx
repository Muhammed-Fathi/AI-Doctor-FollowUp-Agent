import { HealthPage } from "../pages/HealthPage";

/**
 * Phase 1 application shell.
 *
 * One route, one page: the foundation/health view. Doctor and patient routes
 * arrive in P6 and are intentionally absent here.
 */
export function App() {
  return <HealthPage />;
}
