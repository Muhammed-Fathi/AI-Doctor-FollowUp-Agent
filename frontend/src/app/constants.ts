/** Shared UI copy and contract-derived constants. */

/**
 * Mandatory educational notice (`REQ-SEC-05`). The wording is fixed by the
 * accepted P0 contracts and must not be paraphrased.
 */
export const DEMO_NOTICE = "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE" as const;

export type DependencyState = "ok" | "unavailable" | "not_configured";

/** Human-readable label per dependency state (never a clinical judgement). */
export const DEPENDENCY_LABELS: Record<DependencyState, string> = {
  ok: "OK",
  unavailable: "Unavailable",
  not_configured: "Not configured in Phase 1",
};

/** Explanation shown next to each dependency row. */
export const DEPENDENCY_NOTES: Record<string, string> = {
  db: "Local SQLite application database (SQLAlchemy + Alembic).",
  ollama: "Local model runtime. Wired in P5; not used by this phase.",
  tesseract: "Local OCR engine. Wired in P3; not used by this phase.",
};
